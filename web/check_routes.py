import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "wapp", str(Path(__file__).parent / "app.py")
)
if spec is None:
    raise SystemExit("Failed to create module spec for web.app")

m = importlib.util.module_from_spec(spec)
if spec.loader is None:
    raise SystemExit("No loader available for web.app spec")

spec.loader.exec_module(m)  # type: ignore[attr-defined]

app = getattr(m, "app", None)
print("APP_DEFINED", bool(app))
if app:
    rules = sorted(app.url_map.iter_rules(), key=lambda x: x.rule)
    for r in rules:
        methods = ",".join(sorted((r.methods or set()) - {"HEAD", "OPTIONS"}))
        print(f"{r.rule} [{methods}] => {r.endpoint}")
