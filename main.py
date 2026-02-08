import os
from anthropic import Anthropic
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

# Initialize client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def run_agent(user_message: str):
    print(f"\n🧑 User: {user_message}\n")

    # Simple call to Claude (without tools yet)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    # Extract text from response
    final_text = ""
    for block in response.content:
        if block.type == "text":
            final_text += block.text

    print(f"\n🤖 Claude: {final_text}\n")
    print(f"Stop reason: {response.stop_reason}")


if __name__ == "__main__":
    # Example 1: Calculator
    run_agent("¿Cuánto es 150 multiplicado por 23?")

    # # Example 2: Weather
    # run_agent("¿Qué tiempo hace en Madrid?")

    # # Example 3: Combined
    # run_agent("¿Qué temperatura hace en Barcelona? Y luego suma esa temperatura más 10")