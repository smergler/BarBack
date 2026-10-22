import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_script_rejects_legacy_key(tmp_path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("SUPABASE_")}
    env["SUPABASE_PROJECT_URL"] = "https://x.supabase.co"
    env["SUPABASE_PRIVATE_KEY"] = "eyJx"
    env["BARBACK_ENV_PATH"] = str(tmp_path / "missing.env")
    r = subprocess.run(
        [sys.executable, "scripts/create_test_users.py"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=60,
    )
    assert r.returncode != 0
    assert "SUPABASE_SECRET_KEY" in r.stderr
    assert "eyJx" not in r.stderr
