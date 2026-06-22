# Prompt: React Frontend

Build the React + TypeScript frontend for the drink suggester app. Use Vite. Style with Tailwind CSS.

**Pages:**
- `/login` — Supabase Auth UI (email/password), redirect to `/` on success
- `/` — Home / Recommend page (main screen)
- `/inventory` — View and manage bottles
- `/companions` — View and manage drinking companions
- `/sessions` — Session history

**Home page (`/`) — the main experience:**
A clean, card-based UI with:
- Occasion input (text or dropdown: "movie night", "dinner party", "casual", "date night", custom)
- Mood/vibe input (text: "something refreshing", "spirit-forward", "light and fizzy")
- Companion selector (multi-select from companions list)
- Optional constraints text field
- "Suggest Drinks" button → calls POST /recommend
- Results displayed as cards: drink name, description, why it fits, full recipe, and a "Log this drink" button
- "Log this drink" opens a quick modal to record verdict and add to current session

**Inventory page:**
- Table of all bottles (filterable by category)
- Add/edit bottle form (name, category, is_favorite toggle)
- Mark as out of stock (soft delete)

**Companions page:**
- List of companions with their liked/disliked descriptors shown as tags
- Add/edit companion form

**Sessions page:**
- Timeline of past sessions, most recent first
- Each session expandable to show drinks tried and verdicts
- "New Session" button

**API client (`lib/api.ts`):**
- Base URL from `VITE_API_URL` env var
- Automatically attach Supabase JWT to all requests via Authorization header
- Typed response interfaces for all endpoints

Use `@supabase/supabase-js` for auth. Use `react-query` (TanStack Query) for data fetching and caching.
