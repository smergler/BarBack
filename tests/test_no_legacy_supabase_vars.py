"""Guard: legacy Supabase env var names must not reappear in tracked files."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent

PATTERN = r"SUPABASE_(ANON_KEY|PRIVATE_KEY|JWT_TOKEN)|supabase_anon_key"
EXCLUDES = [
    ":(exclude)plans",
    ":(exclude)CodeReview.md",
    ":(exclude)POSTMORTEM_*.md",
    ":(exclude)KNOWN_ISSUES.md",
    ":(exclude)tests/test_no_legacy_supabase_vars.py",
    ":(exclude)backend/supabase_keys.py",
    # tests that deliberately set or clear the legacy names to exercise the migration errors
    ":(exclude)tests/test_supabase_keys.py",
    ":(exclude)tests/test_config_endpoint.py",
    ":(exclude)tests/test_db_client.py",
    ":(exclude)tests/test_create_test_users_script.py",
]


@pytest.mark.skipif(shutil.which("git") is None, reason="git not available")
def test_no_legacy_supabase_vars_in_tracked_files():
    r = subprocess.run(
        ["git", "grep", "-nE", PATTERN, "--", ".", *EXCLUDES],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert r.returncode in (0, 1), r.stderr
    assert r.stdout == "", f"legacy Supabase names found:\n{r.stdout}"
