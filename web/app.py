import os
import sys
import datetime
from flask import Flask, jsonify, render_template, request, send_from_directory, redirect, flash, url_for, Response, make_response
from werkzeug.utils import secure_filename
import io
import json
import zipfile

app = Flask(__name__)

# Beveiligingsinstellingen
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
SECRET_KEY = os.environ.get('U_XMLATOR_SECRET')

if FLASK_ENV == 'production' and not SECRET_KEY:
    raise SystemExit(
        'FOUT: Zet de U_XMLATOR_SECRET omgevingsvariabele als FLASK_ENV=production.\n'
        'Voorbeeld (PowerShell): $env:U_XMLATOR_SECRET = "uw-geheim-hier"'
    )

app.secret_key = SECRET_KEY or 'verander-dit-naar-een-lang-geheim-1234'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('U_XMLATOR_COOKIE_SECURE', '1') == '1'
app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('U_XMLATOR_SAMESITE', 'Lax')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}


def get_output_directory(aanvraag_type=None):
    """Bepaal uitvoermap voor gegenereerde bestanden."""
    base = os.path.join(os.path.dirname(__file__), '..')
    
    if aanvraag_type:
        atype = str(aanvraag_type).upper()
        if atype in ['ZBM', 'VM']:
            return os.path.join(base, 'uzs_filedrop', 'UZI-GAP3', 'UZSx_ACC1', 'v0428')
        elif atype in ['DIGIPOORT', 'OTP3']:
            return os.path.join(base, 'uzs_filedrop', 'UZI-GAP3', 'UZSx_ACC1', 'UwvZwMelding_MQ_V0428')
    
    return os.path.join(base, 'build', 'excel_generated')


def list_generated_files(limit=25, prune=False):
    """Lijst gegenereerde XML-bestanden, optioneel met verwijdering van oudste."""
    directories = [
        get_output_directory('ZBM'),
        get_output_directory('Digipoort'),
        get_output_directory()
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
    
    files_with_time.sort(key=lambda x: x[2], reverse=True)
    total_count = len(files_with_time)
    
    if prune and total_count > limit:
        for fname, fpath, _ in files_with_time[limit:]:
            try:
                os.remove(fpath)
            except Exception as e:
                print(f"[WAARSCHUWING] Kon {fname} niet verwijderen: {e}", file=sys.stderr)
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


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/genereer_xml")
def genereer_xml():
    zip_limits = {'max_files': 50, 'max_size_mb': 100}
    generated, total_count = list_generated_files(limit=25, prune=True)
    return render_template("genereer_xml.html", zip_limits=zip_limits, generated=generated, total_count=total_count)


@app.route("/resultaten/fragment")
def resultaten_fragment():
    zip_limits = {'max_files': 50, 'max_size_mb': 100}
    generated, total_count = list_generated_files(limit=25, prune=True)
    return make_response(render_template(
        "_results_panel.html",
        zip_limits=zip_limits,
        generated=generated,
        total_count=total_count
    ))


@app.route('/resultaten/download/<filename>')
def download_generated(filename):
    if not filename.endswith('.xml') or '/' in filename or '..' in filename:
        flash('Ongeldige bestandsnaam.', 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))
    
    directories = [
        get_output_directory('ZBM'),
        get_output_directory('Digipoort'),
        get_output_directory()
    ]
    
    for output_dir in directories:
        if os.path.exists(output_dir):
            file_path = os.path.join(output_dir, filename)
            if os.path.exists(file_path):
                return send_from_directory(output_dir, filename, as_attachment=True)
    
    flash('Bestand niet gevonden.', 'danger')
    return redirect(request.referrer or url_for('genereer_xml'))


@app.route('/resultaten/delete-selected', methods=['POST'])
def delete_selected_files():
    try:
        data = request.get_json(silent=True) or {}
        filenames = data.get('filenames') or []
        if not isinstance(filenames, list) or not filenames:
            return jsonify({'error': 'Geen bestanden geselecteerd'}), 400
        
        out_dir = get_output_directory()
        deleted = 0
        
        for fn in filenames:
            if not isinstance(fn, str) or '/' in fn or '..' in fn or not fn.endswith('.xml'):
                continue
            fp = os.path.join(out_dir, fn)
            if os.path.exists(fp) and os.path.isfile(fp):
                try:
                    os.remove(fp)
                    deleted += 1
                except Exception:
                    pass
        
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        return jsonify({'error': f'Fout bij verwijderen: {e}'}), 500


@app.route('/resultaten/download-zip', methods=['POST'])
def download_generated_zip():
    try:
        data = request.get_json(silent=True) or {}
        filenames = data.get('filenames') or []
        if not isinstance(filenames, list) or not filenames:
            return jsonify({'error': 'Geen bestanden geselecteerd'}), 400
        
        safe_files = []
        out_dir = get_output_directory()
        for fn in filenames:
            if not isinstance(fn, str) or '/' in fn or '..' in fn or not fn.endswith('.xml'):
                return jsonify({'error': f'Ongeldige bestandsnaam: {fn}'}), 400
            fp = os.path.join(out_dir, fn)
            if not os.path.exists(fp) or not os.path.isfile(fp):
                return jsonify({'error': f'Bestand niet gevonden: {fn}'}), 404
            safe_files.append((fn, fp))
        
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


@app.route('/upload_excel', methods=['POST'])
def upload_excel():
    import subprocess
    import tempfile
    import openpyxl
    import warnings
    
    file = request.files.get('excel_file')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if not file:
        msg = 'Geen bestand geüpload.'
        if is_ajax:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))
    
    _, ext = os.path.splitext(file.filename or '')
    if ext.lower() not in ALLOWED_EXTENSIONS:
        msg = 'Ongeldig bestandstype; alleen .xlsx en .xls zijn toegestaan.'
        if is_ajax:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))
    
    if request.content_length and request.content_length > app.config['MAX_CONTENT_LENGTH']:
        msg = f'Bestand te groot (max {app.config["MAX_CONTENT_LENGTH"] // (1024*1024)} MB).'
        if is_ajax:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'danger')
        return redirect(request.referrer or url_for('genereer_xml'))
    
    uploads_dir = os.path.join(os.path.dirname(__file__), '..', 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    orig_filename = file.filename if file.filename else 'upload.xlsx'
    filename = secure_filename(orig_filename)
    file_path = os.path.join(uploads_dir, filename)
    file.save(file_path)

    aanvraag_type = request.form.get('aanvraag_type', 'ZBM').strip().upper()
    
    try:
        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        if ws is None:
            msg = 'Het geüploade Excel-bestand bevat geen werkblad of is ongeldig.'
            if is_ajax:
                return jsonify({'success': False, 'error': msg}), 400
            flash(msg, 'danger')
            return redirect(request.referrer or url_for('genereer_xml'))
        
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=False))
        header_names = [cell.value for cell in header_row]
        type_col = None
        for idx, name in enumerate(header_names):
            if name and str(name).strip().lower() in ['cdberichttype', 'aanvraag_type', 'type']:
                type_col = idx
                break
        
        if type_col is None:
            ws.cell(row=1, column=len(header_names)+1, value='CdBerichtType')
            type_col = len(header_names)
        
        for i, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row), start=2):
            ws.cell(row=i, column=type_col+1, value=aanvraag_type)
        
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

    generator_path = os.path.join(os.path.dirname(__file__), '..', 'tools', 'generate_from_excel.py')
    output_dir = get_output_directory(aanvraag_type)
    os.makedirs(output_dir, exist_ok=True)
    python_exe = os.environ.get('PYTHON_EXE', sys.executable)
    
    try:
        result = subprocess.run([
            python_exe,
            generator_path,
            '--input', patched_excel_path,
            '--outdir', output_dir,
            '--mode', 'single'
        ], capture_output=True, text=True, check=True)
        
        msg = f'Excel-bestand succesvol geüpload en {aanvraag_type} XML-bestanden gegenereerd.'
        
        if is_ajax:
            return jsonify({'success': True, 'message': msg}), 200
        flash(msg, 'success')
    except subprocess.CalledProcessError as e:
        msg = f'Fout bij genereren van XML: {e.stderr or e.stdout}'
        if is_ajax:
            return jsonify({'success': False, 'error': msg}), 400
        flash(msg, 'danger')
    except Exception as e:
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
    
    return redirect(url_for('genereer_xml'))


@app.route('/health')
def health():
    return jsonify({'status': 'healthy'}), 200


@app.route('/ready')
def ready():
    try:
        downloads_dir = os.path.join(os.path.dirname(__file__), '..', 'web', 'static', 'downloads')
        os.makedirs(downloads_dir, exist_ok=True)
        return jsonify({'status': 'ready'}), 200
    except Exception:
        return jsonify({'status': 'not_ready'}), 503


@app.route('/favicon.ico')
def favicon():
    return '', 204


if __name__ == "__main__":
    app.run(debug=False)
