# server.py
# Flask backend for WanderWise — connects the web UI to the ADK agent

import os
import asyncio
import io
import json
import re
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)  # Allow requests from the frontend

# ── Import agents ──
from agents.root_travel_agent import root_agent
from agents.map_agent import map_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

# Session service — keeps conversation history per user session
session_service = InMemorySessionService()

APP_NAME = "wanderwise"


async def _run_map_agent(itinerary_text: str) -> dict:
    """
    Run the map agent on an itinerary reply.
    Uses a fresh isolated session — never touches the user's conversation history.
    Returns locations dict with hotels and day-tagged activities.
    """
    map_sess = InMemorySessionService()
    session_id = "map_session"

    await map_sess.create_session(
        app_name=APP_NAME, user_id=session_id, session_id=session_id,
    )

    runner = Runner(agent=map_agent, app_name=APP_NAME, session_service=map_sess)
    content = genai_types.Content(
        role="user", parts=[genai_types.Part(text=itinerary_text)],
    )

    map_reply = ""
    async for event in runner.run_async(
        user_id=session_id, session_id=session_id, new_message=content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                map_reply = "".join(
                    p.text for p in event.content.parts if hasattr(p, "text") and p.text
                )

    print(f"[DEBUG] Map agent raw output: {map_reply[:300] if map_reply else 'empty'}")

    locations = {"hotels": [], "activities": []}
    if not map_reply:
        return locations

    try:
        clean = map_reply.strip()
        clean = re.sub(r'^```(?:json)?\s*', '', clean)
        clean = re.sub(r'\s*```$', '', clean)
        parsed = json.loads(clean)

        for h in parsed.get("hotels", []):
            if h.get("lat") and h.get("lon") and h.get("name"):
                locations["hotels"].append({
                    "name": h["name"],
                    "lat": h["lat"],
                    "lon": h["lon"],
                    "address": h.get("address", ""),
                    "description": h.get("description", ""),
                })

        for a in parsed.get("activities", []):
            if a.get("lat") and a.get("lon") and a.get("name"):
                locations["activities"].append({
                    "name": a["name"],
                    "lat": a["lat"],
                    "lon": a["lon"],
                    "address": a.get("address", ""),
                    "day": a.get("day"),
                    "description": a.get("description", ""),
                })

        print(f"[DEBUG] Map agent parsed: hotels={len(locations['hotels'])}, activities={len(locations['activities'])}")

    except Exception as e:
        print(f"[DEBUG] Map agent JSON parse error: {e}")
        print(f"[DEBUG] Raw map output was: {map_reply}")

    return locations


def run_agent(session_id: str, user_message: str):
    """
    Run the WanderWise ADK agent for a given session and user message.
    Returns (reply_text, locations_dict) where locations has hotels and activities.
    """
    async def _run():
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=session_id, session_id=session_id,
        )
        if session is None:
            session = await session_service.create_session(
                app_name=APP_NAME, user_id=session_id, session_id=session_id,
            )

        runner = Runner(
            agent=root_agent, app_name=APP_NAME, session_service=session_service,
        )

        content = genai_types.Content(
            role="user", parts=[genai_types.Part(text=user_message)],
        )

        final_response = ""

        async for event in runner.run_async(
            user_id=session_id, session_id=session_id, new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = "".join(
                        p.text for p in event.content.parts if hasattr(p, "text") and p.text
                    )

        if not final_response:
            return "I wasn't able to generate a response. Please try again.", {"hotels": [], "activities": []}

        print(f"[DEBUG] Root agent reply length: {len(final_response)} chars")

        # Run map agent on every response to extract geocoded locations with day tags
        locations = await _run_map_agent(final_response)

        return final_response, locations

    return asyncio.run(_run())


# ── Routes ──

@app.route("/")
def index():
    """Serve the main web UI."""
    return app.send_static_file("index.html")


@app.route("/api/config", methods=["GET"])
def config():
    """
    Safely expose only the Google Maps API key to the frontend.
    Never expose Gemini or Places keys here.
    """
    return jsonify({
        "google_maps_key": os.getenv("GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_PLACES_API_KEY", "")
    })


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Expects JSON: { "message": str, "session_id": str }
    Returns JSON: { "reply": str, "locations": { "hotels": [...], "activities": [...] } }
    """
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' in request body"}), 400

    user_message = data.get("message", "").strip()
    session_id = data.get("session_id", "default-session")

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    try:
        reply, locations = run_agent(session_id, user_message)
        return jsonify({"reply": reply, "locations": locations})
    except Exception as e:
        print(f"[ERROR] Agent failed: {e}")
        return jsonify({"error": "The agent encountered an error. Please try again."}), 500


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "agent": "root_travel_agent"})


@app.route("/api/reset", methods=["POST"])
def reset():
    """
    Reset a session (clear conversation history).
    Expects JSON: { "session_id": str }
    """
    data = request.get_json()
    session_id = data.get("session_id", "default-session")

    async def _reset():
        await session_service.delete_session(
            app_name=APP_NAME,
            user_id=session_id,
            session_id=session_id,
        )

    try:
        asyncio.run(_reset())
        return jsonify({"status": "session reset"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export", methods=["POST"])
def export_pdf():
    """
    Generate a PDF of the latest itinerary.
    Expects JSON: { "content": str, "title": str }
    Returns: PDF file download
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    data = request.get_json()
    if not data or "content" not in data:
        return jsonify({"error": "Missing content"}), 400

    raw_content = data.get("content", "")
    title = data.get("title", "My WanderWise Itinerary")

    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm, leftMargin=20*mm,
            topMargin=20*mm, bottomMargin=20*mm
        )

        # ── Styles ──
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'WTitle', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=22,
            textColor=colors.HexColor('#1a1612'),
            spaceAfter=4, alignment=TA_CENTER
        )
        subtitle_style = ParagraphStyle(
            'WSubtitle', parent=styles['Normal'],
            fontName='Helvetica', fontSize=10,
            textColor=colors.HexColor('#7a7268'),
            spaceAfter=16, alignment=TA_CENTER
        )
        section_style = ParagraphStyle(
            'WSection', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=12,
            textColor=colors.HexColor('#c4633a'),
            spaceBefore=14, spaceAfter=4,
        )
        day_style = ParagraphStyle(
            'WDay', parent=styles['Normal'],
            fontName='Helvetica-Bold', fontSize=10,
            textColor=colors.HexColor('#c9a84c'),
            spaceBefore=10, spaceAfter=3,
            leftIndent=0,
        )
        body_style = ParagraphStyle(
            'WBody', parent=styles['Normal'],
            fontName='Helvetica', fontSize=10,
            textColor=colors.HexColor('#1a1612'),
            spaceAfter=4, leading=15,
        )
        bullet_style = ParagraphStyle(
            'WBullet', parent=styles['Normal'],
            fontName='Helvetica', fontSize=10,
            textColor=colors.HexColor('#1a1612'),
            spaceAfter=3, leading=14,
            leftIndent=12, bulletIndent=0,
        )
        footer_style = ParagraphStyle(
            'WFooter', parent=styles['Normal'],
            fontName='Helvetica', fontSize=8,
            textColor=colors.HexColor('#7a7268'),
            alignment=TA_CENTER, spaceBefore=20,
        )

        story = []

        # ── Header ──
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("✦ WanderWise", title_style))
        story.append(Paragraph(title, subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0d8cc'), spaceAfter=12))

        # ── Parse and render content ──
        lines = raw_content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                story.append(Spacer(1, 3*mm))
                continue

            # Strip markdown bold
            line_clean = re.sub(r'\*\*(.*?)\*\*', r'\1', line)
            line_clean = re.sub(r'\*(.*?)\*', r'\1', line_clean)

            # Day headers
            if re.match(r'^Day\s+\d+', line_clean, re.IGNORECASE):
                story.append(Paragraph(line_clean, day_style))
                continue

            # Section headers (ends with colon, short line)
            if line_clean.endswith(':') and len(line_clean) < 60 and not line_clean.startswith('*'):
                story.append(Paragraph(line_clean, section_style))
                continue

            # Bullet points
            if line_clean.startswith('*') or line_clean.startswith('-'):
                item = re.sub(r'^[\*\-]\s*', '', line_clean)
                story.append(Paragraph(f"• {item}", bullet_style))
                continue

            # Normal text
            story.append(Paragraph(line_clean, body_style))

        # ── Footer ──
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0d8cc'), spaceBefore=16))
        story.append(Paragraph(
            f"Generated by WanderWise AI · {datetime.now().strftime('%B %d, %Y')}",
            footer_style
        ))

        doc.build(story)
        buffer.seek(0)

        safe_title = re.sub(r'[^a-zA-Z0-9\s]', '', title).strip().replace(' ', '_')[:40]
        filename = f"WanderWise_{safe_title}.pdf"

        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        print(f"[ERROR] PDF export failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/suggestions", methods=["POST"])
def get_suggestions():
    """
    Generate 4 follow-up suggestions using Gemini based on the latest AI reply.
    Expects JSON: { "reply": str, "user_message": str }
    Returns: { "suggestions": [str, str, str, str] }
    """
    data = request.get_json()
    if not data or "reply" not in data:
        return jsonify({"suggestions": []}), 400

    ai_reply = data.get("reply", "")[:600]
    user_message = data.get("user_message", "")

    try:
        from google import genai as google_genai
        client = google_genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        prompt = f"""The user asked a travel question and got a travel plan back.

User asked: "{user_message}"
AI responded with: {ai_reply}

Generate exactly 4 short follow-up suggestions the user might want to ask next.
Rules:
- Return ONLY a JSON array of 4 strings, nothing else, no markdown
- Each string must be under 60 characters
- Make them varied: mix modifications, additions, and questions
- Make them specific to this exact trip
- Examples: "Add a day trip to Kyoto", "Switch to luxury hotels", "What's the best time to visit?", "Add more food experiences"
"""

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()

        suggestions = json.loads(raw)
        if not isinstance(suggestions, list):
            raise ValueError("Not a list")

        return jsonify({"suggestions": suggestions[:4]})

    except Exception as e:
        print(f"[ERROR] Suggestions failed: {e}")
        return jsonify({"suggestions": [
            "Add more restaurant recommendations",
            "Switch to a different budget tier",
            "Extend the trip by 2 days",
            "What's the best time of year to visit?"
        ]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    print(f"\n🌍 WanderWise server starting on http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)