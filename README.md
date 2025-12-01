Problem Statement

Planning travel is frustratingly time-consuming because users must manually search for hotels, discover local attractions, and cross-reference dozens of sites just to answer basic questions like “Where should I stay?” or “What is there to do nearby?” Hotel listings rarely provide meaningful context about surrounding activities, while activity websites often lack important logistical details such as distance, neighborhood safety, or availability. This fragmentation forces travelers to juggle tabs, compare inconsistent descriptions, and interpret unstructured information without guidance. As travel expectations grow and destinations become more complex, this manual research approach becomes overwhelming and inefficient. Travelers need a system capable of gathering verified information quickly, analyzing it intelligently, and presenting it in a cohesive format that removes the burden of piecing everything together themselves.

Solution Statement

A multi-agent travel planner solves this challenge by dividing the problem into specialized reasoning units that work together under a centralized orchestrator. Instead of requiring the user to manually check travel sites or parse raw API responses, the system delegates hotel-related queries to a dedicated hotel agent and activity-related queries to an activities agent. These specialized agents retrieve real data from the Geoapify Places API, analyze relevance, filter noise, and return structured insights that reflect the user’s intent. The orchestrator coordinates the agents, interpreting the user’s question, deciding which agent should handle it, and assembling the final answer. The result is a streamlined, intelligent planning workflow where users simply ask travel questions and receive clear, well-structured recommendations backed by real data.

Architecture

The core of this system is the travel_planner_agent, a centralized orchestrator built with Google’s Agent Development Kit. It defines the system’s reasoning style, instruction set, and behavioral expectations. When a user makes a request, the orchestrator interprets the intent and routes the query to the appropriate sub-agent. It does not retrieve hotels or activities directly; instead, it manages the workflow between the hotel_agent and activities_agent, ensuring that each part of the user’s request is handled by the agent designed to process it. After receiving results, the orchestrator formats the information into a coherent narrative that feels unified rather than stitched together.

The hotel_agent specializes in hotel discovery. It interprets user prompts involving accommodations and calls the custom search_hotels tool, which integrates with Geoapify’s Places API. After retrieving the data, it filters out incomplete or irrelevant results, processes key attributes, and organizes them into a structured response.

The activities_agent performs an analogous role for points of interest and things to do. Whenever a user asks about attractions, experiences, or local activities, this agent calls the search_activities tool. It processes the results, ranks them based on relevance, and generates a summary suitable for the orchestrator to incorporate into the final output.

Together, these three agents form a modular, extensible architecture: one planner at the top and two domain experts beneath it. Because each agent has a clear role and narrow focus, the system remains organized, reliable, and easy to expand.

Hotel Agent: hotel_agent

The hotel_agent is a purpose-built specialist for handling all accommodation-related requests. When invoked by the orchestrator, it extracts the key details from the user’s prompt—such as destination, radius, and desired number of results—and forwards these parameters to the search_hotels tool. This tool communicates with the Geoapify Places API and returns structured hotel data. The agent then evaluates and formats the results, ensuring they are readable, relevant, and aligned with the user’s needs. Its responsibility is not only to gather data but to interpret it, producing a clean, user-friendly summary of available hotel options.

Activities Agent: activities_agent

The activities_agent focuses exclusively on analyzing attractions and things to do around a target location. Using the search_activities tool, it queries the Geoapify API for points of interest within a chosen radius. After receiving raw results, the agent filters them, removes duplicates or low-signal entries, and organizes the remaining activities into a meaningful and digestible presentation. This agent brings clarity to an otherwise overwhelming amount of location data, allowing users to get a quick understanding of what makes the destination interesting or worthwhile.

Essential Tools and Utilities

The search_hotels tool is the system’s external data engine for hotel discovery. It constructs a Geoapify Places API request, handles authentication through environment variables, builds the query URL, and parses the returned JSON. It also cleans response data by extracting name, coordinates, address, and other essential attributes. This tool transforms raw API responses into structured datasets that the hotel_agent can reason over.

The search_activities tool performs the same essential function for attractions and points of interest. It interacts with the Geoapify Places API, retrieves activity data, normalizes the fields, and returns it in a consistent structure. These tools elevate the agents from purely reasoning systems into data-driven assistants capable of working with real-world travel information.

Conclusion

This multi-agent travel system is a clear demonstration of how specialization and orchestration can simplify complex user workflows. By dividing responsibilities between a planner and two domain-expert agents, the system produces recommendations that are reliable, structured, and grounded in real data. The orchestrator ensures all information flows smoothly, while each sub-agent brings focused expertise to its domain. The architecture is both robust and flexible, allowing future extensions such as restaurant search, trip budgeting, automated itinerary generation, or neighborhood-level safety scoring—all fitting naturally into the existing agent hierarchy. For travelers, this results in a faster, more organized planning experience that avoids the chaos of manual searching.

Value Statement

This system dramatically reduces the amount of effort required to plan trips by automating hotel and activity discovery with real API-backed data. Users receive consistent, structured answers that would normally require several manual searches, multiple comparison steps, and interpretation of unstructured online content. If more development time were available, expanding the system with a transportation analysis agent or a restaurant discovery agent would further enhance its usefulness and bring additional domains under the same unified planning workflow.

Installation

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

The workflow begins when a user submits a travel query. The travel_planner_agent analyzes the intent and delegates it to either the hotel_agent or activities_agent. The chosen agent performs the necessary external search through its associated tool, processes and filters the results, and returns structured information. The orchestrator then collects the output, integrates it into a coherent response, and presents it to the user. This clean delegation pattern ensures each component performs exactly the task it’s designed for, producing a highly organized multi-agent travel planning experience.
