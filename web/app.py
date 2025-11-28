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
from werkzeug.utils import secure_filename

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
    from .beheer import beheer_bp
    from .instellingen import instellingen_bp

    app.register_blueprint(beheer_bp, url_prefix="/beheer")
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
    try:
        wb = openpyxl.load_workbook(
            filename=io.BytesIO(f.read()), read_only=True, data_only=True
        )
    except Exception as e:
        flash("Kon Excel-bestand niet lezen: " + str(e), "danger")
        return redirect(url_for("genereer_xml"))

    sheet = wb.active

    # Read headers from first row
    rows = sheet.iter_rows(values_only=True)
    try:
        headers = [h if h is not None else "" for h in next(rows)]
    except StopIteration:
        flash("Leeg Excel-bestand", "danger")
        return redirect(url_for("genereer_xml"))

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
        data["BSN"] = str(r.get("bsn", "")).strip() if r.get("bsn") is not None else ""
        data["Naam"] = (
            str(r.get("naam", "")).strip() if r.get("naam") is not None else ""
        )

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
        tree = fill_xml_template(None, data, unique_suffix)
        root = tree.getroot()

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
                    # find the actual file in the known OUTPUT_MAP locations
                    found = None
                    for folder in OUTPUT_MAP.values():
                        p = folder / fn
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


@app.route("/login", methods=["GET", "POST"])
def login():
    # Hardened login: checks admin credentials from env vars or defaults.
    ADMIN_USER = os.environ.get("U_XMLATOR_ADMIN_USER", "admin")
    ADMIN_PASS = os.environ.get("U_XMLATOR_ADMIN_PASS", "admin123")

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["user"] = {"name": username}
            # manage area flag
            session["beheer_ingelogd"] = True
            flash("Ingelogd als beheerder")
            next_target = request.args.get("next") or url_for("index")
            return redirect(next_target)
        else:
            flash("Ongeldige gebruikersnaam of wachtwoord", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    session.pop("beheer_ingelogd", None)
    flash("Uitgelogd")
    return redirect(url_for("index"))


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
