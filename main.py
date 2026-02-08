import os
from anthropic import Anthropic
from dotenv import load_dotenv
import json

# Load environment variables from .env file
load_dotenv()

def run_agent(user_message: str):
    print("Hello from claude agent! user message:", user_message)


if __name__ == "__main__":
    # Example 1: Calculator
    run_agent("¿Cuánto es 150 multiplicado por 23?")

    # Example 2: Weather
    run_agent("¿Qué tiempo hace en Madrid?")

    # Example 3: Combined
    run_agent("¿Qué temperatura hace en Barcelona? Y luego suma esa temperatura más 10")