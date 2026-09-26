# DocAgent Web Platform - Backend

FastAPI backend with WebSocket real-time updates, JWT authentication, and DeepAgents integration.

## Quick Start

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/docagent
REDIS_URL=redis://localhost:6379
JWT_SECRET=your-secret-key
DEEPAGENTS_MODEL=claude-sonnet-4-5-20250929
```
