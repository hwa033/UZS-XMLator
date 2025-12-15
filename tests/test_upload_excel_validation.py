import pytest
from lxml import etree
from web.utils import validate_normalized_rows_for_generator


class DummyGen:
    def build_message_element(self, rec, ns_body):
        # create a minimal message element with optional Burgerservicenr and CdBerichtType
        m = etree.Element("{" + ns_body + "}UwvZwMeldingInternBody")
        if rec.get("BSN"):
            b = etree.SubElement(m, "{" + ns_body + "}Burgerservicenr")
            b.text = str(rec.get("BSN"))
        if rec.get("CdBerichtType"):
            c = etree.SubElement(m, "{" + ns_body + "}CdBerichtType")
            c.text = str(rec.get("CdBerichtType"))
        # return element and a detected aanvraag type
        atype = rec.get("CdBerichtType") or "ZBM"
        return m, atype


def test_validate_rows_missing_bsn():
    rows = [
        {"Naam": "Jan Test", "DatEersteAoDag": "20250101"},
    ]
    excel_headers = ["Naam", "DatEersteAoDag"]
    gen = DummyGen()
    bodies, errors, bulk = validate_normalized_rows_for_generator(
        rows,
        excel_headers,
        validate_flag=False,
        form_aanvraag_type="ZBM",
        aanvraag_map={"Digipoort": "OTP3"},
        cd_bericht_default="ZBM",
        gen_module=gen,
        ns_body="http://schemas.uwv.nl/UwvML/Berichten/UwvZwMeldingInternBody-v0428",
        schema=None,
    )
    assert bodies == []
    assert any("ontbrekende BSN" in e for e in errors)


def test_validate_rows_ok():
    rows = [
        {"Naam": "Jan Test", "DatEersteAoDag": "20250101", "BSN": "12345"},
    ]
    excel_headers = ["BSN", "Naam", "DatEersteAoDag"]
    gen = DummyGen()
    bodies, errors, bulk = validate_normalized_rows_for_generator(
        rows,
        excel_headers,
        validate_flag=False,
        form_aanvraag_type="ZBM",
        aanvraag_map={"Digipoort": "OTP3"},
        cd_bericht_default="ZBM",
        gen_module=gen,
        ns_body="http://schemas.uwv.nl/UwvML/Berichten/UwvZwMeldingInternBody-v0428",
        schema=None,
    )
    assert len(bodies) == 1
    assert errors == []
*** End Patch