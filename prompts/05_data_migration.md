# Prompt: Migrate Existing Markdown Data

Write a Python migration script `backend/scripts/migrate_from_markdown.py` that reads the existing markdown notes files and seeds the Supabase database.

The markdown files are at these paths (adjust as needed):
- Inventory: `~/Documents/Journals/drink recipes/Liquor inventory.md`
- Companions: `~/Documents/Journals/drink recipes/Drinking Companions.md`
- Sessions: `~/Documents/Journals/drink recipes/sessions/*.md`

**Inventory parsing:**
The inventory markdown is organized into sections by spirit category (e.g. `## Bourbon`, `## Mezcal`). Each line is a bottle name, sometimes with `[favorite]` tag. Parse these into inventory rows with the correct category.

**Companions parsing:**
The companion markdown has sections per person with likes, dislikes, and session notes. Parse into companion rows with likes[] and dislikes[] arrays.

**Sessions parsing:**
Each session file has a title (filename), a date, a list of drinks tried, and verdict notes. Parse into session rows + session_drink rows.

The script should:
1. Load a `.env` file for SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
2. Accept a `--user-email` flag to look up the user_id from Supabase auth
3. Upsert records (skip if already exists by name+user_id)
4. Print a summary: "Inserted X bottles, Y companions, Z sessions"

Use `supabase-py` for database writes. Use `python-dotenv` for env loading.
