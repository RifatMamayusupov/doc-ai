# DeepAgents CLI Analysis

## Project Overview
**DeepAgents CLI** is a Python-based command-line interface tool designed to act as an AI coding assistant. It leverages a Terminal User Interface (TUI) built with `Textual` to provide an interactive chat experience with an AI agent. The agent is powered by LangChain/LangGraph and supports various tools and skills.

## Architecture
The application follows a modular architecture:

1.  **Entry Point (`main.py`)**:
    - Handles command-line argument parsing (`argparse`).
    - Checks for optional dependencies (`textual`, `tavily`, etc.).
    - Initializes the agent and launches the UI or executes one-off commands.

2.  **User Interface (`app.py` & `widgets/`)**:
    - Built using the `Textual` framework.
    - Features a chat-like interface with input, message history, and status bar.
    - Custom widgets handle specific message types (User, Assistant, Tool Calls).

3.  **Agent Logic (`agent.py` & `sessions.py`)**:
    - Uses `LangGraph` for state management and agent orchestration.
    - Supports persistent sessions via thread IDs.
    - Integrates with `LangSmith` for tracing (implied by config imports).

4.  **Tools & Skills (`tools.py` & `skills/`)**:
    - **Tools**: Standard utilities like `web_search`, `fetch_url`, `http_request`.
    - **Skills**: A modular system to extend agent capabilities (e.g., `doc-ai`, `excel-agent`).

## Key Components

| File/Directory | Description |
| :--- | :--- |
| `main.py` | CLI entry point, dependency checks, and command routing. |
| `app.py` | Main Textual App class, managing the TUI lifecycle. |
| `agent.py` | Defines the LangChain agent structure and behavior. |
| `config.py` | Configuration management (likely environment variables). |
| `tools.py` | Implementation of core tools available to the agent. |
| `skills/` | Directory containing specialized agent skills. |
| `widgets/` | UI components for the chat interface. |

## Dependencies
Key external libraries identified:
- **Textual**: For the TUI.
- **Rich**: For rich text formatting in the terminal.
- **LangChain / LangGraph**: For AI agent logic.
- **Tavily Python**: For web search capabilities.
- **Python-Dotenv**: For environment variable management.

## Usage Patterns
The CLI supports multiple modes:
- **Interactive Mode**: Launches the TUI for a chat session.
- **Command Mode**: Likely supports specific commands via sub-parsers (e.g., listing agents or threads).
