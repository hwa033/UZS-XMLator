from functools import wraps

from flask import Blueprint, redirect, render_template, session, url_for

beheer_bp = Blueprint("beheer", __name__, template_folder="templates")


# Simple login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("beheer_ingelogd"):
            return redirect(url_for("beheer.login"))
        return f(*args, **kwargs)

    return decorated_function


@beheer_bp.route("/login", methods=["GET", "POST"])
def login():
    # Redirect to the unified app login page and supply a next parameter
    # so the user returns to the beheer dashboard after authentication.
    return redirect(url_for("login", next=url_for("beheer.dashboard")))


@beheer_bp.route("/logout")
def logout():
    session.pop("beheer_ingelogd", None)
    return redirect(url_for("beheer.login"))


@beheer_bp.route("/")
@login_required
def dashboard():
    # Hier kun je alle beheertaken tonen
    return render_template("beheer_dashboard.html")
