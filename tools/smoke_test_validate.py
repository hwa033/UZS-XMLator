import pathlib
import sys

# Ensure repository root is on sys.path so `web` package is importable
repo_root = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))

from web.app import _load_generator_module
from web.utils import validate_normalized_rows_for_generator

print('Loading generator module...')
gen = _load_generator_module()
if gen is None:
    print('Generator module not found')
    sys.exit(2)

ns_soap, ns_uwvh, ns_body = gen._namespaces()

norm_rows = [
    {"BSN": "123456789", "Naam": "Jan Test", "DatEersteAoDag": "20250101"}
]

bodies, errors, bulk = validate_normalized_rows_for_generator(
    norm_rows,
    ["BSN", "Naam", "DatEersteAoDag"],
    False,  # no XSD validation for smoke test
    "VM",
    {"Digipoort": "OTP3"},
    "VM",
    gen,
    ns_body,
    schema=None,
)

print('errors:', errors)
print('bulk:', bulk)
if bodies:
    elem = bodies[0].find('{' + ns_body + '}CdBerichtType')
    print('CdBerichtType element text:', elem.text if elem is not None else None)
    sys.exit(0)
else:
    print('No bodies returned')
    sys.exit(1)
