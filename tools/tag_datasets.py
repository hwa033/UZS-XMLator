"""Markeer datasets met afgeleide `types` voor filtering.

Gebruik:
    # Dry-run (toont afleiding, schrijft niet):
    python tools/tag_datasets.py --dry-run

    # Pas heuristieken automatisch toe en schrijf naar docs/excel_datasets_tagged.yml
    python tools/tag_datasets.py --auto --output docs/excel_datasets_tagged.yml

    # Om conservatief te blijven: pas niet automatisch DEFAULT_TYPES toe wanneer
    # geen sterke aanwijzing voor een type aanwezig is. Geef `--defaults` om
    # het oudere gedrag te forceren waarin ontbrekende type-afleiding wordt
    # aangevuld met alle DEFAULT_TYPES.

Interactieve modus (prompt) is beschikbaar zonder --auto, maar in deze
omgeving wordt interactieve invoer niet geaccepteerd.
"""

import argparse
from pathlib import Path

import yaml

DEFAULT_TYPES = ["ZBM", "VM", "Digipoort"]


def infer_types_from_record(record: dict):
    """Simple heuristic to infer compatible aanvraag types.

    Rules (conservative):
    - If IBAN or BIC present -> likely payment-related: include ZBM and VM
    - If Loonheffingennr present -> include ZBM and VM
    - If label or naam contains 'digipoort' -> include Digipoort
    - If BSN present -> include ZBM and VM
    - If no strong signal -> return empty (caller may use DEFAULT_TYPES)
    """
    types = set()
    label = record.get("label") or record.get("Naam") or ""
    fields = record.get("fields") or record

    # normalize string values
    def has_nonempty(k):
        v = fields.get(k) if isinstance(fields, dict) else None
        return v is not None and str(v).strip() != ""

    if has_nonempty("Iban") or has_nonempty("Bic"):
        types.update(["ZBM", "VM"])
    if has_nonempty("Loonheffingennr") or has_nonempty("Loonheffingennummer"):
        types.update(["ZBM", "VM"])
    if has_nonempty("BSN"):
        types.update(["ZBM", "VM"])
    lbl = str(label).lower()
    if "digipoort" in lbl or "otp3" in lbl:
        types.add("Digipoort")

    return sorted(types)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", "-f", default="docs/excel_datasets.yml")
    p.add_argument("--output", "-o", default="docs/excel_datasets_tagged.yml")
    p.add_argument(
        "--auto", action="store_true", help="Auto-apply inferred types and write output"
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Show inference but do not write"
    )
    p.add_argument(
        "--defaults",
        action="store_true",
        help=(
            "When inference yields no types, apply DEFAULT_TYPES " "(legacy behaviour)"
        ),
    )
    args = p.parse_args()

    src = Path(args.file)
    if not src.exists():
        print("Source file not found:", src)
        return 2

    raw = yaml.safe_load(src.read_text(encoding="utf-8")) or {}
    datasets = []
    if (
        isinstance(raw, dict)
        and "datasets" in raw
        and isinstance(raw["datasets"], list)
    ):
        datasets = raw["datasets"]
    elif isinstance(raw, list):
        datasets = raw
    else:
        # find first list
        for v in raw.values():
            if isinstance(v, list):
                datasets = v
                break

    changed = 0
    out = []
    for ds in datasets:
        if not isinstance(ds, dict):
            out.append(ds)
            continue
        inferred = infer_types_from_record(ds)
        # By default we keep an empty inferred list (conservative). If the
        # user supplies --defaults, fall back to the legacy behaviour and
        # mark the dataset as compatible with all DEFAULT_TYPES.
        if not inferred and args.defaults:
            inferred = DEFAULT_TYPES.copy()
        ds_types = (
            ds.get("types") or ds.get("aanvraag_types") or ds.get("aanvraag_type")
        )
        if isinstance(ds_types, list):
            current = [str(x) for x in ds_types]
        elif ds_types:
            current = [str(ds_types)]
        else:
            current = []

        if sorted(current) != sorted(inferred):
            ds["types"] = inferred
            changed += 1
        out.append(ds)

    print(f"Datasets scanned: {len(out)}; updated: {changed}")
    if args.dry_run or not args.auto:
        # Print summary table
        for ds in out:
            label = (
                ds.get("label") or (ds.get("fields") or {}).get("Naam") or ds.get("id")
            )
            print(f"- id={ds.get('id')}: label='{label}' types={ds.get('types')}")

    if args.auto:
        dst = Path(args.output)
        dst.write_text(
            yaml.safe_dump({"datasets": out}, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
        print("Wrote:", dst)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
