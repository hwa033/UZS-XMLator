import datetime
import io
import json
import os
import sys
import zipfile
from typing import Any

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from .instellingen import instellingen_bp

app = Flask(__name__)

# Laad configuratie uit instellingen.json
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "instellingen.json")


def _load_config():
    defaults = {
        "omgeving": "UZSTA_OMG",
        "filedrop_locaties": {},
        "upload_max_size_mb": 10,
        "xsd_path": "docs/UwvZwMeldingInternBody-v0428-b01.xsd",
        "log_level": "INFO",
        "output_directory": "",
        "auto_validate": False,
        "default_test_indicator": "2",
        "default_fiscaal_nr": "",
        "default_loonheffing_nr": "",
        "file_retention_days": 30,
    }
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return defaults
            merged = defaults.copy()
            merged.update(data)
            return merged
    except Exception as e:
        print(
            f"Waarschuwing: Kon configuratie niet laden ({CONFIG_PATH}): {e}",
            file=sys.stderr,
        )
        return defaults


CONFIG = _load_config()

# Beveiligingsinstellingen
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
SECRET_KEY = os.environ.get("U_XMLATOR_SECRET")

if FLASK_ENV == "production" and not SECRET_KEY:
    raise SystemExit(
        "FOUT: Zet de U_XMLATOR_SECRET omgevingsvariabele als FLASK_ENV=production.\n"
        'Voorbeeld (PowerShell): $env:U_XMLATOR_SECRET = "uw-geheim-hier"'
    )

app.secret_key = SECRET_KEY or "verander-dit-naar-een-lang-geheim-1234"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("U_XMLATOR_COOKIE_SECURE", "1") == "1"
)
app.config["SESSION_COOKIE_SAMESITE"] = os.environ.get("U_XMLATOR_SAMESITE", "Lax")
app.config["MAX_CONTENT_LENGTH"] = (
    max(1, int(CONFIG.get("upload_max_size_mb", 10))) * 1024 * 1024
)
ALLOWED_EXTENSIONS = {".xlsx", ".xls"}

# Register blueprints
app.register_blueprint(instellingen_bp, url_prefix="/instellingen")


def _error_log_path():
    base = os.path.join(os.path.dirname(__file__), "..")
    logdir = os.path.join(base, "build", "logs")
    try:
        os.makedirs(logdir, exist_ok=True)
    except Exception:
        pass
    return os.path.join(logdir, "xmlator_errors.jsonl")


@app.route("/api/openapi.yaml")
def openapi_spec():
    """Serve OpenAPI spec (static YAML in docs/)."""
    docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    return send_from_directory(docs_dir, "openapi.yaml", mimetype="application/yaml")


def _append_error_log(entry: dict):
    try:
        p = _error_log_path()
        entry = dict(entry or {})
        if "tijdstip" not in entry:
            entry["tijdstip"] = datetime.datetime.now().isoformat()
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_error_log(max_items: int = 20):
    try:
        p = _error_log_path()
        if not os.path.exists(p):
            return []
        lines = []
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                lines.append(line)
        items = []
        for s in reversed(lines):
            try:
                items.append(json.loads(s))
            except Exception:
                continue
            if len(items) >= max_items:
                break
        return items
    except Exception:
        return []


def get_output_directory(aanvraag_type=None, omgeving=None):
    """
    Bepaal uitvoermap voor gegenereerde bestanden op basis van berichttype en omgeving.

    aanvraag_type: OTP3, ZBM, VM
    omgeving: UZSTA_OMG, UZSA_ACC1, UZSC_ACC1, UZSD_ACC1, UZSP_ACC1 (default uit config)
    """
    # Lokale fallback voor dev/test
    base = os.path.join(os.path.dirname(__file__), "..")
    fallback_dir = os.path.join(base, "build", "excel_generated")

    # Laad actuele configuratie
    cfg = _load_config()
    # Omgeving uit config indien niet expliciet opgegeven
    if omgeving is None:
        omgeving = cfg.get("omgeving", "UZSTA_OMG")

    filedrop_locaties = cfg.get("filedrop_locaties", {})

    # Optional override for filedrop base path (e.g., set XMLATOR_FILEDROP_BASE=/data/filedrop)
    default_filedrop_base = r"D:\\GUP\\UZS\\filedrop"
    override_filedrop_base = os.environ.get("XMLATOR_FILEDROP_BASE")

    def _normalize(path: str) -> str:
        # Expand env vars and user home, then apply optional base override
        expanded = os.path.expanduser(os.path.expandvars(path))
        if override_filedrop_base:
            norm_expanded = expanded.replace("\\", "/")
            norm_default = default_filedrop_base.replace("\\", "/")
            norm_override = override_filedrop_base.replace("\\", "/")
            if norm_expanded.startswith(norm_default):
                expanded = norm_override + norm_expanded[len(norm_default):]
        return os.path.normpath(expanded)

    # Helper: probeer pad te gebruiken/aan te maken, anders None teruggeven
    def _try_use(path: str):
        path = _normalize(path)
        try:
            # Controleer of drive beschikbaar is (Windows): bv. 'D:\\'
            drive, _ = os.path.splitdrive(path)
            if drive and not os.path.exists(drive + os.path.sep):
                return None
            os.makedirs(path, exist_ok=True)
            return path
        except Exception as e:
            print(
                f"[WAARSCHUWING] Kan uitvoermap niet aanmaken ({path}): {e}",
                file=sys.stderr,
            )
            return None

    if aanvraag_type and omgeving in filedrop_locaties:
        berichttype = str(aanvraag_type).upper()
        omg_map = filedrop_locaties[omgeving]

        # 1) Exacte match
        if berichttype in omg_map:
            chosen = _try_use(omg_map[berichttype])
            if chosen:
                return chosen

        # 2) ZBM/VM delen locatie
        if berichttype in ["ZBM", "VM"]:
            for key in ["ZBM", "VM"]:
                if key in omg_map:
                    chosen = _try_use(omg_map[key])
                    if chosen:
                        return chosen

        # 3) OTP3/DIGIPOORT delen locatie
        if berichttype in ["DIGIPOORT", "OTP3"]:
            for key in ["OTP3", "DIGIPOORT"]:
                if key in omg_map:
                    chosen = _try_use(omg_map[key])
                    if chosen:
                        return chosen

    # 4) Fallback naar lokale directory (voor dev/test)
    os.makedirs(fallback_dir, exist_ok=True)
    return fallback_dir


def list_generated_files(limit=25, prune=False):
    """Lijst gegenereerde XML-bestanden, optioneel met verwijdering van oudste."""
    directories = [
        get_output_directory("ZBM"),
        get_output_directory("Digipoort"),
        get_output_directory(),
    ]
    files_with_time = []
    for out_dir in directories:
        if os.path.exists(out_dir):
            for fname in os.listdir(out_dir):
                if fname.endswith(".xml"):
                    fpath = os.path.join(out_dir, fname)
                    try:
                        mtime = os.path.getmtime(fpath)
                        files_with_time.append((fname, fpath, mtime))
                    except Exception:
                        continue

    files_with_time.sort(key=lambda x: x[2], reverse=True)
    total_count = len(files_with_time)

    if prune and total_count > limit:
        for fname, fpath, _ in files_with_time[limit:]:
            try:
                os.remove(fpath)
            except Exception as e:
                print(
                    f"[WAARSCHUWING] Kon {fname} niet verwijderen: {e}", file=sys.stderr
                )
        files_with_time = files_with_time[:limit]
        total_count = len(files_with_time)

    generated = []
    for fname, fpath, mtime in files_with_time[:limit]:
        try:
            tijdstip = datetime.datetime.fromtimestamp(mtime).isoformat()
            size = os.path.getsize(fpath)
            generated.append({"filename": fname, "tijdstip": tijdstip, "size": size})
        except Exception:
            continue
    return generated, total_count


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/genereer_xml")
def genereer_xml():
    zip_limits = {"max_files": 50, "max_size_mb": 100}
    generated, total_count = list_generated_files(limit=25, prune=True)
    return render_template(
        "genereer_xml.html",
        zip_limits=zip_limits,
        generated=generated,
        total_count=total_count,
    )


@app.route("/resultaten/fragment")
def resultaten_fragment():
    zip_limits = {"max_files": 50, "max_size_mb": 100}
    generated, total_count = list_generated_files(limit=25, prune=True)
    return make_response(
        render_template(
            "_results_panel.html",
            zip_limits=zip_limits,
            generated=generated,
            total_count=total_count,
        )
    )


@app.route("/resultaten/download/<filename>")
def download_generated(filename):
    if not filename.endswith(".xml") or "/" in filename or ".." in filename:
        flash("Ongeldige bestandsnaam.", "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    directories = [
        get_output_directory("ZBM"),
        get_output_directory("Digipoort"),
        get_output_directory(),
    ]

    for output_dir in directories:
        if os.path.exists(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.exists(file_path):
                return send_from_directory(output_dir, filename, as_attachment=True)

    flash("Bestand niet gevonden.", "danger")
    return redirect(request.referrer or url_for("genereer_xml"))


@app.route("/resultaten/delete-selected", methods=["POST"])
def delete_selected_files():
    try:
        data = request.get_json(silent=True) or {}
        filenames = data.get("filenames") or []
        if not isinstance(filenames, list) or not filenames:
            return jsonify({"error": "Geen bestanden geselecteerd"}), 400

        # Gebruik exact dezelfde directories als list_generated_files() doet
        directories = [
            get_output_directory("ZBM"),
            get_output_directory("Digipoort"),
            get_output_directory(),
        ]

        # Bouw een mapping van bestandsnaam → volledig pad door alle dirs te scannen
        file_map = {}
        for out_dir in directories:
            if os.path.exists(out_dir):
                for fname in os.listdir(out_dir):
                    if fname.endswith(".xml"):
                        fpath = os.path.join(out_dir, fname)
                        if os.path.isfile(fpath):
                            file_map[fname] = fpath

        deleted = 0
        missing = []

        for fn in filenames:
            if (
                not isinstance(fn, str)
                or "/" in fn
                or ".." in fn
                or not fn.endswith(".xml")
            ):
                continue

            if fn not in file_map:
                missing.append(fn)
                continue

            fpath = file_map[fn]
            try:
                os.remove(fpath)
                deleted += 1
            except Exception as e:
                print(
                    f"[WAARSCHUWING] Kon {fpath} niet verwijderen: {e}", file=sys.stderr
                )
                missing.append(fn)

        return jsonify({"success": True, "deleted": deleted, "missing": missing})
    except Exception as e:
        print(f"[FOUT] delete_selected_files: {e}", file=sys.stderr)
        return jsonify({"error": f"Fout bij verwijderen: {e}"}), 500


@app.route("/resultaten/download-zip", methods=["POST"])
def download_generated_zip():
    try:
        data = request.get_json(silent=True) or {}
        filenames = data.get("filenames") or []
        if not isinstance(filenames, list) or not filenames:
            return jsonify({"error": "Geen bestanden geselecteerd"}), 400

        safe_files = []
        out_dir = get_output_directory()
        for fn in filenames:
            if (
                not isinstance(fn, str)
                or "/" in fn
                or ".." in fn
                or not fn.endswith(".xml")
            ):
                return jsonify({"error": f"Ongeldige bestandsnaam: {fn}"}), 400
            fp = os.path.join(out_dir, fn)
            if not os.path.exists(fp) or not os.path.isfile(fp):
                return jsonify({"error": f"Bestand niet gevonden: {fn}"}), 404
            safe_files.append((fn, fp))

        mem = io.BytesIO()
        with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for name, path in safe_files:
                zf.write(path, arcname=name)
        mem.seek(0)
        zip_bytes = mem.getvalue()

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_name = f"uwv_xmlator_selectie_{ts}.zip"
        headers = {
            "Content-Type": "application/zip",
            "Content-Disposition": f"attachment; filename*=UTF-8''{zip_name}",
            "Content-Length": str(len(zip_bytes)),
        }
        return Response(zip_bytes, headers=headers)
    except Exception as e:
        return jsonify({"error": f"Fout bij maken van ZIP: {e}"}), 500


@app.route("/upload_excel", methods=["POST"])
def upload_excel():
    import subprocess
    import tempfile
    import warnings

    import openpyxl

    file = request.files.get("excel_file")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not file:
        msg = "Geen bestand geüpload."
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in ALLOWED_EXTENSIONS:
        msg = "Ongeldig bestandstype; alleen .xlsx en .xls zijn toegestaan."
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    # Herlaad settings voor runtime wijzigingen
    cfg = _load_config()
    app.config["MAX_CONTENT_LENGTH"] = (
        max(1, int(cfg.get("upload_max_size_mb", 10))) * 1024 * 1024
    )

    if (
        request.content_length
        and request.content_length > app.config["MAX_CONTENT_LENGTH"]
    ):
        msg = f'Bestand te groot (max {app.config["MAX_CONTENT_LENGTH"] // (1024*1024)} MB).'
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    orig_filename = file.filename if file.filename else "upload.xlsx"
    filename = secure_filename(orig_filename)
    file_path = os.path.join(uploads_dir, filename)
    file.save(file_path)

    aanvraag_type = request.form.get("aanvraag_type", "ZBM").strip().upper()

    try:
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        if ws is None:
            msg = "Het geüploade Excel-bestand bevat geen werkblad of is ongeldig."
            if is_ajax:
                return jsonify({"success": False, "error": msg}), 400
            flash(msg, "danger")
            return redirect(request.referrer or url_for("genereer_xml"))

        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=False))
        header_names = [cell.value for cell in header_row]
        type_col = None
        for idx, name in enumerate(header_names):
            if name and str(name).strip().lower() in [
                "cdberichttype",
                "aanvraag_type",
                "type",
            ]:
                type_col = idx
                break

        if type_col is None:
            ws.cell(row=1, column=len(header_names) + 1, value="CdBerichtType")
            type_col = len(header_names)

        for i, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
            ws.cell(row=i, column=type_col + 1, value=aanvraag_type)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            patched_excel_path = tmp.name
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wb.save(patched_excel_path)
    except Exception as exc:
        msg = f"Fout bij verwerken van het Excel-bestand: {exc}"
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    generator_path = os.path.join(
        os.path.dirname(__file__), "..", "tools", "generate_from_excel.py"
    )
    output_dir = get_output_directory(aanvraag_type)
    os.makedirs(output_dir, exist_ok=True)
    python_exe = os.environ.get("PYTHON_EXE", sys.executable)

    try:
        subprocess.run(
            [
                python_exe,
                generator_path,
                "--input",
                patched_excel_path,
                "--outdir",
                output_dir,
                "--mode",
                "single",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        msg = f"Excel-bestand succesvol geüpload en {aanvraag_type} XML-bestanden gegenereerd."

        if is_ajax:
            return jsonify({"success": True, "message": msg}), 200
        flash(msg, "success")
    except subprocess.CalledProcessError as e:
        _append_error_log(
            {
                "type": "generation_error",
                "aanvraag_type": aanvraag_type,
                "omgeving": CONFIG.get("omgeving", ""),
                "output_dir": output_dir,
                "stderr": e.stderr,
                "stdout": e.stdout,
                "returncode": e.returncode,
                "filename": orig_filename,
            }
        )
        msg = f"Fout bij genereren van XML: {e.stderr or e.stdout}"
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
    except Exception as e:
        _append_error_log(
            {
                "type": "generation_exception",
                "aanvraag_type": aanvraag_type,
                "omgeving": CONFIG.get("omgeving", ""),
                "output_dir": output_dir,
                "error": str(e),
                "filename": orig_filename,
            }
        )
        msg = f"Fout bij genereren van XML: {e}"
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
    finally:
        for path in (patched_excel_path, file_path):
            try:
                if path and os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

    return redirect(url_for("genereer_xml"))


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/ready")
def ready():
    try:
        downloads_dir = os.path.join(
            os.path.dirname(__file__), "..", "web", "static", "downloads"
        )
        os.makedirs(downloads_dir, exist_ok=True)
        return jsonify({"status": "ready"}), 200
    except Exception:
        return jsonify({"status": "not_ready"}), 503


@app.route("/favicon.ico")
def favicon():
    return "", 204


###########
# Dashboard API — echte data op basis van gegenereerde XML-bestanden
###########


def _collect_output_directories():
    # Verzamel de relevante directories om te scannen
    dirs = []
    try:
        dirs.append(get_output_directory("ZBM"))
    except Exception:
        pass
    try:
        dirs.append(get_output_directory("OTP3"))
    except Exception:
        pass
    try:
        dirs.append(get_output_directory())
    except Exception:
        pass
    # Unique & bestaand
    unique = []
    for d in dirs:
        if d and d not in unique and os.path.exists(d):
            unique.append(d)
    return unique


def _scan_files(max_items=None):
    """Scan alle uitvoerdirectories en retourneer lijst met dicts per bestand."""
    result = []
    for d in _collect_output_directories():
        try:
            for fname in os.listdir(d):
                if not fname.lower().endswith(".xml"):
                    continue
                fpath = os.path.join(d, fname)
                try:
                    mtime = os.path.getmtime(fpath)
                    size = os.path.getsize(fpath)
                except Exception:
                    continue
                # Heuristische type-detectie op basis van pad
                lowerp = d.lower()
                if "uwvzwmelding_mq_v0428".lower() in lowerp:
                    btype = "OTP3"
                elif os.path.sep + "v0428" + os.path.sep in d:
                    btype = "ZBM/VM"
                else:
                    btype = "Onbekend"
                result.append(
                    {
                        "filename": fname,
                        "path": fpath,
                        "mtime": mtime,
                        "tijdstip": datetime.datetime.fromtimestamp(mtime).isoformat(),
                        "size": size,
                        "type": btype,
                        "status": "Geslaagd",
                    }
                )
        except Exception:
            continue
    # Nieuwste eerst
    result.sort(key=lambda x: x["mtime"], reverse=True)
    if max_items is not None:
        return result[:max_items]
    return result


@app.route("/api/test/laatste")
def api_test_laatste():
    try:
        files = _scan_files(max_items=1)
        if files:
            latest = files[0]
            return jsonify(
                {
                    "status": latest.get("status", "Geslaagd"),
                    "datum": latest.get("tijdstip"),
                }
            )
        else:
            return jsonify({"status": "Geen data", "datum": ""})
    except Exception as e:
        return jsonify({"status": "Onbekend", "datum": "", "error": str(e)})


@app.route("/api/test/totaal")
def api_test_totaal():
    try:
        total = len(_scan_files())
        return jsonify({"totaal": total})
    except Exception as e:
        return jsonify({"totaal": 0, "error": str(e)})


@app.route("/api/test/historie")
def api_test_historie():
    try:
        files = _scan_files(max_items=50)
        # Map naar eenvoudiger payload
        payload = [
            {
                "bestandsnaam": f["filename"],
                "tijdstip": f["tijdstip"],
                "size": f["size"],
                "status": f["status"],
                "type": f["type"],
            }
            for f in files
        ]
        return jsonify(payload)
    except Exception:
        return jsonify([])


def _aggregate_by_day(days: int = 14):
    now = datetime.datetime.now()
    start = now - datetime.timedelta(days=days - 1)
    # Maak emmers per dag
    buckets: dict[str, dict[str, Any]] = {}
    for i in range(days):
        d = (start + datetime.timedelta(days=i)).date().isoformat()
        buckets[d] = {"datum": d, "totaal": 0, "geslaagd": 0, "gefaald": 0}
    for f in _scan_files():
        dt = datetime.datetime.fromtimestamp(f["mtime"]).date().isoformat()
        if dt in buckets:
            buckets[dt]["totaal"] += 1
            buckets[dt]["geslaagd"] += 1
    # Verrijk met succes_percentage en sorteer oplopend op datum
    out = []
    for d in sorted(buckets.keys()):
        row = buckets[d]
        total = row["totaal"]
        geslaagd = row["geslaagd"]
        if total > 0:
            sp = round(100.0 * (geslaagd / total), 2)
        else:
            sp = None
        row["succes_percentage"] = sp
        out.append(row)
    return out


@app.route("/api/xml/throughput")
def api_xml_throughput():
    try:
        days = int(request.args.get("days", 14))
    except Exception:
        days = 14
    try:
        return jsonify({"aggregated": _aggregate_by_day(days)})
    except Exception:
        return jsonify({"aggregated": []})


@app.route("/api/xml/latest-errors")
def api_xml_latest_errors():
    try:
        items = _read_error_log(max_items=20)
        return jsonify(items)
    except Exception:
        return jsonify([])


@app.route("/api/xml-stats")
def api_xml_stats():
    try:
        days = int(request.args.get("days", 14))
    except Exception:
        days = 14
    try:
        return jsonify({"aggregated": _aggregate_by_day(days)})
    except Exception:
        return jsonify({"aggregated": []})


if __name__ == "__main__":
    app.run(debug=False)
