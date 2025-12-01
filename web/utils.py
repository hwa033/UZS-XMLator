import datetime
import json
from pathlib import Path
from typing import Optional

from lxml import etree


def _format_date_yyyymmdd(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.strftime("%Y%m%d")
    try:
        if isinstance(value, (int, float)):
            serial = float(value)
            if serial > 0 and serial < 60000:
                base = datetime.datetime(1899, 12, 30)
                try:
                    dt = base + datetime.timedelta(days=serial)
                    return dt.strftime("%Y%m%d")
                except Exception:
                    pass
        if isinstance(value, str) and value.isdigit():
            serial = float(value)
            if serial > 0 and serial < 60000:
                base = datetime.datetime(1899, 12, 30)
                try:
                    dt = base + datetime.timedelta(days=serial)
                    return dt.strftime("%Y%m%d")
                except Exception:
                    pass
    except Exception:
        pass
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d%m%Y", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            dt = datetime.datetime.strptime(s, fmt)
            return dt.strftime("%Y%m%d")
        except Exception:
            continue
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) == 8:
        return digits
    return s


def _get_success_rate(events_path: Path) -> Optional[str]:
    try:
        total = 0
        success = 0
        if events_path.exists():
            with open(events_path, "r", encoding="utf-8") as ef:
                for line in ef:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                        total += 1
                        if ev.get("success"):
                            success += 1
                    except Exception:
                        continue
        if total > 0:
            return f"{round((success / total) * 100)}%"
    except Exception:
        pass
    return None


def excel_serial_to_yyyymmdd(serial, date1904: bool = False) -> str:
    try:
        serial_f = float(serial)
    except Exception:
        return ""
    if serial_f <= 0 or serial_f > 60000:
        return ""
    try:
        if date1904:
            base = datetime.datetime(1904, 1, 1)
        else:
            base = datetime.datetime(1899, 12, 30)
        dt = base + datetime.timedelta(days=serial_f)
        return dt.strftime("%Y%m%d")
    except Exception:
        return ""


def fill_xml_template(
    template_path: Path | None, data: dict, unique_suffix: str
) -> etree._ElementTree:
    NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
    NS_UWVH = "http://schemas.uwv.nl/UwvML/Header-v0202"
    NS_BODY = "http://schemas.uwv.nl/UwvML/Berichten/UwvZwMeldingInternBody-v0428"

    nsmap = {"SOAP-ENV": NS_SOAP, "uwvh": NS_UWVH, None: NS_BODY}
    envelope = etree.Element(etree.QName(NS_SOAP, "Envelope"), nsmap=nsmap)
    header = etree.SubElement(envelope, etree.QName(NS_SOAP, "Header"))
    uwv_header = etree.SubElement(header, etree.QName(NS_UWVH, "UwvMLHeader"))

    route = etree.SubElement(uwv_header, "RouteInformatie")
    bron = etree.SubElement(route, "Bron")
    etree.SubElement(bron, "ApplicatieNaam").text = data.get(
        "BronApplicatie", "Digipoort"
    )
    if data.get("Deterministic"):
        dt_send = (
            data.get("DatTijdVersturenBericht")
            or data.get("FixedTimestamp")
            or "2025-10-28T13:00:00+02:00"
        )
        etree.SubElement(bron, "DatTijdVersturenBericht").text = dt_send
    else:
        etree.SubElement(bron, "DatTijdVersturenBericht").text = (
            datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
        )
    bestemming = etree.SubElement(route, "Bestemming")
    etree.SubElement(bestemming, "ApplicatieNaam").text = data.get(
        "BestemmingApplicatie", "UZS"
    )
    gu_nr = data.get("GegevensUitwisselingsnr") or f"GegUitNr_{unique_suffix}"
    etree.SubElement(route, "GegevensUitwisselingsnr").text = gu_nr
    if data.get("RefnrGegevensUitwisselingsExtern"):
        ref_nr = str(data.get("RefnrGegevensUitwisselingsExtern"))
        etree.SubElement(route, "RefnrGegevensUitwisselingsExtern").text = ref_nr

    bericht = etree.SubElement(uwv_header, "BerichtIdentificatie")
    ber_ref = data.get("BerichtReferentienr") or f"BerRefNr_{unique_suffix}"
    etree.SubElement(bericht, "BerichtReferentienr").text = ber_ref
    bericht_type = etree.SubElement(bericht, "BerichtType")
    etree.SubElement(bericht_type, "BerichtNaam").text = "UwvZwMeldingInternBody"
    etree.SubElement(bericht_type, "VersieMajor").text = "04"
    etree.SubElement(bericht_type, "VersieMinor").text = "28"
    etree.SubElement(bericht_type, "Buildnr").text = "01"
    etree.SubElement(bericht_type, "CommunicatieType").text = "Melding"
    etree.SubElement(bericht_type, "CommunicatieElement").text = "Melding"
    if data.get("Deterministic"):
        dt_create = (
            data.get("DatTijdAanmaakBericht")
            or data.get("FixedTimestamp")
            or "2025-10-28T13:00:00+02:00"
        )
        etree.SubElement(bericht, "DatTijdAanmaakBericht").text = dt_create
    else:
        now_str = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
        etree.SubElement(bericht, "DatTijdAanmaakBericht").text = now_str
    etree.SubElement(bericht, "IndTestbericht").text = str(
        data.get("IndTestbericht", "2")
    )

    trans = etree.SubElement(uwv_header, "Transactie")
    tr_ref = data.get("TransactieReferentienr") or f"TraRefNr_{unique_suffix}"
    etree.SubElement(trans, "TransactieReferentienr").text = tr_ref
    etree.SubElement(trans, "Volgordenr").text = "1"
    etree.SubElement(trans, "IndLaatsteBericht").text = "1"

    body = etree.SubElement(envelope, etree.QName(NS_SOAP, "Body"))
    uwb = etree.SubElement(body, etree.QName(NS_BODY, "UwvZwMeldingInternBody"))
    etree.SubElement(uwb, "CdBerichtType").text = data.get("CdBerichtType", "OTP3")
    etree.SubElement(uwb, "IndAlleenControleUzs").text = str(
        data.get("IndAlleenControleUzs", "2")
    )

    ket = etree.SubElement(uwb, "Ketenpartij")
    if data.get("FiscaalNr"):
        etree.SubElement(ket, "FiscaalNr").text = str(data.get("FiscaalNr"))
    if data.get("Loonheffingennr"):
        etree.SubElement(ket, "Loonheffingennr").text = str(data.get("Loonheffingennr"))
    etree.SubElement(ket, "Naam").text = data.get(
        "OrganisatieNaam", data.get("Organisatie", "")
    )
    etree.SubElement(ket, "CdRolKetenpartij").text = data.get("CdRolKetenpartij", "01")
    etree.SubElement(ket, "CdSrtIndiener").text = data.get("CdSrtIndiener", "WG")
    etree.SubElement(ket, "NaamSoftwarePakket").text = data.get(
        "NaamSoftwarePakket", "XML-Automator"
    )
    etree.SubElement(ket, "VersieSoftwarePakket").text = data.get(
        "VersieSoftwarePakket", "0.1"
    )
    etree.SubElement(ket, "VolgNr").text = "1"
    if any(
        data.get(k) for k in ("NaamContactpersoonAfd", "TelefoonnrContactpersoonAfd")
    ):
        kcont = etree.SubElement(ket, "Contactgegevens")
        if data.get("NaamContactpersoonAfd"):
            etree.SubElement(kcont, "NaamContactpersoonAfd").text = str(
                data.get("NaamContactpersoonAfd")
            )
        if data.get("TelefoonnrContactpersoonAfd"):
            etree.SubElement(kcont, "TelefoonnrContactpersoonAfd").text = str(
                data.get("TelefoonnrContactpersoonAfd")
            )

    np = etree.SubElement(uwb, "NatuurlijkPersoon")
    if data.get("BSN"):
        etree.SubElement(np, "Burgerservicenr").text = str(data.get("BSN"))
    if data.get("Geb_datum"):
        geb = data.get("Geb_datum")
        if isinstance(geb, str) and geb.isdigit() and len(geb) == 8:
            etree.SubElement(np, "Geboortedat").text = geb
        else:
            etree.SubElement(np, "Geboortedat").text = _format_date_yyyymmdd(geb)
    naam = data.get("Naam", "")
    if naam:
        parts = naam.split()
        etree.SubElement(np, "EersteVoornaam").text = parts[0]
        if len(parts) > 1:
            initials = "".join(p[0] for p in parts[:-1] if p)
            etree.SubElement(np, "Voorletters").text = initials
            etree.SubElement(np, "SignificantDeelVanDeAchternaam").text = " ".join(
                parts[1:]
            )
        else:
            etree.SubElement(np, "Voorletters").text = parts[0][0] if parts[0] else ""

    if any(
        data.get(k)
        for k in (
            "NaamContactpersoonAfd",
            "Geslacht",
            "TelefoonnrContactpersoonAfd",
            "NrLokaleVestiging",
            "EMailAdres",
        )
    ):
        contact = etree.SubElement(uwb, "Contactgegevens")
        if data.get("NaamContactpersoonAfd"):
            etree.SubElement(contact, "NaamContactpersoonAfd").text = str(
                data.get("NaamContactpersoonAfd")
            )
        if data.get("Geslacht"):
            etree.SubElement(contact, "Geslacht").text = str(data.get("Geslacht"))
        if data.get("TelefoonnrContactpersoonAfd"):
            etree.SubElement(contact, "TelefoonnrContactpersoonAfd").text = str(
                data.get("TelefoonnrContactpersoonAfd")
            )
        if data.get("NrLokaleVestiging"):
            etree.SubElement(contact, "NrLokaleVestiging").text = str(
                data.get("NrLokaleVestiging")
            )
        if data.get("EMailAdres"):
            etree.SubElement(contact, "EMailAdres").text = str(data.get("EMailAdres"))

    mz = etree.SubElement(uwb, "MeldingZiekte")
    if data.get("DatEersteAoDag"):
        etree.SubElement(mz, "DatEersteAoDag").text = _format_date_yyyymmdd(
            data.get("DatEersteAoDag")
        )
    if data.get("IndDirecteUitkering"):
        etree.SubElement(mz, "IndDirecteUitkering").text = str(
            data.get("IndDirecteUitkering")
        )
    if data.get("CdRedenAangifteAo"):
        etree.SubElement(mz, "CdRedenAangifteAo").text = str(
            data.get("CdRedenAangifteAo")
        )
    if data.get("CdRedenZiekmelding"):
        etree.SubElement(mz, "CdRedenZiekmelding").text = str(
            data.get("CdRedenZiekmelding")
        )
    if data.get("IndWerkdagOpZaterdag"):
        etree.SubElement(mz, "IndWerkdagOpZaterdag").text = str(
            data.get("IndWerkdagOpZaterdag")
        )
    if data.get("IndWerkdagOpZondag"):
        etree.SubElement(mz, "IndWerkdagOpZondag").text = str(
            data.get("IndWerkdagOpZondag")
        )

    ae = etree.SubElement(uwb, "AdministratieveEenheid")
    if data.get("Loonheffingennr"):
        etree.SubElement(ae, "Loonheffingennr").text = str(data.get("Loonheffingennr"))
    if data.get("OrganisatieNaam"):
        etree.SubElement(ae, "Naam").text = str(data.get("OrganisatieNaam"))
    bank = etree.SubElement(ae, "Bankrekening")
    if data.get("Bankrekeningnr"):
        etree.SubElement(bank, "Bankrekeningnr").text = str(data.get("Bankrekeningnr"))
    if data.get("Bic"):
        etree.SubElement(bank, "Bic").text = str(data.get("Bic"))
    if data.get("Iban"):
        etree.SubElement(bank, "Iban").text = str(data.get("Iban"))

    tree = etree.ElementTree(envelope)
    return tree
