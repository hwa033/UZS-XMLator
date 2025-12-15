
# --- Imports (must be at the very top) ---
import os
import datetime
from flask import Flask, jsonify, render_template, request, send_from_directory, redirect, flash, url_for
from markupsafe import escape
from werkzeug.utils import secure_filename

# --- Flask app instance (must be at top level) ---
app = Flask(__name__)
app.secret_key = 'change-this-to-a-very-secret-key-1234'

# --- Download generated XML file endpoint ---
@app.route('/resultaten/download/<filename>')
def download_generated(filename):
    # Only allow .xml files, prevent path traversal
    if not filename.endswith('.xml') or '/' in filename or '..' in filename:
        flash('Ongeldige bestandsnaam.', 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'build', 'excel_generated')
    file_path = os.path.join(output_dir, filename)
    if not os.path.exists(file_path):
        flash('Bestand niet gevonden.', 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))
    return send_from_directory(output_dir, filename, as_attachment=True)
app.secret_key = 'change-this-to-a-very-secret-key-1234'

# --- JSON upload endpoint for genereer_json.html ---
@app.route('/upload_json', methods=['POST'])
def upload_json():
    file = request.files.get('json_file')
    if not file:
        flash('Geen JSON-bestand geüpload.', 'danger')
        return redirect(request.referrer or url_for('genereer_json'))
    # Hier kun je de verwerking van het JSON-bestand toevoegen
    # Bijvoorbeeld: bestand opslaan, valideren, verwerken, etc.
    # file.save(os.path.join('uploads', secure_filename(file.filename)))
    flash('JSON-bestand succesvol geüpload (dummy handler).', 'success')
    return redirect(request.referrer or url_for('genereer_json'))

# --- Excel upload endpoint for genereer_xml.html ---
@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    file = request.files.get('excel_file')
    if not file:
        flash('Geen bestand geüpload.', 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))
    # Save the uploaded file to uploads directory
    uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    orig_filename = file.filename if file.filename else 'upload.xlsx'
    filename = secure_filename(orig_filename)
    file_path = os.path.join(uploads_dir, filename)
    file.save(file_path)

    # Get aanvraag_type from form
    aanvraag_type = request.form.get('aanvraag_type', 'ZBM').strip().upper()
    # Patch the Excel file to set aanvraag_type for all rows (in a temp file)
    import openpyxl
    import tempfile
    import subprocess

    import warnings
    try:
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        if ws is None:
            flash('Het geüploade Excel-bestand bevat geen werkblad of is ongeldig.', 'danger')
            return redirect(request.referrer or url_for('genereer_xml'))
        # Always set aanvraag_type for all rows, even if column exists
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=False))
        header_names = [cell.value for cell in header_row]
        type_col = None
        for idx, name in enumerate(header_names):
            if name and str(name).strip().lower() in ['cdberichttype', 'aanvraag_type', 'type']:
                type_col = idx
                break
        if type_col is None:
            # Add aanvraag_type as new column
            ws.cell(row=1, column=len(header_names)+1, value='CdBerichtType')
            type_col = len(header_names)
        # Overwrite aanvraag_type for all data rows
        for i, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
            ws.cell(row=i, column=type_col+1, value=aanvraag_type)
        # Save to a temp file, suppressing openpyxl UserWarnings
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            patched_excel_path = tmp.name
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            wb.save(patched_excel_path)
    except Exception as exc:
        flash(f'Fout bij verwerken van het Excel-bestand: {exc}', 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))

    # Call the Excel-to-XML generator script
    generator_path = os.path.join(os.path.dirname(__file__), '..', 'tools', 'generate_from_excel.py')
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'build', 'excel_generated')
    os.makedirs(output_dir, exist_ok=True)
    python_exe = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.venv', 'Scripts', 'python.exe'))
    import sys
    try:
        print(f"[DEBUG] Calling generator: {python_exe} {generator_path} --input {patched_excel_path} --outdir {output_dir} --mode single", file=sys.stderr)
        result = subprocess.run([
            python_exe,
            generator_path,
            '--input', patched_excel_path,
            '--outdir', output_dir,
            '--mode', 'single'
        ], capture_output=True, text=True, check=True)
        print(f"[DEBUG] Generator stdout: {result.stdout}", file=sys.stderr)
        print(f"[DEBUG] Generator stderr: {result.stderr}", file=sys.stderr)
        flash(f'Excel-bestand succesvol geüpload en {aanvraag_type} XML-bestanden gegenereerd.', 'success')
    except subprocess.CalledProcessError as e:
        print(f"[DEBUG] Generator failed: {e.stderr}\n{e.stdout}", file=sys.stderr)
        flash(f'Fout bij genereren van XML: {e.stderr}\n{e.stdout}', 'danger')
    finally:
        try:
            os.remove(patched_excel_path)
        except Exception:
            pass
    # Log the files found after upload
    try:
        files = os.listdir(output_dir)
        print(f"[DEBUG] Files in output_dir after upload: {files}", file=sys.stderr)
    except Exception as e:
        print(f"[DEBUG] Could not list files in output_dir: {e}", file=sys.stderr)
    return redirect(url_for('genereer_xml'))

@app.route("/genereer_xml/fragment")
def genereer_xml_fragment():
    """Fragment van de resultatenlijst voor AJAX refresh."""
    zip_limits = {
        'max_files': 50,
        'max_size_mb': 100
    }
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'build', 'excel_generated')
    generated = []
    if os.path.exists(output_dir):
        for fname in sorted(os.listdir(output_dir), reverse=True):
            if fname.endswith('.xml'):
                fpath = os.path.join(output_dir, fname)
                try:
                    tijdstip = datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat()
                    size = os.path.getsize(fpath)
                    generated.append({
                        'filename': fname,
                        'tijdstip': tijdstip,
                        'size': size
                    })
                except Exception:
                    continue
    return render_template(
        "genereer_xml.html",
        zip_limits=zip_limits,
        generated=generated,
        fragment_only=True
    )

# --- Placeholder API endpoints for frontend JS ---
@app.route('/api/test/laatste')
def api_test_laatste():
    out_dir = get_output_directory()
    try:
        xml_files = [f for f in os.listdir(out_dir) if f.endswith('.xml')]
        if not xml_files:
            print("[api_test_laatste] No XML files found.")
            return jsonify({"error": "Geen testresultaten gevonden"}), 404
        latest_file = max(xml_files, key=lambda f: os.path.getmtime(os.path.join(out_dir, f)))
        file_path = os.path.join(out_dir, latest_file)
        timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        size = os.path.getsize(file_path)
        result = {"filename": latest_file, "timestamp": timestamp, "size": size}
        # print(f"[api_test_laatste] Returning: {result}")
        return jsonify(result)
    except Exception as e:
        # print(f"[api_test_laatste] Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/xml-stats')
def api_xml_stats():
    out_dir = get_output_directory()
    try:
        xml_files = [f for f in os.listdir(out_dir) if f.endswith('.xml')]
        # Aggregate by date
        daily = {}
        for f in xml_files:
            file_path = os.path.join(out_dir, f)
            dt = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).date().isoformat()
            if dt not in daily:
                daily[dt] = {"datum": dt, "totaal": 0, "geslaagd": 0, "gefaald": 0}
            daily[dt]["totaal"] += 1
            daily[dt]["geslaagd"] += 1  # For now, all are 'geslaagd'
            # If you want to mark some as failed, adjust here
        # Calculate success percentage
        aggregated = []
        for dt in sorted(daily.keys()):
            d = daily[dt]
            totaal = d["totaal"]
            geslaagd = d["geslaagd"]
            gefaald = d["gefaald"]
            succes_percentage = int(round((geslaagd / totaal) * 100)) if totaal > 0 else 0
            d["succes_percentage"] = succes_percentage
            aggregated.append(d)
        result = {"aggregated": aggregated}
        # print(f"[api_xml_stats] Returning: {result}")
        return jsonify(result)
    except Exception as e:
        # print(f"[api_xml_stats] Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/xml/throughput')
def api_xml_throughput():
    out_dir = get_output_directory()
    try:
        xml_files = [f for f in os.listdir(out_dir) if f.endswith('.xml')]
        daily = {}
        for f in xml_files:
            file_path = os.path.join(out_dir, f)
            dt = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).date().isoformat()
            if dt not in daily:
                daily[dt] = {"datum": dt, "totaal": 0, "geslaagd": 0, "gefaald": 0}
            daily[dt]["totaal"] += 1
            daily[dt]["geslaagd"] += 1  # For now, all are 'geslaagd'
            # If you want to mark some as failed, adjust here
        aggregated = []
        for dt in sorted(daily.keys()):
            d = daily[dt]
            totaal = d["totaal"]
            geslaagd = d["geslaagd"]
            gefaald = d["gefaald"]
            succes_percentage = int(round((geslaagd / totaal) * 100)) if totaal > 0 else 0
            d["succes_percentage"] = succes_percentage
            aggregated.append(d)
        result = {"aggregated": aggregated}
        # print(f"[api_xml_throughput] Returning: {result}")
        return jsonify(result)
    except Exception as e:
        # print(f"[api_xml_throughput] Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test/totaal')
def api_test_totaal():
    out_dir = get_output_directory()
    try:
        xml_files = [f for f in os.listdir(out_dir) if f.endswith('.xml')]
        result = {"totaal": len(xml_files)}
        # print(f"[api_test_totaal] Returning: {result}")
        return jsonify(result)
    except Exception as e:
        # print(f"[api_test_totaal] Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/test/historie')
def api_test_historie():
    out_dir = get_output_directory()
    try:
        xml_files = [f for f in os.listdir(out_dir) if f.endswith('.xml')]
        historie = []
        for f in sorted(xml_files, key=lambda x: os.path.getmtime(os.path.join(out_dir, x)), reverse=True):
            file_path = os.path.join(out_dir, f)
            historie.append({
                "filename": f,
                "timestamp": datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                "size": os.path.getsize(file_path)
            })
        result = {"historie": historie}
        # print(f"[api_test_historie] Returning: {result}")
        return jsonify(result)
    except Exception as e:
        # print(f"[api_test_historie] Error: {e}")
        return jsonify({"error": str(e)}), 500

# --- Helper to get the output directory ---
def get_output_directory():
    # Adjust this path as needed for your project
    return os.path.join(os.path.dirname(__file__), '..', 'build')

# --- Preview helper ---
def _safe_preview_content(content, max_chars=2000):
    # Return a safe, truncated preview for display
    if not isinstance(content, str):
        try:
            content = content.decode("utf-8", errors="replace")
        except Exception:
            content = str(content)
    preview = content[:max_chars]
    if len(content) > max_chars:
        preview += "\n... (afgekapt)"
    return escape(preview)

# --- Voorvertoning endpoint ---
@app.route("/resultaten/preview/<filename>")
def resultaten_preview(filename):
    # Only allow .xml files, prevent path traversal
    if not filename.endswith(".xml") or "/" in filename or ".." in filename:
        return jsonify({"error": "Ongeldige bestandsnaam"}), 400
    out_dir = get_output_directory()
    file_path = os.path.join(out_dir, filename)
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return jsonify({"error": "Bestand niet gevonden"}), 404
    try:
        size = os.path.getsize(file_path)
        tijdstip = datetime.datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        preview = _safe_preview_content(content, max_chars=2000)
        return jsonify({
            "filename": filename,
            "size": size,
            "tijdstip": tijdstip,
            "preview": preview
        })
    except Exception as e:
        return jsonify({"error": f"Fout bij lezen: {e}"}), 500

# --- Main frontend routes ---
@app.route("/")
def home():
    return render_template("dashboard.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/genereer_xml")
def genereer_xml():
    # Provide default context variables expected by the template
    zip_limits = {
        'max_files': 50,  # adjust as needed
        'max_size_mb': 100
    }
    # Always refresh the results list on page load
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'build', 'excel_generated')
    generated = []
    if os.path.exists(output_dir):
        for fname in sorted(os.listdir(output_dir), reverse=True):
            if fname.endswith('.xml'):
                fpath = os.path.join(output_dir, fname)
                try:
                    tijdstip = datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).isoformat()
                    size = os.path.getsize(fpath)
                    generated.append({
                        'filename': fname,
                        'tijdstip': tijdstip,
                        'size': size
                    })
                except Exception:
                    continue
    return render_template("genereer_xml.html", zip_limits=zip_limits, generated=generated)

@app.route("/genereer_json")
def genereer_json():
    zip_limits = {
        'max_files': 50,  # adjust as needed
        'max_size_mb': 100
    }
    generated = []  # or load actual generated files if available
    return render_template("genereer_json.html", zip_limits=zip_limits, generated=generated)

@app.route("/historie")
def historie():
    return render_template("historie.html")

@app.route("/instellingen/")
def instellingen():
    return render_template("instellingen.html")

@app.route("/datasets")
def datasets():
    return render_template("datasets.html")

@app.route("/logs")
def logs():
    return render_template("logs.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/documentatie")
def documentatie():
    return render_template("documentatie.html")

@app.route("/design_preview")
def design_preview():
    return render_template("design_preview.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/configuratie")
def configuratie():
    return render_template("configuratie.html")

# --- Favicon handler ---
@app.route('/favicon.ico')
def favicon():
    return '', 204

if __name__ == "__main__":
    try:
        app.run(debug=True)
    except Exception as e:
        import traceback
        print("\n--- FLASK STARTUP ERROR ---")
        traceback.print_exc()
        print("--- END ERROR ---\n")
        raise