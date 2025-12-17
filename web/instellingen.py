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
from werkzeug.utils import secure_filename


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

    if request.method == "POST":
        # Update instellingen
        settings["upload_max_size_mb"] = int(request.form.get("upload_max_size_mb", 16))
        settings["xsd_path"] = request.form.get(
            "xsd_path", settings.get("xsd_path", "")
        )
        settings["log_level"] = request.form.get(
            "log_level", settings.get("log_level", "INFO")
        )
        settings["output_directory"] = request.form.get(
            "output_directory", settings.get("output_directory", "")
        )
        settings["auto_validate"] = request.form.get("auto_validate") == "on"
        settings["default_test_indicator"] = request.form.get(
            "default_test_indicator", settings.get("default_test_indicator", "2")
        )
        settings["default_fiscaal_nr"] = request.form.get(
            "default_fiscaal_nr", settings.get("default_fiscaal_nr", "")
        )
        settings["default_loonheffing_nr"] = request.form.get(
            "default_loonheffing_nr", settings.get("default_loonheffing_nr", "")
        )
        settings["file_retention_days"] = int(
            request.form.get(
                "file_retention_days", settings.get("file_retention_days", 30)
            )
        )
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        flash("Instellingen opgeslagen", "success")
        return redirect(url_for("instellingen.configuratie"))

    return render_template("configuratie.html", settings=settings)





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
