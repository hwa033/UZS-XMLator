"""
Mock REST API Server voor XML Validatie Tests
==============================================

Eenvoudige Flask API server die XML validatie endpoints simuleert
voor het testen van API integratie.
"""

import time
from collections import defaultdict
from datetime import datetime
from functools import wraps

from flask import Flask, jsonify, request
from lxml import etree

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max

# Rate limiting - simpel in-memory
verzoek_teller = defaultdict(list)
RATE_LIMIT = 50  # Max verzoeken per minuut
RATE_WINDOW = 60  # Seconden


def rate_limiet():
    """Decorator voor rate limiting"""

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            client_ip = request.remote_addr
            nu = time.time()

            # Verwijder oude entries
            verzoek_teller[client_ip] = [
                t for t in verzoek_teller[client_ip] if nu - t < RATE_WINDOW
            ]

            # Check limiet
            if len(verzoek_teller[client_ip]) >= RATE_LIMIT:
                return (
                    jsonify(
                        {
                            "fout": "Rate limit overschreden",
                            "bericht": f"Maximaal {RATE_LIMIT} verzoeken per minuut",
                        }
                    ),
                    429,
                )

            verzoek_teller[client_ip].append(nu)
            return f(*args, **kwargs)

        return wrapper

    return decorator


def voeg_security_headers_toe(response):
    """Voeg security headers toe aan response"""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


@app.after_request
def after_request(response):
    """Voeg headers toe aan alle responses"""
    return voeg_security_headers_toe(response)


@app.route("/api/health", methods=["GET"])
@rate_limiet()
def health_check():
    """Health check endpoint"""
    return jsonify(
        {"status": "ok", "tijdstip": datetime.now().isoformat(), "versie": "1.0.0"}
    )


@app.route("/api/xml/valideer", methods=["POST"])
@rate_limiet()
def valideer_xml():
    """Valideer XML structuur"""
    try:
        xml_data = request.data.decode("utf-8")

        if not xml_data or len(xml_data.strip()) == 0:
            return jsonify({"geldig": False, "fout": "Lege XML data ontvangen"}), 400

        # Probeer XML te parsen
        try:
            etree.fromstring(xml_data.encode("utf-8"))
            return (
                jsonify(
                    {
                        "geldig": True,
                        "bericht": "XML is geldig",
                        "tijdstip": datetime.now().isoformat(),
                    }
                ),
                200,
            )

        except etree.XMLSyntaxError as e:
            return (
                jsonify(
                    {
                        "geldig": False,
                        "fout": str(e),
                        "regel": e.lineno if hasattr(e, "lineno") else None,
                    }
                ),
                400,
            )

    except Exception as e:
        return jsonify({"geldig": False, "fout": f"Server fout: {str(e)}"}), 500


@app.route("/api/xml/upload", methods=["POST"])
@rate_limiet()
def upload_xml():
    """Upload XML bestand"""
    if "bestand" not in request.files:
        return jsonify({"fout": "Geen bestand gevonden in request"}), 400

    bestand = request.files["bestand"]

    if bestand.filename == "":
        return jsonify({"fout": "Geen bestand geselecteerd"}), 400

    if not bestand.filename.endswith(".xml"):
        return jsonify({"fout": "Alleen XML bestanden zijn toegestaan"}), 400

    try:
        xml_inhoud = bestand.read()
        etree.fromstring(xml_inhoud)

        # Genereer uniek bestand ID
        bestand_id = f"xml_{int(time.time() * 1000)}"

        return (
            jsonify(
                {
                    "bestand_id": bestand_id,
                    "bestandsnaam": bestand.filename,
                    "grootte": len(xml_inhoud),
                    "tijdstip": datetime.now().isoformat(),
                }
            ),
            201,
        )

    except etree.XMLSyntaxError as e:
        return jsonify({"fout": "Ongeldig XML bestand", "details": str(e)}), 400
    except Exception as e:
        return jsonify({"fout": f"Upload fout: {str(e)}"}), 500


@app.route("/api/xml/bulk-valideer", methods=["POST"])
@rate_limiet()
def bulk_valideer():
    """Valideer meerdere XML documenten"""
    try:
        bulk_data = request.data.decode("utf-8")
        xml_documenten = bulk_data.split("\n---\n")

        resultaten = []
        voor_aantal = 0
        tegen_aantal = 0

        for idx, xml_doc in enumerate(xml_documenten):
            if not xml_doc.strip():
                continue

            try:
                etree.fromstring(xml_doc.encode("utf-8"))
                resultaten.append({"index": idx, "geldig": True})
                voor_aantal += 1
            except etree.XMLSyntaxError as e:
                resultaten.append({"index": idx, "geldig": False, "fout": str(e)})
                tegen_aantal += 1

        return (
            jsonify(
                {
                    "totaal": len(resultaten),
                    "geldig": voor_aantal,
                    "ongeldig": tegen_aantal,
                    "resultaten": resultaten,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"fout": f"Bulk validatie fout: {str(e)}"}), 500


@app.route("/api/admin/gebruikers", methods=["GET"])
@rate_limiet()
def admin_gebruikers():
    """Admin endpoint - vereist authenticatie"""
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return (
            jsonify({"fout": "Unauthorized", "bericht": "Authenticatie vereist"}),
            401,
        )

    if not auth_header.startswith("Bearer "):
        return jsonify({"fout": "Ongeldige authenticatie header"}), 401

    token = auth_header.replace("Bearer ", "")

    # Simpele token validatie (in productie zou dit JWT validatie zijn)
    if "test" not in token:
        return jsonify({"fout": "Ongeldige token"}), 403

    return (
        jsonify(
            {
                "gebruikers": [
                    {"id": 1, "naam": "Test Gebruiker 1"},
                    {"id": 2, "naam": "Test Gebruiker 2"},
                ]
            }
        ),
        200,
    )


@app.errorhandler(404)
def niet_gevonden(e):
    """404 error handler"""
    return jsonify({"fout": "Endpoint niet gevonden", "pad": request.path}), 404


@app.errorhandler(405)
def methode_niet_toegestaan(e):
    """405 error handler"""
    return (
        jsonify(
            {
                "fout": "HTTP methode niet toegestaan",
                "methode": request.method,
                "pad": request.path,
            }
        ),
        405,
    )


@app.errorhandler(413)
def bestand_te_groot(e):
    """413 error handler"""
    return jsonify({"fout": "Bestand te groot", "max_grootte": "16MB"}), 413


if __name__ == "__main__":
    print("🚀 Mock XML API Server wordt gestart...")
    print("📍 Beschikbaar op: http://localhost:8080")
    print("\n📋 Beschikbare endpoints:")
    print("   GET  /api/health              - Health check")
    print("   POST /api/xml/valideer        - XML validatie")
    print("   POST /api/xml/upload          - XML upload")
    print("   POST /api/xml/bulk-valideer   - Bulk validatie")
    print("   GET  /api/admin/gebruikers    - Admin (auth vereist)")
    print("\n🛑 Stop met Ctrl+C\n")

    app.run(host="0.0.0.0", port=8080, debug=True)
