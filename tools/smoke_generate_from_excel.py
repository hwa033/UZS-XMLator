import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))  # noqa: E402
from web.app import _load_generator_module
from web.utils import validate_normalized_rows_for_generator

print("Loading generator...")
gen = _load_generator_module()
if gen is None:
    print("generator missing")
    sys.exit(2)
ns_soap, ns_uwvh, ns_body = gen._namespaces()
rows, formula_count = gen.read_excel_rows(
    str(repo_root / "docs" / "Input XML electr ziekmeldinge.xlsx"), data_only=True
)
print("Rows read:", len(rows), "formulas:", formula_count)
# normalize rows using app helper
from web.app import _normalize_record_for_generator

norm_rows = [_normalize_record_for_generator(r) for r in rows]
print("First normalized row sample keys:", list(norm_rows[0].keys())[:10])

bodies, errors, bulk = validate_normalized_rows_for_generator(
    norm_rows,
    list(rows[0].keys()) if rows else [],
    False,
    "VM",
    {"Digipoort": "OTP3"},
    "VM",
    gen,
    ns_body,
    schema=None,
)
print("Errors:", errors)
print("Bulk type:", bulk)
if bodies:
    out_dir = repo_root / "build" / "smoke_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    env = gen.build_envelope_with_header_and_bodies(bodies, sender="VM")
    saved = gen.save_envelope(env, str(out_dir), "smoke", bulk or "VM")
    print("Saved envelope to", saved)
    print("Contents:")
    print(Path(saved).read_text(encoding="utf-8")[:1000])
else:
    print("No bodies created")

print("Done")
