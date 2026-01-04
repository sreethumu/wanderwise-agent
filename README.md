# WanderWise - Multi-Agent Travel Planner

## # WanderWise - Multi-Agent Travel Planner

## Problem Statement

Planning travel is frustratingly time-consuming because users must manually search for hotels, discover local attractions, and cross-reference dozens of sites just to answer basic questions like “Where should I stay?” or “What is there to do nearby?” Hotel listings rarely provide meaningful context about surrounding activities, while activity websites often lack important logistical details such as distance, neighborhood safety, or availability. This fragmentation forces travelers to juggle tabs, compare inconsistent descriptions, and interpret unstructured information without guidance. As travel expectations grow and destinations become more complex, this manual research approach becomes overwhelming and inefficient. Travelers need a system capable of gathering verified information quickly, analyzing it intelligently, and presenting it in a cohesive format that removes the burden of piecing everything together themselves.

Solution Statement

A multi-agent travel planner solves this challenge by dividing the problem into specialized reasoning units that work together under a centralized orchestrator. Instead of requiring the user to manually check travel sites or parse raw API responses, the system delegates hotel-related queries to a dedicated hotel agent and activity-related queries to an activities agent. These specialized agents retrieve real data from the Geoapify Places API, analyze relevance, filter noise, and return structured insights that reflect the user’s intent. The orchestrator coordinates the agents, interpreting the user’s question, deciding which agent should handle it, and assembling the final answer. The result is a streamlined, intelligent planning workflow where users simply ask travel questions and receive clear, well-structured recommendations backed by real data.

Architecture

The core of this system is the travel_planner_agent, a centralized orchestrator built with Google’s Agent Development Kit. It defines the system’s reasoning style, instruction set, and behavioral expectations. When a user makes a request, the orchestrator interprets the intent and routes the query to the appropriate sub-agent. It does not retrieve hotels or activities directly; instead, it manages the workflow between the hotel_agent and activities_agent, ensuring that each part of the user’s request is handled by the agent designed to process it. After receiving results, the orchestrator formats the information into a coherent narrative that feels unified rather than stitched together.

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

This project was built on Python 3.11+. A virtual environment is recommended. After activating it, install dependencies with:

pip install -r requirements.txt

Running the Agent in ADK Web Mode

To launch the web interface for interactive testing:

adk web

To run automated tests:

python -m tests.test_agent

Project Structure

The travel_planner_agent is the root orchestrator and lives in travel_planner_agent.py. Sub-agents are located in the sub_agents directory, including hotel_agent.py and activities_agent.py. All external API interactions occur within the tools directory, where hotel_tools.py and activities_tools.py define the functions used by the agents. The config.py file specifies model and agent configurations, and the tests directory contains integration tests for verifying system behavior.

Workflow

The travel query workflow:

Input Query: Users run run.py and type a travel-related question.

Root Agent Orchestration: root_travel_agent parses the query, identifies intent, and decides which agent should handle it.

### Agent Execution:

hotel_agent: Fetches hotel data (location, ratings, availability) via Geoapify

activity_agent: Queries Geoapify and OpenTripMap for points of interest, landmarks, and attractions. Filters and ranks results

Response Aggregation: Root agent collects outputs from sub-agents and assembles a cohesive, readable response

User Output: Structured results are presented in the terminal, making travel planning simple without manually cross-referencing multiple sources

This delegation model ensures each agent focuses on its domain while the root agent maintains control, delivering a reliable and scalable multi-agent travel planning experience.

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

- Day 1: Arrive in Paris, check into your hotel. Stroll through the Latin Quarter, have dinner at a traditional bistro (e.g., Bouillon Chartier - cost estimate unavailable).

- Day 2: Visit the Louvre Museum (cost estimate unavailable), relax in the Tuileries Garden. Dinner in the Marais.

- Day 3: Explore Notre Dame and Île de la Cité, visit Sainte-Chapelle (cost estimate unavailable), dinner with a view of the Eiffel Tower.

- Day 4: Musée d'Orsay (cost estimate unavailable), Montmartre & Sacré-Cœur, dinner in Montmartre.

- Day 5: Day trip to Versailles (cost estimate unavailable), dinner near your hotel.

- Day 6: Centre Pompidou (cost estimate unavailable), lunch at a local café, optional Seine cruise.

- Day 7: Visit Marché des Enfants Rouges, explore Canal Saint-Martin, final dinner in Paris.

#### Notes:

- Paris has excellent public transit; consider a Navigo Easy pass.

- Many museums support online booking.

- Dinner suggestions are general; booking ahead is recommended.
