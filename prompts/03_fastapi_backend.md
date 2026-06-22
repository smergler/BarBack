# Prompt: FastAPI Backend Implementation

Implement the full FastAPI backend for the drink suggester app. The scaffold already exists. Fill in all routers, models, and services.

**Auth middleware (`middleware/auth.py`):**
- Extract Bearer token from Authorization header
- Validate it against Supabase using the SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
- Use `supabase-py` library: `from supabase import create_client`
- Call `supabase.auth.get_user(token)` to get the user_id
- Inject user_id as a FastAPI dependency: `async def get_current_user(token: str = Depends(oauth2_scheme))`
- Return 401 on invalid token

**Inventory router (`routers/inventory.py`):**
- GET /inventory — list all active bottles for current user, filterable by category
- POST /inventory — add a bottle
- PUT /inventory/{id} — update a bottle (name, notes, is_favorite, is_active)
- DELETE /inventory/{id} — soft delete (set is_active=false)
- GET /inventory/categories — return distinct categories for the user's inventory

**Companions router (`routers/companions.py`):**
- GET /companions — list all companions for current user
- POST /companions — create companion
- PUT /companions/{id} — update companion (likes, dislikes, notes)
- DELETE /companions/{id} — delete companion
- POST /companions/{id}/feedback — add a like or dislike based on a session drink verdict (updates the likes/dislikes arrays)

**Sessions router (`routers/sessions.py`):**
- GET /sessions — list sessions (most recent first), optional limit param
- POST /sessions — create a new session (title, occasion, companion_ids, session_date)
- GET /sessions/{id} — get session with its drinks
- POST /sessions/{id}/drinks — add a drink to a session (name, recipe, verdict, notes, was_suggested_by_ai)
- PUT /sessions/{id}/drinks/{drink_id} — update verdict or notes on a drink

**Recommend router (`routers/recommend.py`):**
See prompt 04 for the LLM implementation. For now, stub this with a placeholder response.

Use asyncpg for DB access (not SQLAlchemy). Use Pydantic v2 models for request/response. Include proper error handling (404 when item not found, 403 when item belongs to different user).
