"""
packagereport.py

Non-destructive report that:
- enumerates top-level entries under `.venv/Lib/site-packages` (or detected site-packages)
- computes on-disk size per entry (MB)
- gets installed packages via `pip freeze`
- searches repository files (excl. .venv, build, dist, .git) for import patterns or `pkg.` usage
- prints a CSV-like table to stdout: package,size_mb,referenced,match_count,example_match

Run from repository root with the same Python interpreter used for the project (ideally inside .venv).
"""

import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Candidate site-packages locations
candidates = [ROOT / ".venv" / "Lib" / "site-packages"]
# fallback to sysconfig paths
try:
    import site

    for p in site.getsitepackages():
        candidates.append(Path(p))
except Exception:
    pass

site_pkgs = None
for c in candidates:
    if c.exists():
        site_pkgs = c
        break

if not site_pkgs:
    # try sys.path heuristics
    for p in sys.path:
        if p and "site-packages" in p:
            pth = Path(p)
            if pth.exists():
                site_pkgs = pth
                break

if not site_pkgs:
    print("No site-packages directory found. Is `.venv` created and activated?")
    sys.exit(2)

# gather top-level names under site-packages
entries = []
for child in site_pkgs.iterdir():
    # consider packages (dirs) and top-level .py files and .dist-info
    if child.name.endswith((".dist-info", ".egg-info")):
        continue
    entries.append(child)


# compute sizes
def get_size(p: Path):
    total = 0
    if p.is_file():
        try:
            return p.stat().st_size
        except Exception:
            return 0
    for root, dirs, files in os.walk(p, onerror=lambda e: None):
        for f in files:
            try:
                fp = Path(root) / f
                total += fp.stat().st_size
            except Exception:
                continue
    return total


entry_sizes = []
for e in entries:
    sz = get_size(e)
    entry_sizes.append((e.name, e, sz))

entry_sizes.sort(key=lambda t: t[2], reverse=True)

# get installed packages via pip
try:
    res = subprocess.run(
        [sys.executable, "-m", "pip", "list", "--format=freeze"],
        capture_output=True,
        text=True,
        check=True,
    )
    pkgs = [line.split("==")[0] for line in res.stdout.splitlines() if line.strip()]
except subprocess.CalledProcessError:
    pkgs = []

pkg_set = set([p.lower() for p in pkgs])

# Prepare search: walk repo files excluding common dirs
EXCLUDE_DIRS = {
    ".venv",
    ".git",
    "build",
    "dist",
    ".vscode",
    "__pycache__",
    "results",
    "resultaten",
}
FILE_EXTS = {".py", ".robot", ".xml", ".js", ".html", ".yml", ".yaml", ".md", ".txt"}


def iter_repo_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        # modify dirnames in-place to prune
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if Path(fn).suffix.lower() in FILE_EXTS:
                yield Path(dirpath) / fn


# build file index (read each file once) — more efficient than reading per-package
file_paths = list(iter_repo_files(ROOT))
file_texts = {}
for fp in file_paths:
    try:
        file_texts[fp] = fp.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        file_texts[fp] = ""

# search utility templates
IMPORT_RE_TEMPLATE = r"(^|\W)(from|import)\s+{name}(\b|\.|\s)"
DOT_RE_TEMPLATE = r"\b{name}\."

results = []

# We'll consider top N largest entries, map entry name to probable package name(s)
MAX = 150
to_scan = entry_sizes[:MAX]

# build regex patterns per package
pkg_patterns = {}
for name, pathobj, size in to_scan:
    if name.endswith(".py"):
        base = name[:-3]
    else:
        base = name
    candidates_names = {
        base.lower(),
        base.replace("-", "_").lower(),
        base.replace("_", "-").lower(),
    }
    for p in list(pkg_set):
        if p and p in base.lower():
            candidates_names.add(p)
    # compile regexes for this package
    patterns = []
    for cand in set(candidates_names):
        if not cand:
            continue
        imp_re = re.compile(
            IMPORT_RE_TEMPLATE.format(name=re.escape(cand)),
            re.IGNORECASE | re.MULTILINE,
        )
        dot_re = re.compile(DOT_RE_TEMPLATE.format(name=re.escape(cand)), re.IGNORECASE)
        patterns.append((cand, imp_re, dot_re))
    pkg_patterns[name] = (pathobj, size, patterns)

# iterate files once, update counters
pkg_stats = {
    name: {"size": size, "matches": 0, "example": ""}
    for name, (pathobj, size, patterns) in pkg_patterns.items()
}

# Build token -> package mapping to avoid scanning every package for every file
token_to_packages = defaultdict(list)
for pkg_name, (pathobj, size, patterns) in pkg_patterns.items():
    for cand, imp_re, dot_re in patterns:
        token_to_packages[cand].append(pkg_name)

tokens = sorted([t for t in token_to_packages.keys() if t], key=lambda s: -len(s))
if tokens:
    big_pattern = re.compile(
        r"\b(" + "|".join(re.escape(t) for t in tokens) + r")(\b|\.)", re.IGNORECASE
    )
else:
    big_pattern = None

for fp, text in file_texts.items():
    if not text or not big_pattern:
        continue
    found = set(m.group(1).lower() for m in big_pattern.finditer(text))
    if not found:
        continue
    # for each token found, update related packages
    for token in found:
        for pkg_name in token_to_packages.get(token, []):
            pathobj, size, patterns = pkg_patterns[pkg_name]
            # find matches for that package's patterns
            for cand, imp_re, dot_re in patterns:
                if imp_re.search(text) or dot_re.search(text):
                    c = len(imp_re.findall(text)) + len(dot_re.findall(text))
                    pkg_stats[pkg_name]["matches"] += c
                    if not pkg_stats[pkg_name]["example"]:
                        for i, line in enumerate(text.splitlines(), 1):
                            if imp_re.search(line) or dot_re.search(line):
                                pkg_stats[pkg_name][
                                    "example"
                                ] = f"{fp.relative_to(ROOT)}:{i}:{line.strip()}"
                                break

# assemble results
for name, (pathobj, size, patterns) in pkg_patterns.items():
    st = pkg_stats.get(name, {})
    referenced = st.get("matches", 0) > 0
    match_count = st.get("matches", 0)
    example = st.get("example", "")
    size_mb = round(size / (1024 * 1024), 2)
    results.append((name, size_mb, referenced, match_count, example))

# Write concise table for largest entries to UTF-8 CSV in build/
out_dir = ROOT / "build"
out_dir.mkdir(exist_ok=True)
out_file = out_dir / "package_report.csv"

with out_file.open("w", encoding="utf-8", newline="") as fh:
    fh.write("package, size_mb, referenced, match_count, example_match\n")
    printed = 0
    for name, size_mb, referenced, match_count, example in results:
        # skip builtin caches like __pycache__
        if name.startswith("__"):
            continue
        fh.write(
            f'"{name}",{size_mb},{"YES" if referenced else "NO"},{match_count},"{example}"\n'
        )
        printed += 1
        if printed >= 200:
            break

# Also write a short summary of top installed packages (from pip) that are large and unreferenced
unreferenced = [(n, s, r, m, e) for (n, s, r, m, e) in results if (not r) and s > 0]
with out_file.open("a", encoding="utf-8", newline="") as fh:
    if unreferenced:
        fh.write("\n# Unreferenced site-packages (size_mb > 0) — review before uninstalling\n")
        for n, s, r, m, e in sorted(unreferenced, key=lambda t: t[1], reverse=True)[:50]:
            fh.write(f"{n}: {s} MB\n")
    else:
        fh.write("\n# No large unreferenced site-packages detected by this scan\n")

print(f"Wrote package report to: {out_file}\nRows written: {printed}")
