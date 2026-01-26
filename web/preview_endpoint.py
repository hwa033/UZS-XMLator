# --- Preview helper and endpoint (must be after app = Flask(...)) ---
import datetime
from pathlib import Path

from markupsafe import escape


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


def _resultaten_preview(app, get_output_directory, jsonify):
    """Create preview endpoint (injected with deps)."""

    @app.route("/resultaten/preview/<filename>")
    def resultaten_preview(filename):
        # Only allow .xml files, prevent path traversal
        if not filename.endswith(".xml") or "/" in filename or ".." in filename:
            return jsonify({"error": "Ongeldige bestandsnaam"}), 400
        out_dir = get_output_directory()
        file_path = Path(out_dir) / filename
        if not file_path.exists() or not file_path.is_file():
            return jsonify({"error": "Bestand niet gevonden"}), 404
        try:
            size = file_path.stat().st_size
            mtime = datetime.datetime.fromtimestamp(
                file_path.stat().st_mtime
            ).isoformat()
            with open(file_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
            preview = _safe_preview_content(content, max_chars=2000)
            return jsonify(
                {
                    "filename": filename,
                    "size": size,
                    "tijdstip": mtime,
                    "preview": preview,
                }
            )
        except Exception as e:
            return jsonify({"error": f"Fout bij lezen: {e}"}), 500

    return resultaten_preview
