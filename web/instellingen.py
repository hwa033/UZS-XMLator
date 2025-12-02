import json
import os

from flask import Blueprint, flash, redirect, render_template, request, url_for

instellingen_bp = Blueprint("instellingen", __name__, template_folder="templates")

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "instellingen.json")


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
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

    if request.method == "POST":
        # Update instellingen
        settings["upload_max_size_mb"] = int(request.form.get("upload_max_size_mb", 16))
        settings["xsd_path"] = request.form.get("xsd_path", settings.get("xsd_path", ""))
        settings["log_level"] = request.form.get("log_level", settings.get("log_level", "INFO"))
        settings["output_directory"] = request.form.get("output_directory", settings.get("output_directory", ""))
        settings["auto_validate"] = request.form.get("auto_validate") == "on"
        settings["default_test_indicator"] = request.form.get("default_test_indicator", settings.get("default_test_indicator", "2"))
        settings["default_fiscaal_nr"] = request.form.get("default_fiscaal_nr", settings.get("default_fiscaal_nr", ""))
        settings["default_loonheffing_nr"] = request.form.get("default_loonheffing_nr", settings.get("default_loonheffing_nr", ""))
        settings["file_retention_days"] = int(request.form.get("file_retention_days", settings.get("file_retention_days", 30)))
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        flash("Instellingen opgeslagen", "success")
        return redirect(url_for("instellingen.configuratie"))

    return render_template("configuratie.html", settings=settings)
