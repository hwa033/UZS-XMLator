"""
Minimal Flask app using domain layer.
Business logic moved to web/domain.py, routes organized in web/routes/
"""

import datetime
import io
import json
import os
import sys
import uuid
from pathlib import Path

from flask import (
    Flask,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pydantic import ValidationError
from werkzeug.utils import secure_filename

from .domain import (
    Configuration,
    ExcelValidator,
    FileManager,
    FiledropRouter,
    GeneratedFile,
)
from .instellingen import instellingen_bp
from .models import ExcelRow, ExcelUploadRequest, JsonUploadRequest
from .utils import fill_xml_template

# ============================================================================
# FLASK APP SETUP
# ============================================================================

app = Flask(__name__)

# Optional CORS
cors_origins = os.environ.get("XMLATOR_CORS_ORIGINS")
if cors_origins:
    origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    if origins:
        CORS(app, resources={r"/api/*": {"origins": origins}})

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per minute"],
    storage_uri=os.environ.get("XMLATOR_LIMITER_STORAGE", "memory://"),
)

# ============================================================================
# CONFIGURATION & DEPENDENCY INJECTION
# ============================================================================

CONFIG_PATH = Path(__file__).parent / "instellingen.json"
CONFIG = Configuration.load_from_file(CONFIG_PATH)

ROUTER = FiledropRouter(CONFIG)
FILE_MANAGER = FileManager(ROUTER)

ALLOWED_EXTENSIONS = {"xlsx", "xls", "xlsm"}

# Security
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
SECRET_KEY = os.environ.get("U_XMLATOR_SECRET")

if FLASK_ENV.lower() != "development" and not SECRET_KEY:
    raise SystemExit(
        "ERROR: Set U_XMLATOR_SECRET environment variable (required outside development)."
    )

app.secret_key = SECRET_KEY or "change-this-to-a-long-secret-1234"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = FLASK_ENV.lower() != "development"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["MAX_CONTENT_LENGTH"] = (
    max(1, int(CONFIG.get("upload_max_size_mb", 10))) * 1024 * 1024
)

app.register_blueprint(instellingen_bp, url_prefix="/instellingen")

# ============================================================================
# ROUTES - PAGES
# ============================================================================


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/genereer_xml")
def genereer_xml():
    zip_limits = {"max_files": 50, "max_size_mb": 100}
    files, total_count = FILE_MANAGER.list_generated_files(limit=25, prune=True)
    generated = [
        {"filename": f.filename, "tijdstip": f.tijdstip, "size": f.size} for f in files
    ]
    return render_template(
        "genereer_xml.html",
        zip_limits=zip_limits,
        generated=generated,
        total_count=total_count,
    )


@app.route("/resultaten/fragment")
def resultaten_fragment():
    zip_limits = {"max_files": 50, "max_size_mb": 100}
    files, total_count = FILE_MANAGER.list_generated_files(limit=25, prune=True)
    generated = [
        {"filename": f.filename, "tijdstip": f.tijdstip, "size": f.size} for f in files
    ]
    return make_response(
        render_template(
            "_results_panel.html",
            zip_limits=zip_limits,
            generated=generated,
            total_count=total_count,
        )
    )


# ============================================================================
# ROUTES - FILE MANAGEMENT
# ============================================================================


@app.route("/resultaten/download/<filename>")
def download_generated(filename):
    """Download a generated XML file"""
    if not filename.endswith(".xml") or "/" in filename or ".." in filename:
        flash("Invalid filename.", "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    directories = [
        ROUTER.get_output_directory("ZBM"),
        ROUTER.get_output_directory("Digipoort"),
        ROUTER.get_output_directory(),
    ]

    for output_dir in directories:
        if output_dir.exists():
            file_path = output_dir / filename
            if file_path.exists():
                from flask import send_file

                response = send_file(
                    file_path,
                    as_attachment=True,
                    download_name=filename,
                    mimetype="application/xml",
                )
                response.headers["X-Content-Type-Options"] = "nosniff"
                return response

    flash("File not found.", "danger")
    return redirect(request.referrer or url_for("genereer_xml"))


@app.route("/resultaten/delete-selected", methods=["POST"])
def delete_selected_files():
    """Delete selected files"""
    try:
        data = request.get_json(silent=True) or {}
        filenames = data.get("filenames") or []

        if not isinstance(filenames, list) or not filenames:
            return jsonify({"error": "No files selected"}), 400

        deleted, missing = FILE_MANAGER.delete_files(filenames)
        return jsonify({"success": True, "deleted": deleted, "missing": missing})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/resultaten/download-zip", methods=["POST"])
def download_generated_zip():
    """Download selected files as ZIP"""
    try:
        import zipfile

        data = request.get_json(silent=True) or {}
        filenames = data.get("filenames") or []

        if not isinstance(filenames, list) or not filenames:
            return jsonify({"error": "No files selected"}), 400

        # Build file map
        directories = [
            ROUTER.get_output_directory("ZBM"),
            ROUTER.get_output_directory("Digipoort"),
            ROUTER.get_output_directory(),
        ]
        unique_dirs = list(dict.fromkeys(directories))

        file_map = {}
        for out_dir in unique_dirs:
            if out_dir.exists():
                for fname in out_dir.iterdir():
                    if fname.suffix == ".xml" and fname.is_file():
                        file_map[fname.name] = fname

        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fn in filenames:
                if fn in file_map:
                    fpath = file_map[fn]
                    zf.write(fpath, arcname=fn)

        zip_buffer.seek(0)
        from flask import send_file

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="results.zip",
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================================
# ROUTES - UPLOAD ENDPOINTS
# ============================================================================


def _format_pydantic_errors(errors: list[dict]) -> list[str]:
    formatted = []
    for err in errors:
        loc = err.get("loc")
        if isinstance(loc, (list, tuple)):
            loc_str = ".".join(str(p) for p in loc)
        elif loc:
            loc_str = str(loc)
        else:
            loc_str = "field"
        msg = err.get("msg", "Invalid input")
        formatted.append(f"{loc_str}: {msg}" if loc_str else msg)
    return formatted


@app.route("/genereer_xml_json/upload_json", methods=["POST"])
@limiter.limit("20 per minute")
def upload_json():
    """Upload JSON and generate XML"""
    file = request.files.get("json_file")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not file:
        msg = "No JSON file uploaded."
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    try:
        payload = json.load(io.TextIOWrapper(file.stream, encoding="utf-8"))
    except Exception as exc:
        msg = f"Invalid JSON: {exc}"
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    if not isinstance(payload, dict):
        msg = "JSON payload must be an object."
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    try:
        req_model = JsonUploadRequest(
            aanvraag_type=request.form.get("aanvraag_type", "ZBM"),
            validate=str(request.form.get("validate", "on")).lower() != "off",
            BSN=payload.get("BSN"),
            Geboortedatum=payload.get("Geboortedatum") or payload.get("geboortedatum"),
        )
    except ValidationError as exc:
        formatted = _format_pydantic_errors(exc.errors())
        msg = f"Invalid request: {'; '.join(formatted)}"
        if is_ajax:
            return jsonify({"success": False, "error": msg, "errors": formatted}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    aanvraag_type = req_model.aanvraag_type
    cd_bericht = ExcelValidator.normalize_berichttype(aanvraag_type)

    payload.setdefault("CdBerichtType", cd_bericht)
    payload.setdefault("BronApplicatie", cd_bericht)

    # Validate required fields
    bsn_value = req_model.BSN
    geb_value = req_model.Geboortedatum
    if bsn_value is not None:
        payload["BSN"] = bsn_value
    if geb_value is not None:
        payload["Geboortedatum"] = geb_value

    if not bsn_value or str(bsn_value).strip() == "":
        msg = "Missing BSN in JSON payload."
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    if not geb_value or str(geb_value).strip() == "":
        msg = "Missing Geboortedatum in JSON payload."
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    unique_suffix = uuid.uuid4().hex[:8]
    try:
        tree = fill_xml_template(None, payload, unique_suffix)
    except Exception as exc:
        msg = f"Error building XML: {exc}"
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    # Validation
    if req_model.validate_request:
        try:
            from lxml import etree  # type: ignore[import-not-found]

            xsd_path = CONFIG.get(
                "xsd_path", "docs/UwvZwMeldingInternBody-v0428-b01.xsd"
            )
            xsd_full = Path(__file__).parent.parent / xsd_path
            if xsd_full.exists():
                schema = etree.XMLSchema(file=str(xsd_full))  # type: ignore
                ns_body = (
                    "http://schemas.uwv.nl/UwvML/Berichten/UwvZwMeldingInternBody-v0428"
                )
                uwb = tree.getroot().find(f".//{{{ns_body}}}UwvZwMeldingInternBody")
                if uwb is None:
                    raise ValueError("UwvZwMeldingInternBody missing from XML.")
                if not schema.validate(uwb):
                    errs = "; ".join(str(e.message) for e in schema.error_log)
                    raise ValueError(f"XSD validation failed: {errs}")
        except Exception as exc:
            msg = f"Validation error: {exc}"
            if is_ajax:
                return jsonify({"success": False, "error": msg}), 400
            flash(msg, "danger")
            return redirect(request.referrer or url_for("genereer_xml"))

    # Save file
    output_dir = ROUTER.get_output_directory(aanvraag_type)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_bsn = "".join(ch for ch in str(bsn_value) if ch.isalnum()) or "row"
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = "digipoort" if cd_bericht == "OTP3" else cd_bericht.lower()
    filename = f"{prefix}_{safe_bsn}_{ts}.xml"
    file_path = output_dir / filename

    try:
        tree.write(str(file_path), encoding="utf-8", xml_declaration=True)
    except Exception as exc:
        msg = f"Error saving XML: {exc}"
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 500
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    msg = f"JSON processed successfully. {aanvraag_type} XML generated."
    if is_ajax:
        return (
            jsonify({"success": True, "message": msg, "filename": filename}),
            200,
        )
    flash(msg, "success")
    return redirect(url_for("genereer_xml"))


@app.route("/upload_excel", methods=["POST"])
@limiter.limit("20 per minute")
def upload_excel():
    """Upload Excel and generate XML"""
    import subprocess

    file = request.files.get("excel_file")
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if not file:
        msg = "Geen bestand geüpload."
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    _, ext = os.path.splitext(file.filename or "")
    if ext.lower() not in [f".{e}" for e in ALLOWED_EXTENSIONS]:
        msg = "Ongeldig bestandstype; alleen .xlsx en .xls zijn toegestaan."
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    try:
        req_model = ExcelUploadRequest(
            aanvraag_type=request.form.get("aanvraag_type", "ZBM"),
            validate=str(request.form.get("validate", "on")).lower() != "off",
        )
    except ValidationError as exc:
        formatted = _format_pydantic_errors(exc.errors())
        msg = f"Invalid request: {'; '.join(formatted)}"
        if is_ajax:
            return jsonify({"success": False, "error": msg, "errors": formatted}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    cfg = Configuration.load_from_file(CONFIG_PATH)
    use_excel_com = bool(cfg.get("excel_com_enabled")) or (
        os.environ.get("XMLATOR_USE_EXCEL_COM", "").lower() in {"1", "true", "yes", "on"}
    )
    app.config["MAX_CONTENT_LENGTH"] = (
        max(1, int(cfg.get("upload_max_size_mb", 10))) * 1024 * 1024
    )

    if (
        request.content_length
        and request.content_length > app.config["MAX_CONTENT_LENGTH"]
    ):
        msg = (
            f"Bestand te groot (max "
            f'{app.config["MAX_CONTENT_LENGTH"] // (1024*1024)} MB).'
        )
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    uploads_dir = Path(__file__).parent.parent / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    orig_filename = file.filename if file.filename else "upload.xlsx"
    filename = secure_filename(orig_filename)
    file_path = uploads_dir / filename
    file.save(str(file_path))

    def _cell_to_str(value):
        if value is None:
            return ""
        if isinstance(value, datetime.datetime):
            return value.strftime("%Y%m%d")
        if isinstance(value, datetime.date):
            return value.strftime("%Y%m%d")
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, int):
            return str(value)
        return str(value).strip()

    if req_model.validate_request:
        try:
            import openpyxl

            wb_val = openpyxl.load_workbook(str(file_path), data_only=True)
            ws_val = wb_val.active
            if ws_val is None:
                raise ValueError("Het geüploade Excel-bestand bevat geen werkblad.")

            header_row = next(ws_val.iter_rows(min_row=1, max_row=1))
            headers = [_cell_to_str(cell.value) for cell in header_row]
            if not any(headers):
                raise ValueError("Excel-bestand bevat geen kolomkoppen.")

            errors = []
            has_full_name = "Voornaam" in headers and "Achternaam" in headers
            for idx, row in enumerate(ws_val.iter_rows(min_row=2, values_only=True), start=2):
                row_values = [_cell_to_str(v) for v in row]
                if not any(row_values):
                    continue
                row_dict = {
                    headers[i]: row_values[i]
                    for i in range(min(len(headers), len(row_values)))
                    if headers[i]
                }
                try:
                    if has_full_name:
                        ExcelRow(**row_dict)
                    else:
                        JsonUploadRequest(
                            aanvraag_type=req_model.aanvraag_type,
                            BSN=row_dict.get("BSN"),
                            Geboortedatum=row_dict.get("Geboortedatum"),
                        )
                except ValidationError as exc:
                    formatted = _format_pydantic_errors(exc.errors())
                    details = "; ".join(formatted)
                    errors.append(f"Row {idx}: {details}")

            if errors:
                error_msg = "Validatie mislukt: " + "; ".join(errors[:5])
                if len(errors) > 5:
                    error_msg += f" (en {len(errors) - 5} meer)"
                if is_ajax:
                    return jsonify(
                        {"success": False, "error": error_msg, "errors": errors},
                    ), 400
                flash(error_msg, "danger")
                return redirect(request.referrer or url_for("genereer_xml"))
        except Exception as exc:
            msg = f"Fout bij valideren van Excel: {exc}"
            if is_ajax:
                return jsonify({"success": False, "error": msg}), 400
            flash(msg, "danger")
            return redirect(request.referrer or url_for("genereer_xml"))

    aanvraag_type = req_model.aanvraag_type
    cd_override = ExcelValidator.normalize_berichttype(aanvraag_type)

    try:
        if use_excel_com:
            try:
                import win32com.client  # type: ignore
            except Exception:
                msg = (
                    "Excel COM niet beschikbaar. Installeer pywin32 en zorg dat "
                    "Microsoft Excel is geïnstalleerd."
                )
                if is_ajax:
                    return jsonify({"success": False, "error": msg}), 400
                flash(msg, "danger")
                return redirect(request.referrer or url_for("genereer_xml"))

            excel = None
            wb = None
            try:
                excel = win32com.client.DispatchEx("Excel.Application")
                excel.Visible = False
                excel.DisplayAlerts = False
                wb = excel.Workbooks.Open(str(file_path), ReadOnly=True)
                if wb.Worksheets.Count < 1:
                    raise ValueError(
                        "Het geüploade Excel-bestand bevat geen werkblad of is ongeldig."
                    )
            finally:
                try:
                    if wb is not None:
                        wb.Close(False)
                except Exception:
                    pass
                try:
                    if excel is not None:
                        excel.Quit()
                except Exception:
                    pass
        else:
            import openpyxl

            wb = openpyxl.load_workbook(str(file_path))
            ws = wb.active
            if ws is None:
                msg = "Het geüploade Excel-bestand bevat geen werkblad of is ongeldig."
                if is_ajax:
                    return jsonify({"success": False, "error": msg}), 400
                flash(msg, "danger")
                return redirect(request.referrer or url_for("genereer_xml"))

        patched_excel_path = str(file_path)
    except Exception as exc:
        msg = f"Fout bij verwerken van het Excel-bestand: {exc}"
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    generator_path = Path(__file__).parent.parent / "tools" / "generate_from_excel.py"
    output_dir = ROUTER.get_output_directory(aanvraag_type)
    output_dir.mkdir(parents=True, exist_ok=True)
    existing_files = set()
    if output_dir.exists():
        try:
            existing_files = {f.name for f in output_dir.glob("*.xml")}
        except Exception:
            pass

    python_exe = os.environ.get("PYTHON_EXE", sys.executable)
    log_path = Path(__file__).parent.parent / "build" / "logs" / "generator_excel.log"

    use_internal_generator = (
        getattr(sys, "frozen", False)
        or os.path.basename(str(sys.executable)).lower() == "xmlator.exe"
        or os.path.basename(str(python_exe)).lower() == "xmlator.exe"
        or not generator_path.exists()
    )

    try:
        if use_excel_com:
            os.environ["XMLATOR_USE_EXCEL_COM"] = "1"

        if use_internal_generator:
            from tools import generate_from_excel as gen

            gen.generate_from_excel_file(
                patched_excel_path,
                str(output_dir),
                mode="single",
                log_path=str(log_path),
                data_only=True,
                cd_bericht_override=cd_override,
            )
        else:
            env = os.environ.copy()
            if use_excel_com:
                env["XMLATOR_USE_EXCEL_COM"] = "1"
            subprocess.run(
                [
                    python_exe,
                    str(generator_path),
                    "--input",
                    patched_excel_path,
                    "--outdir",
                    str(output_dir),
                    "--mode",
                    "single",
                    "--data-only",
                    "--cd-bericht",
                    cd_override,
                ],
                capture_output=True,
                text=True,
                check=True,
                env=env,
            )

        msg = (
            f"Excel-bestand succesvol geüpload en {aanvraag_type} "
            f"XML-bestanden gegenereerd."
        )

        generated_files = []
        if output_dir.exists():
            try:
                current_files = {f.name for f in output_dir.glob("*.xml")}
                new_files = sorted(
                    [f for f in current_files if f not in existing_files],
                    key=lambda f: (output_dir / f).stat().st_mtime,
                    reverse=True,
                )
                generated_files = new_files
            except Exception:
                pass

        if not generated_files:
            error_msg = "Geen XML-bestanden gegenereerd. Controleer of alle verplichte velden aanwezig zijn (BSN, Geboortedatum)."
            if is_ajax:
                return jsonify({"success": False, "error": error_msg}), 400
            flash(error_msg, "danger")
            return redirect(request.referrer or url_for("genereer_xml"))

        if is_ajax:
            response_data = {
                "success": True,
                "message": msg,
                "download_links": [
                    {"filename": fname, "url": f"/resultaten/download/{fname}"}
                    for fname in generated_files
                ],
            }
            response_data["message"] += f" {len(generated_files)} bestand(en) beschikbaar voor download."
            return jsonify(response_data), 200

        flash(msg, "success")

    except subprocess.CalledProcessError as e:
        msg = f"Fout bij genereren van XML: {e.stderr or e.stdout}"
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")

    except Exception as e:
        msg = f"Fout bij genereren van XML: {e}"
        if is_ajax:
            return jsonify({"success": False, "error": msg}), 400
        flash(msg, "danger")

    finally:
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass

    return redirect(url_for("genereer_xml"))


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================


@app.route("/health")
@limiter.exempt
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/ready")
@limiter.exempt
def ready():
    status = {"status": "ready"}
    try:
        output_dir = ROUTER.get_output_directory(quiet=True)
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        status["status"] = "not_ready"

    return jsonify(status), 200 if status["status"] == "ready" else 503


@app.route("/favicon.ico")
def favicon():
    return "", 204


# ============================================================================
# BACKWARDS COMPATIBILITY - Legacy function exports
# ============================================================================


def get_output_directory(aanvraag_type=None, omgeving=None):
    """Legacy compatibility wrapper - use ROUTER instead"""
    return ROUTER.get_output_directory(aanvraag_type, omgeving)


def list_generated_files(limit=25, prune=False):
    """Legacy compatibility wrapper - use FILE_MANAGER instead"""
    files, total = FILE_MANAGER.list_generated_files(limit, prune)
    return (
        [{"filename": f.filename, "tijdstip": f.tijdstip, "size": f.size} for f in files],
        total,
    )


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
