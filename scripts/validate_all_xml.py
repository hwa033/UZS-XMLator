import glob
from pathlib import Path
from lxml import etree

XSD_PATH = Path('docs') / 'UwvZwMeldingInternBody-v0428-b01.xsd'
SOAP_ENV = 'http://schemas.xmlsoap.org/soap/envelope/'


def validate_file(path: str, schema: etree.XMLSchema) -> tuple[str, bool, list[str]]:
    errors: list[str] = []
    try:
        root = etree.parse(path).getroot()
        body = root.find(f'.//{{{SOAP_ENV}}}Body')
        if body is None or len(body) == 0:
            return path, False, ['No SOAP Body or empty body']
        child = next(iter(body))
        ok = schema.validate(child)
        if not ok:
            for e in schema.error_log:
                errors.append(f'Line {e.line}: {e.message}')
        return path, ok, errors
    except Exception as ex:
        return path, False, [str(ex)]


def main() -> int:
    if not XSD_PATH.exists():
        print(f'XSD not found: {XSD_PATH}')
        return 1
    parser = etree.XMLParser(load_dtd=True, no_network=False)
    schema = etree.XMLSchema(etree.parse(str(XSD_PATH), parser))

    paths = []
    paths += glob.glob('docs/*.xml')
    paths += glob.glob('web/resultaten/*.xml')
    paths += glob.glob('build/*.xml')
    paths += glob.glob('build/excel_generated/*.xml')
    paths += glob.glob('build/minimal_xml_output/*.xml')
    paths += glob.glob('build/UZS_XMLator/*.xml')

    if not paths:
        print('No XML files found in docs/ or web/resultaten/')
        return 0

    total = 0
    ok_count = 0
    failed = []

    for p in sorted(paths):
        total += 1
        path, ok, errs = validate_file(p, schema)
        status = 'OK' if ok else 'FAIL'
        print(f'{path}: {status}')
        if not ok:
            failed.append((path, errs))
        else:
            ok_count += 1

    print('\nSummary:')
    print(f'  Total:  {total}')
    print(f'  Passed: {ok_count}')
    print(f'  Failed: {total - ok_count}')

    if failed:
        print('\nFailures:')
        for path, errs in failed:
            for msg in errs:
                print(f'  {path}: {msg}')
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
