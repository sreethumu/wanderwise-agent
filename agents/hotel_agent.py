# agents/hotel_agent.py

import logging
from google.adk.agents import LlmAgent
from google.adk.tools.function_tool import FunctionTool
from tools.hotel_tools import search_hotels
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
hotel_search_tool = FunctionTool(func=search_hotels)

hotel_agent = LlmAgent(
    name="hotel_agent",
    model="gemini-2.0-flash",
    description="Agent to find hotel accommodations based on user constraints.",
    instruction="""
You are the HOTEL-FINDER AGENT.

You receive a JSON request (in plain text) with the following keys:
- "destination": destination city
- "guests": number of guests
- "budget": budget preference (e.g., "luxury", "mid-range", "budget")
- "preferences": other hotel preferences (e.g., hostel vs hotel, amenities)

Your task:

1) Call the hotel_search_tool with the provided destination.
   Example call format:
   {"tool": "hotel_search_tool", "input": {"city": "Tokyo", "radius_m": 5000, "limit": 10}}

2) From the returned hotel list, select up to 5 candidate hotels.
   - If budget is "budget" or "mid-range", prioritize hotels where "price" field exists and appears reasonable; 
   - If price is missing, you may instead prioritize by "rating" or central location/named city area.

3) For each candidate hotel, return a structured summary in plain text:
   - Name
   - Address
   - Approximate price/range (if provided; otherwise "estimate unavailable")
   - Rating (if available)
   - Short note: e.g. "central location, good reviews" or "price unknown, check manually"

4) If the tool returns an error or no hotels, output: 
   "No suitable hotels found for [destination] with your constraints."

Important rules:
- Do NOT invent prices or availability if not provided.
- Return only plain text.
""",
    tools=[search_hotels],
)
