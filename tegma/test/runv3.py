import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent
from dotenv import load_dotenv

load_dotenv()
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

research_subagent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions",
    "system_prompt": "You are a great researcher",
    "tools": [internet_search],
    "model": "google_genai:gemini-2.0-flash",  # Optional override, defaults to main agent model
}
subagents = [research_subagent]

agent = create_deep_agent(
    model="google_genai:gemini-3-pro-preview",
    subagents=subagents
)


while True:
    user_input = input("Enter your question: ")
    if user_input.lower() in ["exit", "quit"]:
        break
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": user_input,
                }
            ],
        },
        config={"configurable": {"thread_id": "12345"}},
    )

    print(result['messages'][-1].content)