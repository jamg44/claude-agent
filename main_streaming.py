import os
from anthropic import Anthropic
from dotenv import load_dotenv
import json
from tools import TOOL_DEFINITIONS, TOOL_EXECUTORS

# Load environment variables from .env file
load_dotenv()

# Initialize client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL="claude-sonnet-4-20250514"

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool by name using the registry"""
    executor = TOOL_EXECUTORS.get(tool_name)

    if executor:
        return executor(tool_input)

    return f"Tool not found: {tool_name}"

def run_agent_streaming(user_message: str, system_prompt: str = None):
    """Execute the agent with streaming responses

    Args:
        user_message: The user's question/request
        system_prompt: Optional system prompt to control agent behavior
    """
    print(f"\n🧑 User: {user_message}\n")

    # Message history
    messages = [
        {"role": "user", "content": user_message}
    ]

    # Safety: max iterations to prevent infinite loops
    max_iterations = 10
    iteration = 0

    # Main loop
    while iteration < max_iterations:
        iteration += 1
        print(f"--- Iteration {iteration} ---")

        request_params = {
            "model": MODEL,
            "max_tokens": 1024,
            "tools": TOOL_DEFINITIONS,
            "messages": messages
        }

        # Add system prompt if provided
        if system_prompt:
            request_params["system"] = system_prompt

        # Use streaming
        accumulated_text = ""
        tool_uses = []

        with client.messages.stream(**request_params) as stream:
            for event in stream:
                # Text delta - print as it arrives
                if event.type == "content_block_delta":
                    if hasattr(event.delta, 'text'):
                        print(event.delta.text, end='', flush=True)
                        accumulated_text += event.delta.text

                # Tool use block started
                elif event.type == "content_block_start":
                    if hasattr(event.content_block, 'type') and event.content_block.type == "tool_use":
                        tool_uses.append({
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input": {}
                        })

                # Tool input delta
                elif event.type == "content_block_delta":
                    if hasattr(event.delta, 'partial_json'):
                        # Accumulate tool input (comes in chunks)
                        if tool_uses:
                            # This is tricky - we'll handle it simpler
                            pass

            # Get final message
            response = stream.get_final_message()

        print()  # New line after streaming
        print(f"Stop reason: {response.stop_reason}")

        if response.stop_reason == "end_turn":
            print(f"\n✅ Agent completed\n")
            return

            # print(response)
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

                    print(f"\n🔧 Executing tool: {tool_name}")
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
                "content": tool_results
            })

        else:
            print(f"⚠️  Unexpected stop_reason: {response.stop_reason}")
            return  # Exit function

    print(f"⚠️  Max iterations ({max_iterations}) reached. Stopping.")

if __name__ == "__main__":
    print("=" * 80)
    print("STREAMING DEMO")
    print("=" * 80)

    educational_prompt = """You are an educational assistant.
Always explain your reasoning step-by-step.
When using tools, explain why you're using them."""

    run_agent_streaming(
        "¿Qué temperatura hace en Barcelona? Y luego suma esa temperatura más 10",
        system_prompt=educational_prompt
    )