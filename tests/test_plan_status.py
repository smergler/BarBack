import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "plan_status", Path(__file__).resolve().parent.parent / "scripts" / "plan_status.py"
)
plan_status = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan_status)


def _plan(tmp_path, slug, text):
    d = tmp_path / slug
    d.mkdir()
    (d / "PLAN.md").write_text(text)
    return d / "PLAN.md"


def test_counts_each_marker(tmp_path):
    p = _plan(tmp_path, "a", "## Task 1\n- [x] 1.1 done\n- [ ] 1.2 todo\n- [>] 1.3 moved\n- [!] 1.4 stuck\n")
    r = plan_status.parse_plan(p)
    assert (r["done"], r["open_agent"], r["transferred"], r["blocked"], r["total"]) == (1, 1, 1, 1, 4)


def test_requires_human_is_not_agent_work_and_next_skips_it(tmp_path):
    p = _plan(tmp_path, "a", (
        "- [ ] **1.1 needs a person**\n      Requires human: dashboard\n"
        "- [ ] **1.2 agent task**\n"
    ))
    r = plan_status.parse_plan(p)
    assert (r["open_human"], r["open_agent"], r["next_agent"]) == (1, 1, "1.2")


def test_heading_ends_a_block(tmp_path):
    p = _plan(tmp_path, "a", "- [ ] 1.1 agent task\n## Human-required steps\nRequires human: note\n")
    assert plan_status.parse_plan(p)["open_human"] == 0


def test_empty_plan(tmp_path):
    r = plan_status.parse_plan(_plan(tmp_path, "a", "# nothing here\n"))
    assert (r["total"], r["next_agent"]) == (0, "-")


def test_render_has_generated_header_and_rows():
    out = plan_status.render([{"slug": "a", "done": 1, "total": 2, "open_agent": 1, "open_human": 0,
                               "blocked": 0, "transferred": 0, "next_agent": "1.2"}])
    assert out.startswith(plan_status.HEADER)
    assert "| a | 1/2 | 1 | 0 | 0 | 0 | 1.2 |" in out


def test_exclude_drops_a_plan(tmp_path, monkeypatch):
    _plan(tmp_path, "keep", "- [x] 1.1 a\n")
    _plan(tmp_path, "drop", "- [x] 1.1 a\n")
    monkeypatch.setattr(plan_status, "PLANS_DIR", tmp_path)
    monkeypatch.setattr("sys.argv", ["plan_status.py", "--exclude", "drop"])
    plan_status.main()
    out = (tmp_path / "STATUS.md").read_text()
    assert "| keep |" in out and "| drop |" not in out


def test_prefixed_subtask_ids_are_counted(tmp_path):
    p = _plan(tmp_path, "a", "- [x] **P1.1 first**\n- [ ] **P1.2 second**\n")
    r = plan_status.parse_plan(p)
    assert (r["done"], r["total"], r["next_agent"]) == (1, 2, "P1.2")
