import sys
from xml.etree import ElementTree as ET
from pathlib import Path

ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
      'body': 'http://schemas.uwv.nl/UwvML/Berichten/UwvZwMeldingInternBody-v0428',
      'uwvh': 'http://schemas.uwv.nl/UwvML/Header-v0202'}


def load_xml(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    try:
        tree = ET.parse(str(p))
        return tree
    except Exception as e:
        raise RuntimeError(f"Failed to parse {p}: {e}")


def extract_messages(tree):
    root = tree.getroot()
    body = root.find('soap:Body', ns)
    if body is None:
        return []
    msgs = []
    # find any child where local-name == UwvZwMeldingInternBody
    for mb in body.findall('.//'):
        if mb.tag.endswith('UwvZwMeldingInternBody'):
            msgs.append(mb)
    # fallback: any element named UwvZwMeldingInternBody anywhere
    if not msgs:
        for el in body.iter():
            if el.tag.split('}')[-1] == 'UwvZwMeldingInternBody':
                msgs.append(el)
    return msgs


def get_text(el, childname):
    # search by local-name
    for c in el:
        if c.tag.split('}')[-1] == childname:
            txt = c.text.strip() if c.text and c.text.strip() else None
            return txt
    return None


def person_fields(msg):
    # Burgerservicenr, SignificantDeelVanDeAchternaam, Geboortedat
    pers = None
    for c in msg:
        if c.tag.split('}')[-1] == 'NatuurlijkPersoon':
            pers = c
            break
    if pers is None:
        return {}
    return {
        'BSN': get_text(pers, 'Burgerservicenr'),
        'Naam': get_text(pers, 'SignificantDeelVanDeAchternaam'),
        'Geboortedat': get_text(pers, 'Geboortedat')
    }


def summary_from_tree(tree):
    msgs = extract_messages(tree)
    summaries = []
    for m in msgs:
        summ = {}
        summ['CdBerichtType'] = get_text(m, 'CdBerichtType')
        summ.update(person_fields(m))
        summ['DatEersteAoDag'] = None
        for c in m:
            if c.tag.split('}')[-1] == 'MeldingZiekte':
                summ['DatEersteAoDag'] = get_text(c, 'DatEersteAoDag')
                break
        # Ketenpartij fiscal and loonheffing
        ket = None
        for c in m:
            if c.tag.split('}')[-1] == 'Ketenpartij':
                ket = c; break
        if ket is not None:
            summ['FiscaalNr'] = get_text(ket, 'FiscaalNr')
            summ['Loonheffingennr'] = get_text(ket, 'Loonheffingennr')
        else:
            summ['FiscaalNr'] = None
            summ['Loonheffingennr'] = None
        summaries.append(summ)
    return summaries


def compare_summaries(s1, s2):
    out = []
    out.append(f'Message counts: left={len(s1)} right={len(s2)}')
    count = min(len(s1), len(s2))
    for i in range(count):
        a = s1[i]
        b = s2[i]
        diffs = []
        for k in ['CdBerichtType','BSN','Naam','Geboortedat','DatEersteAoDag','FiscaalNr','Loonheffingennr']:
            av = a.get(k)
            bv = b.get(k)
            if (av or '') != (bv or ''):
                diffs.append((k,av,bv))
        if diffs:
            out.append(f'-- Differences in message {i+1}:')
            for d in diffs:
                out.append(f"   {d[0]}: left={d[1]!r} right={d[2]!r}")
        else:
            out.append(f'-- Message {i+1}: identical key fields')
    if len(s1) != len(s2):
        out.append('Note: different message counts; additional messages printed')
        longer = s1 if len(s1)>len(s2) else s2
        side = 'left' if len(s1)>len(s2) else 'right'
        for i in range(count, len(longer)):
            out.append(f'-- Extra message in {side} index {i+1}: {longer[i]}')
    return '\n'.join(out)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: compare_xmls.py <other-xml-path> [base-xml-path]')
        print('If base-xml-path is omitted, the script compares against build/excel_generated/generated_bulk_20251128_123700.xml')
        sys.exit(1)
    other = sys.argv[1]
    base = sys.argv[2] if len(sys.argv)>2 else 'build/excel_generated/generated_bulk_20251128_123700.xml'
    try:
        t_base = load_xml(base)
    except Exception as e:
        print('Failed to load base file',base,':',e)
        sys.exit(2)
    try:
        t_other = load_xml(other)
    except Exception as e:
        print('Failed to load other file',other,':',e)
        sys.exit(3)
    s1 = summary_from_tree(t_base)
    s2 = summary_from_tree(t_other)
    print('Comparison result:\n')
    print(compare_summaries(s1,s2))
