# agents/activity_agent.py

from google.adk.agents import LlmAgent
from google.adk.tools.function_tool import FunctionTool
from tools.activity_tools import search_activities
from dotenv import load_dotenv

load_dotenv()
activity_search_tool = FunctionTool(func=search_activities)

activity_agent = LlmAgent(
    name="activity_agent",
    model="gemini-2.5-flash",
    description="Agent to find activities / POIs based on user trip preferences.",
    instruction="""
You are the ACTIVITY / POI AGENT.

You receive a JSON request (in plain text) with the following keys:
- "destination": destination city (pass this as "city" to the tool)
- "interests": list of interests or activity types (e.g., museums, culture; pass as "kinds" comma-separated string to the tool)
- "radius": optional travel radius in km (pass as "radius_m" in meters, e.g. 5000 for 5 km)

Your task:

1) **Call the activity_search_tool** with the correct parameter names: city, kinds (optional), radius_m (optional, default 5000), limit (optional, default 10).
   - Example tool call format:
     {"tool": "activity_search_tool", "input": {"city": "Tokyo", "kinds": "cultural,museums", "radius_m": 5000, "limit": 10}}
   - Map destination -> city, interests -> kinds (comma-separated string), radius in km -> radius_m (meters).

2) From the returned list of activities, select **up to 8–12 items** that best match the interests.  
   - If no interests are provided, select popular or highly-rated activities for the destination.

3) For each selected activity, return a **structured summary in plain text**, including:
   - Name  
   - Kind / category  
   - Short note (if available; if missing, write "information unavailable")  
   - Approximate location or coordinates (lat/lon; if missing, write "information unavailable")

4) If the tool returns an error or no activities are found, output:  
   `"No suitable activities found for [destination] with given preferences."`

**Important rules:**
- Do NOT invent activity details or locations.  
- Return only plain text, suitable for inclusion in a travel itinerary.  
- Ensure uniform formatting for all activities, even if some data is unavailable.
""",
    tools=[activity_search_tool],
)
