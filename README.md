# Construction AI Platform

AI-powered construction project management platform. Capstone project.

## Stack

- **Backend:** FastAPI + Python 3.12
- **Database:** PostgreSQL 16 with pgvector
- **Cache:** Redis 7
- **LLM Provider:** Google Gemini (swappable)

## Getting started

Prerequisites: Docker Desktop, Python 3.12, Git.

1. Copy `.env.example` to `.env` and fill in your values (especially `GEMINI_API_KEY`)
2. `docker compose up --build`
3. Open http://localhost:8000/docs


## Project Structure:

construction-ai-platform/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   └── config.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── agents/
│   │   └── memory/
│   ├── alembic/
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── data/
├── docker/
├── scripts/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md

## Focus workflows (this build)

- Meeting Intelligence
- Supplier Risk Analysis
- Executive Weekly Report