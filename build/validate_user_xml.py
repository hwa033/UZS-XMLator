from pathlib import Path
from lxml import etree
import xml.etree.ElementTree as ET
import sys

DOC_PATH = Path('docs') / 'UwvZwMeldingInternBody-v0428-b01-Envelope copy.xsd'
CLEAN_PATH = Path('build') / 'user_generated_131254.xml'


def load_doc(path: Path):
    if not path.exists():
        print('File not found:', path)
        sys.exit(2)
    raw = path.read_text(encoding='utf-8')
    # clean any leading HTML/text (e.g. browser wrapper) and find first '<'
    i = raw.find('<')
    if i > 0:
        raw = raw[i:]
    try:
        # write cleaned copy for downstream tools
        CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        CLEAN_PATH.write_text(raw, encoding='utf-8')
        return etree.fromstring(raw)
    except Exception as e:
        print('Failed to parse XML after cleaning:', e)
        sys.exit(3)


def extract_key_fields_etree(tree):
    # Use ElementTree for simple text extraction by local-name
    root = ET.fromstring(etree.tostring(tree))
    msgs = []
    for el in root.findall('.//'):
        if el.tag.split('}')[-1] == 'UwvZwMeldingInternBody':
            m = el
            def get_local(parent, child):
                for c in parent:
                    if c.tag.split('}')[-1] == child:
                        return c.text.strip() if c.text and c.text.strip() else None
                return None

            pers = None
            for c in m:
                if c.tag.split('}')[-1] == 'NatuurlijkPersoon':
                    pers = c
                    break
            bsn = None; naam = None; gebo = None
            if pers is not None:
                for c in pers:
                    ln = c.tag.split('}')[-1]
                    if ln == 'Burgerservicenr':
                        bsn = c.text.strip() if c.text and c.text.strip() else None
                    if ln == 'SignificantDeelVanDeAchternaam':
                        naam = c.text.strip() if c.text and c.text.strip() else None
                    if ln == 'Geboortedat':
                        gebo = c.text.strip() if c.text and c.text.strip() else None

            datEerste = None
            for c in m:
                if c.tag.split('}')[-1] == 'MeldingZiekte':
                    for cc in c:
                        if cc.tag.split('}')[-1] == 'DatEersteAoDag':
                            datEerste = cc.text.strip() if cc.text and cc.text.strip() else None
                            break
            # Ketenpartij
            fiscaal = None; loon = None
            for c in m:
                if c.tag.split('}')[-1] == 'Ketenpartij':
                    for cc in c:
                        if cc.tag.split('}')[-1] == 'FiscaalNr':
                            fiscaal = cc.text.strip() if cc.text and cc.text.strip() else None
                        if cc.tag.split('}')[-1] == 'Loonheffingennr':
                            loon = cc.text.strip() if cc.text and cc.text.strip() else None
            cd = get_local(m, 'CdBerichtType')
            msgs.append({'CdBerichtType': cd, 'BSN': bsn, 'Naam': naam, 'Geboortedat': gebo, 'DatEersteAoDag': datEerste, 'FiscaalNr': fiscaal, 'Loonheffingennr': loon})
    return msgs


def main():
    tree = load_doc(DOC_PATH)
    # normalize to ElementTree-compatible Element
    if isinstance(tree, etree._ElementTree):
        root = tree.getroot()
    else:
        root = tree
    # for schema validation we need an ElementTree
    tree_obj = etree.ElementTree(root)
    # Try to load schema from the app (if available)
    try:
        from web.app import _load_message_xsd, _LAST_XSD_ERROR
        schema = _load_message_xsd()
    except Exception:
        schema = None
        _LAST_XSD_ERROR = None

    # If app-provided loader didn't return a schema, attempt to load schema directly
    if schema is None:
        print('App loader did not return a schema; attempting direct XSD load...')
        try:
            xsd_path = Path('docs') / 'UwvZwMeldingInternBody-v0428-b01.xsd'
            perm_parser = etree.XMLParser(load_dtd=True, no_network=False)
            doc = etree.parse(str(xsd_path), perm_parser)
            schema = etree.XMLSchema(doc)
            print('Loaded schema directly from', xsd_path)
        except Exception as ex:
            schema = None
            print('Direct XSD load failed:', ex)

    # validate each UwvZwMeldingInternBody element if we have a schema
    if schema is None:
        print('Schema not available for validation.')
    else:
        bodies = []
        for el in tree_obj.findall('.//'):
            if el.tag.split('}')[-1] == 'UwvZwMeldingInternBody':
                bodies.append(el)
        if not bodies:
            print('No UwvZwMeldingInternBody elements found for validation')
        for i, b in enumerate(bodies, start=1):
            ok = schema.validate(b)
            print(f'Message {i}: XSD valid =', ok)
            if not ok:
                for e in schema.error_log:
                    print(' -', e.message)

    # extract key fields and print
    summaries = extract_key_fields_etree(tree)
    print('\nExtracted message summaries:')
    for i, s in enumerate(summaries, start=1):
        print(f'-- Message {i}:')
        for k, v in s.items():
            print(f'   {k}: {v}')


if __name__ == '__main__':
    main()
from pathlib import Path
from lxml import etree
import xml.etree.ElementTree as ET
import sys

DOC_PATH = Path('docs') / 'UwvZwMeldingInternBody-v0428-b01-Envelope copy.xsd'
CLEAN_PATH = Path('build') / 'user_generated_131254.xml'

def load_doc(path: Path):
    if not path.exists():
        print('File not found:', path)
        sys.exit(2)
    raw = path.read_text(encoding='utf-8')
    # clean any leading HTML/text (e.g. browser wrapper) and find first '<'
    i = raw.find('<')
    if i > 0:
        raw = raw[i:]
    try:
        # write cleaned copy for downstream tools
        CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
        CLEAN_PATH.write_text(raw, encoding='utf-8')
        return etree.fromstring(raw)
    except Exception as e:
        print('Failed to parse XML after cleaning:', e)
        sys.exit(3)

def extract_key_fields_etree(tree):
    # Use ElementTree for simple text extraction by local-name
    root = ET.fromstring(etree.tostring(tree))
    ns_body = 'http://schemas.uwv.nl/UwvML/Berichten/UwvZwMeldingInternBody-v0428'
    from pathlib import Path
    from lxml import etree
    import xml.etree.ElementTree as ET
    import sys

    DOC_PATH = Path('docs') / 'UwvZwMeldingInternBody-v0428-b01-Envelope copy.xsd'
    CLEAN_PATH = Path('build') / 'user_generated_131254.xml'


    def load_doc(path: Path):
        if not path.exists():
            print('File not found:', path)
            sys.exit(2)
        raw = path.read_text(encoding='utf-8')
        # clean any leading HTML/text (e.g. browser wrapper) and find first '<'
        i = raw.find('<')
        if i > 0:
            raw = raw[i:]
        try:
            # write cleaned copy for downstream tools
            CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
            CLEAN_PATH.write_text(raw, encoding='utf-8')
            return etree.fromstring(raw)
        except Exception as e:
            print('Failed to parse XML after cleaning:', e)
            sys.exit(3)


    def extract_key_fields_etree(tree):
        # Use ElementTree for simple text extraction by local-name
        root = ET.fromstring(etree.tostring(tree))
        msgs = []
        for el in root.findall('.//'):
            if el.tag.split('}')[-1] == 'UwvZwMeldingInternBody':
                m = el
                def get_local(parent, child):
                    for c in parent:
                        if c.tag.split('}')[-1] == child:
                            return c.text.strip() if c.text and c.text.strip() else None
                    return None

                pers = None
                for c in m:
                    if c.tag.split('}')[-1] == 'NatuurlijkPersoon':
                        pers = c
                        break
                bsn = None; naam = None; gebo = None
                if pers is not None:
                    for c in pers:
                        ln = c.tag.split('}')[-1]
                        if ln == 'Burgerservicenr':
                            bsn = c.text.strip() if c.text and c.text.strip() else None
                        if ln == 'SignificantDeelVanDeAchternaam':
                            naam = c.text.strip() if c.text and c.text.strip() else None
                        if ln == 'Geboortedat':
                            gebo = c.text.strip() if c.text and c.text.strip() else None

                datEerste = None
                for c in m:
                    if c.tag.split('}')[-1] == 'MeldingZiekte':
                        for cc in c:
                            if cc.tag.split('}')[-1] == 'DatEersteAoDag':
                                datEerste = cc.text.strip() if cc.text and cc.text.strip() else None
                                break
                # Ketenpartij
                fiscaal = None; loon = None
                for c in m:
                    if c.tag.split('}')[-1] == 'Ketenpartij':
                        for cc in c:
                            if cc.tag.split('}')[-1] == 'FiscaalNr':
                                fiscaal = cc.text.strip() if cc.text and cc.text.strip() else None
                            if cc.tag.split('}')[-1] == 'Loonheffingennr':
                                loon = cc.text.strip() if cc.text and cc.text.strip() else None
                cd = get_local(m, 'CdBerichtType')
                msgs.append({'CdBerichtType': cd, 'BSN': bsn, 'Naam': naam, 'Geboortedat': gebo, 'DatEersteAoDag': datEerste, 'FiscaalNr': fiscaal, 'Loonheffingennr': loon})
        return msgs


    def main():
        tree = load_doc(DOC_PATH)
        # normalize to ElementTree-compatible Element
        if isinstance(tree, etree._ElementTree):
            root = tree.getroot()
        else:
            root = tree
        # for schema validation we need an ElementTree
        tree_obj = etree.ElementTree(root)
        # Try to load schema from the app (if available)
        try:
            from web.app import _load_message_xsd, _LAST_XSD_ERROR
            schema = _load_message_xsd()
        except Exception:
            schema = None
            _LAST_XSD_ERROR = None

        # If app-provided loader didn't return a schema, attempt to load schema directly
        if schema is None:
            print('App loader did not return a schema; attempting direct XSD load...')
            try:
                xsd_path = Path('docs') / 'UwvZwMeldingInternBody-v0428-b01.xsd'
                perm_parser = etree.XMLParser(load_dtd=True, no_network=False)
                doc = etree.parse(str(xsd_path), perm_parser)
                schema = etree.XMLSchema(doc)
                print('Loaded schema directly from', xsd_path)
            except Exception as ex:
                schema = None
                print('Direct XSD load failed:', ex)

        # validate each UwvZwMeldingInternBody element if we have a schema
        if schema is None:
            print('Schema not available for validation.')
        else:
            bodies = []
            for el in tree_obj.findall('.//'):
                if el.tag.split('}')[-1] == 'UwvZwMeldingInternBody':
                    bodies.append(el)
            if not bodies:
                print('No UwvZwMeldingInternBody elements found for validation')
            for i, b in enumerate(bodies, start=1):
                ok = schema.validate(b)
                print(f'Message {i}: XSD valid =', ok)
                if not ok:
                    for e in schema.error_log:
                        print(' -', e.message)

        # extract key fields and print
        summaries = extract_key_fields_etree(tree)
        print('\nExtracted message summaries:')
        for i, s in enumerate(summaries, start=1):
            print(f'-- Message {i}:')
            for k, v in s.items():
                print(f'   {k}: {v}')


    if __name__ == '__main__':
        main()
