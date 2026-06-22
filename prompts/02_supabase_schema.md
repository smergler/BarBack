# Prompt: Supabase Database Schema

Write the SQL migration to create the following schema in Supabase. Run this in the Supabase SQL editor.

Tables:

**inventory**
- id (uuid, primary key, default gen_random_uuid())
- user_id (uuid, references auth.users, not null)
- name (text, not null) — bottle name e.g. "Four Roses Small Batch"
- category (text, not null) — e.g. "bourbon", "mezcal", "liqueur", "bitters", "vermouth"
- subcategory (text) — e.g. "rye", "blanco", "amaro"
- brand (text)
- is_favorite (boolean, default false)
- notes (text)
- is_active (boolean, default true) — false means out of stock
- created_at (timestamptz, default now())
- updated_at (timestamptz, default now())

**companions**
- id (uuid, primary key)
- user_id (uuid, references auth.users)
- name (text, not null)
- relationship (text) — e.g. "wife", "friend", "colleague"
- likes (text[]) — array of descriptors e.g. ["spirit-forward", "mezcal", "old fashioned style"]
- dislikes (text[]) — e.g. ["sweet", "tropical"]
- notes (text)
- created_at, updated_at

**sessions**
- id (uuid, primary key)
- user_id (uuid, references auth.users)
- title (text) — e.g. "Movie night with popcorn"
- occasion (text) — e.g. "movie night", "dinner party", "casual evening"
- companion_ids (uuid[]) — who was there
- notes (text)
- session_date (date, default current_date)
- created_at, updated_at

**session_drinks**
- id (uuid, primary key)
- session_id (uuid, references sessions)
- name (text) — cocktail name
- recipe (text)
- verdict (text) — "loved it", "ok", "miss"
- notes (text)
- was_suggested_by_ai (boolean, default false)
- created_at

Enable Row Level Security on all tables. Write RLS policies so users can only see and modify their own rows. Also create a trigger to auto-update `updated_at` on inventory and companions.
