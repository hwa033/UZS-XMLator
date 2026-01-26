import json
import os
from pathlib import Path

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

instellingen_bp = Blueprint("instellingen", __name__, template_folder="templates")

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "instellingen.json")


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
                    lines = [l.rstrip("\n") for l in lines]
            except Exception:
                lines = ["[Fout bij lezen van logbestand]"]
        logs.append({"title": title, "lines": lines})
    return render_template("logs.html", logs=logs)


@instellingen_bp.route("/")
def dashboard():
    """Main dashboard showing admin panel with all management options"""
    return render_template("instellingen.html")


@instellingen_bp.route("/configuratie", methods=["GET", "POST"])
def configuratie():
    """System configuration settings"""
    # Laad huidige instellingen
    if not os.path.exists(SETTINGS_FILE):
        settings = {
            "upload_max_size_mb": 16,
            "xsd_path": "docs/UwvZwMeldingInternBody-v0428-b01.xsd",
            "log_level": "INFO",
            "output_directory": "uzs_filedrop/UZI-GAP3/UZSx_ACC1/v0428",
            "auto_validate": True,
            "default_test_indicator": "2",
            "default_fiscaal_nr": "136910038",
            "default_loonheffing_nr": "136910038L01",
            "file_retention_days": 30,
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

        upload_max_size_mb, err = _as_int("upload_max_size_mb", settings.get("upload_max_size_mb", 16))
        if err:
            errors.append(err)

        file_retention_days, err = _as_int("file_retention_days", settings.get("file_retention_days", 30))
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
        # Optional: update filedrop paths for selected environment
        fp_otp3 = request.form.get("otp3_path", "").strip()
        fp_zbm = request.form.get("zbm_path", "").strip()
        fp_vm = request.form.get("vm_path", "").strip()

        # Valideer paden (waarschuwing als niet bereikbaar, maar niet blokkeren)
        for label, path in [("OTP3", fp_otp3), ("ZBM", fp_zbm), ("VM", fp_vm)]:
            if path:
                drive, _ = os.path.splitdrive(path)
                if drive and not os.path.exists(drive + os.path.sep):
                    flash(f"Waarschuwing: Drive {drive} voor {label} niet beschikbaar; pad wordt wel opgeslagen.", "warning")
                elif not os.path.exists(path):
                    flash(f"Info: Pad voor {label} bestaat nog niet maar wordt opgeslagen (kan later worden aangemaakt).", "info")

        if settings.get("filedrop_locaties") is None or not isinstance(settings.get("filedrop_locaties"), dict):
            settings["filedrop_locaties"] = {}
        env_map = settings["filedrop_locaties"].get(settings["omgeving"], {})
        if fp_otp3:
            env_map["OTP3"] = fp_otp3
        if fp_zbm:
            env_map["ZBM"] = fp_zbm
        if fp_vm:
            env_map["VM"] = fp_vm
        settings["filedrop_locaties"][settings["omgeving"]] = env_map

        if errors:
            for e in errors:
                flash(e, "danger")
            # Prepare current env paths for template
            env_paths = settings.get("filedrop_locaties", {}).get(settings.get("omgeving", "UZSTA_OMG"), {})
            return render_template("configuratie.html", settings=settings, env_options=env_options, env_paths=env_paths)

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        flash("Instellingen opgeslagen", "success")
        return redirect(url_for("instellingen.configuratie"))

    env_paths = settings.get("filedrop_locaties", {}).get(settings.get("omgeving", "UZSTA_OMG"), {})
    return render_template("configuratie.html", settings=settings, env_options=env_options, env_paths=env_paths)





@instellingen_bp.route("/documentatie")
def documentatie():
    """Show user documentation and help"""
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
