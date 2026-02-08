import os
from anthropic import Anthropic
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Initialize client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Tool definitions
TOOLS = [
    {
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
]

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return the result as string"""

    if tool_name == "calculator":
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

    return "Tool not found"

def run_agent(user_message: str):
    print(f"\n🧑 User: {user_message}\n")

    # Simple call to Claude (without tools yet)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        tools=TOOLS,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    # Extract text from response
    final_text = ""
    for block in response.content:
        if block.type == "text":
            final_text += block.text

    # print(response)

    print(f"\n🤖 Claude: {final_text}\n")
    print(f"Stop reason: {response.stop_reason}")

    # Check if Claude wants to use tools
    if response.stop_reason == "tool_use":
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id

                print(f"🔧 Executing tool: {tool_name}")
                print(f"   Input: {tool_input}")

                # Execute the tool
                result = execute_tool(tool_name=tool_name, tool_input=tool_input)

                print(f"   Result: {result}\n")


if __name__ == "__main__":
    # Example 1: Calculator
    run_agent("¿Cuánto es 150 multiplicado por 23?")

    # # Example 2: Weather
    # run_agent("¿Qué tiempo hace en Madrid?")

    # # Example 3: Combined
    # run_agent("¿Qué temperatura hace en Barcelona? Y luego suma esa temperatura más 10")