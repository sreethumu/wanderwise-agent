# run.py

import os
import asyncio
import logging
from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from agents.root_travel_agent import root_travel_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)-8s | %(name)s | %(message)s",
    force=True,  # Override any existing logging config
)
logger = logging.getLogger(__name__)

load_dotenv()
api1 = os.getenv("GEOAPIFY_API_KEY")
api2 = os.getenv("OPENTRIPMAP_API_KEY")
if not api1 or not api2:
    raise RuntimeError("Please set GEOAPIFY_API_KEY and OPENTRIPMAP_API_KEY in .env")


async def main():
    runner = InMemoryRunner(agent=root_travel_agent)
    print("✅ Travel‑planner ADK runner ready.")
    user_request = input("Enter your travel request: ")
    logger.info(f"📝 User Request: {user_request}")

    events = await runner.run_debug(user_request)

    # Loop through events — find the final response event(s)
    final_texts = []
    for ev in events:
        # is_final_response() identifies final agent responses. :contentReference[oaicite:0]{index=0}
        if ev.is_final_response():
            if ev.content and ev.content.parts:
                for part in ev.content.parts:
                    text = getattr(part, "text", None)
                    if text and text.strip():
                        final_texts.append(text.strip())

    if not final_texts:
        print("⚠️ No final agent response found. Here are all events for debugging:")
        for ev in events:
            print("---- Event:", ev)
    else:
        print("\n--- Travel Plan ---\n")
        for t in final_texts:
            print(t)


if __name__ == "__main__":
    asyncio.run(main())
