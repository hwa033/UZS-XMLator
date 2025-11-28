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


def build_envelope_with_header_and_bodies(bodies: Iterable[ET.Element], sender: str = "Digipoort") -> ET.Element:
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

    # BerichtIdentificatie
    bi = ET.SubElement(uwvh, "BerichtIdentificatie")
    ET.SubElement(bi, "BerichtReferentienr").text = f"BerRef-{uuid.uuid4().hex[:8]}"
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
    ET.SubElement(msg, "CdBerichtType").text = "OTP3"
    ET.SubElement(msg, "IndAlleenControleUzs").text = record.get("IndAlleenControleUzs", "2")

    # Ketenpartij
    kp = ET.SubElement(msg, "Ketenpartij")
    lhn = record.get("Loonheffingennummer")
    if lhn:
        ET.SubElement(kp, "FiscaalNr").text = lhn[:9]
        ET.SubElement(kp, "Loonheffingennr").text = str(lhn)
    else:
        ET.SubElement(kp, "FiscaalNr").text = ""
        ET.SubElement(kp, "Loonheffingennr").text = ""
    ET.SubElement(kp, "Naam").text = record.get("IndienerNaam", "")
    ET.SubElement(kp, "CdRolKetenpartij").text = record.get("CdRolKetenpartij", "01")
    ET.SubElement(kp, "CdSrtIndiener").text = record.get("CdSrtIndiener", "WG")
    ET.SubElement(kp, "NaamSoftwarePakket").text = record.get("NaamSoftwarePakket", "Generated")
    ET.SubElement(kp, "VersieSoftwarePakket").text = record.get("VersieSoftwarePakket", "1.0")
    ET.SubElement(kp, "BerichtkenmerkIndiener").text = record.get("BerichtkenmerkIndiener", "")
    ET.SubElement(kp, "VolgNr").text = record.get("VolgNr", "1")
    kp_c = ET.SubElement(kp, "Contactgegevens")
    ET.SubElement(kp_c, "NaamContactpersoonAfd").text = record.get("Kp_NaamContactpersoon", "")
    ET.SubElement(kp_c, "TelefoonnrContactpersoonAfd").text = record.get("Kp_TelefoonnrContactpersoonAfd", "")

    # NatuurlijkPersoon
    np = ET.SubElement(msg, "NatuurlijkPersoon")
    bsn = record.get("BSN")
    if bsn is not None:
        ET.SubElement(np, "Burgerservicenr").text = str(bsn)
    geb = record.get("Geboortedatum")
    if geb is not None:
        ET.SubElement(np, "Geboortedat").text = str(geb)
    ET.SubElement(np, "IndOverlijden").text = record.get("IndOverlijden", "2")
    ET.SubElement(np, "Geslacht").text = record.get("Geslacht", "")
    ET.SubElement(np, "EersteVoornaam").text = record.get("EersteVoornaam", "")
    ET.SubElement(np, "Voorletters").text = record.get("Voorletters", "")
    ET.SubElement(np, "Voorvoegsel").text = record.get("Voorvoegsel", "")
    ach = record.get("Achternaam")
    if ach is not None:
        ET.SubElement(np, "SignificantDeelVanDeAchternaam").text = str(ach)
    ET.SubElement(np, "Telefoonnr").text = record.get("Telefoonnr", "")
    ET.SubElement(np, "TelefoonnrMobiel").text = record.get("TelefoonnrMobiel", "")
    ET.SubElement(np, "TelefoonnrBuitenland").text = record.get("TelefoonnrBuitenland", "")

    # Contactgegevens (top-level)
    contact = ET.SubElement(msg, "Contactgegevens")
    ET.SubElement(contact, "NaamContactpersoonAfd").text = record.get("Contact_NaamContactpersoonAfd", "")
    ET.SubElement(contact, "Geslacht").text = record.get("Contact_Geslacht", "")
    ET.SubElement(contact, "TelefoonnrContactpersoonAfd").text = record.get("Contact_TelefoonnrContactpersoonAfd", "")
    ET.SubElement(contact, "NrLokaleVestiging").text = record.get("Contact_NrLokaleVestiging", "")
    ET.SubElement(contact, "EMailAdres").text = record.get("Contact_EMailAdres", "")

    # MeldingZiekte
    mz = ET.SubElement(msg, "MeldingZiekte")
    ET.SubElement(mz, "IndVerzoekTotIntrekken").text = record.get("IndVerzoekTotIntrekken", "2")
    ET.SubElement(mz, "ReferentieMelding").text = record.get("ReferentieMelding", "ReferentieMelding - MeldingZiekte")
    ET.SubElement(mz, "DatTijdOpstellenMelding").text = record.get("DatTijdOpstellenMelding", "")
    ET.SubElement(mz, "DatOntvangstMeldingWerkgever").text = record.get("DatOntvangstMeldingWerkgever", "")
    d1 = record.get("DatEersteAoDag")
    if d1 is not None:
        ET.SubElement(mz, "DatEersteAoDag").text = str(d1)
    ET.SubElement(mz, "ToelichtingMelding").text = record.get("ToelichtingMelding", "")
    ET.SubElement(mz, "IndWerkverplichtingEersteAoDag").text = record.get("IndWerkverplichtingEersteAoDag", "1")
    idd = record.get("IndDirecteUitkering")
    if idd is not None:
        ET.SubElement(mz, "IndDirecteUitkering").text = str(idd)
    ET.SubElement(mz, "CdRedenAangifteAo").text = record.get("CdRedenAangifteAo", "")
    ET.SubElement(mz, "CdRedenZiekmelding").text = record.get("CdRedenZiekmelding", "")
    ET.SubElement(mz, "AantGewerkteUrenEersteAoDag").text = record.get("AantGewerkteUrenEersteAoDag", "")
    ET.SubElement(mz, "AantRoosterurenEersteAoDag").text = record.get("AantRoosterurenEersteAoDag", "")
    ET.SubElement(mz, "IndWerkdagOpZaterdag").text = record.get("IndWerkdagOpZaterdag", "2")
    ET.SubElement(mz, "IndWerkdagOpZondag").text = record.get("IndWerkdagOpZondag", "2")
    ET.SubElement(mz, "BedrSvLoonGedWerkenEersteAoDag").text = record.get("BedrSvLoonGedWerkenEersteAoDag", "")
    ET.SubElement(mz, "CdRedenRegres").text = record.get("CdRedenRegres", "")
    ET.SubElement(mz, "OmsRedenTeLateAanvraagUitkering").text = record.get("OmsRedenTeLateAanvraagUitkering", "")
    ET.SubElement(mz, "GemiddeldAantWerkurenPerWeek").text = record.get("GemiddeldAantWerkurenPerWeek", "")
    ET.SubElement(mz, "IndEDnstvrbndCtrTijdensZiekte").text = record.get("IndEDnstvrbndCtrTijdensZiekte", "")

    # AdministratieveEenheid
    ae = ET.SubElement(msg, "AdministratieveEenheid")
    ET.SubElement(ae, "Loonheffingennr").text = record.get("Loonheffingennummer", "")
    ET.SubElement(ae, "Naam").text = record.get("AE_Naam", "")
    bank = ET.SubElement(ae, "Bankrekening")
    ET.SubElement(bank, "Bankrekeningnr").text = record.get("Bankrekeningnr", "")
    ET.SubElement(bank, "Bic").text = record.get("BIC", record.get("Bic", ""))
    ET.SubElement(bank, "Iban").text = record.get("Rekeningnummer (IBAN)", record.get("IBAN", ""))
    sr = ET.SubElement(ae, "SectorRisicogroep")
    ET.SubElement(sr, "CdRisicopremiegroep").text = record.get("CdRisicopremiegroep", "")
    ET.SubElement(sr, "CdSectorOsv").text = record.get("CdSectorOsv", "")
    arb = ET.SubElement(ae, "Arbeidsverhouding")
    ET.SubElement(arb, "Volgnr").text = record.get("Volgnr", "1")
    ET.SubElement(arb, "IndLoonheffingskorting").text = record.get("IndLoonheffingskorting", "1")
    ET.SubElement(arb, "Personeelsnr").text = record.get("Personeelsnr", "")
    ET.SubElement(arb, "NaamBeroepOngecodeerd").text = record.get("NaamBeroepOngecodeerd", "")
    ET.SubElement(arb, "CdAardArbv").text = record.get("CdAardArbv", "")
    ET.SubElement(arb, "CdLbtabel").text = record.get("CdLbtabel", "")
    ET.SubElement(arb, "DatB").text = record.get("DatB", "")
    ET.SubElement(arb, "AantLoonwachtdagen").text = record.get("AantLoonwachtdagen", "")
    ET.SubElement(arb, "PercLoondoorbetalingTijdensAo").text = record.get("PercLoondoorbetalingTijdensAo", "")
    ET.SubElement(arb, "IndArbeidsgehandicapt").text = record.get("IndArbeidsgehandicapt", "")

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
