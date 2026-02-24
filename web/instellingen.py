import json
import os
from pathlib import Path

from flask import (
    Blueprint,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

instellingen_bp = Blueprint("instellingen", __name__, template_folder="templates")

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "instellingen.json")
FLASK_ENV = os.environ.get("FLASK_ENV", "development")


def _admin_token() -> str | None:
    return os.environ.get("U_XMLATOR_ADMIN_TOKEN") or os.environ.get("U_XMLATOR_SECRET")


def _extract_request_token() -> str | None:
    header_token = request.headers.get("X-Admin-Token")
    if header_token:
        return header_token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "", 1).strip()
    return request.args.get("admin_token")


@instellingen_bp.before_request
def _protect_instellingen():
    # Allow API endpoints (JSON) with minimal protection
    if request.endpoint and request.endpoint.startswith("instellingen.add_omgeving"):
        if session.get("beheer_ingelogd"):
            return None
        if FLASK_ENV.lower() == "development":
            return None
        return jsonify({"error": "Unauthorized"}), 401

    if request.endpoint and request.endpoint.startswith("instellingen.delete_omgeving"):
        if session.get("beheer_ingelogd"):
            return None
        if FLASK_ENV.lower() == "development":
            return None
        return jsonify({"error": "Unauthorized"}), 401

    # Standard protection for other routes
    if session.get("beheer_ingelogd"):
        return None
    if FLASK_ENV.lower() == "development":
        return None
    configured = _admin_token()
    if not configured:
        return Response("Admin token niet ingesteld", status=503)
    provided = _extract_request_token()
    if not provided or provided != configured:
        return Response("Admin token vereist", status=401)
    return None


def _load_config():
    """Load settings from JSON file."""
    if not os.path.exists(SETTINGS_FILE):
        return {
            "upload_max_size_mb": 16,
            "xsd_path": "docs/UwvZwMeldingInternBody-v0428-b01.xsd",
            "log_level": "INFO",
            "output_directory": "",
            "auto_validate": True,
            "excel_com_enabled": False,
            "default_test_indicator": "2",
            "default_fiscaal_nr": "136910038",
            "default_loonheffing_nr": "136910038L01",
            "file_retention_days": 30,
            "filedrop_locaties": {},
        }
    with open(SETTINGS_FILE, encoding="utf-8") as f:
        return json.load(f)


@instellingen_bp.route("/logs")
def logs():
    """Bekijk recente logbestanden (alleen voor admins)."""
    # Locaties van logbestanden
    log_dir = Path(__file__).parent.parent / "build" / "logs"
    log_files = [
        (log_dir / "generator_excel.log", "Generator Excel Log"),
        (log_dir / "generator_json.log", "Generator JSON Log"),
        (log_dir / "user_uploads_json.log", "User Uploads JSON Log"),
    ]
    logs = []
    for path, title in log_files:
        lines = []
        if path.exists():
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    # Laatste 100 regels, zonder alles in geheugen te laden
                    from collections import deque

                    lines = list(deque(f, 100))
                    lines = [line.rstrip("\n") for line in lines]
            except Exception:
                lines = ["[Fout bij lezen van logbestand]"]
        logs.append({"title": title, "lines": lines})
    return render_template("logs.html", logs=logs)


@instellingen_bp.route("/")
def dashboard():
    """Dashboard voor beheer: alle instellingen-opties."""
    return render_template("instellingen.html")


@instellingen_bp.route("/configuratie", methods=["GET", "POST"])
def configuratie():
    """Systeemconfiguratie aanpassen."""
    # Laad huidige instellingen
    if not os.path.exists(SETTINGS_FILE):
        settings = {
            "upload_max_size_mb": 16,
            "xsd_path": "docs/UwvZwMeldingInternBody-v0428-b01.xsd",
            "log_level": "INFO",
            "output_directory": "",
            "auto_validate": True,
            "excel_com_enabled": False,
            "default_test_indicator": "2",
            "default_fiscaal_nr": "136910038",
            "default_loonheffing_nr": "136910038L01",
            "file_retention_days": 30,
            "filedrop_locaties": {},
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    else:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            settings = json.load(f)

    # Options for environments
    env_options = [
        "UZSA_ACC1",
        "UZSC_ACC1",
        "UZSD_ACC1",
        "UZSP_ACC1",
        "UZSTA_OMG",
    ]

    if request.method == "POST":
        form_type = request.form.get("form_type", "config")
        errors = []

        def _as_int(field, default, min_value=1):
            raw = request.form.get(field, "").strip()
            if not raw:
                return default, f"{field} mag niet leeg zijn"
            try:
                val = int(raw)
                if val < min_value:
                    return default, f"{field} moet >= {min_value}"
                return val, None
            except ValueError:
                return default, f"{field} moet een getal zijn"

        # Alleen valideren als het de configuratie form is
        if form_type == "config":
            upload_max_size_mb, err = _as_int(
                "upload_max_size_mb", settings.get("upload_max_size_mb", 16)
            )
            if err:
                errors.append(err)

            file_retention_days, err = _as_int(
                "file_retention_days", settings.get("file_retention_days", 30)
            )
            if err:
                errors.append(err)

            settings["upload_max_size_mb"] = upload_max_size_mb
            settings["file_retention_days"] = file_retention_days
            settings["omgeving"] = request.form.get(
                "omgeving", settings.get("omgeving", "UZSTA_OMG")
            )
            settings["xsd_path"] = request.form.get(
                "xsd_path", settings.get("xsd_path", "")
            ).strip()
            settings["excel_com_enabled"] = (
                request.form.get("excel_com_enabled") == "on"
            )

        # Filedrop paden
        fp_otp3 = request.form.get("otp3_path", "").strip()
        fp_zbm = request.form.get("zbm_path", "").strip()
        fp_vm = request.form.get("vm_path", "").strip()

        # Alleen filedrop paden opslaan als form_type="filedrop" of als er paden zijn gegeven
        if form_type == "filedrop" or (fp_otp3 or fp_zbm or fp_vm):
            # Valideer paden (waarschuwing als niet bereikbaar, maar niet blokkeren)
            for label, path in [("OTP3", fp_otp3), ("ZBM", fp_zbm), ("VM", fp_vm)]:
                if not path:
                    continue
                drive, _ = os.path.splitdrive(path)
                if drive and not os.path.exists(drive + os.path.sep):
                    flash(
                        f"Waarschuwing: Drive {drive} voor {label} niet beschikbaar; "
                        f"pad wordt wel opgeslagen.",
                        "warning",
                    )
                    continue
                try:
                    os.makedirs(path, exist_ok=True)
                except Exception as exc:
                    flash(
                        f"Waarschuwing: pad voor {label} niet bereikbaar (rechten?): {exc}",
                        "warning",
                    )
                else:
                    if not os.path.exists(path):
                        flash(
                            f"Info: Pad voor {label} bestaat nog niet maar wordt opgeslagen"
                            f" (kan later worden aangemaakt).",
                            "info",
                        )

            if settings.get("filedrop_locaties") is None or not isinstance(
                settings.get("filedrop_locaties"), dict
            ):
                settings["filedrop_locaties"] = {}
            env_map = settings["filedrop_locaties"].get(settings["omgeving"], {})
            if fp_otp3:
                env_map["OTP3"] = fp_otp3
            else:
                env_map.pop("OTP3", None)
            if fp_zbm:
                env_map["ZBM"] = fp_zbm
            else:
                env_map.pop("ZBM", None)
            if fp_vm:
                env_map["VM"] = fp_vm
            else:
                env_map.pop("VM", None)
            settings["filedrop_locaties"][settings["omgeving"]] = env_map

        if errors:
            for e in errors:
                flash(e, "danger")
            # Prepare current env paths for template
            env_paths = settings.get("filedrop_locaties", {}).get(
                settings.get("omgeving", "UZSTA_OMG"), {}
            )
            return render_template(
                "configuratie.html",
                settings=settings,
                env_options=env_options,
                env_paths=env_paths,
            )

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        flash("Instellingen opgeslagen", "success")
        return redirect(url_for("instellingen.configuratie"))

    env_paths = settings.get("filedrop_locaties", {}).get(
        settings.get("omgeving", "UZSTA_OMG"), {}
    )
    return render_template(
        "configuratie.html",
        settings=settings,
        env_options=env_options,
        env_paths=env_paths,
    )


@instellingen_bp.route("/documentatie")
def documentatie():
    """Toon gebruikersdocumentatie en help."""
    # Check which documentation files exist
    docs_path = Path(__file__).parent.parent / "docs"
    available_docs = []

    doc_files = [
        (
            "Gebruikershandleiding XML Automatisering Web Dashboard.md",
            "Gebruikershandleiding",
        ),
        ("digitale_aanvragen_uzs.md", "Digitale Aanvragen UZS"),
        ("LOCAL_CHART_FALLBACK.md", "Chart.js Fallback"),
    ]

    for filename, title in doc_files:
        doc_path = docs_path / filename
        if doc_path.exists():
            available_docs.append(
                {"filename": filename, "title": title, "size": doc_path.stat().st_size}
            )

    return render_template("documentatie.html", available_docs=available_docs)


@instellingen_bp.route("/add_omgeving", methods=["POST"])
def add_omgeving():
    """Voeg nieuwe omgeving toe."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Geen JSON data ontvangen"}), 400

        omg = data.get("omgeving", "").strip().upper()

        if not omg or not all(c.isalnum() or c == "_" for c in omg):
            return jsonify({"success": False, "error": "Ongeldige omgevingnaam"}), 400

        settings = _load_config()
        if settings.get("filedrop_locaties") is None:
            settings["filedrop_locaties"] = {}

        if omg in settings["filedrop_locaties"]:
            return jsonify({"success": False, "error": "Omgeving bestaat al"}), 400

        # Voeg lege omgeving toe
        settings["filedrop_locaties"][omg] = {}

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

        return jsonify({"success": True, "omgeving": omg}), 200
    except Exception as e:
        import traceback

        print(f"Error in add_omgeving: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@instellingen_bp.route("/delete_omgeving", methods=["POST"])
def delete_omgeving():
    """Verwijder omgeving."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Geen JSON data ontvangen"}), 400

        omg = data.get("omgeving", "").strip()

        settings = _load_config()
        if omg not in settings.get("filedrop_locaties", {}):
            return jsonify({"success": False, "error": "Omgeving niet gevonden"}), 400

        # Prevent deleting current environment
        if omg == settings.get("omgeving"):
            return (
                jsonify(
                    {"success": False, "error": "Kan huidige omgeving niet verwijderen"}
                ),
                400,
            )

        del settings["filedrop_locaties"][omg]

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

        return jsonify({"success": True}), 200
    except Exception as e:
        import traceback

        print(f"Error in delete_omgeving: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
