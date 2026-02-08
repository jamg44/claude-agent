"""Calculator tool - performs basic math operations"""

# Tool definition
TOOL_DEFINITION = {
    "name": "calculator",
    "description": "Performs basic math operations. Can add, subtract, multiply and divide two numbers.",
    "input_schema": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["add", "subtract", "multiply", "divide"],
                "description": "The operation to perform"
            },
            "a": {
                "type": "number",
                "description": "First number"
            },
            "b": {
                "type": "number",
                "description": "Second number"
            }
        },
        "required": ["operation", "a", "b"]
    }
}


# Tool executor
def execute(tool_input: dict) -> str:
    """Execute calculator operations"""
    operation = tool_input["operation"]
    a = tool_input["a"]
    b = tool_input["b"]

    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            return "Error: Division by zero"
        result = a / b
    else:
        return f"Unknown operation: {operation}"

    return str(result)