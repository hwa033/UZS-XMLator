import argparse
import sys
from pathlib import Path

# Ensure web package can be imported when running from project root
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

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


def main():
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
    args = parser.parse_args()

    # If --reload requested, use Flask built-in reloader (development only)
    if args.reload:
        print(
            f"Starting in development mode with reloader on http://{args.host}:{args.port} (debug=True)"
        )
        # debug=True enables the reloader; it should ONLY be used for development
        app.run(host=args.host, port=args.port, debug=True)
        return

    # Production-like run: prefer waitress if available, otherwise run Flask without reloader
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
                "waitress niet geïnstalleerd; fallback naar Flask dev-server (debug=False)"
            )
            app.run(host=args.host, port=args.port, debug=False)
    except KeyboardInterrupt:
        print("\nStop ontvangen (KeyboardInterrupt), applicatie afgesloten.")
    except Exception as e:
        print("Onverwachte fout bij starten van de server:", e)
        raise


if __name__ == "__main__":
    main()
