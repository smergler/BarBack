-- Migration: add ownership guard to preference RPCs.
-- Prevents any authenticated user from writing preferences to a companion they don't own
-- via PostgREST /rpc calls. Previously SECURITY DEFINER bypassed RLS with no ownership check.

CREATE OR REPLACE FUNCTION upsert_companion_like(
  p_companion_id uuid,
  p_value        text
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.companions WHERE id = p_companion_id AND user_id = auth.uid()
  ) THEN
    RAISE EXCEPTION 'not authorized for companion %', p_companion_id USING ERRCODE = '42501';
  END IF;

  INSERT INTO public.companion_preferences(companion_id, type, value)
  VALUES (p_companion_id, 'like', p_value)
  ON CONFLICT (companion_id, value) DO UPDATE SET type = 'like';
END;
$$;

CREATE OR REPLACE FUNCTION upsert_companion_dislike(
  p_companion_id uuid,
  p_value        text
) RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.companions WHERE id = p_companion_id AND user_id = auth.uid()
  ) THEN
    RAISE EXCEPTION 'not authorized for companion %', p_companion_id USING ERRCODE = '42501';
  END IF;

  INSERT INTO public.companion_preferences(companion_id, type, value)
  VALUES (p_companion_id, 'dislike', p_value)
  ON CONFLICT (companion_id, value) DO UPDATE SET type = 'dislike';
END;
$$;
