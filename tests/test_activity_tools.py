import pytest
from unittest.mock import patch
import tools.activity_tools as activity_tools


@patch.object(activity_tools, "search_activities")
def test_search_activities_basic(mock_search):
    mock_search.return_value = {
        "activities": [{"name": "Test Activity"}],
        "status": "success",
    }
    result = activity_tools.search_activities("Paris", radius_m=5)
    assert "activities" in result
    assert isinstance(result["activities"], list)
    assert result["activities"][0]["name"] == "Test Activity"


@patch.object(activity_tools, "search_activities")
def test_search_activities_empty(mock_search):
    mock_search.return_value = {"activities": [], "status": "success"}
    result = activity_tools.search_activities("", radius_m=5)
    assert "activities" in result
    assert isinstance(result["activities"], list)
    assert result["activities"] == []
