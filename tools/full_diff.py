import sys
from pathlib import Path
import difflib

if len(sys.argv) < 3:
    print('Usage: full_diff.py <file1> <file2>')
    sys.exit(1)

f1 = Path(sys.argv[1])
f2 = Path(sys.argv[2])
if not f1.exists():
    print('File not found:', f1); sys.exit(2)
if not f2.exists():
    print('File not found:', f2); sys.exit(3)

s1 = f1.read_text(encoding='utf-8').splitlines(keepends=True)
s2 = f2.read_text(encoding='utf-8').splitlines(keepends=True)

ud = difflib.unified_diff(s1, s2, fromfile=str(f1), tofile=str(f2), lineterm='')
out = list(ud)

outp = Path('build') / 'full_diff.txt'
outp.parent.mkdir(parents=True, exist_ok=True)
outp.write_text('\n'.join(out), encoding='utf-8')
print('Wrote diff to', outp)
# Print first 400 lines (or full if shorter)
MAX_LINES = 400
for i, line in enumerate(out[:MAX_LINES]):
    print(line)
if len(out) > MAX_LINES:
    print('\n... (diff truncated, full diff in build/full_diff.txt)')
