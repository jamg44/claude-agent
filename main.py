import os
from anthropic import Anthropic
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Initialize client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL="claude-sonnet-4-20250514"

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
    },
    {
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

    elif tool_name == "get_weather":
        city = tool_input["city"]
        # Mock - in real life you'd call a weather API
        return json.dumps({
            "city": city,
            "temperature": 22,
            "condition": "Sunny",
            "humidity": 65
        })

    return "Tool not found"

def run_agent(user_message: str):
    print(f"\n🧑 User: {user_message}\n")

    # Message history
    messages = [
        {"role": "user", "content": user_message}
    ]

    # Safety: max iterations to prevent infinite loops
    max_iterations = 3
    iteration = 0

    # Main loop
    while iteration < max_iterations:
        iteration += 1
        print(f"--- Iteration {iteration} ---")

        # Call LLM
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            tools=TOOLS,
            messages=messages
        )

        print(f"Stop reason: {response.stop_reason}")

        if response.stop_reason == "end_turn":
            # LLM finished, extract final text
            final_text = ""
            for block in response.content:
                if block.type == "text":
                    final_text += block.text

            # print(response)
            print(f"\n🤖 LLM: {final_text}\n")
            return  # Exit function instead of break
        elif response.stop_reason == "tool_use":
            # LLM wants to use tools
            # Add LLM's response to history
            messages.append({
                "role": "assistant",
                "content": response.content
            })

            # Execute all requested tools
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    print(f"🔧 Executing tool: {tool_name}")
                    print(f"   Input: {tool_input}")

                    # Execute the tool
                    result = execute_tool(tool_name, tool_input)
                    print(f"   Result: {result}\n")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Add results to history
            messages.append({
                "role": "user",
                "content": tool_results # This can be structured differently based on how you want to pass results back to the LLM
            })

        else:
            print(f"⚠️  Unexpected stop_reason: {response.stop_reason}")
            return  # Exit function

    print(f"⚠️  Max iterations ({max_iterations}) reached. Stopping.")


if __name__ == "__main__":
    # Example 1: Calculator
    run_agent("¿Cuánto es 150 multiplicado por 23?")

    # Example 2: Weather
    run_agent("¿Qué tiempo hace en Madrid?")

    # Example 3: Combined
    run_agent("¿Qué temperatura hace en Barcelona? Y luego suma esa temperatura más 10")