# server.py
# Flask backend for WanderWise — connects the web UI to the ADK agent

import os
import asyncio
import io
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)  # Allow requests from the frontend

# ── Import your WanderWise agent ──
from agents.root_travel_agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

# Session service — keeps conversation history per user session
session_service = InMemorySessionService()

APP_NAME = "wanderwise"


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
        locations = {"hotels": [], "activities": []}

        async for event in runner.run_async(
            user_id=session_id, session_id=session_id, new_message=content,
        ):
            # Debug: print every event type to terminal so we can see what's coming through
            try:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # Direct function_response on a part
                        if hasattr(part, 'function_response') and part.function_response:
                            try:
                                resp = part.function_response.response
                                _extract_locations(resp, locations)
                            except Exception:
                                pass

                        # Some ADK versions wrap it differently
                        if hasattr(part, 'text') and part.text:
                            pass  # text parts are handled below

                # Also check event-level tool responses (sub-agent results)
                if hasattr(event, 'tool_response') and event.tool_response:
                    try:
                        _extract_locations(event.tool_response, locations)
                    except Exception:
                        pass

                # Check actions for any function responses
                if hasattr(event, 'actions') and event.actions:
                    for action in event.actions:
                        if hasattr(action, 'function_response') and action.function_response:
                            try:
                                _extract_locations(action.function_response.response, locations)
                            except Exception:
                                pass

            except Exception as e:
                print(f"[DEBUG] Event parse error: {e}")

            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = "".join(
                        p.text for p in event.content.parts if hasattr(p, "text") and p.text
                    )

        print(f"[DEBUG] Final locations: hotels={len(locations['hotels'])}, activities={len(locations['activities'])}")

        # Fallback: if agent responded but no locations extracted,
        # try calling the tools directly based on what city the user mentioned
        if not locations["hotels"] and not locations["activities"] and final_response:
            locations = _try_direct_tool_call(user_message)

        return final_response or "I wasn't able to generate a response. Please try again.", locations

    return asyncio.run(_run())


def _extract_locations(resp, locations):
    """Helper to pull hotels/activities out of a tool response dict."""
    if not isinstance(resp, dict):
        return
    if resp.get("status") == "success":
        if "hotels" in resp:
            for h in resp["hotels"]:
                if isinstance(h, dict) and h.get("lat") and h.get("lon"):
                    locations["hotels"].append(h)
        if "activities" in resp:
            for a in resp["activities"]:
                if isinstance(a, dict) and a.get("lat") and a.get("lon"):
                    locations["activities"].append(a)


def _try_direct_tool_call(user_message: str) -> dict:
    """
    Fallback: if the agent didn't surface tool results through events,
    call search_hotels and search_activities directly using the city
    mentioned in the user message.
    """
    from tools.activity_tools import search_activities, geocode_city
    from tools.hotel_tools import search_hotels
    import re

    locations = {"hotels": [], "activities": []}

    # Simple city extraction — look for common patterns
    city_match = re.search(
        r'\b(?:to|in|visit|trip to|going to|travel to)\s+([A-Z][a-zA-Z\s]+?)(?:\.|,|\?|!|$|\s+for|\s+next|\s+with)',
        user_message
    )
    if not city_match:
        return locations

    city = city_match.group(1).strip()
    print(f"[DEBUG] Fallback direct tool call for city: {city}")

    try:
        hotel_result = search_hotels(city, limit=5)
        if hotel_result.get("status") == "success":
            locations["hotels"] = [
                h for h in hotel_result["hotels"] if h.get("lat") and h.get("lon")
            ]
    except Exception as e:
        print(f"[DEBUG] Fallback hotel search failed: {e}")

    try:
        activity_result = search_activities(city, limit=15)
        if activity_result.get("status") == "success":
            locations["activities"] = [
                a for a in activity_result["activities"] if a.get("lat") and a.get("lon")
            ]
    except Exception as e:
        print(f"[DEBUG] Fallback activity search failed: {e}")

    return locations


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
        import re
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
    import google.generativeai as genai

    data = request.get_json()
    if not data or "reply" not in data:
        return jsonify({"suggestions": []}), 400

    ai_reply = data.get("reply", "")[:600]
    user_message = data.get("user_message", "")

    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-2.0-flash")

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

        response = model.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()

        import json
        suggestions = json.loads(raw)
        if not isinstance(suggestions, list):
            raise ValueError("Not a list")

        return jsonify({"suggestions": suggestions[:4]})

    except Exception as e:
        print(f"[ERROR] Suggestions failed: {e}")
        # Fallback hardcoded suggestions
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