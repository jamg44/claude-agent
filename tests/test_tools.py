"""Unit tests for tools - no LLM calls, no token usage"""
import json
from tools import TOOL_EXECUTORS, TOOL_DEFINITIONS


def test_calculator_multiply():
    """Test calculator multiplication"""
    result = TOOL_EXECUTORS["calculator"]({
        "operation": "multiply",
        "a": 150,
        "b": 23
    })
    assert result == "3450"


def test_calculator_divide():
    """Test calculator division"""
    result = TOOL_EXECUTORS["calculator"]({
        "operation": "divide",
        "a": 100,
        "b": 4
    })
    assert result == "25.0"


def test_calculator_divide_by_zero():
    """Test calculator division by zero"""
    result = TOOL_EXECUTORS["calculator"]({
        "operation": "divide",
        "a": 10,
        "b": 0
    })
    assert "Error" in result


def test_weather():
    """Test weather tool"""
    result = TOOL_EXECUTORS["get_weather"]({"city": "Madrid"})
    data = json.loads(result)
    assert data["city"] == "Madrid"
    assert "temperature" in data
    assert "condition" in data


def test_time():
    """Test time tool"""
    result = TOOL_EXECUTORS["get_time"]({})
    # Just check it returns a date string format
    assert len(result) > 10
    assert "-" in result
    assert ":" in result


def test_all_tools_registered():
    """Verify all tools are properly registered"""
    assert len(TOOL_DEFINITIONS) == len(TOOL_EXECUTORS)

    for tool_def in TOOL_DEFINITIONS:
        tool_name = tool_def["name"]
        assert tool_name in TOOL_EXECUTORS, f"Tool {tool_name} missing executor"


def test_tool_definitions_valid():
    """Verify all tool definitions have required fields"""
    for tool_def in TOOL_DEFINITIONS:
        assert "name" in tool_def
        assert "description" in tool_def
        assert "input_schema" in tool_def