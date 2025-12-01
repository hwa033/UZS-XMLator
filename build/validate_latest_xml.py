from lxml import etree
import sys
xml_path = 'build/excel_generated/generated_bulk_20251128_124349.xml'
xsd_path = 'docs/UwvZwMeldingInternBody-v0428-b01.xsd'
try:
    schema_doc = etree.parse(xsd_path)
    schema = etree.XMLSchema(schema_doc)
    doc = etree.parse(xml_path)
    valid = schema.validate(doc)
    print(f'XSD valid: {valid}')
    if not valid:
        for e in schema.error_log:
            print(f'Line {e.line}: {e.message}')
    else:
        print('No XSD errors.')
except Exception as ex:
    print('Validation error:', ex)
