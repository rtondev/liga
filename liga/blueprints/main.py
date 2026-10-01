from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for

from liga.art import axolotl_svg
from liga.game.chemistry import RULES
from liga.security import current_user, login_required
from liga.services import accounts

bp = Blueprint("main", __name__)


@bp.route("/")
def home():
    return render_template("main/home.html")


@bp.route("/como-jogar")
def tutorial():
    return render_template("main/tutorial.html", rules=RULES)


@bp.route("/menu")
def menu():
    return render_template("main/menu.html")


@bp.route("/ranking")
def ranking():
    tab = request.args.get("aba", "geral")
    user = current_user()
    pending = []
    if tab == "amigos":
        rows = accounts.friends_ranking(user["id"]) if user else []
        pending = accounts.pending_requests(user["id"]) if user else []
    else:
        tab = "geral"
        rows = accounts.ranking()
    position = accounts.position_of(user["id"]) if user else None
    return render_template(
        "main/ranking.html",
        rows=rows,
        tab=tab,
        position=position,
        pending=pending,
    )


@bp.route("/mascote/<mood>.svg")
def mascot(mood):
    color = request.args.get("cor", "rosa")
    if mood not in {"feliz", "triste", "neutro"}:
        abort(404)
    return Response(axolotl_svg(color, mood), mimetype="image/svg+xml")


@bp.route("/termos")
def terms():
    return render_template("settings/terms.html")


@bp.route("/amigos", methods=["POST"])
@login_required
def add_friend():
    error = accounts.request_friend(current_user()["id"], request.form.get("username", ""))
    flash(error or "Pedido enviado.", "error" if error else "info")
    return redirect(url_for("main.ranking", aba="amigos"))


@bp.route("/amigos/<int:request_id>", methods=["POST"])
@login_required
def answer_friend(request_id):
    error = accounts.respond_friend(
        current_user()["id"],
        request_id,
        request.form.get("aceitar") == "1",
    )
    if error:
        flash(error, "error")
    return redirect(url_for("main.ranking", aba="amigos"))
