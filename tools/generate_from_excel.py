"""
Generate SOAP-format XML messages from the Excel sheet
`docs/Input XML electr ziekmeldinge.xlsx`.

Behavior (minimal):
- Read the first worksheet, expect a header row with columns.
- For each data row, produce a SOAP-Envelope XML with a single
  `UwvZwMeldingInternBody` containing mapped fields.
- Save each XML to `build/excel_generated/generated_<BSN>_<timestamp>.xml`.
- Append a line to `build/logs/generator_excel.log` with status.

This is intentionally minimal and uses only `openpyxl` for reading
the Excel file and `xml.etree.ElementTree` for XML writing.
"""
from __future__ import annotations
import argparse
import os
from datetime import datetime, timezone
from typing import Dict, Iterable
import uuid
import xml.etree.ElementTree as ET

try:
    import openpyxl
except Exception:
    raise SystemExit("openpyxl is required to run this script. Install it in your environment.")


def read_excel_rows(path: str, data_only: bool = False):
    """Read all rows from the workbook and return a tuple (rows_list, formula_count).

    If `data_only` is True, `openpyxl` will prefer cached values over formulas
    (useful if the workbook was saved with calculated values). Regardless, any
    cell value that begins with '=' will be treated as a formula and sanitized
    to an empty string; such occurrences are counted and returned so callers
    can log or warn about them.
    """
    wb = openpyxl.load_workbook(path, read_only=True, data_only=data_only)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [h if h is not None else "" for h in next(rows_iter)]
    out_rows = []
    formula_count = 0
    for row in rows_iter:
        rec = {}
        for i in range(len(headers)):
            raw = row[i] if i < len(row) else None
            # sanitize formula-like strings to avoid embedding formulas in XML
            if isinstance(raw, str) and raw.strip().startswith("="):
                formula_count += 1
                value = ""
            else:
                value = raw
            rec[headers[i]] = value
        out_rows.append(rec)
    return out_rows, formula_count


def _namespaces():
    NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
    NS_UWVH = "http://schemas.uwv.nl/UwvML/Header-v0202"
    NS_BODY = "http://schemas.uwv.nl/UwvML/Berichten/UwvZwMeldingInternBody-v0428"
    ET.register_namespace('SOAP-ENV', NS_SOAP)
    ET.register_namespace('uwvh', NS_UWVH)
    return NS_SOAP, NS_UWVH, NS_BODY


def build_envelope_with_header_and_bodies(bodies: Iterable[ET.Element], sender: str = "Digipoort", tester_name: str = "tester") -> ET.Element:
    """Create a SOAP Envelope with header information and append provided message bodies.

    Header fields mimic the sample: RouteInformatie, BerichtIdentificatie and Transactie.
    """
    ns_soap, ns_uwvh, ns_body = _namespaces()
    env = ET.Element("{" + ns_soap + "}Envelope")
    header = ET.SubElement(env, "{" + ns_soap + "}Header")
    uwvh = ET.SubElement(header, "{" + ns_uwvh + "}UwvMLHeader")

    # RouteInformatie
    route = ET.SubElement(uwvh, "RouteInformatie")
    bron = ET.SubElement(route, "Bron")
    ET.SubElement(bron, "ApplicatieNaam").text = sender
    ET.SubElement(bron, "DatTijdVersturenBericht").text = datetime.now(timezone.utc).astimezone().isoformat()
    dst = ET.SubElement(route, "Bestemming")
    ET.SubElement(dst, "ApplicatieNaam").text = "UZS"
    ET.SubElement(route, "GegevensUitwisselingsnr").text = f"GegUitNr-{uuid.uuid4().hex[:8]}"
    ET.SubElement(route, "RefnrGegevensUitwisselingsExtern").text = "NOCOREFLEX"

    # BerichtIdentificatie - use tester name + timestamp (max 50 chars)
    bi = ET.SubElement(uwvh, "BerichtIdentificatie")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    safe_name = tester_name.replace(" ", "")[:30]  # sanitize and limit name
    ET.SubElement(bi, "BerichtReferentienr").text = f"{safe_name}_{ts}"[:50]
    bt = ET.SubElement(bi, "BerichtType")
    ET.SubElement(bt, "BerichtNaam").text = "UwvZwMeldingInternBody"
    ET.SubElement(bt, "VersieMajor").text = "04"
    ET.SubElement(bt, "VersieMinor").text = "28"
    ET.SubElement(bt, "Buildnr").text = "01"
    ET.SubElement(bt, "CommunicatieType").text = "Melding"
    ET.SubElement(bt, "CommunicatieElement").text = "Melding"
    ET.SubElement(bi, "DatTijdAanmaakBericht").text = datetime.now(timezone.utc).astimezone().isoformat()
    ET.SubElement(bi, "IndTestbericht").text = "2"

    # Transactie
    tr = ET.SubElement(uwvh, "Transactie")
    ET.SubElement(tr, "TransactieReferentienr").text = f"TraRef-{uuid.uuid4().hex[:8]}"
    ET.SubElement(tr, "Volgordenr").text = "1"
    ET.SubElement(tr, "IndLaatsteBericht").text = "1"

    body = ET.SubElement(env, "{" + ns_soap + "}Body")
    for b in bodies:
        body.append(b)

    return env


def save_envelope(envelope: ET.Element, out_dir: str, basename_hint: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"generated_{basename_hint}_{ts}.xml"
    path = os.path.join(out_dir, filename)
    try:
        ET.indent(envelope)  # pretty print (Python 3.9+)
    except Exception:
        pass
    tree = ET.ElementTree(envelope)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    return path


def append_log(log_path: str, entry: str) -> None:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(entry + "\n")


def build_message_element(record: Dict[str, str], ns_body: str) -> ET.Element:
    """Create a `UwvZwMeldingInternBody` element (without Envelope/Body wrapper).

    This function is intentionally minimal and maps Excel columns to
    the child elements used in the sample XML.
    """
    msg = ET.Element("{" + ns_body + "}UwvZwMeldingInternBody")

    def qname(tag: str) -> str:
        return "{" + ns_body + "}" + tag

    def set_if(parent, tag, value):
        if value is None:
            return
        s = str(value).strip()
        if s == "":
            return
        ET.SubElement(parent, qname(tag)).text = s

    def set_date_if(parent, tag, value, date_only=True):
        if value is None:
            return
        # normalize common date/datetime representations to ISO
        try:
            if isinstance(value, datetime):
                if date_only:
                    out = value.strftime("%Y%m%d")
                else:
                    out = value.strftime("%Y%m%d%H%M%S")
                ET.SubElement(parent, qname(tag)).text = out
                return
            s = str(value).strip()
            if s == "":
                return
            # if value is compact numeric YYYYMMDD, keep as-is for date-only
            if len(s) == 8 and s.isdigit():
                if date_only:
                    out = s  # keep YYYYMMDD format
                else:
                    out = f"{s}000000" if len(s) == 8 else s
                ET.SubElement(parent, qname(tag)).text = out
                return
            # try ISO parse
            try:
                dt = datetime.fromisoformat(s)
                if date_only:
                    out = dt.strftime("%Y%m%d")
                else:
                    out = dt.strftime("%Y%m%d%H%M%S")
                ET.SubElement(parent, qname(tag)).text = out
                return
            except Exception:
                # fallback: do not write if unclear
                return
        except Exception:
            return

    # Prefer an explicit CdBerichtType provided in the Excel row (common headers
    # include 'CdBerichtType', 'aanvraag_type' or 'Type'). If none present,
    # default to OTP3 which is the Digipoort/OTP3 message code.
    try:
        aanvraag_map = {"Digipoort": "OTP3"}
        excel_cd_names = ['CdBerichtType', 'aanvraag_type', 'Type']
        excel_cd = None
        for n in excel_cd_names:
            v = record.get(n)
            if v is not None and str(v).strip() != '':
                excel_cd = str(v).strip()
                break
        if excel_cd:
            cd_val = aanvraag_map.get(excel_cd, excel_cd)
        else:
            cd_val = "OTP3"
    except Exception:
        cd_val = "OTP3"
    ET.SubElement(msg, qname("CdBerichtType")).text = cd_val
    ET.SubElement(msg, qname("IndAlleenControleUzs")).text = record.get("IndAlleenControleUzs", "2")

    # Ketenpartij
    kp = ET.SubElement(msg, qname("Ketenpartij"))
    lhn = record.get("Loonheffingennummer") or record.get("Loonheffingennr") or record.get("Loonheffingennr")
    if lhn:
        set_if(kp, "FiscaalNr", str(lhn)[:9])
        set_if(kp, "Loonheffingennr", str(lhn))
    set_if(kp, "Naam", record.get("IndienerNaam", None))
    ET.SubElement(kp, qname("CdRolKetenpartij")).text = record.get("CdRolKetenpartij", "01")
    ET.SubElement(kp, qname("CdSrtIndiener")).text = record.get("CdSrtIndiener", "WG")
    ET.SubElement(kp, qname("NaamSoftwarePakket")).text = record.get("NaamSoftwarePakket", "Generated")
    ET.SubElement(kp, qname("VersieSoftwarePakket")).text = record.get("VersieSoftwarePakket", "1.0")
    ET.SubElement(kp, qname("BerichtkenmerkIndiener")).text = record.get("BerichtkenmerkIndiener", "")
    ET.SubElement(kp, qname("VolgNr")).text = record.get("VolgNr", "1")
    kp_c = ET.SubElement(kp, qname("Contactgegevens"))
    ET.SubElement(kp_c, qname("NaamContactpersoonAfd")).text = record.get("Kp_NaamContactpersoon", "")
    ET.SubElement(kp_c, qname("TelefoonnrContactpersoonAfd")).text = record.get("Kp_TelefoonnrContactpersoonAfd", "")

    # NatuurlijkPersoon
    np = ET.SubElement(msg, qname("NatuurlijkPersoon"))
    bsn = record.get("BSN")
    if bsn is not None:
        set_if(np, "Burgerservicenr", bsn)
    geb = record.get("Geboortedatum")
    set_date_if(np, "Geboortedat", geb, date_only=True)
    # optional flags
    set_if(np, "IndOverlijden", record.get("IndOverlijden", None))
    set_if(np, "Geslacht", record.get("Geslacht", None))
    set_if(np, "EersteVoornaam", record.get("EersteVoornaam", None))
    set_if(np, "Voorletters", record.get("Voorletters", None))
    set_if(np, "Voorvoegsel", record.get("Voorvoegsel", None))
    ach = record.get("Achternaam")
    if ach is not None:
        set_if(np, "SignificantDeelVanDeAchternaam", ach)
    set_if(np, "Telefoonnr", record.get("Telefoonnr", None))
    set_if(np, "TelefoonnrMobiel", record.get("TelefoonnrMobiel", None))
    set_if(np, "TelefoonnrBuitenland", record.get("TelefoonnrBuitenland", None))

    # Contactgegevens (top-level)
    contact = ET.SubElement(msg, qname("Contactgegevens"))
    set_if(contact, "NaamContactpersoonAfd", record.get("Contact_NaamContactpersoonAfd", None))
    set_if(contact, "Geslacht", record.get("Contact_Geslacht", None))
    set_if(contact, "TelefoonnrContactpersoonAfd", record.get("Contact_TelefoonnrContactpersoonAfd", None))
    set_if(contact, "NrLokaleVestiging", record.get("Contact_NrLokaleVestiging", None))
    set_if(contact, "EMailAdres", record.get("Contact_EMailAdres", None))

    # MeldingZiekte
    mz = ET.SubElement(msg, qname("MeldingZiekte"))
    set_if(mz, "IndVerzoekTotIntrekken", record.get("IndVerzoekTotIntrekken", None))
    set_if(mz, "ReferentieMelding", record.get("ReferentieMelding", None))
    # DatTijdOpstellenMelding expects a datetime-like value
    set_date_if(mz, "DatTijdOpstellenMelding", record.get("DatTijdOpstellenMelding", None), date_only=False)
    set_date_if(mz, "DatOntvangstMeldingWerkgever", record.get("DatOntvangstMeldingWerkgever", None), date_only=True)
    d1 = record.get("DatEersteAoDag")
    set_date_if(mz, "DatEersteAoDag", d1, date_only=True)
    set_if(mz, "ToelichtingMelding", record.get("ToelichtingMelding", None))
    set_if(mz, "IndWerkverplichtingEersteAoDag", record.get("IndWerkverplichtingEersteAoDag", None))
    set_if(mz, "IndDirecteUitkering", record.get("IndDirecteUitkering", None))
    set_if(mz, "CdRedenAangifteAo", record.get("CdRedenAangifteAo", None))
    set_if(mz, "CdRedenZiekmelding", record.get("CdRedenZiekmelding", None))
    set_if(mz, "AantGewerkteUrenEersteAoDag", record.get("AantGewerkteUrenEersteAoDag", None))
    set_if(mz, "AantRoosterurenEersteAoDag", record.get("AantRoosterurenEersteAoDag", None))
    set_if(mz, "IndWerkdagOpZaterdag", record.get("IndWerkdagOpZaterdag", None))
    set_if(mz, "IndWerkdagOpZondag", record.get("IndWerkdagOpZondag", None))
    set_if(mz, "BedrSvLoonGedWerkenEersteAoDag", record.get("BedrSvLoonGedWerkenEersteAoDag", None))
    set_if(mz, "CdRedenRegres", record.get("CdRedenRegres", None))
    set_if(mz, "OmsRedenTeLateAanvraagUitkering", record.get("OmsRedenTeLateAanvraagUitkering", None))
    set_if(mz, "GemiddeldAantWerkurenPerWeek", record.get("GemiddeldAantWerkurenPerWeek", None))
    set_if(mz, "IndEDnstvrbndCtrTijdensZiekte", record.get("IndEDnstvrbndCtrTijdensZiekte", None))

    # AdministratieveEenheid
    ae = ET.SubElement(msg, qname("AdministratieveEenheid"))
    set_if(ae, "Loonheffingennr", record.get("Loonheffingennummer", None))
    set_if(ae, "Naam", record.get("AE_Naam", None))
    bank = ET.SubElement(ae, qname("Bankrekening"))
    set_if(bank, "Bankrekeningnr", record.get("Bankrekeningnr", None))
    set_if(bank, "Bic", record.get("BIC", record.get("Bic", None)))
    set_if(bank, "Iban", record.get("Rekeningnummer (IBAN)", record.get("IBAN", None)))
    sr = ET.SubElement(ae, qname("SectorRisicogroep"))
    set_if(sr, "CdRisicopremiegroep", record.get("CdRisicopremiegroep", None))
    set_if(sr, "CdSectorOsv", record.get("CdSectorOsv", None))
    arb = ET.SubElement(ae, qname("Arbeidsverhouding"))
    set_if(arb, "Volgnr", record.get("Volgnr", None))
    set_if(arb, "IndLoonheffingskorting", record.get("IndLoonheffingskorting", None))
    set_if(arb, "Personeelsnr", record.get("Personeelsnr", None))
    set_if(arb, "NaamBeroepOngecodeerd", record.get("NaamBeroepOngecodeerd", None))
    set_if(arb, "CdAardArbv", record.get("CdAardArbv", None))
    set_if(arb, "CdLbtabel", record.get("CdLbtabel", None))
    set_date_if(arb, "DatB", record.get("DatB", None), date_only=True)
    set_if(arb, "AantLoonwachtdagen", record.get("AantLoonwachtdagen", None))
    set_if(arb, "PercLoondoorbetalingTijdensAo", record.get("PercLoondoorbetalingTijdensAo", None))
    set_if(arb, "IndArbeidsgehandicapt", record.get("IndArbeidsgehandicapt", None))

    return msg
    # Add any remaining columns from the Excel that were not explicitly
    # mapped above. This makes the generator adapt to uploads where the
    # header contains extra fields — each non-empty extra column becomes
    # a direct child element of `UwvZwMeldingInternBody` with a
    # sanitized tag name derived from the header.
    known_keys = {
        'IndAlleenControleUzs', 'Loonheffingennummer', 'IndienerNaam', 'CdRolKetenpartij',
        'CdSrtIndiener', 'NaamSoftwarePakket', 'VersieSoftwarePakket', 'BerichtkenmerkIndiener',
        'VolgNr', 'Kp_NaamContactpersoon', 'Kp_TelefoonnrContactpersoonAfd', 'BSN', 'Geboortedatum',
        'IndOverlijden', 'Geslacht', 'EersteVoornaam', 'Voorletters', 'Voorvoegsel', 'Achternaam',
        'Telefoonnr', 'TelefoonnrMobiel', 'TelefoonnrBuitenland', 'Contact_NaamContactpersoonAfd',
        'Contact_Geslacht', 'Contact_TelefoonnrContactpersoonAfd', 'Contact_NrLokaleVestiging',
        'Contact_EMailAdres', 'IndVerzoekTotIntrekken', 'ReferentieMelding', 'DatTijdOpstellenMelding',
        'DatOntvangstMeldingWerkgever', 'DatEersteAoDag', 'ToelichtingMelding', 'IndWerkverplichtingEersteAoDag',
        'IndDirecteUitkering', 'CdRedenAangifteAo', 'CdRedenZiekmelding', 'AantGewerkteUrenEersteAoDag',
        'AantRoosterurenEersteAoDag', 'IndWerkdagOpZaterdag', 'IndWerkdagOpZondag', 'BedrSvLoonGedWerkenEersteAoDag',
        'CdRedenRegres', 'OmsRedenTeLateAanvraagUitkering', 'GemiddeldAantWerkurenPerWeek',
        'IndEDnstvrbndCtrTijdensZiekte', 'AE_Naam', 'Bankrekeningnr', 'BIC', 'Rekeningnummer (IBAN)',
        'IBAN', 'CdRisicopremiegroep', 'CdSectorOsv', 'Volgnr', 'IndLoonheffingskorting', 'Personeelsnr',
        'NaamBeroepOngecodeerd', 'CdAardArbv', 'CdLbtabel', 'DatB', 'AantLoonwachtdagen',
        'PercLoondoorbetalingTijdensAo', 'IndArbeidsgehandicapt'
    }

    import re

    def _sanitize_tag(name: str) -> str:
        # Remove leading/trailing whitespace
        t = name.strip()
        # replace spaces and slashes with underscores
        t = re.sub(r"[\s/]+", "_", t)
        # remove characters that are invalid in XML names
        t = re.sub(r"[^0-9A-Za-z_\-\.:]", "", t)
        # XML names must not start with a digit or punctuation; prefix if needed
        if re.match(r"^[0-9\-\.:]", t):
            t = f"F_{t}"
        # avoid empty tag name
        if not t:
            t = "Field"
        return t

    for key, val in record.items():
        if key in known_keys:
            continue
        if val is None:
            continue
        if isinstance(val, str) and val.strip() == "":
            continue
        tag = _sanitize_tag(str(key))
        ET.SubElement(msg, tag).text = str(val)

    return msg


def main():
    parser = argparse.ArgumentParser(description="Generate SOAP XML from the Excel sheet")
    parser.add_argument("--mode", choices=("single", "bulk"), default="bulk", help="single: one file per row; bulk: single file containing all messages")
    parser.add_argument("--input", default=r"docs/Input XML electr ziekmeldinge.xlsx", help="Path to input Excel file")
    parser.add_argument("--outdir", default=r"build/excel_generated", help="Output directory for XML files")
    parser.add_argument("--log", default=r"build/logs/generator_excel.log", help="Path to append logs")
    parser.add_argument("--data-only", action="store_true", help="Open workbook with openpyxl data_only=True to prefer cached values over formulas")
    args = parser.parse_args()

    src = os.path.abspath(args.input)
    out_dir = os.path.abspath(args.outdir)
    log_path = os.path.abspath(args.log)

    # Read rows and build message elements
    messages = []
    rows, formula_count = read_excel_rows(src, data_only=args.data_only)
    for rec in rows:
        try:
            # build per-row message element (namespaced)
            _, _, ns_body = _namespaces()
            msg = build_message_element(rec, ns_body)
            messages.append((rec, msg))
        except Exception as exc:
            append_log(log_path, f"{datetime.now(timezone.utc).isoformat()}\tERROR_BUILD_MSG\t{exc}")

    processed = 0
    if args.mode == "bulk":
        # create one envelope containing all message bodies
        bodies = [m for (_, m) in messages]
        envelope = build_envelope_with_header_and_bodies(bodies)
        saved = save_envelope(envelope, out_dir, "bulk")
        append_log(log_path, f"{datetime.now(timezone.utc).isoformat()}Z\t{saved}\tSUCCESS\t{len(bodies)}")
        processed = len(bodies)
        if formula_count:
            append_log(log_path, f"{datetime.now(timezone.utc).isoformat()}Z\tSANITIZED_FORMULAS\t{formula_count}")
    else:
        # single mode: one envelope per message
        for idx, (rec, m) in enumerate(messages, start=1):
            try:
                env = build_envelope_with_header_and_bodies([m])
                bsn = rec.get("BSN") or f"row{idx}"
                safe_bsn = str(bsn).replace(" ", "_")
                saved = save_envelope(env, out_dir, safe_bsn)
                append_log(log_path, f"{datetime.now(timezone.utc).isoformat()}Z\t{saved}\tSUCCESS")
                processed += 1
            except Exception as exc:
                append_log(log_path, f"{datetime.now(timezone.utc).isoformat()}Z\tERROR_SAVE\t{exc}")
        if formula_count:
            append_log(log_path, f"{datetime.now(timezone.utc).isoformat()}Z\tSANITIZED_FORMULAS\t{formula_count}")

    print(f"Processed {processed} rows; outputs written to: {out_dir}")


if __name__ == '__main__':
    main()
