
# --- Imports (must be at the very top) ---
import os
import sys
import datetime
from flask import Flask, jsonify, render_template, request, send_from_directory, redirect, flash, url_for
from markupsafe import escape
from werkzeug.utils import secure_filename
from flask import Response
import io
import json
import zipfile

# --- Flask app instance (must be at top level) ---
app = Flask(__name__)

# Security: Environment-based secret key with production guard
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
SECRET_KEY = os.environ.get('U_XMLATOR_SECRET')

if FLASK_ENV == 'production' and not SECRET_KEY:
    raise SystemExit(
        'ERROR: U_XMLATOR_SECRET environment variable must be set when FLASK_ENV=production.\n'
        'Example (PowerShell): $env:U_XMLATOR_SECRET = "your-secret-key-here"'
    )

app.secret_key = SECRET_KEY or 'change-this-to-a-very-secret-key-1234'

# Session cookie security settings
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('U_XMLATOR_COOKIE_SECURE', '1') == '1'
app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('U_XMLATOR_SAMESITE', 'Lax')
app.config['PERMANENT_SESSION_LIFETIME'] = int(os.environ.get('U_XMLATOR_SESSION_SECONDS', '604800'))

# Size guard for uploads (10 MB default) and allowed extensions
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}

# --- Download generated XML file endpoint ---
@app.route('/resultaten/download/<filename>')
def download_generated(filename):
    # Only allow .xml files, prevent path traversal
    if not filename.endswith('.xml') or '/' in filename or '..' in filename:
        flash('Ongeldige bestandsnaam.', 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))
    
    # Search in all output directories
    directories = [
        get_output_directory('ZBM'),
        get_output_directory('Digipoort'),
        get_output_directory()  # Default/backwards compatible
    ]
    
    print(f"[DEBUG] Looking for file: {filename}", file=sys.stderr)
    for output_dir in directories:
        print(f"[DEBUG] Checking directory: {output_dir}", file=sys.stderr)
        if os.path.exists(output_dir):
            file_path = os.path.join(output_dir, filename)
            print(f"[DEBUG] Looking for: {file_path}, exists: {os.path.exists(file_path)}", file=sys.stderr)
            if os.path.exists(file_path):
                print(f"[DEBUG] Found file, sending from: {output_dir}", file=sys.stderr)
                return send_from_directory(output_dir, filename, as_attachment=True)
    
    print(f"[DEBUG] File not found in any directory", file=sys.stderr)
    flash('Bestand niet gevonden.', 'danger')
    return redirect(request.referrer or url_for('genereer_xml'))

# --- Delete selected generated XML files ---
@app.route('/resultaten/delete-selected', methods=['POST'])
def delete_selected_files():
    try:
        data = request.get_json(silent=True) or {}
        filenames = data.get('filenames') or []
        if not isinstance(filenames, list) or not filenames:
            return jsonify({'error': 'Geen bestanden geselecteerd'}), 400
        # Validate each filename and delete
        out_dir = get_output_directory() if 'get_output_directory' in globals() else os.path.join(os.path.dirname(__file__), '..', 'build', 'excel_generated')
        deleted = []
        failed = []
        for fn in filenames:
            if not isinstance(fn, str) or '/' in fn or '..' in fn or not fn.endswith('.xml'):
                failed.append(fn)
                continue
            fp = os.path.join(out_dir, fn)
            if not os.path.exists(fp) or not os.path.isfile(fp):
                failed.append(fn)
                continue
            try:
                os.remove(fp)
                deleted.append(fn)
            except Exception as e:
                failed.append(fn)
                print(f"[ERROR] Failed to delete {fn}: {e}", file=sys.stderr)
        return jsonify({
            'success': True,
            'deleted': len(deleted),
            'failed': len(failed),
            'deleted_files': deleted
        })
    except Exception as e:
        return jsonify({'error': f'Fout bij verwijderen: {e}'}), 500



@app.route('/resultaten/download-zip', methods=['POST'])
def download_generated_zip():
    try:
        data = request.get_json(silent=True) or {}
        filenames = data.get('filenames') or []
        if not isinstance(filenames, list) or not filenames:
            return jsonify({'error': 'Geen bestanden geselecteerd'}), 400
        # Validate each filename
        safe_files = []
        out_dir = get_output_directory() if 'get_output_directory' in globals() else os.path.join(os.path.dirname(__file__), '..', 'build', 'excel_generated')
        for fn in filenames:
            if not isinstance(fn, str) or '/' in fn or '..' in fn or not fn.endswith('.xml'):
                return jsonify({'error': f'Ongeldige bestandsnaam: {fn}'}), 400
            fp = os.path.join(out_dir, fn)
            if not os.path.exists(fp) or not os.path.isfile(fp):
                return jsonify({'error': f'Bestand niet gevonden: {fn}'}), 404
            safe_files.append((fn, fp))
        # Build ZIP in memory
        mem = io.BytesIO()
        with zipfile.ZipFile(mem, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            for name, path in safe_files:
                zf.write(path, arcname=name)
        mem.seek(0)
        zip_bytes = mem.getvalue()
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_name = f"uwv_xmlator_selectie_{ts}.zip"
        headers = {
            'Content-Type': 'application/zip',
            'Content-Disposition': f"attachment; filename*=UTF-8''{zip_name}",
            'Content-Length': str(len(zip_bytes))
        }
        return Response(zip_bytes, headers=headers)
    except Exception as e:
        return jsonify({'error': f'Fout bij maken van ZIP: {e}'}), 500

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
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    print(f"[DEBUG] upload_excel called, is_ajax={is_ajax}, file={file}", file=sys.stderr)
    if not file:
        msg = 'Geen bestand geüpload.'
        if is_ajax:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))
    # Validate extension
    _, ext = os.path.splitext(file.filename or '')
    if ext.lower() not in ALLOWED_EXTENSIONS:
        msg = 'Ongeldig bestandstype; alleen .xlsx en .xls zijn toegestaan.'
        if is_ajax:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))
    # Optional: content length guard
    if request.content_length and request.content_length > app.config['MAX_CONTENT_LENGTH']:
        msg = f'Bestand te groot (max {app.config["MAX_CONTENT_LENGTH"] // (1024*1024)} MB).'
        if is_ajax:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'danger')
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
            msg = 'Het geüploade Excel-bestand bevat geen werkblad of is ongeldig.'
            if is_ajax:
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'danger')
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
        msg = f'Fout bij verwerken van het Excel-bestand: {exc}'
        if is_ajax:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))

    # Call the Excel-to-XML generator script
    generator_path = os.path.join(os.path.dirname(__file__), '..', 'tools', 'generate_from_excel.py')
    # Use type-specific output directory
    output_dir = get_output_directory(aanvraag_type)
    os.makedirs(output_dir, exist_ok=True)
    python_exe = os.environ.get('PYTHON_EXE', sys.executable)
    
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
        
        # Generation completed successfully
        msg = f'Excel-bestand succesvol geüpload en {aanvraag_type} XML-bestanden gegenereerd.'
        
        if is_ajax:
            return jsonify({
                'success': True,
                'message': msg
            }), 200
        flash(msg, 'success')
    except subprocess.CalledProcessError as e:
        print(f"[DEBUG] Generator failed: {e.stderr}\n{e.stdout}", file=sys.stderr)
        msg = f'Fout bij genereren van XML: {e.stderr}\n{e.stdout}'
        if is_ajax:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'danger')
    except Exception as e:
        # Catch other failures such as missing python executable or script errors
        print(f"[DEBUG] Generator unexpected error: {e}", file=sys.stderr)
        msg = f'Fout bij genereren van XML: {e}'
        if is_ajax:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'danger')
    finally:
        for path in (patched_excel_path, file_path):
            try:
                if path and os.path.exists(path):
                    os.remove(path)
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
    generated, total_count = list_generated_files(limit=25, prune=True)
    from flask import make_response
    html = render_template(
        "_results_panel.html",
        zip_limits=zip_limits,
        generated=generated,
        total_count=total_count
    )
    print("[DEBUG] /genereer_xml/fragment generated files:", [f['filename'] for f in generated])
    resp = make_response(html)
    return resp

# Generic resultaten fragment (shared by pages)
@app.route("/resultaten/fragment")
def resultaten_fragment():
    zip_limits = {
        'max_files': 50,
        'max_size_mb': 100
    }
    generated, total_count = list_generated_files(limit=25, prune=True)
    from flask import make_response
    html = render_template(
        "_results_panel.html",
        zip_limits=zip_limits,
        generated=generated,
        total_count=total_count
    )
    return make_response(html)
    print("[DEBUG] /genereer_xml/fragment HTML snippet:\n", html[:500], '...')
    return make_response(html)

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
def get_output_directory(aanvraag_type=None):
    """
    Get output directory for generated files.
    If aanvraag_type is provided, returns type-specific path according to docs:
    - ZBM/VM: uzs_filedrop/UZI-GAP3/UZSx_ACC1/v0428
    - Digipoort/OTP3: uzs_filedrop/UZI-GAP3/UZSx_ACC1/UwvZwMelding_MQ_V0428
    If aanvraag_type is None, returns default build/excel_generated (for backwards compatibility)
    """
    base = os.path.join(os.path.dirname(__file__), '..')
    
    if aanvraag_type:
        atype = str(aanvraag_type).upper()
        if atype in ['ZBM', 'VM']:
            return os.path.join(base, 'uzs_filedrop', 'UZI-GAP3', 'UZSx_ACC1', 'v0428')
        elif atype in ['DIGIPOORT', 'OTP3']:
            return os.path.join(base, 'uzs_filedrop', 'UZI-GAP3', 'UZSx_ACC1', 'UwvZwMelding_MQ_V0428')
    
    # Default: backwards compatible path
    return os.path.join(base, 'build', 'excel_generated')

# --- Helper: list generated files (optionally prune oldest beyond limit) ---
def list_generated_files(limit=25, prune=False):
    # Scan all output directories (ZBM/VM, Digipoort, and backwards-compatible default)
    directories = [
        get_output_directory('ZBM'),
        get_output_directory('Digipoort'),
        get_output_directory()  # Default/backwards compatible
    ]
    files_with_time = []
    for out_dir in directories:
        if os.path.exists(out_dir):
            for fname in os.listdir(out_dir):
                if fname.endswith('.xml'):
                    fpath = os.path.join(out_dir, fname)
                    try:
                        mtime = os.path.getmtime(fpath)
                        files_with_time.append((fname, fpath, mtime))
                    except Exception:
                        continue
    # Sort newest first
    files_with_time.sort(key=lambda x: x[2], reverse=True)
    total_count = len(files_with_time)
    if prune and total_count > limit:
        # delete oldest beyond limit
        for fname, fpath, _ in files_with_time[limit:]:
            try:
                os.remove(fpath)
            except Exception as e:
                print(f"[WARN] kon {fname} niet verwijderen: {e}", file=sys.stderr)
        files_with_time = files_with_time[:limit]
        total_count = len(files_with_time)
    generated = []
    for fname, fpath, mtime in files_with_time[:limit]:
        try:
            tijdstip = datetime.datetime.fromtimestamp(mtime).isoformat()
            size = os.path.getsize(fpath)
            generated.append({
                'filename': fname,
                'tijdstip': tijdstip,
                'size': size
            })
        except Exception:
            continue
    return generated, total_count


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
    generated, total_count = list_generated_files(limit=25, prune=True)
    return render_template("genereer_xml.html", zip_limits=zip_limits, generated=generated, total_count=total_count)

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