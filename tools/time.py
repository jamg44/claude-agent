"""Time tool - returns current time"""
from datetime import datetime

TOOL_DEFINITION = {
    "name": "get_time",
    "description": "Returns the current date and time",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

def execute(tool_input: dict) -> str:
    """Get current time"""
    now = datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")