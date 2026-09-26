# Web Directory Analysis

## Overview
The `web` directory contains a full-stack web application designed to provide a browser-based interface for the Doc.AI agent. It replicates the CLI's capabilities, including document processing, chat, and file management, but with a modern UI.

## Structure
The project is split into two main directories:
- **`backend/`**: Python-based server logic.
- **`frontend/`**: HTML/CSS/JS-based user interface.

### Backend (`web/backend/`)
- **Framework**: **FastAPI** is used as the main web server (`main.py`).
- **Database**: SQLite (`docai.db`) with `database.py` handling CRUD operations for chats, messages, and documents.
- **Authentication**: JWT-based auth (`auth.py`) with registration and login endpoints.
- **WebSockets**: Real-time communication (`websocket_handler.py`) to stream agent responses and tool execution status.
- **Agent Integration**:
    - `web_adapter.py`: A crucial component that adapts the CLI-based agent to work over WebSockets. It intercepts LangChain events and streams them as JSON.
    - `simple_agent.py` & `test_agent.py`: Likely simplified or test versions of the agent logic.
- **Document Processing**: `documents.py` and `analyze_excel.py` suggest specialized features for handling Excel and generating documents.

### Frontend (`web/frontend/`)
- **Technology**: Pure **HTML/CSS/JavaScript** (Vanilla JS). No heavy frameworks like React or Vue are visible in the file list, though it uses libraries via CDN.
- **Libraries**:
    - `marked.js`: For rendering Markdown.
    - `highlight.js`: For syntax highlighting in code blocks.
- **Components**:
    - `index.html`: The main chat interface.
    - `login.html`: Authentication page.
    - `css/style.css`: Styling.
    - `js/`: Likely contains the logic for WebSocket handling and UI updates (though not explicitly read, it's implied).

## Key Features
1.  **Real-time Chat**: Uses WebSockets to stream tokens and tool updates, mimicking the CLI experience.
2.  **File Management**: Supports file uploads (`uploads/` directory) and document generation (`generated_docs/`).
3.  **Authentication**: Secure access via login/register.
4.  **Visual Feedback**: The frontend is designed to show tool execution states (e.g., "Reading file...", "Generating document...").

## Conclusion
This is a **Full-Stack Application** that successfully wraps the core `deepagents-cli` logic in a web interface. It uses FastAPI for the heavy lifting (agent orchestration, file I/O) and a lightweight vanilla JS frontend for the user experience. The `WebUIAdapter` is the bridge that makes the CLI agent compatible with the web environment.
