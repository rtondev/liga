import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import abort, flash, jsonify, redirect, request, session, url_for

from liga.services.accounts import public_user, user_by_id


def current_user():
    from flask import g

    if "user_cache" not in g:
        uid = session.get("user_id")
        g.user_cache = public_user(user_by_id(uid)) if uid else None
    return g.user_cache


def login_user(user_id: int, remember: bool = False) -> None:
    session.clear()
    session["user_id"] = user_id
    session["csrf"] = secrets.token_hex(16)
    session.permanent = remember


def logout_user() -> None:
    session.clear()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            flash("Entre para continuar.", "info")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def verified_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Entre para continuar.", "info")
            return redirect(url_for("auth.login"))
        if not user["email_verified"]:
            flash("Confirme o e-mail para jogar.", "info")
            return redirect(url_for("auth.confirm"))
        return view(*args, **kwargs)

    return wrapped


def ensure_csrf() -> str:
    token = session.get("csrf")
    if not token:
        token = secrets.token_hex(16)
        session["csrf"] = token
    return token


def csrf_ok() -> bool:
    sent = request.form.get("csrf") or request.headers.get("X-CSRF")
    if not sent and request.is_json:
        payload = request.get_json(silent=True) or {}
        sent = payload.get("csrf")
    return bool(sent) and sent == session.get("csrf")


def reject_csrf():
    if request.is_json or request.headers.get("X-CSRF"):
        return jsonify({"ok": False, "error": "Sessão expirada. Atualize a página."}), 400
    flash("Atualize a página e tente de novo.", "error")
    ref = request.referrer
    if ref and urlparse(ref).netloc == request.host:
        return redirect(ref)
    return redirect(url_for("main.home"))


def guard_post():
    if request.method == "POST" and not csrf_ok():
        return reject_csrf()
    return None
