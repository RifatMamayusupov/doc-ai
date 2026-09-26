import os
from typing import Literal
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from tavily import TavilyClient
from dotenv import load_dotenv
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

def make_backend(runtime):
    return CompositeBackend(
        default=StateBackend(runtime),  # Ephemeral storage
        routes={
            "/memories/": StoreBackend(runtime)  # Persistent storage
        }
    )


load_dotenv()

# 1. Initialize Tavily and Model
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
model = init_chat_model("google_genai:gemini-2.0-flash")

# 2. Enhanced Search Skill (Added topic and raw content)
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search. Use 'finance' topic for crypto/stock prices."""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

# 3. Research-focused System Prompt
research_instructions = """You are an expert financial researcher. 
When asked about prices or market data, use the internet_search tool with topic='finance'.
Break down complex tasks into steps using your built-in planning tools.
Write your findings into a detailed, polished report."""

agent = create_deep_agent(
    tools=[internet_search],
    system_prompt=research_instructions,
    model=model,
    store=InMemoryStore(),  # Required for StoreBackend
    backend=make_backend,
    checkpointer=checkpointer
)

# 4. Run the Agent
result = agent.invoke({"messages": [{"role": "user", "content": "BTC price qancha hozir?"}]})
print(result["messages"][-1].content)