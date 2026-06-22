# Prompt: Deploy to Railway + Supabase + Vercel

Step-by-step deployment of the drink suggester app.

**Supabase setup:**
1. Create a new Supabase project at supabase.com
2. Run the SQL from `02_supabase_schema.md` in the SQL editor
3. Enable Email auth in Authentication → Providers
4. Copy: Project URL, anon key, service_role key

**Railway (backend):**
1. `railway login` then `railway init` in the `backend/` directory
2. Set environment variables in Railway dashboard:
   - SUPABASE_URL
   - SUPABASE_SERVICE_ROLE_KEY
   - ANTHROPIC_API_KEY
   - FRONTEND_URL (your Vercel URL, set after Vercel deploy)
3. Add a `railway.toml`:
```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
```
4. `railway up` — Railway auto-detects Python, installs requirements.txt, deploys
5. Note the Railway URL (e.g. `https://drink-suggester-api.up.railway.app`)

**Vercel (frontend):**
1. `vercel` in the `frontend/` directory
2. Set environment variables:
   - VITE_API_URL = your Railway URL
   - VITE_SUPABASE_URL = your Supabase project URL
   - VITE_SUPABASE_ANON_KEY = your Supabase anon key
3. `vercel --prod`

**Data migration:**
After deployment, run the migration script locally:
```bash
cd backend
python scripts/migrate_from_markdown.py --user-email your@email.com
```

**Testing the full stack:**
1. Open your Vercel URL
2. Sign up with your email
3. Check Supabase dashboard → auth.users to confirm account created
4. Go to /inventory — should show migrated bottles
5. Go to home page, select an occasion and companions, click Suggest Drinks
6. Confirm LLM response appears
