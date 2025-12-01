import pytest
from unittest.mock import patch
import tools.hotel_tools as hotel_tools


@patch.object(hotel_tools, "geocode_city")
@patch.object(hotel_tools, "search_hotels")
def test_search_hotels_basic(mock_search, mock_geocode):
    mock_geocode.return_value = {"lat": 48.8566, "lon": 2.3522}  # Paris coordinates
    mock_search.return_value = {"hotels": [{"name": "Test Hotel"}], "status": "success"}
    result = hotel_tools.search_hotels("Paris", radius_m=5)
    assert "hotels" in result
    assert isinstance(result["hotels"], list)
    assert result["hotels"][0]["name"] == "Test Hotel"


@patch.object(hotel_tools, "geocode_city")
@patch.object(hotel_tools, "search_hotels")
def test_search_hotels_empty(mock_search, mock_geocode):
    mock_geocode.return_value = {"lat": 0, "lon": 0}
    mock_search.return_value = {"hotels": [], "status": "success"}
    result = hotel_tools.search_hotels("", radius_m=5)
    assert "hotels" in result
    assert result["hotels"] == []
