import json
import os
from pathlib import Path
import yaml

from flask import Blueprint, flash, redirect, render_template, request, url_for, send_file
from werkzeug.utils import secure_filename

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


@instellingen_bp.route("/datasets", methods=["GET", "POST"])
def datasets():
    """Manage Excel datasets"""
    yaml_path = Path(__file__).parent.parent / "docs" / "excel_datasets.yml"
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "upload":
            if "excel_file" not in request.files:
                flash("Geen bestand geselecteerd", "danger")
                return redirect(url_for("instellingen.datasets"))
            
            file = request.files["excel_file"]
            if file.filename == "":
                flash("Geen bestand geselecteerd", "danger")
                return redirect(url_for("instellingen.datasets"))
            
            # Save uploaded Excel file to docs folder
            filename = secure_filename(file.filename)
            dest_path = Path(__file__).parent.parent / "docs" / filename
            file.save(str(dest_path))
            flash(f"Dataset '{filename}' succesvol geüpload naar docs/", "success")
            return redirect(url_for("instellingen.datasets"))
        
        elif action == "delete":
            filename = request.form.get("filename")
            if filename:
                file_path = Path(__file__).parent.parent / "docs" / secure_filename(filename)
                if file_path.exists() and file_path.suffix in [".xlsx", ".xls"]:
                    file_path.unlink()
                    flash(f"Dataset '{filename}' verwijderd", "success")
                else:
                    flash("Bestand niet gevonden", "danger")
            return redirect(url_for("instellingen.datasets"))
    
    # List all Excel files in docs folder
    docs_path = Path(__file__).parent.parent / "docs"
    excel_files = []
    if docs_path.exists():
        import datetime
        for f in docs_path.glob("*.xlsx"):
            mtime = f.stat().st_mtime
            excel_files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": mtime,
                "modified_str": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        for f in docs_path.glob("*.xls"):
            mtime = f.stat().st_mtime
            excel_files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "modified": mtime,
                "modified_str": datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
    
    excel_files.sort(key=lambda x: x["modified"], reverse=True)
    
    return render_template("datasets.html", excel_files=excel_files)


@instellingen_bp.route("/historie")
def historie():
    """View XML generation history from events log"""
    events_file = Path(__file__).parent / "xml_events.jsonl"
    events = []
    
    if events_file.exists():
        try:
            with open(events_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        events.append(event)
                    except:
                        continue
        except:
            pass
    
    # Reverse to show newest first
    events.reverse()
    
    # Limit to last 200 events
    events = events[:200]
    
    return render_template("historie.html", events=events)


@instellingen_bp.route("/documentatie")
def documentatie():
    """Show user documentation and help"""
    # Check which documentation files exist
    docs_path = Path(__file__).parent.parent / "docs"
    available_docs = []
    
    doc_files = [
        ("Gebruikershandleiding XML Automatisering Web Dashboard.md", "Gebruikershandleiding"),
        ("digitale_aanvragen_uzs.md", "Digitale Aanvragen UZS"),
        ("LOCAL_CHART_FALLBACK.md", "Chart.js Fallback"),
    ]
    
    for filename, title in doc_files:
        doc_path = docs_path / filename
        if doc_path.exists():
            available_docs.append({
                "filename": filename,
                "title": title,
                "size": doc_path.stat().st_size
            })
    
    return render_template("documentatie.html", available_docs=available_docs)
