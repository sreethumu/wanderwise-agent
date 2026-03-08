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


def run_agent(session_id: str, user_message: str) -> str:
    """
    Run the WanderWise ADK agent for a given session and user message.
    Returns the agent's text response.
    """
    async def _run():
        # Create session if it doesn't exist yet
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=session_id,
            session_id=session_id,
        )
        if session is None:
            session = await session_service.create_session(
                app_name=APP_NAME,
                user_id=session_id,
                session_id=session_id,
            )

        runner = Runner(
            agent=root_agent,
            app_name=APP_NAME,
            session_service=session_service,
        )

        content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)],
        )

        final_response = ""
        async for event in runner.run_async(
            user_id=session_id,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response = "".join(
                        p.text for p in event.content.parts if hasattr(p, "text")
                    )

        return final_response or "I wasn't able to generate a response. Please try again."

    return asyncio.run(_run())


# ── Routes ──

@app.route("/")
def index():
    """Serve the main web UI."""
    return app.send_static_file("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Main chat endpoint.
    Expects JSON: { "message": str, "session_id": str }
    Returns JSON: { "reply": str } or { "error": str }
    """
    data = request.get_json()

    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' in request body"}), 400

    user_message = data.get("message", "").strip()
    session_id = data.get("session_id", "default-session")

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    try:
        reply = run_agent(session_id, user_message)
        return jsonify({"reply": reply})
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