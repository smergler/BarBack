# Prompt: Project Scaffold

Scaffold a full-stack drink recommendation app with the following structure:

```
drink-suggester/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   │   ├── inventory.py
│   │   │   ├── companion.py
│   │   │   └── session.py
│   │   ├── routers/
│   │   │   ├── inventory.py
│   │   │   ├── companions.py
│   │   │   ├── sessions.py
│   │   │   └── recommend.py
│   │   ├── services/
│   │   │   ├── llm.py
│   │   │   └── recommender.py
│   │   └── middleware/
│   │       └── auth.py
│   ├── requirements.txt
│   ├── .env.example
│   └── railway.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── lib/
│   │   │   └── api.ts
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

Requirements:
- Backend: FastAPI + Python 3.11+
- Frontend: React 18 + TypeScript + Vite
- Auth: Supabase Auth (JWT validation in FastAPI middleware)
- DB: Supabase PostgreSQL via asyncpg
- Environment variables: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ANTHROPIC_API_KEY, FRONTEND_URL (for CORS)

Create all files with stubs/placeholders. Include a README with setup instructions. The backend should run with `uvicorn app.main:app --reload` and the frontend with `npm run dev`.
