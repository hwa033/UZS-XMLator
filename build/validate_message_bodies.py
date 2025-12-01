from lxml import etree
xml_path = 'build/excel_generated/generated_bulk_20251128_124349.xml'
xsd_path = 'docs/UwvZwMeldingInternBody-v0428-b01.xsd'
try:
    schema_doc = etree.parse(xsd_path)
    schema = etree.XMLSchema(schema_doc)
    doc = etree.parse(xml_path)
    ns = {'ns2': 'http://schemas.uwv.nl/UwvML/Berichten/UwvZwMeldingInternBody-v0428'}
    bodies = doc.findall('.//ns2:UwvZwMeldingInternBody', ns)
    print(f'Found {len(bodies)} message bodies.')
    for i, body in enumerate(bodies, 1):
        valid = schema.validate(body)
        print(f'Message {i}: XSD valid = {valid}')
        if not valid:
            for e in schema.error_log:
                print(f'  Line {e.line}: {e.message}')
except Exception as ex:
    print('Validation error:', ex)
