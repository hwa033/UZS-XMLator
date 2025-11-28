import datetime

from web import utils


def test_excel_serial_to_yyyymmdd_1900():
    # Compute serial for 2020-01-01 using 1900-based system (base 1899-12-30)
    import datetime

    base = datetime.datetime(1899, 12, 30)
    target = datetime.datetime(2020, 1, 1)
    serial = (target - base).days
    res = utils.excel_serial_to_yyyymmdd(serial, date1904=False)
    assert res == "20200101"


def test_excel_serial_to_yyyymmdd_1904():
    # Compute serial for 2020-01-01 using 1904-based system (base 1904-01-01)
    import datetime

    base = datetime.datetime(1904, 1, 1)
    target = datetime.datetime(2020, 1, 1)
    serial = (target - base).days
    res = utils.excel_serial_to_yyyymmdd(serial, date1904=True)
    assert res == "20200101"


def test_format_date_various():
    assert utils._format_date_yyyymmdd("2020-01-01") == "20200101"
    assert utils._format_date_yyyymmdd("01-01-2020") == "20200101"
    assert utils._format_date_yyyymmdd(datetime.date(2020, 1, 1)) == "20200101"
    # numeric string serial
    assert utils._format_date_yyyymmdd("43831") == "20200101"
