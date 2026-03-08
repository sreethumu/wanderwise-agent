from agents.hotel_agent import LlmAgent as HotelAgent
from agents.activity_agent import LlmAgent as ActivitiesAgent
from agents.root_travel_agent import LlmAgent as TravelCoordinatorAgent


def test_hotel_agent_output():
    agent = HotelAgent(name="TestHotelAgent")
    assert agent.name == "TestHotelAgent"


def test_activities_agent_output():
    agent = ActivitiesAgent(name="TestActivitiesAgent")
    assert agent.name == "TestActivitiesAgent"


def test_coordinator_agent_routing():
    coordinator = TravelCoordinatorAgent(name="TestCoordinatorAgent")
    assert coordinator.name == "TestCoordinatorAgent"
