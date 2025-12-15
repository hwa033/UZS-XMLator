from web.utils import extract_excel_cd, decide_cd_override


def test_extract_excel_cd_from_keys():
    rec = {"CdBerichtType": " VM ", "aanvraag_type": "X"}
    assert extract_excel_cd(rec) == "VM"


def test_extract_excel_cd_none():
    rec = {"something": "value"}
    assert extract_excel_cd(rec) is None


def test_decide_cd_override_cases():
    known = {"VM", "ZBM", "OTP3"}

    # Digipoort always forces OTP3
    desired, override = decide_cd_override(existing_text="VM", excel_cd=None, form_aanvraag_type="Digipoort", cd_bericht_default="ZBM", known_codes=known)
    assert desired == "OTP3" and override is True

    # existing valid and matches desired -> no override
    desired, override = decide_cd_override(existing_text="ZBM", excel_cd=None, form_aanvraag_type="ZBM", cd_bericht_default="ZBM", known_codes=known)
    assert desired == "ZBM" and override is False

    # existing invalid -> override
    desired, override = decide_cd_override(existing_text="BAD", excel_cd=None, form_aanvraag_type="ZBM", cd_bericht_default="ZBM", known_codes=known)
    assert override is True and desired == "ZBM"

    # no existing -> override
    desired, override = decide_cd_override(existing_text=None, excel_cd=None, form_aanvraag_type="ZBM", cd_bericht_default="ZBM", known_codes=known)
    assert override is True

    # excel provides explicit code
    desired, override = decide_cd_override(existing_text="ZBM", excel_cd="VM", form_aanvraag_type="ZBM", cd_bericht_default="ZBM", known_codes=known)
    assert desired == "VM" and override is True
