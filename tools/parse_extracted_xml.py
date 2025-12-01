from xml.etree import ElementTree as ET
import sys
p='build/extracted2_Digipoort.xml'
try:
    tree=ET.parse(p)
except Exception as e:
    print('Failed to parse',p,':',e); sys.exit(2)
root=tree.getroot()
ns = { 'soap':'http://schemas.xmlsoap.org/soap/envelope/', 'ns2':'http://schemas.uwv.nl/UwvML/Berichten/UwvZwMeldingInternBody-v0428', 'uwvh':'http://schemas.uwv.nl/UwvML/Header-v0202' }
body = root.find('soap:Body', ns)
if body is None:
    print('No SOAP Body found'); sys.exit(3)
bod = body.find('ns2:UwvZwMeldingInternBody', ns)
if bod is None:
    print('No UwvZwMeldingInternBody found'); sys.exit(4)

def t(q):
    el = bod.find(q, ns)
    return el.text.strip() if el is not None and el.text and el.text.strip()!='' else None

fields = {
    'CdBerichtType': t('ns2:CdBerichtType'),
    'BSN (Burgerservicenr)': t('ns2:NatuurlijkPersoon/ns2:Burgerservicenr'),
    'Naam (SignificantDeelVanDeAchternaam)': t('ns2:NatuurlijkPersoon/ns2:SignificantDeelVanDeAchternaam'),
    'Geboortedat': t('ns2:NatuurlijkPersoon/ns2:Geboortedat'),
    'DatEersteAoDag': t('ns2:MeldingZiekte/ns2:DatEersteAoDag'),
    'FiscaalNr': t('ns2:Ketenpartij/ns2:FiscaalNr'),
    'Loonheffingennr': t('ns2:Ketenpartij/ns2:Loonheffingennr')
}
print('Parsed fields from',p)
for k,v in fields.items():
    print(f'- {k}: {v}')
