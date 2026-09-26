from langchain.tools import tool
from langchain.agents import create_agent
from deepagents.middleware.subagents import SubAgentMiddleware
from dotenv import load_dotenv
load_dotenv()

@tool
def get_weather(city: str) -> str:
    """Get the weather in a city."""
    return f"The weather in {city} is sunny."

agent = create_agent(
    model="google_genai:gemini-3-pro-preview",
    middleware=[
        SubAgentMiddleware(
            default_model="",
            default_tools=[],
            subagents=[
                {
                    "name": "weather",
                    "description": "This subagent can get weather in cities.",
                    "system_prompt": "Use the get_weather tool to get the weather in a city.",
                    "tools": [get_weather],
                    "model": "gemini-3-pro-preview",
                    "middleware": [],
                }
            ],
        )
    ],
)

while True:
    user_input = input("User: ")
    response = agent.run(user_input)
    print("Agent:", response)
    print("---"*50, "\n")