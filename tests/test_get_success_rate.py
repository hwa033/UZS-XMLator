import json
from importlib import import_module
from pathlib import Path

mod = import_module("web.app")
_get_success_rate = mod._get_success_rate


def test_get_success_rate_tmpfile(tmp_path: Path):
    f = tmp_path / "events.jsonl"
    lines = [
        json.dumps({"success": True}),
        json.dumps({"success": False}),
        json.dumps({"success": True}),
    ]
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    res = _get_success_rate(f)
    assert res == "67%"
