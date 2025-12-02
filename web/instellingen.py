import json
import os
from functools import wraps

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

instellingen_bp = Blueprint("instellingen", __name__, template_folder="templates")

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "instellingen.json")

# Decorator voor beheer login


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("beheer_ingelogd"):
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


@instellingen_bp.route("/")
@login_required
def dashboard():
    """Main dashboard showing admin panel with all management options"""
    return render_template("instellingen.html")


@instellingen_bp.route("/configuratie", methods=["GET", "POST"])
@login_required
def configuratie():
    """System configuration settings"""
    # Laad huidige instellingen
    if not os.path.exists(SETTINGS_FILE):
        settings = {
            "upload_max_size_mb": 16,
            "xsd_path": "docs/UwvZwMeldingInternBody-v0428-b01.xsd",
            "log_level": "INFO",
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    else:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = json.load(f)

    if request.method == "POST":
        # Update instellingen
        settings["upload_max_size_mb"] = int(request.form.get("upload_max_size_mb", 16))
        settings["xsd_path"] = request.form.get("xsd_path", settings["xsd_path"])
        settings["log_level"] = request.form.get("log_level", settings["log_level"])
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
        flash("Instellingen opgeslagen", "success")
        return redirect(url_for("instellingen.configuratie"))

    return render_template("configuratie.html", settings=settings)
