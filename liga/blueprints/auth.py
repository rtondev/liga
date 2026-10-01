from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from liga.security import current_user, login_required, login_user, logout_user
from liga.services import accounts

bp = Blueprint("auth", __name__)


def _purpose() -> str:
    return session.get("code_purpose") or "verify"


def _subject_id():
    if _purpose() == "verify" and current_user():
        return current_user()["id"]
    return session.get("pending_user_id")


@bp.route("/entrar", methods=["GET", "POST"])
def login():
    if current_user() and current_user()["email_verified"]:
        return redirect(url_for("main.home"))
    if request.method == "POST":
        row = accounts.authenticate(request.form.get("username", ""), request.form.get("password", ""))
        if row is None:
            flash("Usuário ou senha incorretos.", "error")
            return redirect(url_for("auth.login"))
        else:
            login_user(row["id"], remember=bool(request.form.get("lembrar")))
            if not row["email_verified"]:
                session["code_purpose"] = "verify"
                if accounts.latest_code(row["id"], "verify") is None:
                    accounts.issue_code(row["id"], "verify")
                return redirect(url_for("auth.confirm"))
            return redirect(url_for("main.home"))
    return render_template("auth/login.html")


@bp.route("/disponivel")
def available():
    me = current_user()
    me_id = me["id"] if me else None
    payload = {}
    username = request.args.get("username", "").strip()
    email = request.args.get("email", "").strip().lower()
    if accounts.USERNAME.match(username):
        row = accounts.user_by_username(username)
        payload["username"] = row is None or row["id"] == me_id
    if accounts.EMAIL.match(email):
        row = accounts.user_by_email(email)
        payload["email"] = row is None or row["id"] == me_id
    return jsonify(payload)


@bp.route("/cadastrar", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        form = {
            "nome": request.form.get("nome", ""),
            "username": request.form.get("username", ""),
            "email": request.form.get("email", ""),
        }
        user_id, error = accounts.register(
            form["nome"],
            form["username"],
            form["email"],
            request.form.get("password", ""),
        )
        if error:
            session["register_form"] = form
            flash(error, "error")
            return redirect(url_for("auth.register"))
        login_user(user_id, remember=bool(request.form.get("lembrar")))
        session["code_purpose"] = "verify"
        accounts.issue_code(user_id, "verify")
        return redirect(url_for("auth.confirm"))
    form = session.pop("register_form", None) or {"nome": "", "username": "", "email": ""}
    return render_template("auth/register.html", form=form)


@bp.route("/sair", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("main.home"))


@bp.route("/senha/esqueci", methods=["GET", "POST"])
def forgot():
    if request.method == "POST":
        row = accounts.user_by_login(request.form.get("email", ""))
        if row is None:
            flash("Não encontrei esse e-mail.", "error")
            return redirect(url_for("auth.forgot"))
        else:
            accounts.issue_code(row["id"], "reset")
            session["pending_user_id"] = row["id"]
            session["code_purpose"] = "reset"
            return redirect(url_for("auth.confirm"))
    return render_template("auth/forgot.html")


@bp.route("/confirmar", methods=["GET", "POST"])
def confirm():
    user_id = _subject_id()
    purpose = _purpose()
    if not user_id:
        return redirect(url_for("auth.login"))
    active = accounts.latest_code(user_id, purpose)
    if request.method == "POST" and request.form.get("reenviar"):
        accounts.issue_code(user_id, purpose, active["payload"] if active else None)
        flash("Novo código gerado.", "info")
        return redirect(url_for("auth.confirm"))
    if request.method == "POST":
        digits = "".join(request.form.get(f"d{i}", "") for i in range(4))
        row, error = accounts.consume_code(user_id, purpose, digits)
        if error:
            flash(error, "error")
            return redirect(url_for("auth.confirm"))
        elif purpose == "reset":
            session["reset_user_id"] = user_id
            return redirect(url_for("auth.reset"))
        else:
            accounts.mark_verified(user_id)
            login_user(user_id, remember=True)
            flash("E-mail confirmado.", "info")
            return redirect(url_for("main.home"))
    active = accounts.latest_code(user_id, purpose)
    return render_template(
        "auth/confirm.html",
        code=active["code"] if active else "",
        purpose=purpose,
    )


@bp.route("/senha/nova", methods=["GET", "POST"])
def reset():
    user_id = session.get("reset_user_id")
    if not user_id:
        return redirect(url_for("auth.forgot"))
    if request.method == "POST":
        if request.form.get("password") != request.form.get("confirm"):
            flash("As senhas não coincidem.", "error")
            return redirect(url_for("auth.reset"))
        else:
            error = accounts.set_password(user_id, request.form.get("password", ""))
            if error:
                flash(error, "error")
                return redirect(url_for("auth.reset"))
            else:
                session.pop("reset_user_id", None)
                login_user(user_id, remember=True)
                accounts.mark_verified(user_id)
                flash("Senha atualizada.", "info")
                return redirect(url_for("main.home"))
    return render_template("auth/reset.html")


@bp.route("/entrar/google")
def google():
    flash("O login com Google não está configurado neste servidor local.", "info")
    return redirect(url_for("auth.register"))
