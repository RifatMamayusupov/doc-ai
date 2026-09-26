from urllib.request import urlopen
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain.chat_models import init_chat_model
from dotenv import load_dotenv
from deepagents.backends import FilesystemBackend


load_dotenv()
checkpointer = MemorySaver()
model = init_chat_model("google_genai:gemini-2.0-flash")

skill_url = "https://raw.githubusercontent.com/langchain-ai/deepagentsjs/refs/heads/main/examples/skills/langgraph-docs/SKILL.md"
with urlopen(skill_url) as response:
    skill_content = response.read().decode('utf-8')

skills_files = {
    "/skills/langgraph-docs/SKILL.md": skill_content
}

agent = create_deep_agent(
    backend=FilesystemBackend(root_dir=".", virtual_mode=True),
    skills=["./skills/"],
    checkpointer=checkpointer,
    model=model,
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
            # Seed the default StateBackend's in-state filesystem (virtual paths must start with "/").
            "files": skills_files
        },
        config={"configurable": {"thread_id": "12345"}},
    )

    print(result['messages'][-1].content)