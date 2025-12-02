import datetime
import io
import json
import os
from pathlib import Path

import yaml
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile
from lxml import etree
import xml.etree.ElementTree as ET
from werkzeug.utils import secure_filename
import importlib.util

try:
    import openpyxl
except Exception:
    openpyxl = None
from .utils import (
    _format_date_yyyymmdd,
    _get_success_rate,
    excel_serial_to_yyyymmdd,
    fill_xml_template,
)

# Minimal Flask app — simplified for easier maintenance.
base = Path(__file__).parent
app = Flask(
    __name__,
    template_folder=str(base / "templates"),
    static_folder=str(base / "static"),
)

# Secret and session hardening
# Prefer an environment-provided secret in production. If running in a
# production environment (FLASK_ENV=production or U_XMLATOR_PROD=1) the
# application will refuse to start without `U_XMLATOR_SECRET` set.
secret = os.environ.get("U_XMLATOR_SECRET")
is_prod = os.environ.get("FLASK_ENV") == "production" or os.environ.get("U_XMLATOR_PROD") == "1"
if not secret:
    if is_prod:
        raise RuntimeError("U_XMLATOR_SECRET must be set when running in production")
    # development fallback (explicitly non-secure)
    secret = "dev-simplified"
app.secret_key = secret

# Secure session cookie defaults; can be overridden via env vars for testing
from datetime import timedelta

app.permanent_session_lifetime = timedelta(seconds=int(os.environ.get("U_XMLATOR_SESSION_SECONDS", str(7 * 24 * 3600))))
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=(os.environ.get("U_XMLATOR_COOKIE_SECURE", "1") != "0"),
    SESSION_COOKIE_SAMESITE=os.environ.get("U_XMLATOR_SAMESITE", "Lax"),
)


def load_datasets_yaml(path: Path):
    if not path.exists():
        return []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        entries = raw.get("datasets") if isinstance(raw, dict) else raw
        if not entries:
            return []
        result = []
        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                continue
            # prefer flattened keys (we keep compatibility with `fields`)
            # fallbacks: prefer nested 'fields', then top-level flattened keys
            src_fields = e.get("fields") if isinstance(e.get("fields"), dict) else {}

            # helper to pick a value from several possible keys
            def pick(*keys):
                for k in keys:
                    if (
                        isinstance(src_fields, dict)
                        and k in src_fields
                        and src_fields.get(k) not in (None, "")
                    ):
                        return src_fields.get(k)
                    if k in e and e.get(k) not in (None, ""):
                        return e.get(k)
                return ""

            label_val = e.get("label") or pick("Naam", "BSN") or f"Dataset {i+1}"

            # normalize common field names into a flat 'fields' dict for JS consumption
            norm_fields = {
                "BSN": pick("BSN", "Burgerservicenr", "burgerservicenr"),
                "Naam": pick("Naam", "naam"),
                "Geb_datum": pick(
                    "Geb_datum", "Geboortedat", "Geboortedatum", "geb_datum"
                ),
                "Loonheffingennr": pick(
                    "Loonheffingennr", "Loonheffingennummer", "loonheffingennr"
                ),
                "Iban": pick("Iban", "IBAN", "Rekeningnummer"),
                "Bic": pick("Bic", "BIC"),
                # keep original raw fields as fallback
                "__raw": src_fields or {},
            }

            # Do not mix global test defaults into each dataset record.
            # Each `norm_fields` entry must reflect values from the same dataset row only.
            # If you want global defaults for interactive demo, handle that at render-time
            # or on the client when explicitly requested, to avoid mismatching BSN and name.

            ds = {
                "id": e.get("id", i),
                "label": label_val,
                "fields": norm_fields,
                # also expose top-level shortcuts for templates that expect them
                "BSN": norm_fields.get("BSN", ""),
                "Naam": norm_fields.get("Naam", ""),
                "Geb_datum": norm_fields.get("Geb_datum", ""),
                "Loonheffingennr": norm_fields.get("Loonheffingennr", ""),
                "Iban": norm_fields.get("Iban", ""),
                "Bic": norm_fields.get("Bic", ""),
            }
            result.append(ds)
        return result
    except Exception:
        return []


# Where generated XMLs are saved per aanvraag type
OUTPUT_MAP = {
    "ZBM": base.parent / "uzs_filedrop" / "UZI-GAP3" / "UZSx_ACC1" / "v0428",
    "VM": base.parent / "uzs_filedrop" / "UZI-GAP3" / "UZSx_ACC1" / "v0428",
    "Digipoort": base.parent
    / "uzs_filedrop"
    / "UZI-GAP3"
    / "UZSx_ACC1"
    / "UwvZwMelding_MQ_V0428",
}

# Central downloads directory for bulk archives (independent of aanvraag type)
DOWNLOADS_DIR = Path(__file__).parent / "static" / "downloads"
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Limits for bulk zip requests (can be overridden by env vars)
ZIP_MAX_FILES = int(os.environ.get("U_XMLATOR_MAX_ZIP_FILES", "50"))
ZIP_MAX_TOTAL_SIZE = int(os.environ.get("U_XMLATOR_MAX_ZIP_TOTAL_BYTES", str(50 * 1024 * 1024)))
ZIP_MAX_FILE_SIZE = int(os.environ.get("U_XMLATOR_MAX_ZIP_FILE_BYTES", str(10 * 1024 * 1024)))

# One-time cleanup guard to avoid running cleanup during import
_CLEANUP_RUN = False


def _cleanup_downloads(max_age_minutes: int = 60):
    """Remove files in DOWNLOADS_DIR older than max_age_minutes."""
    try:
        cutoff = datetime.datetime.now() - datetime.timedelta(minutes=max_age_minutes)
        for p in DOWNLOADS_DIR.iterdir():
            try:
                if p.is_file():
                    mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
                    if mtime < cutoff:
                        p.unlink()
            except Exception:
                continue
    except Exception:
        pass


def save_xml(tree: etree._ElementTree, aanvraag_type: str, filename: str):
    out_dir = OUTPUT_MAP.get(aanvraag_type) or (
        base.parent / "uzs_filedrop" / "UZI-GAP3" / "UZSx_ACC1" / "v0428"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename
    tree.write(str(out_path), encoding="utf-8", xml_declaration=True, pretty_print=True)
    # Log event for dashboard and analytics
    try:
        events_file = Path(__file__).parent / "xml_events.jsonl"
        event = {
            "tijdstip": datetime.datetime.now().isoformat(),
            "filename": filename,
            "aanvraag_type": aanvraag_type,
            "output_path": str(out_path),
            "size": out_path.stat().st_size if out_path.exists() else 0,
            "success": True,
        }
        with open(events_file, "a", encoding="utf-8") as ef:
            ef.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return out_path


# Register optional admin blueprints if present
try:
    from .instellingen import instellingen_bp

    app.register_blueprint(instellingen_bp, url_prefix="/instellingen")
except Exception:
    # If the blueprint import fails, continue without admin pages.
    pass


@app.route("/")
def index():
    # Pre-compute some dashboard values so tiles show data server-side even if JS fails
    # Run one-time cleanup if necessary (lazy, avoids import-time decorators)
    try:
        _maybe_run_cleanup()
    except Exception:
        pass
    # Simplified: we no longer track test historie in the minimal app
    total_tests = 0
    last_status = None
    last_time = None
    # Compute a basic success percentage from xml_events.jsonl as a fallback
    events_file = Path(__file__).parent / "xml_events.jsonl"
    success_rate = _get_success_rate(events_file)

    return render_template(
        "dashboard.html",
        total_tests=total_tests,
        last_test_status=last_status,
        last_test_time=last_time,
        success_rate=success_rate,
    )


@app.route("/health")
def health():
    """Simple health check for load balancers and quick probes."""
    try:
        return (
            jsonify({"status": "ok", "time": datetime.datetime.utcnow().isoformat()}),
            200,
        )
    except Exception:
        return jsonify({"status": "error"}), 500


@app.route("/ready")
def ready():
    """Readiness check: verifies writable downloads dir and required libs present."""
    ok = True
    checks = {}
    try:
        checks["downloads_exists"] = DOWNLOADS_DIR.exists()
        try:
            checks["downloads_writable"] = os.access(str(DOWNLOADS_DIR), os.W_OK)
        except Exception:
            checks["downloads_writable"] = False
            ok = False
    except Exception:
        checks["downloads_exists"] = False
        checks["downloads_writable"] = False
        ok = False
    checks["openpyxl_installed"] = openpyxl is not None
    if not checks["openpyxl_installed"]:
        ok = False
    status = 200 if ok else 503
    return jsonify({"ready": ok, "checks": checks}), status


def _maybe_run_cleanup():
    """Run cleanup once per process when the index page is loaded.

    Avoids import-time decorator usage which caused compatibility errors in
    some runtime environments. This runs lazily on first index request.
    """
    global _CLEANUP_RUN
    if _CLEANUP_RUN:
        return
    try:
        _cleanup_downloads(max_age_minutes=24 * 60)
    except Exception:
        pass
    _CLEANUP_RUN = True


def _load_generator_module():
    """Dynamically load `tools/generate_from_excel.py` as a module if present.

    Returns the loaded module or None on error.
    """
    try:
        gen_path = Path(__file__).parent.parent / "tools" / "generate_from_excel.py"
        if not gen_path.exists():
            return None
        spec = importlib.util.spec_from_file_location("tools_generate_from_excel", str(gen_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _normalize_record_for_generator(rec: dict) -> dict:
    """Normalize a row dict (header->value) to the canonical keys expected by the generator.

    The input `rec` comes from `read_excel_rows()` and uses the original header
    strings as keys. This function produces a new dict with keys like 'BSN',
    'Naam', 'Geboortedatum', 'Loonheffingennummer' etc. populated from common
    header aliases.
    """
    import re

    def tok(s: str) -> str:
        if s is None:
            return ""
        t = str(s).strip().lower()
        # remove non-alphanumeric
        t = re.sub(r"[^0-9a-z]+", "", t)
        return t

    key_map = {tok(k): k for k in rec.keys()}

    def pick(*candidates):
        for c in candidates:
            v = key_map.get(c)
            if v is not None:
                return rec.get(v)
        return None

    out = {}
    # common mappings
    out["BSN"] = pick("bsn", "burgerservicenr", "burgerservicenummer")
    out["Naam"] = pick("naam", "volledigenaam", "volledige naam", "voornaamachternaam")
    out["Achternaam"] = pick("achternaam", "surname", "lastname")
    out["EersteVoornaam"] = pick("voornaam", "eerstevoornaam", "firstname")
    out["Geboortedatum"] = pick("geboortedatum", "geboortedat", "gebdatum", "geb_datum")
    out["DatEersteAoDag"] = pick("dateersteaodag", "dateersteaodag", "dat_eerste_aodag")
    out["IndDirecteUitkering"] = pick("inddirecteuitkering", "inddirecteuitkering")
    out["CdRedenAangifteAo"] = pick("cdredenaangifteao", "cdredenaangifteao")
    out["CdRedenZiekmelding"] = pick("cdredenziekmelding", "cdredenziekmelding")
    out["IndWerkdagOpZaterdag"] = pick("indwerkdagopzaterdag", "indwerkdagopzaterdag")
    out["IndWerkdagOpZondag"] = pick("indwerkdagopzondag", "indwerkdagopzondag")
    out["Loonheffingennummer"] = pick("loonheffingennummer", "loonheffingennr", "loonheffingennr")
    out["IBAN"] = pick("iban", "rekeningnummeriban", "rekeningnummer")
    out["BIC"] = pick("bic", "bic")
    out["Personeelsnr"] = pick("personeelsnr", "personeelsnummer")

    # copy any other keys through (sanitize to generator-friendly keys)
    for k, v in rec.items():
        if v is None:
            continue
        if isinstance(k, str) and tok(k) in ("bsn", "naam", "achternaam", "voornaam", "geboortedatum"):
            continue
        # keep original header name as-is for wider generator compatibility
        out.setdefault(k, v)

    # If 'Naam' is missing, try to build it from available name parts
    try:
        if not out.get("Naam") or str(out.get("Naam")).strip() == "":
            parts = []
            # prefer EersteVoornaam + Achternaam
            if out.get("EersteVoornaam"):
                parts.append(str(out.get("EersteVoornaam")).strip())
            # try also common alternatives from original row if present
            alt_last = None
            for candidate in ("Achternaam", "SignificantDeelVanDeAchternaam", "lastname", "surname"):
                if out.get(candidate):
                    alt_last = out.get(candidate)
                    break
            if alt_last:
                parts.append(str(alt_last).strip())
            # If we still have no parts but Achternaam exists and is a plausible string, use it as the name
            if not parts and out.get("Achternaam"):
                try:
                    al = out.get("Achternaam")
                    if not (isinstance(al, (int, float)) and float(al) == 0):
                        s_al = str(al).strip()
                        if s_al and s_al not in ("0", "None"):
                            parts.append(s_al)
                except Exception:
                    pass
            # fallback: look for fields in the original headers that look like 'voorletters' or 'initialen'
            if not parts:
                for h in ("voorletters", "initialen", "initials", "voornaam"):
                    # check original record keys (case-insensitive)
                    for k, v in rec.items():
                        if k is None:
                            continue
                        kk = tok(k)
                        if kk == h and v:
                            parts.append(str(v).strip())
            if parts:
                out["Naam"] = " ".join(parts)
    except Exception:
        pass

    return out


def _is_valid_yyyymmdd(s: str) -> bool:
    """Return True if s matches YYYYMMDD and is a real date."""
    if not s:
        return False
    try:
        ss = str(s).strip()
        # accept either compact YYYYMMDD or ISO YYYY-MM-DD
        if len(ss) == 8 and ss.isdigit():
            datetime.datetime.strptime(ss, "%Y%m%d")
            return True
        if len(ss) == 10 and ss[4] == '-' and ss[7] == '-':
            datetime.datetime.strptime(ss, "%Y-%m-%d")
            return True
        return False
    except Exception:
        return False


_CACHED_XSD_SCHEMA = None
_LAST_XSD_ERROR = None


def _load_message_xsd():
    """Load and cache the `UwvZwMeldingInternBody` XMLSchema if available.

    Returns an lxml.etree.XMLSchema object or None if not loadable.
    """
    global _CACHED_XSD_SCHEMA
    if _CACHED_XSD_SCHEMA is not None:
        return _CACHED_XSD_SCHEMA
    xsd_path = Path(__file__).parent.parent / "docs" / "UwvZwMeldingInternBody-v0428-b01.xsd"
    if not xsd_path.exists():
        return None

    # Try a "safe" parse that avoids network fetches and external entity resolution
    try:
        safe_parser = etree.XMLParser(load_dtd=False, no_network=True, resolve_entities=False)
        doc = etree.parse(str(xsd_path), safe_parser)
        try:
            schema = etree.XMLSchema(doc)
            _CACHED_XSD_SCHEMA = schema
            return schema
        except Exception as se:
            app.logger.warning("XSD compile failed (safe parse): %s", se)
            # Fall through to a more permissive parse below
    except Exception as e:
        app.logger.debug("Safe XSD parse failed, will attempt permissive parse: %s", e)

    # Attempt a permissive parse that allows external resources, but catch failures
    try:
        permissive_parser = etree.XMLParser(load_dtd=True, no_network=False)
        doc2 = etree.parse(str(xsd_path), permissive_parser)
        schema2 = etree.XMLSchema(doc2)
        _CACHED_XSD_SCHEMA = schema2
        return schema2
    except Exception as ex:
        app.logger.warning("Full XSD load/compile failed: %s", ex)
        # Record the error for the request/response so the UI can show an inline warning.
        global _LAST_XSD_ERROR
        try:
            _LAST_XSD_ERROR = str(ex)
        except Exception:
            _LAST_XSD_ERROR = "XSD load/compile failed"
        _CACHED_XSD_SCHEMA = None
        return None


def _validate_generator_record(rec: dict) -> list:
    """Validate a normalized record (keys like 'BSN','Naam','DatEersteAoDag').

    Returns a list of error messages (empty if valid).
    """
    errs = []
    # BSN required
    bsn = rec.get("BSN") or rec.get("Burgerservicenr")
    if not bsn or str(bsn).strip() == "":
        errs.append("ontbrekende BSN")
    # Naam required (either 'Naam' or first+last)
    naam = rec.get("Naam")
    if not naam or str(naam).strip() == "":
        first = rec.get("EersteVoornaam") or rec.get("Voornaam") or rec.get("Voorletters")
        last = rec.get("Achternaam") or rec.get("SignificantDeelVanDeAchternaam")
        if not (first or last):
            errs.append("ontbrekende Naam")
    # DatEersteAoDag required and must be YYYYMMDD
    dae = rec.get("DatEersteAoDag") or rec.get("DatEersteAoDag")
    if dae:
        s = str(dae).strip()
        # allow Excel serial numbers (digits less than 6?) we'll only validate YYYYMMDD here
        if len(s) == 8 and s.isdigit():
            if not _is_valid_yyyymmdd(s):
                errs.append(f"ongeldige DatEersteAoDag: {s}")
        else:
            # try to parse common date formats
            try:
                # leverage existing helper to format; if it raises or returns empty, flag
                formatted = _format_date_yyyymmdd(dae)
                if not formatted or not _is_valid_yyyymmdd(formatted):
                    errs.append(f"ongeldige DatEersteAoDag: {dae}")
            except Exception:
                errs.append(f"ongeldige DatEersteAoDag: {dae}")
    else:
        errs.append("ontbrekende DatEersteAoDag")
    return errs


def _is_blank_normalized_record(rec: dict) -> bool:
    """Return True if the normalized record appears to be an empty/placeholder row.

    We consider a row blank if it contains no meaningful identifying values
    (no BSN, no Naam/Achternaam, no Loonheffingennummer, no IBAN).
    """
    try:
        def is_empty(v):
            if v is None:
                return True
            s = str(v).strip()
            if s == "" or s in ("0", "None"):
                return True
            return False

        keys = [rec.get('BSN'), rec.get('Naam'), rec.get('Achternaam'), rec.get('Loonheffingennummer'), rec.get('IBAN'), rec.get('Rekeningnummer (IBAN)')]
        return all(is_empty(k) for k in keys)
    except Exception:
        return False


@app.route("/favicon.ico")
def favicon():
    # Serve a favicon from static if present, otherwise return 204
    p = Path(app.static_folder) / "favicon.ico"
    if p.exists():
        return send_file(str(p))
    return "", 204


@app.route("/logo.png")
def logo():
    # Serve a project-root logo if present in project root or static/img
    base_dir = Path(__file__).parent.parent
    candidates = [
        base_dir / "uzs_logo.png",
        base_dir / "uzs-logo.png",
        Path(app.static_folder) / "img" / "uzs_logo.png",
    ]
    for c in candidates:
        if c.exists():
            try:
                return send_file(str(c), mimetype="image/png")
            except Exception:
                return send_file(str(c))
    return "", 404


@app.route("/genereer_xml")
def genereer_xml():
    # Render the generator page (bulk upload only)
    total_tests = 0
    last_status = None
    last_time = None

    events_file = Path(__file__).parent / "xml_events.jsonl"
    success_rate = _get_success_rate(events_file)

    return render_template(
        "genereer_xml.html",
        xml_path=None,
        total_tests=total_tests,
        last_test_status=last_status,
        last_test_time=last_time,
        success_rate=success_rate,
    )


@app.route("/genereer_xml/upload_excel", methods=["POST"])
def upload_excel():
    if openpyxl is None:
        flash(
            "Excel-ondersteuning niet beschikbaar (openpyxl niet geïnstalleerd).",
            "danger",
        )
        return redirect(url_for("genereer_xml"))

    if "excel_file" not in request.files:
        flash("Geen bestand geüpload", "danger")
        return redirect(url_for("genereer_xml"))

    f = request.files["excel_file"]
    if f.filename == "":
        flash("Geen bestand geselecteerd", "danger")
        return redirect(url_for("genereer_xml"))

    # Read workbook from uploaded file (file storage provides file-like object)
    # Read bytes once so we can both parse in-memory and save a temp file
    content = f.read()
    try:
        wb = openpyxl.load_workbook(filename=io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        flash("Kon Excel-bestand niet lezen: " + str(e), "danger")
        return redirect(url_for("genereer_xml"))

    sheet = wb.active

    # Read headers from first row for legacy in-process parsing
    rows = sheet.iter_rows(values_only=True)
    try:
        headers = [h if h is not None else "" for h in next(rows)]
    except StopIteration:
        flash("Leeg Excel-bestand", "danger")
        return redirect(url_for("genereer_xml"))

    # Determine aanvraag type (used by generator output mapping)
    # `form_aanvraag_type` preserves the raw UI selection (used for envelope sender)
    form_aanvraag_type = request.form.get("aanvraag_type") or "ZBM"
    # Map friendly form values to schema-allowed CdBerichtType codes.
    # ONLY Digipoort gets mapped to OTP3; all other types remain unchanged.
    aanvraag_map = {
        "Digipoort": "OTP3",
    }
    # Known schema codes which we should accept as-is if present in the generated
    # message. If the generator wrote one of these codes already (e.g. 'VM' or
    # 'ZBM'), we won't override it with the selected `aanvraag_type`.
    _KNOWN_CDBERICHT_TYPES = {"KCC", "OTP1", "OTP3", "RFE", "RFV", "RFX", "VM", "ZBM", "KAAN", "ZBMA"}
    # `cd_bericht_default` is the schema code we will use for CdBerichtType when
    # no explicit value is present in the Excel row. ONLY map Digipoort to OTP3;
    # all other types (ZBM, VM, etc.) keep their original code.
    cd_bericht_default = aanvraag_map.get(form_aanvraag_type, form_aanvraag_type)
    # Determine whether to validate records (checkbox on form). Default: True
    validate_flag = str(request.form.get("validate", "on")).strip().lower() in ("1", "true", "on", "yes")

    # Attempt to use the in-process Excel->XML generator (tools/generate_from_excel.py)
    gen = _load_generator_module()
    if gen is None:
        # Help the user debug: if the generator isn't loadable we fall back to legacy parsing
        flash(
            "In-process generator niet gevonden of niet laadb... Gebruik legacy parser.",
            "warning",
        )
    else:
        # generator will be used; avoid noisy per-request flashes in the UI
        pass
    temp_file_path = None
    if gen is not None:
        try:
            # save uploaded bytes to a tmp file for the generator
            tf = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            try:
                tf.write(content)
                tf.flush()
            finally:
                tf.close()
            temp_file_path = tf.name

            # read rows using the generator's helper (use cached values when available)
            # data_only=True prefers stored/calculated values instead of formulas, which
            # avoids sanitizing useful display values to empty strings.
            rows_list, formula_count = gen.read_excel_rows(temp_file_path, data_only=True)
            ns_soap, ns_uwvh, ns_body = gen._namespaces()

            generated = []
            errors = []
            # Capture any XSD load error for UI; reset before per-request use
            global _LAST_XSD_ERROR
            _LAST_XSD_ERROR = None

            # choose output directory: map to OUTPUT_MAP if possible, otherwise generator default
            out_dir = OUTPUT_MAP.get(form_aanvraag_type) or (Path(__file__).parent.parent / "build" / "excel_generated")
            out_dir_str = str(out_dir)
            os.makedirs(out_dir_str, exist_ok=True)

            log_path = str(Path(__file__).parent.parent / "build" / "logs" / "generator_excel.log")

            # Use bulk when there are multiple records; otherwise create one file per row
            # Only load XSD/schema if validation is enabled
            schema = _load_message_xsd() if validate_flag else None
            # Determine which fields the uploaded Excel provides so we can validate
            # only against those. `rows_list` is a list of dicts keyed by header
            # names returned by the in-process generator.
            excel_headers = []
            if rows_list:
                # first row's keys represent the headers (generator normalizes them)
                excel_headers = list(rows_list[0].keys())

            # Helper to check for presence among synonyms
            def _record_has_any(rec, names):
                for n in names:
                    v = rec.get(n)
                    if v is not None and str(v).strip() != "":
                        return True
                return False

            # Known important fields and common header synonyms
            important_field_synonyms = {
                'BSN': ['BSN', 'Burgerservicenr', 'Burgerservicenr'],
                'Naam': ['Achternaam', 'SignificantDeelVanDeAchternaam', 'Naam', 'IndienerNaam'],
                'DatEersteAoDag': ['DatEersteAoDag', 'DatEersteAoDag'],
                'Loonheffingennummer': ['Loonheffingennummer', 'Loonheffingennr', 'Loonheffingennr'],
            }
            if len(rows_list) > 1:
                bodies = []
                for idx, rec in enumerate(rows_list, start=2):
                    try:
                        rec_norm = _normalize_record_for_generator(rec)
                        # Skip blank/placeholder rows without reporting errors
                        if _is_blank_normalized_record(rec_norm):
                            continue
                        # Dynamic validation: only enforce important fields that are
                        # present in the uploaded Excel headers. This makes the
                        # validation adapt to the sheet the user uploaded.
                        for imp, syns in important_field_synonyms.items():
                            if any(h in excel_headers for h in syns):
                                if not _record_has_any(rec, syns):
                                    errors.append(f"Regel {idx}: {imp} ontbreekt of is ongeldig")
                                    # skip this record
                                    continue

                        # record-level validation (BSN, Naam, DatEersteAoDag) if enabled
                        rec_errs = _validate_generator_record(rec_norm) if validate_flag else []
                        if rec_errs:
                            errors.append(f"Regel {idx}: " + "; ".join(rec_errs))
                            continue

                        msg = gen.build_message_element(rec_norm, ns_body)
                        # Handle CdBerichtType: ONLY override with OTP3 if user selected Digipoort.
                        # For all other types (ZBM, VM, etc.), keep existing valid schema codes.
                        try:
                            excel_cd_names = ['CdBerichtType', 'aanvraag_type', 'Type']
                            excel_cd = None
                            for n in excel_cd_names:
                                v = rec_norm.get(n)
                                if v is not None and str(v).strip() != '':
                                    excel_cd = str(v).strip()
                                    break
                            
                            # Determine desired code: if Excel has explicit value, use it (mapped if needed)
                            if excel_cd:
                                desired = aanvraag_map.get(excel_cd, excel_cd)
                            else:
                                desired = cd_bericht_default
                            
                            # Get existing CdBerichtType from generated message
                            # Child elements use default namespace, must search with namespace
                            existing = msg.findall('{' + ns_body + '}CdBerichtType')
                            existing_text = None
                            if existing and len(existing) > 0:
                                t = existing[0].text
                                existing_text = t.strip() if t is not None else None

                            # ONLY override if:
                            # 1. User selected Digipoort (form_aanvraag_type == "Digipoort"), OR
                            # 2. Existing value is not a valid schema code
                            should_override = False
                            if form_aanvraag_type == "Digipoort":
                                # Always set to OTP3 for Digipoort, regardless of Excel content
                                desired = "OTP3"
                                should_override = True
                            elif existing_text and existing_text not in _KNOWN_CDBERICHT_TYPES:
                                # Override invalid codes with the desired value
                                should_override = True
                            elif not existing_text:
                                # No existing value, set the desired one
                                should_override = True

                            if should_override:
                                if existing:
                                    for c in existing:
                                        c.text = desired
                                else:
                                    ET.SubElement(msg, '{' + ns_body + '}CdBerichtType').text = desired
                        except Exception:
                            pass

                        # XSD validation per message if validation is enabled and schema available
                        if validate_flag and schema is not None:
                            try:
                                xml_bytes = ET.tostring(msg, encoding="utf-8")
                                lmsg = etree.fromstring(xml_bytes)
                                if not schema.validate(lmsg):
                                    # collect schema errors
                                    le = schema.error_log
                                    msgs = []
                                    for e in le:
                                        msgs.append(str(e.message))
                                    errors.append(f"Regel {idx}: XSD fouten: {'; '.join(msgs)}")
                                    continue
                            except Exception as ve:
                                errors.append(f"Regel {idx}: XSD validatiefout: {ve}")
                                continue

                        bodies.append(msg)
                    except Exception as exc:
                        try:
                            gen.append_log(log_path, f"{datetime.datetime.now().isoformat()}\tERROR_BUILD_MSG\t{exc}")
                        except Exception:
                            pass

                # Get tester name from session or default
                tester_name = session.get("user", {}).get("name", "tester")
                envelope = gen.build_envelope_with_header_and_bodies(bodies, sender=form_aanvraag_type, tester_name=tester_name)
                saved = gen.save_envelope(envelope, out_dir_str, "bulk")
                try:
                    gen.append_log(log_path, f"{datetime.datetime.now().isoformat()}\t{saved}\tSUCCESS\t{len(bodies)}")
                except Exception:
                    pass
                generated = [Path(saved).name]
            else:
                gen_files = []
                schema = _load_message_xsd() if validate_flag else None
                for idx, rec in enumerate(rows_list, start=2):
                    try:
                        rec_norm = _normalize_record_for_generator(rec)

                        # Dynamic validation based on the provided headers
                        for imp, syns in important_field_synonyms.items():
                            if any(h in excel_headers for h in syns):
                                if not _record_has_any(rec, syns):
                                    errors.append(f"Regel {idx}: {imp} ontbreekt of is ongeldig")
                                    # skip this record
                                    continue

                        rec_errs = _validate_generator_record(rec_norm) if validate_flag else []
                        if rec_errs:
                            errors.append(f"Regel {idx}: " + "; ".join(rec_errs))
                            continue

                        m = gen.build_message_element(rec_norm, ns_body)
                        try:
                            # Handle CdBerichtType: ONLY override with OTP3 if user selected Digipoort.
                            # For all other types (ZBM, VM, etc.), keep existing valid schema codes.
                            excel_cd_names = ['CdBerichtType', 'aanvraag_type', 'Type']
                            excel_cd = None
                            for n in excel_cd_names:
                                v = rec_norm.get(n)
                                if v is not None and str(v).strip() != '':
                                    excel_cd = str(v).strip()
                                    break
                            
                            # Determine desired code
                            if excel_cd:
                                desired = aanvraag_map.get(excel_cd, excel_cd)
                            else:
                                desired = cd_bericht_default
                            
                            # Get existing CdBerichtType
                            # Child elements use default namespace, must search with namespace
                            existing = m.findall('{' + ns_body + '}CdBerichtType')
                            existing_text = None
                            if existing and len(existing) > 0:
                                t = existing[0].text
                                existing_text = t.strip() if t is not None else None

                            # ONLY override if:
                            # 1. User selected Digipoort, OR
                            # 2. Existing value is not a valid schema code
                            should_override = False
                            if form_aanvraag_type == "Digipoort":
                                # Always set to OTP3 for Digipoort, regardless of Excel content
                                desired = "OTP3"
                                should_override = True
                            elif existing_text and existing_text not in _KNOWN_CDBERICHT_TYPES:
                                should_override = True
                            elif not existing_text:
                                should_override = True

                            if should_override:
                                if existing:
                                    for c in existing:
                                        c.text = desired
                                else:
                                    ET.SubElement(m, '{' + ns_body + '}CdBerichtType').text = desired
                        except Exception:
                            pass
                        if validate_flag and schema is not None:
                            try:
                                xml_bytes = ET.tostring(m, encoding="utf-8")
                                lmsg = etree.fromstring(xml_bytes)
                                if not schema.validate(lmsg):
                                    le = schema.error_log
                                    msgs = [str(e.message) for e in le]
                                    errors.append(f"Regel {idx}: XSD fouten: {'; '.join(msgs)}")
                                    continue
                            except Exception as ve:
                                errors.append(f"Regel {idx}: XSD validatiefout: {ve}")
                                continue
                        # Get tester name from session or default
                        tester_name = session.get("user", {}).get("name", "tester")
                        env = gen.build_envelope_with_header_and_bodies([m], sender=form_aanvraag_type, tester_name=tester_name)
                        bsn = rec_norm.get("BSN") or f"row{idx}"
                        safe_bsn = str(bsn).replace(" ", "_")
                        saved = gen.save_envelope(env, out_dir_str, safe_bsn)
                        try:
                            gen.append_log(log_path, f"{datetime.datetime.now().isoformat()}\t{saved}\tSUCCESS")
                        except Exception:
                            pass
                        gen_files.append(Path(saved).name)
                    except Exception as exc:
                        try:
                            gen.append_log(log_path, f"{datetime.datetime.now().isoformat()}\tERROR_SAVE\t{exc}")
                        except Exception:
                            pass
                generated = gen_files

                # (XSD loader error already reset earlier for the request)

            # Attempt to remove temp file
            try:
                if temp_file_path:
                    os.unlink(temp_file_path)
            except Exception:
                pass

            # If generator produced files, create a ZIP like the original flow and render results
            bulk_zip_name = None
            if generated:
                try:
                    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    bulk_zip_name = f"bulk_{form_aanvraag_type}_{ts}.zip"
                    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
                    zip_path = DOWNLOADS_DIR / bulk_zip_name
                    from zipfile import ZIP_DEFLATED as _ZIP_DEF, ZipFile as _ZipFile
                    with _ZipFile(str(zip_path), "w", _ZIP_DEF) as zf:
                        for fn in generated:
                            found = None
                            # search priority: the out_dir where generator saved the file,
                            # then configured OUTPUT_MAP folders, then the build/excel_generated fallback
                            candidates = []
                            try:
                                candidates.append(Path(out_dir_str))
                            except Exception:
                                pass
                            candidates.extend(list(OUTPUT_MAP.values()))
                            candidates.append(Path(__file__).parent.parent / "build" / "excel_generated")
                            for folder in candidates:
                                p = Path(folder) / fn
                                if p.exists():
                                    found = p
                                    break
                            if found:
                                zf.write(str(found), arcname=fn)
                except Exception:
                    bulk_zip_name = None

            yaml_candidate = Path(__file__).parent.parent / "docs" / "excel_datasets.yml"
            datasets = load_datasets_yaml(yaml_candidate)
            success_rate = None
            total_tests = 0
            last_status = None
            last_time = None
            bulk_results = {"generated": generated, "errors": errors}
            # Pass any XSD loader error message to the template so we can show an inline warning
            xsd_error = _LAST_XSD_ERROR
            return render_template(
                "genereer_xml.html",
                xml_path=None,
                excel_records=datasets,
                total_tests=total_tests,
                last_test_status=last_status,
                last_test_time=last_time,
                success_rate=success_rate,
                bulk_results=bulk_results,
                bulk_zip=bulk_zip_name,
                xsd_error=xsd_error,
            )
        except Exception:
            # fall through to original in-Python mapping fallback
            try:
                if temp_file_path:
                    os.unlink(temp_file_path)
            except Exception:
                pass
            pass

    # By default, we map normalized header names -> indices

    # Check for client-provided mapping indices (mapping_bsn etc.). If provided, we will use indices
    mapping = {}
    mapping_keys = [
        "bsn",
        "geboortedatum",
        "naam",
        "dateersteaodag",
        "inddirecteuitkering",
        "cdredenaangifteao",
        "cdredenziekmelding",
        "indwerkdagopzaterdag",
        "indwerkdagopzondag",
    ]
    for k in mapping_keys:
        mv = request.form.get(f"mapping_{k}")
        if mv is not None and mv != "":
            try:
                mapping[k] = int(mv)
            except Exception:
                mapping[k] = None

    generated = []
    errors = []
    aanvraag_type = request.form.get("aanvraag_type") or "ZBM"

    # detect workbook date mode
    try:
        date1904 = bool(getattr(wb.properties, "date1904", False))
    except Exception:
        date1904 = False

    row_index = 1
    for row in rows:
        row_index += 1
        # If mapping is provided, pick values by index, otherwise try to find by normalized header names
        r = {}
        if mapping:
            for mk in mapping:
                idx = mapping.get(mk)
                if idx is None:
                    r[mk] = None
                else:
                    try:
                        r[mk] = row[idx] if idx < len(row) else None
                    except Exception:
                        r[mk] = None
        else:
            # normalize header keys for fallback mapping
            def norm(h):
                return (
                    (str(h).strip().lower().replace(" ", "").replace("_", ""))
                    if h is not None
                    else ""
                )

            header_norm = {i: norm(headers[i]) for i in range(len(headers))}
            for i, val in enumerate(row):
                key = header_norm.get(i, "")
                if key:
                    r[key] = val

        # map to required keys
        data = {}
        # Accept several aliases for BSN
        bsn_val = None
        for candidate in ("bsn", "burgerservicenr", "burgerservicenummer", "burgerservicenr"):
            if r.get(candidate) is not None:
                bsn_val = r.get(candidate)
                break
        data["BSN"] = str(bsn_val).strip() if bsn_val is not None else ""

        # Name: accept direct 'naam' or compose from first name + last name
        naam_val = None
        if r.get("naam") is not None:
            naam_val = r.get("naam")
        else:
            first = r.get("voornaam") or r.get("eerstevoornaam") or r.get("voorletters") or ""
            last = r.get("achternaam") or r.get("significantdeelvandeachternaam") or ""
            combined = f"{first} {last}".strip()
            if combined:
                naam_val = combined
        data["Naam"] = str(naam_val).strip() if naam_val is not None else ""

        gebo_val = r.get("geboortedatum")
        if gebo_val is None:
            data["Geb_datum"] = ""
        elif isinstance(gebo_val, (int, float)) or (
            isinstance(gebo_val, str) and gebo_val.isdigit()
        ):
            data["Geb_datum"] = excel_serial_to_yyyymmdd(gebo_val, date1904=date1904)
        else:
            data["Geb_datum"] = _format_date_yyyymmdd(gebo_val)

        # Melding Ziekte fields
        dae_val = r.get("dateersteaodag")
        if dae_val is None:
            data["DatEersteAoDag"] = ""
        elif isinstance(dae_val, (int, float)) or (
            isinstance(dae_val, str) and dae_val.isdigit()
        ):
            data["DatEersteAoDag"] = excel_serial_to_yyyymmdd(
                dae_val, date1904=date1904
            )
        else:
            data["DatEersteAoDag"] = _format_date_yyyymmdd(dae_val)
        v = r.get("inddirecteuitkering")
        data["IndDirecteUitkering"] = str(v).strip() if v is not None else ""
        v = r.get("cdredenaangifteao")
        data["CdRedenAangifteAo"] = str(v).strip() if v is not None else ""
        v = r.get("cdredenziekmelding")
        data["CdRedenZiekmelding"] = str(v).strip() if v is not None else ""
        v = r.get("indwerkdagopzaterdag")
        data["IndWerkdagOpZaterdag"] = str(v).strip() if v is not None else ""
        v = r.get("indwerkdagopzondag")
        data["IndWerkdagOpZondag"] = str(v).strip() if v is not None else ""

        # Basic validation
        if not data["BSN"] or not data["Naam"]:
            errors.append(f"Regel {row_index}: ontbrekende BSN of Naam; overslaan")
            continue

        unique_suffix = (
            datetime.datetime.now().strftime("%Y%m%d%H%M%S") + f"_{row_index}"
        )
        data["CdBerichtType"] = aanvraag_type
        data["BronApplicatie"] = aanvraag_type
        tree = fill_xml_template(None, data, unique_suffix)
        root = tree.getroot()
        # XSD validation for legacy flow
        schema = _load_message_xsd()
        if schema is not None:
            try:
                xml_bytes = ET.tostring(root, encoding="utf-8")
                lroot = etree.fromstring(xml_bytes)
                if not schema.validate(lroot):
                    le = schema.error_log
                    msgs = [str(e.message) for e in le]
                    errors.append(f"Regel {row_index}: XSD fouten: {'; '.join(msgs)}")
                    continue
            except Exception as ve:
                errors.append(f"Regel {row_index}: XSD validatiefout: {ve}")
                continue

        def add_or_set(tag, val):
            if val is None or val == "":
                return
            for elem in root.iter(tag):
                elem.text = str(val)
            if not any(True for _ in root.iter(tag)):
                etree.SubElement(root, tag).text = str(val)

        add_or_set("DatEersteAoDag", data.get("DatEersteAoDag"))
        add_or_set("IndDirecteUitkering", data.get("IndDirecteUitkering"))
        add_or_set("CdRedenAangifteAo", data.get("CdRedenAangifteAo"))
        add_or_set("CdRedenZiekmelding", data.get("CdRedenZiekmelding"))
        add_or_set("IndWerkdagOpZaterdag", data.get("IndWerkdagOpZaterdag"))
        add_or_set("IndWerkdagOpZondag", data.get("IndWerkdagOpZondag"))

        filename = f"aanvraag_{aanvraag_type}_{unique_suffix}.xml"
        try:
            save_xml(tree, aanvraag_type, filename)
            generated.append(filename)
        except Exception as e:
            errors.append(f"Regel {row_index}: fout bij opslaan {e}")

    # Close workbook
    try:
        wb.close()
    except Exception:
        pass

    # If we generated files, create a ZIP archive for convenience
    bulk_zip_name = None
    if generated:
        try:
            from zipfile import ZIP_DEFLATED, ZipFile

            ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            bulk_zip_name = f"bulk_{aanvraag_type}_{ts}.zip"
            # Create zip in central DOWNLOADS_DIR so download route can serve it
            DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
            zip_path = DOWNLOADS_DIR / bulk_zip_name
            with ZipFile(str(zip_path), "w", ZIP_DEFLATED) as zf:
                for fn in generated:
                    # search OUTPUT_MAP locations and fallback to build/excel_generated
                    found = None
                    candidates = list(OUTPUT_MAP.values())
                    candidates.append(Path(__file__).parent.parent / "build" / "excel_generated")
                    for folder in candidates:
                        p = Path(folder) / fn
                        if p.exists():
                            found = p
                            break
                    if found:
                        zf.write(str(found), arcname=fn)
            # Also include zip name in generated list for template convenience
        except Exception:
            bulk_zip_name = None

    # Render same template with summary
    yaml_candidate = Path(__file__).parent.parent / "docs" / "excel_datasets.yml"
    datasets = load_datasets_yaml(yaml_candidate)
    # reuse tile data
    success_rate = None

    # Ensure these dashboard variables exist for the render context
    total_tests = 0
    last_status = None
    last_time = None

    bulk_results = {"generated": generated, "errors": errors}
    return render_template(
        "genereer_xml.html",
        xml_path=None,
        excel_records=datasets,
        total_tests=total_tests,
        last_test_status=last_status,
        last_test_time=last_time,
        success_rate=success_rate,
        bulk_results=bulk_results,
        bulk_zip=bulk_zip_name,
    )


@app.route("/resultaten")
def resultaten_pagina():
    # List generated XMLs from OUTPUT_MAP locations
    generated = []
    try:
        for k, folder in OUTPUT_MAP.items():
            if not folder.exists():
                continue
            for f in folder.glob("*.xml"):
                try:
                    generated.append(
                        {
                            "tijdstip": datetime.datetime.fromtimestamp(
                                f.stat().st_mtime
                            ).isoformat(),
                            "filename": f.name,
                            "aanvraag_type": k,
                            "output_path": str(f),
                            "size": f.stat().st_size,
                        }
                    )
                except Exception:
                    continue
        generated = sorted(generated, key=lambda x: x.get("tijdstip") or "", reverse=True)
    except Exception:
        generated = []
    # expose server-side ZIP limits to the template for tooltips and UI hints
    zip_limits = {
        "max_files": ZIP_MAX_FILES,
        "max_total_bytes": ZIP_MAX_TOTAL_SIZE,
        "max_file_bytes": ZIP_MAX_FILE_SIZE,
    }
    return render_template("resultaten.html", generated=generated, zip_limits=zip_limits)



@app.route("/resultaten/download/<filename>")
def download_generated(filename):
    # Search known output locations for the filename and send it
    for folder in OUTPUT_MAP.values():
        p = folder / secure_filename(filename)
        try:
            if p.exists():
                return send_file(
                    str(p), as_attachment=True, download_name=secure_filename(filename)
                )
        except Exception:
            continue
    # Also check central downloads directory
    dl = DOWNLOADS_DIR / secure_filename(filename)
    try:
        if dl.exists():
            return send_file(
                str(dl), as_attachment=True, download_name=secure_filename(filename)
            )
    except Exception:
        pass
    flash("Gevraagd bestand niet gevonden", "danger")
    return redirect(url_for("resultaten_pagina"))


@app.route("/resultaten/download-body/<filename>")
def download_body_only(filename):
    """Extract and download just the UwvZwMeldingInternBody (without SOAP envelope)."""
    fn = secure_filename(filename)
    found = None
    
    # Search for the file in known locations
    for folder in OUTPUT_MAP.values():
        p = folder / fn
        if p.exists() and p.is_file():
            found = p
            break
    
    if not found:
        dl = DOWNLOADS_DIR / fn
        if dl.exists() and dl.is_file():
            found = dl
    
    if not found:
        flash("Bestand niet gevonden", "danger")
        return redirect(url_for("resultaten_pagina"))
    
    try:
        # Parse the SOAP XML
        tree = etree.parse(str(found))
        root = tree.getroot()
        
        # Find the SOAP Body element
        ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/'}
        body = root.find('.//soap:Body', ns)
        
        if body is None:
            flash("Geen SOAP Body gevonden in XML", "danger")
            return redirect(url_for("resultaten_pagina"))
        
        # Get the first child of Body (should be UwvZwMeldingInternBody)
        body_content = None
        for child in body:
            body_content = child
            break
        
        if body_content is None:
            flash("Geen content gevonden in SOAP Body", "danger")
            return redirect(url_for("resultaten_pagina"))
        
        # Create a clean copy without SOAP namespace declarations
        xml_bytes = ET.tostring(body_content, encoding='UTF-8')
        clean_body = etree.fromstring(xml_bytes)
        etree.cleanup_namespaces(clean_body)
        
        # Create output filename
        body_filename = fn.replace('.xml', '_body.xml')
        
        # Write body content to a temporary file in downloads dir
        output_path = DOWNLOADS_DIR / body_filename
        output_tree = etree.ElementTree(clean_body)
        output_tree.write(
            str(output_path),
            pretty_print=True,
            xml_declaration=True,
            encoding='UTF-8'
        )
        
        # Send the file
        return send_file(
            str(output_path),
            as_attachment=True,
            download_name=body_filename
        )
        
    except Exception as e:
        flash(f"Fout bij extraheren body: {e}", "danger")
        return redirect(url_for("resultaten_pagina"))


@app.route('/resultaten/download-zip', methods=['POST'])
def download_generated_zip():
    """Create a ZIP archive of requested generated files and return it.

    Expects JSON body: {"filenames": ["a.xml", "b.xml"]}
    Only files from known OUTPUT_MAP locations or the central DOWNLOADS_DIR
    are included. The created ZIP is stored in `DOWNLOADS_DIR` and returned
    as an attachment.
    """
    try:
        req = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON"}), 400
    if not req or not isinstance(req.get('filenames'), list):
        return jsonify({"error": "Missing 'filenames' list"}), 400

    filenames = [secure_filename(str(f)) for f in req.get('filenames') if f]
    if not filenames:
        return jsonify({"error": "No valid filenames provided"}), 400

    # Collect found files
    found_files = []
    for fn in filenames:
        found = None
        for folder in OUTPUT_MAP.values():
            p = folder / fn
            if p.exists() and p.is_file():
                found = p
                break
        if not found:
            dl = DOWNLOADS_DIR / fn
            if dl.exists() and dl.is_file():
                found = dl
        if found:
            found_files.append((fn, found))

    if not found_files:
        return jsonify({"error": "Geen van de gevraagde bestanden gevonden"}), 404

    # Enforce limits: number of files, per-file size, total size
    if len(found_files) > ZIP_MAX_FILES:
        return (
            jsonify({"error": f"Te veel bestanden aangevraagd (max {ZIP_MAX_FILES})"}),
            413,
        )
    total_size = 0
    for arcname, p in found_files:
        try:
            sz = p.stat().st_size
        except Exception:
            sz = 0
        if ZIP_MAX_FILE_SIZE and sz > ZIP_MAX_FILE_SIZE:
            return (
                jsonify({"error": f"Bestand te groot: {arcname} (max {ZIP_MAX_FILE_SIZE} bytes)"}),
                413,
            )
        total_size += sz
    if ZIP_MAX_TOTAL_SIZE and total_size > ZIP_MAX_TOTAL_SIZE:
        return (
            jsonify({"error": "Totale omvang van gekozen bestanden overschrijdt de limiet"}),
            413,
        )

    # Create zip in DOWNLOADS_DIR with a unique name
    ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    zip_name = f"bulk_selected_{ts}.zip"
    zip_path = DOWNLOADS_DIR / zip_name
    try:
        DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        with ZipFile(str(zip_path), 'w', ZIP_DEFLATED) as zf:
            for arcname, p in found_files:
                try:
                    zf.write(str(p), arcname=arcname)
                except Exception:
                    continue
    except Exception as e:
        return jsonify({"error": f"Kon ZIP niet maken: {e}"}), 500

    try:
        return send_file(str(zip_path), as_attachment=True, download_name=zip_name)
    except Exception:
        return jsonify({"error": "Kon ZIP niet terugsturen"}), 500


@app.route('/resultaten/preview/<filename>')
def preview_generated(filename):
    """Return a small preview (first N chars/lines) and metadata for a generated file."""
    fn = secure_filename(filename)
    found = None
    for folder in OUTPUT_MAP.values():
        p = folder / fn
        if p.exists() and p.is_file():
            found = p
            break
    if not found:
        dl = DOWNLOADS_DIR / fn
        if dl.exists() and dl.is_file():
            found = dl
    if not found:
        return jsonify({"error": "Bestand niet gevonden"}), 404

    try:
        stat = found.stat()
        size = stat.st_size
        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).isoformat()
        # Read small preview (first ~8KB)
        preview_text = ''
        with open(found, 'r', encoding='utf-8', errors='ignore') as fh:
            preview_text = fh.read(8192)
            # Truncate to last complete line for nicer display
            if len(preview_text) == 8192:
                # ensure we end at a line break
                last_n = preview_text.rfind('\n')
                if last_n > 0:
                    preview_text = preview_text[:last_n]

        return jsonify({
            "filename": fn,
            "size": size,
            "tijdstip": mtime,
            "preview": preview_text,
        }), 200
    except Exception:
        return jsonify({"error": "Kon bestand niet lezen"}), 500


@app.route("/upload_xml_validatie", methods=["POST"])
def upload_xml_validatie():
    if "xmlfile" not in request.files:
        flash("Geen bestand geüpload", "danger")
        return redirect(url_for("index"))
    bestand = request.files["xmlfile"]
    if bestand.filename == "":
        flash("Geen bestand geselecteerd", "danger")
        return redirect(url_for("index"))
    try:
        content = bestand.read()
        doc = etree.parse(io.BytesIO(content))
        xsd_path = (
            Path(__file__).parent.parent
            / "docs"
            / "UwvZwMeldingInternBody-v0428-b01.xsd"
        )
        if xsd_path.exists():
            schema_doc = etree.parse(str(xsd_path))
            schema = etree.XMLSchema(schema_doc)
            if schema.validate(doc):
                flash(
                    f'Bestand "{bestand.filename}" is geldig en voldoet aan het XSD.',
                    "success",
                )
            else:
                fouten = schema.error_log
                flash("XML voldoet niet aan het XSD: " + str(fouten), "danger")
        else:
            flash(
                "XSD niet gevonden; alleen syntactische XML-validatie uitgevoerd.",
                "warning",
            )
    except Exception as e:
        flash("Fout bij valideren XML: " + str(e), "danger")
    return redirect(url_for("index"))


def _read_xml_events(limit: int | None = None):
    """Read `web/xml_events.jsonl` and return a list of event dicts (newest first)."""
    events_file = Path(__file__).parent / "xml_events.jsonl"
    if not events_file.exists():
        return []
    out = []
    try:
        with open(events_file, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    import json as _json

                    ev = _json.loads(line)
                    out.append(ev)
                except Exception:
                    continue
    except Exception:
        return []
    # sort newest first by tijdstip if present
    try:
        out.sort(key=lambda e: e.get("tijdstip") or e.get("datum") or "", reverse=True)
    except Exception:
        pass
    if limit is not None:
        return out[:limit]
    return out


@app.route('/api/xml/events')
def api_xml_events():
    """Return events for a given date (query param `date=YYYY-MM-DD`)."""
    dateq = request.args.get("date")
    evs = _read_xml_events()
    if dateq:
        filtered = [e for e in evs if (e.get("tijdstip", "").startswith(dateq) or e.get("datum", "").startswith(dateq))]
    else:
        filtered = evs
    return jsonify({"events": filtered}), 200


@app.route('/api/xml/throughput')
@app.route('/api/xml-stats')
def api_xml_throughput():
    """Return aggregated throughput per day for the last `days` days (default 14).

    Response shape: {"aggregated": [ {datum, totaal, geslaagd, gefaald, succes_percentage}, ... ] }
    """
    try:
        days = int(request.args.get("days", "14"))
    except Exception:
        days = 14
    events = _read_xml_events()
    # build counts per date
    from collections import defaultdict

    counts = defaultdict(lambda: {"totaal": 0, "geslaagd": 0, "gefaald": 0})
    for e in events:
        tijd = e.get("tijdstip") or e.get("datum") or ""
        if not tijd:
            continue
        date = tijd[:10]
        counts[date]["totaal"] += 1
        if e.get("success") in (True, "True", "true", 1):
            counts[date]["geslaagd"] += 1
        else:
            counts[date]["gefaald"] += 1

    # build ordered list for the requested range (oldest -> newest)
    import datetime as _dt

    today = _dt.date.today()
    days_list = [today - _dt.timedelta(days=i) for i in range(days - 1, -1, -1)]
    aggregated = []
    for d in days_list:
        key = d.isoformat()
        vals = counts.get(key, {"totaal": 0, "geslaagd": 0, "gefaald": 0})
        totaal = vals.get("totaal", 0)
        geslaagd = vals.get("geslaagd", 0)
        gefaald = vals.get("gefaald", 0)
        succes_pct = None
        if totaal > 0:
            try:
                succes_pct = round((geslaagd / totaal) * 100, 2)
            except Exception:
                succes_pct = None
        aggregated.append({
            "datum": key,
            "totaal": totaal,
            "geslaagd": geslaagd,
            "gefaald": gefaald,
            "succes_percentage": succes_pct,
        })
    return jsonify({"aggregated": aggregated}), 200


@app.route('/api/test/historie')
def api_test_historie():
    # return recent events as an array for the dashboard
    hist = _read_xml_events(limit=200)
    # normalize fields expected by the JS
    norm = []
    for e in hist:
        norm.append(
            {
                "tijdstip": e.get("tijdstip") or e.get("datum") or e.get("time") or "",
                "filename": e.get("filename") or e.get("output_path") or e.get("bestandsnaam") or "",
                "size": e.get("size") or 0,
                "success": e.get("success") in (True, "True", "true", 1),
            }
        )
    return jsonify(norm), 200


@app.route('/api/test/laatste')
def api_test_laatste():
    hist = _read_xml_events(limit=1)
    if not hist:
        return jsonify({}), 200
    e = hist[0]
    status = "Geslaagd" if e.get("success") in (True, "True", "true", 1) else "Gefaald"
    return jsonify({"status": status, "datum": e.get("tijdstip") or e.get("datum")}), 200


@app.route('/api/test/totaal')
def api_test_totaal():
    hist = _read_xml_events()
    return jsonify({"totaal": len(hist)}), 200


@app.route('/api/test/uitvoeren', methods=["POST"])
def api_test_uitvoeren():
    """Simulate a test execution and return a minimal result object suitable for the UI.

    This intentionally does not run real tests; it returns a synthetic success
    response so the dashboard UX can be exercised locally.
    """
    import datetime as _dt

    result = {
        "success": True,
        "tijdstip": _dt.datetime.now().isoformat(),
        "uitvoer": "Simulated test run (local)",
        "foutmeldingen": "",
    }
    return jsonify(result), 200
