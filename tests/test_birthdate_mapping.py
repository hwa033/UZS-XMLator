from tools.generate_from_excel import build_message_element

NS_BODY = "http://schemas.uwv.nl/UwvML/Berichten/UwvZwMeldingInternBody-v0428"


def _find_text(msg, tag):
    el = msg.find("{" + NS_BODY + "}" + tag)
    return el.text if el is not None else None


def test_build_message_accepts_geboortedatum_alias_geb_datum():
    rec = {
        "CdBerichtType": "ZBM",
        "BSN": "123456789",
        "Geb_datum": "1990-01-15",
        "DatEersteAoDag": "2025-01-01",
    }
    msg, _ = build_message_element(rec, NS_BODY)

    np = msg.find("{" + NS_BODY + "}NatuurlijkPersoon")
    assert np is not None
    geb = np.find("{" + NS_BODY + "}Geboortedat")
    assert geb is not None
    assert geb.text == "19900115"


def test_build_message_accepts_dutch_date_format_dd_mm_yyyy():
    rec = {
        "CdBerichtType": "VM",
        "BSN": "123456789",
        "Geboortedatum": "15-01-1990",
        "DatEersteAoDag": "2025-01-01",
    }
    msg, _ = build_message_element(rec, NS_BODY)

    np = msg.find("{" + NS_BODY + "}NatuurlijkPersoon")
    assert np is not None
    geb = np.find("{" + NS_BODY + "}Geboortedat")
    assert geb is not None
    assert geb.text == "19900115"


def test_build_message_requires_birthdate():
    rec = {
        "CdBerichtType": "ZBM",
        "BSN": "123456789",
        "DatEersteAoDag": "2025-01-01",
    }

    try:
        build_message_element(rec, NS_BODY)
        assert False, "Expected ValueError for missing geboortedatum"
    except ValueError as exc:
        assert "geboortedatum" in str(exc).lower()
