"""File download and management routes"""

import os
from flask import Flask, flash, jsonify, redirect, request, send_from_directory, url_for
from ..domain import FileManager, FiledropRouter


def register_file_routes(app: Flask, file_manager: FileManager):
    """Register file download/management endpoints"""

    @app.route("/resultaten/download/<filename>")
    def download_generated(filename):
        """Download a generated XML file"""
        if not filename.endswith(".xml") or "/" in filename or ".." in filename:
            flash("Invalid filename.", "danger")
            return redirect(request.referrer or url_for("genereer_xml"))

        directories = [
            file_manager.router.get_output_directory("ZBM"),
            file_manager.router.get_output_directory("Digipoort"),
            file_manager.router.get_output_directory(),
        ]

        for output_dir in directories:
            if output_dir.exists():
                file_path = output_dir / filename
                if file_path.exists():
                    return send_from_directory(output_dir, filename, as_attachment=True)

        flash("File not found.", "danger")
        return redirect(request.referrer or url_for("genereer_xml"))

    @app.route("/resultaten/delete-selected", methods=["POST"])
    def delete_selected_files():
        """Delete selected files"""
        try:
            data = request.get_json(silent=True) or {}
            filenames = data.get("filenames") or []

            if not isinstance(filenames, list) or not filenames:
                return jsonify({"error": "No files selected"}), 400

            deleted, missing = file_manager.delete_files(filenames)

            return jsonify(
                {"success": True, "deleted": deleted, "missing": missing}
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/resultaten/download-zip", methods=["POST"])
    def download_generated_zip():
        """Download selected files as ZIP"""
        try:
            import zipfile
            import io

            data = request.get_json(silent=True) or {}
            filenames = data.get("filenames") or []

            if not isinstance(filenames, list) or not filenames:
                return jsonify({"error": "No files selected"}), 400

            # Build file map
            directories = [
                file_manager.router.get_output_directory("ZBM"),
                file_manager.router.get_output_directory("Digipoort"),
                file_manager.router.get_output_directory(),
            ]
            unique_dirs = list(dict.fromkeys(directories))

            file_map = {}
            for out_dir in unique_dirs:
                if out_dir.exists():
                    for fname in out_dir.iterdir():
                        if fname.suffix == ".xml" and fname.is_file():
                            file_map[fname.name] = fname

            # Create ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for fn in filenames:
                    if fn in file_map:
                        fpath = file_map[fn]
                        zf.write(fpath, arcname=fn)

            zip_buffer.seek(0)
            return zf.read()  # type: ignore

        except Exception as e:
            return jsonify({"error": str(e)}), 500
