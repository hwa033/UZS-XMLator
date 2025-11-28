import importlib.util
from pathlib import Path


def _load_module_from_tools():
    p = Path(__file__).parent.parent / "tools" / "tag_datasets.py"
    spec = importlib.util.spec_from_file_location("tag_datasets", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_infer_with_iban():
    tag_datasets = _load_module_from_tools()
    rec = {"fields": {"Iban": "NL00BANK0123456789"}}
    types = tag_datasets.infer_types_from_record(rec)
    assert "ZBM" in types and "VM" in types


def test_infer_with_bsn():
    tag_datasets = _load_module_from_tools()
    rec = {"fields": {"BSN": "123456789"}}
    types = tag_datasets.infer_types_from_record(rec)
    assert "ZBM" in types and "VM" in types


def test_infer_none_by_default():
    tag_datasets = _load_module_from_tools()
    rec = {"fields": {"SomeField": "value"}}
    types = tag_datasets.infer_types_from_record(rec)
    assert types == []
