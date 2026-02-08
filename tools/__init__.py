"""Tool registry - imports and registers all available tools"""
from . import calculator
from . import weather

# Auto-build tool definitions list
TOOL_DEFINITIONS = [
    calculator.TOOL_DEFINITION,
    weather.TOOL_DEFINITION
]

# Auto-build tool executors registry
TOOL_EXECUTORS = {
    "calculator": calculator.execute,
    "get_weather": weather.execute
}