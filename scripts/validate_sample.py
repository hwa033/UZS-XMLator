from lxml import etree
import sys
import xml.etree.ElementTree as ET
sys.path.insert(0, 'tools')
from generate_from_excel import _namespaces, build_message_element, build_envelope_with_header_and_bodies

ns_soap, ns_uwvh, ns_body = _namespaces()
# sample record using the exact values that previously failed
rec = {
    'CdBerichtType': 'OTP3',
    'BSN': '213344075',  # Use 'BSN' key instead of 'Burgerservicenr'
    'Geboortedatum': '19801205',  # Use 'Geboortedatum' not 'Geboortedat'
    'DatEersteAoDag': '20251125'
}
msg = build_message_element(rec, ns_body)
env = build_envelope_with_header_and_bodies([msg], sender='Digipoort', tester_name='TesterX')

# pretty-print
try:
    ET.indent(env)
except Exception:
    pass
xml_bytes = ET.tostring(env, encoding='utf-8', xml_declaration=True)

# load XSD
xsd_path = 'docs/UwvZwMeldingInternBody-v0428-b01.xsd'
parser = etree.XMLParser(load_dtd=True, no_network=False, resolve_entities=False)
try:
    doc = etree.parse(xsd_path, parser)
    schema = etree.XMLSchema(doc)
except Exception as e:
    print('Failed to load XSD:', e)
    print('Wrote XML to stdout anyway:')
    print(xml_bytes.decode('utf-8'))
    sys.exit(2)

# validate
root = etree.fromstring(xml_bytes)
# locate the Body child element (UwvZwMeldingInternBody) and validate that element
body_elem = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Body')
if body_elem is None:
    print('No SOAP Body found')
    sys.exit(3)
body_child = None
for c in body_elem:
    body_child = c
    break
if body_child is None:
    print('No child element inside SOAP Body')
    sys.exit(3)
valid = schema.validate(body_child)
print('VALID_BODY:', valid)
if not valid:
    for e in schema.error_log:
        print('ERROR:', e.line, e.message)

# print XML for inspection
xml_str = xml_bytes.decode('utf-8')
print('\n--- GENERATED XML (first 400 chars) ---')
print(xml_str[:400])

# show date elements
import re
for match in re.finditer(r'<(Geboortedat|DatEersteAoDag)>([^<]+)</\1>', xml_str):
    print(f'\n{match.group(1)}: {match.group(2)}')
