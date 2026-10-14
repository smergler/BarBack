-- Migration: harden session_companions ownership.
-- Closes the direct-PostgREST gap the app-layer guard doesn't cover (a user could
-- previously INSERT a foreign companion_id into their own session row), and
-- removes the anon role's ability to call the preference RPCs at all — the
-- in-function auth.uid() check was the only thing stopping unauthenticated calls
-- before this.

-- Cleanup: delete any session_companions rows written before this guard existed
-- where the companion doesn't belong to the session's owner. Runs before the
-- policy change below so it still executes under the pre-existing (looser) policy.
DELETE FROM session_companions sc
USING sessions s
WHERE sc.session_id = s.id
  AND sc.companion_id NOT IN (
    SELECT id FROM companions WHERE user_id = s.user_id
  );

DROP POLICY IF EXISTS "own session_companions" ON session_companions;
CREATE POLICY "own session_companions" ON session_companions
  FOR ALL USING (
    session_id IN (SELECT id FROM sessions WHERE user_id = auth.uid())
    AND companion_id IN (SELECT id FROM companions WHERE user_id = auth.uid())
  );

REVOKE EXECUTE ON FUNCTION upsert_companion_like(uuid, text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION upsert_companion_dislike(uuid, text) FROM PUBLIC;
