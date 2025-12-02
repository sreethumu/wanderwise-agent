# WanderWise - Multi-Agent Travel Planner

## Problem Statement

Planning a trip should feel exciting, but in reality it often feels like a chore. A typical traveler who simply wants “good hotels near the Eiffel Tower” ends up drowning in tabs, switching between hotel sites, map apps, and review pages just to confirm something as basic as distance. The moment they want to find activities as well, the process becomes even more disjointed. There’s no single conversational interface where someone can express what they actually want in natural language—something like:

> “Find me three hotels within five kilometers of the Louvre, and also show me things to do nearby.”

Instead, travelers fight through fragmented platforms and endless lists that were never designed around how people naturally plan trips. The experience becomes time-consuming, mentally draining, and breaks the flow of trip discovery. **I created WanderWise to solve exactly this problem.**

---

## Why Agents?

The travel planning process naturally breaks into several specialized tasks:

- Deciding intent
- Searching for hotels
- Searching for activities
- Retrieving real data from APIs
- Returning clean results

A single monolithic model tends to hallucinate, mis-handle parameters, or blend unrelated tasks together. **Agents**, on the other hand, allow each travel-related task to be handled by a specialist. The system’s coordinator agent can:

- Interpret what the user is asking for
- Determine whether the request is about hotels or activities
- Extract parameters like radius or limit
- Assign the request to the appropriate expert agent

The **Hotel Agent** focuses exclusively on hotel discovery using a real external API, while the **Activities Agent** does the same for attractions and points of interest. This separation:

- Increases reliability
- Reduces hallucination
- Encourages clean modular design
- Mirrors how human teams delegate tasks

The multi-agent architecture allows users to speak naturally while the system quietly handles intent routing, tool calling, and data gathering behind the scenes.

---

## What I Created

**WanderWise** is a three-agent system built with the Google Agent Development Kit (ADK). At the center of the system is the **Travel Coordinator Agent**, which acts as the orchestrator for the entire workflow. It receives the user’s request, interprets the intent, parses the location, and determines whether the user is asking for hotels or activities. It then delegates the request to either the Hotel Agent or the Activities Agent depending on the context.

- **Hotel Agent**: Responsible exclusively for finding hotels. Uses the `search_hotels` tool, which integrates with the **Geoapify Places API** to geocode locations, retrieve hotels within a specified radius, and return structured hotel information including names, addresses, categories, and distances. The agent is strictly guided by its prompt to prevent hallucination and rely only on tool output.

- **Activities Agent**: Focuses on points of interest and things to do. Uses the `search_activities` tool, which calls the **OpenTripMap API** to turn locations into coordinates, search for attractions, and rank them by relevance or importance. Returns clean, structured results without fabricating content.

Together, these agents form a small but highly functional travel team, with the **Coordinator Agent** acting as the manager that routes tasks and combines results into a natural conversational response. The entire architecture reflects modularity, clarity, and real tool-driven capability—no fallback agent, no guesswork, just clean collaboration.

---

## Demo

When interacting with WanderWise, the user can speak naturally and the system handles the complexity behind the scenes. For example:

- **Query**: “Find me three hotels within five kilometers of the Eiffel Tower”  
  **Flow**: Coordinator Agent → Hotel Agent → `search_hotels` (Geoapify) → structured output

- **Query**: “Show me fun things to do near the Louvre”  
  **Flow**: Coordinator Agent → Activities Agent → `search_activities` (Geoapify + OpenTripMap) → structured output

Development involved testing each layer individually—the raw tools, the individual agents, and then the full orchestrated system—to ensure parameter handling, tool calling, and agent routing behaved predictably. The result is a seamless travel experience powered entirely by agents and real APIs.

---

## The Build

WanderWise was built using the **Google Agent Development Kit**, with a focus on:

- Real tool integration
- Structured outputs
- Precise agent boundaries

The system contains three `LlmAgents`:

1. **Travel Coordinator Agent** – interprets queries, routes tasks, aggregates results
2. **Hotel Agent** – uses `search_hotels` (Geoapify) to retrieve hotels
3. **Activities Agent** – uses `search_activities` (Geoapify + OpenTripMap) to retrieve activities

Environment variables are handled through **dotenv** to keep API keys secure. Each tool has clear input schemas that match ADK’s structured function-calling system, ensuring consistent behavior and robust error handling.

Agents have tightly scoped roles to prevent hallucination:

- Coordinator Agent: intent recognition and routing logic only
- Specialist Agents: rely solely on their tools

Development involved iterative testing:

1. Verify raw tool functionality
2. Validate each individual agent with controlled inputs
3. Connect all agents through the orchestrator for end-to-end testing

By the end, the system demonstrated core ADK concepts such as multi-agent routing, tool-driven execution, and API integration in a clean, modular architecture.

---

## If I Had More Time

- Add an **itinerary-building agent** to organize hotel and activity results into a coherent multi-day plan with time estimates
- Integrate a **flight-search agent** for a full travel concierge
- Add **user preference memory** (budget, travel style, accessibility)
- Output **interactive maps** showing hotel and activity locations together

These additions would elevate WanderWise into a deeply personalized, end-to-end trip-planning companion.

---

## Installation

This project was built using **Python 3.11+**.  

### Setup Virtual Environment

```bash
python -m venv venv
# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Set API Keys

Since the .env file has been removed for security, provide your own API keys as environment variables:

Geoapify Places API – hotel and activity data

OpenTripMap API – points of interest, landmarks, attractions
```bash
# macOS/Linux
export GEOAPIFY_API_KEY="your_geoapify_api_key_here"
export OPENTRIPMAP_API_KEY="your_opentripmap_api_key_here"

# Windows
set GEOAPIFY_API_KEY="your_geoapify_api_key_here"
set OPENTRIPMAP_API_KEY="your_opentripmap_api_key_here"
```

Alternatively, store these keys as GitHub Secrets if using GitHub Actions for CI/CD or deployments.

## Running the Agent

All interactions go through run.py:
```bash
python run.py
```

### Example queries:

“Find hotels in Paris within 3 km of the Eiffel Tower.”

“Show me top attractions near Times Square.”

The root agent interprets the query, routes it to the relevant agent, and returns a unified, structured response. The activity_agent uses both Geoapify and OpenTripMap for comprehensive recommendations.

## Sample Run (Full Example)

Below is an example of a full conversation-style input and the type of structured output WanderWise can generate.

### Sample Input

I’m looking for a 7-day cultural vacation in Paris for a couple. We enjoy art museums, historic sites, good food. Prefer boutique hotels, relaxed pace — 2-3 activities a day, some downtime, dinner suggestions, public-transit-friendly

### Sample Output

--- Travel Plan ---
Okay, here is a possible 7-day cultural itinerary for a couple in Paris, focusing on art, history, and food, with a relaxed pace and consideration for public transit:

#### Hotels:
I recommend considering Relais Saint-Sulpice. Its location in the 6th arrondissement is ideal for exploring many cultural sites and enjoying Parisian cafes. Hôtel Plaza Athénée is another good option.

#### Itinerary:

* Day 1: Arrive in Paris, check into your hotel. Stroll through the Latin Quarter, have dinner at a traditional bistro (e.g., Bouillon Chartier - cost estimate unavailable).

* Day 2: Visit the Louvre Museum (cost estimate unavailable), relax in the Tuileries Garden. Dinner in the Marais.

* Day 3: Explore Notre Dame and Île de la Cité, visit Sainte-Chapelle (cost estimate unavailable), dinner with a view of the Eiffel Tower.

* Day 4: Musée d'Orsay (cost estimate unavailable), Montmartre & Sacré-Cœur, dinner in Montmartre.

* Day 5: Day trip to Versailles (cost estimate unavailable), dinner near your hotel.

* Day 6: Centre Pompidou (cost estimate unavailable), lunch at a local café, optional Seine cruise.

* Day 7: Visit Marché des Enfants Rouges, explore Canal Saint-Martin, final dinner in Paris.

#### Notes:

* Paris has excellent public transit; consider a Navigo Easy pass.

* Many museums support online booking.

* Dinner suggestions are general; booking ahead is recommended.

Project Structure
```graphql
wanderwise-agent/
│
├─ agents/                 # All agent modules
│  ├─ __init__.py
│  ├─ root_travel_agent.py # Central orchestrator
│  ├─ hotel_agent.py       # Handles hotel-related queries
│  └─ activity_agent.py    # Handles activity queries, including OpenTripMap
│
├─ tools/                  # API and helper tools
│  ├─ __init__.py
│  ├─ hotel_tools.py       # Geoapify hotel queries
│  └─ activity_tools.py    # Geoapify & OpenTripMap activity queries
│
├─ run.py                  # Entry point to run the system
├─ requirements.txt        # Python dependencies
├─ README.md               # This file
└─ venv/                   # Virtual environment (ignored in Git)
```

## Workflow

The travel query workflow:

Input Query: Users run run.py and type a travel-related question.

Root Agent Orchestration: root_travel_agent parses the query, identifies intent, and decides which agent should handle it.

### Agent Execution:

hotel_agent: Fetches hotel data (location, ratings, availability) via Geoapify

activity_agent: Queries Geoapify and OpenTripMap for points of interest, landmarks, and attractions. Filters and ranks results

Response Aggregation: Root agent collects outputs from sub-agents and assembles a cohesive, readable response

User Output: Structured results are presented in the terminal, making travel planning simple without manually cross-referencing multiple sources

This delegation model ensures each agent focuses on its domain while the root agent maintains control, delivering a reliable and scalable multi-agent travel planning experience.
