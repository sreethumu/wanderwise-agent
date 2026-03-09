# server.py
# Flask backend for WanderWise — connects the web UI to the ADK agent

import os
import asyncio
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import webbrowser

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    print(f"\n🌍 WanderWise server starting on http://localhost:{port}\n")
    webbrowser.open(f"http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)