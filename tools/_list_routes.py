import sys
from pathlib import Path

# Ensure project root is on sys.path so `web` package can be imported
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from web import app

rules = sorted(app.url_map.iter_rules(), key=lambda x: x.rule)
for r in rules:
    methods = ",".join(sorted((r.methods or set()) - {"HEAD", "OPTIONS"}))
    print(f"{r.rule} [{methods}] => {r.endpoint}")
