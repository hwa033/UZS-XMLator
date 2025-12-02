import sys
sys.path.insert(0, 'd:\\ZW\\XML-automation-clean\\tools')
import generate_from_excel as gen

# Test all CdBerichtType scenarios
ns_soap, ns_uwvh, ns_body = gen._namespaces()

test_cases = [
    {'name': 'Digipoort', 'record': {'aanvraag_type': 'Digipoort', 'BSN': '123', 'Geboortedatum': '20000101', 'DatEersteAoDag': '20251125'}},
    {'name': 'ZBM', 'record': {'aanvraag_type': 'ZBM', 'BSN': '123', 'Geboortedatum': '20000101', 'DatEersteAoDag': '20251125'}},
    {'name': 'VM', 'record': {'aanvraag_type': 'VM', 'BSN': '123', 'Geboortedatum': '20000101', 'DatEersteAoDag': '20251125'}},
    {'name': 'No type specified', 'record': {'BSN': '123', 'Geboortedatum': '20000101', 'DatEersteAoDag': '20251125'}},
]

print("CdBerichtType Tests:")
print("-" * 40)
for test in test_cases:
    msg = gen.build_message_element(test['record'], ns_body)
    cd_elem = msg.find('CdBerichtType')
    if cd_elem is not None:
        print(f"{test['name']:20} -> {cd_elem.text}")
    else:
        print(f"{test['name']:20} -> NOT FOUND (ERROR!)")

