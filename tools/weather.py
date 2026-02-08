"""Weather tool - gets current weather for a city (mock)"""
import json

# Tool definition
TOOL_DEFINITION = {
    "name": "get_weather",
    "description": "Gets current weather for a city. Note: this is a mock, returns simulated data.",
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "City name"
            }
        },
        "required": ["city"]
    }
}


# Tool executor
def execute(tool_input: dict) -> str:
    """Get weather for a city (mock)"""
    city = tool_input["city"]
    return json.dumps({
        "city": city,
        "temperature": 22,
        "condition": "Sunny",
        "humidity": 65
    })