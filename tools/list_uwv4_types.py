import re
from pathlib import Path

p = Path(__file__).parent.parent / "docs" / "UwvZwMeldingInternBody-v0428-b01.xsd"
s = p.read_text(encoding="utf-8")
names = set(re.findall(r"uwv4:([A-Za-z0-9_]+)", s))
print(len(names), "types found")
for n in sorted(names):
    print(n)
