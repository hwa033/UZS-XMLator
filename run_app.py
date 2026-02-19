import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path

# Ensure web package can be imported when running from project root
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))


def _load_app():
    try:
        # Prefer package-level import: web exposes `app` in web/__init__.py
        from web import app
    except Exception:
        # Fallback to module import
        try:
            from web.app import app
        except Exception as e:
            print("Fout bij importeren van web.app:", e)
            raise
    return app


def main():
    # Default to production when running the bundled exe unless explicitly set
    if getattr(sys, "frozen", False) and not os.environ.get("FLASK_ENV"):
        os.environ["FLASK_ENV"] = "production"
    if getattr(sys, "frozen", False) and not os.environ.get("U_XMLATOR_SECRET"):
        os.environ["U_XMLATOR_SECRET"] = os.urandom(32).hex()

    parser = argparse.ArgumentParser(
        description="Run the UZS XMLator web app",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Run in development mode with auto-reload (Flask reloader)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to listen on",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Open de browser automatisch na start",
    )
    parser.add_argument(
        "--open-url",
        default=None,
        help="URL om te openen (override voor host/port)",
    )
    args = parser.parse_args()

    app = _load_app()

    should_open = (
        args.open_browser
        or os.environ.get("XMLATOR_OPEN_BROWSER") == "1"
        or getattr(sys, "frozen", False)
    )
    open_url = args.open_url or os.environ.get("XMLATOR_OPEN_URL")
    if not open_url:
        host_for_url = "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
        open_url = f"http://{host_for_url}:{args.port}"

    def _open_browser():
        try:
            webbrowser.open(open_url)
        except Exception:
            pass

    if should_open:
        threading.Timer(1.0, _open_browser).start()

    # If --reload requested, use Flask built-in reloader (development only)
    if args.reload:
        print(
            f"Starting in development mode with reloader on "
            f"http://{args.host}:{args.port} (debug=True)"
        )
        # debug=True enables the reloader; it should ONLY be used for development
        app.run(host=args.host, port=args.port, debug=True)
        return

    # Production-like run: prefer waitress if available, otherwise run Flask
    # without reloader
    try:
        try:
            from waitress import serve
        except ImportError:
            serve = None

        if serve:
            print(f"Starten met waitress op http://{args.host}:{args.port}")
            serve(app, host=args.host, port=args.port)
        else:
            print(
                "waitress niet geïnstalleerd; fallback naar Flask dev-server "
                "(debug=False)"
            )
            app.run(host=args.host, port=args.port, debug=False)
    except KeyboardInterrupt:
        print("\nStop ontvangen (KeyboardInterrupt), applicatie afgesloten.")
    except Exception as e:
        print("Onverwachte fout bij starten van de server:", e)
        raise


if __name__ == "__main__":
    main()
