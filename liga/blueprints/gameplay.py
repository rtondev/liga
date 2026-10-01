from flask import Blueprint, jsonify, redirect, render_template, request, url_for

from liga.security import current_user, verified_required
from liga.services import accounts, matches

bp = Blueprint("play", __name__)


@bp.route("/partida", methods=["GET", "POST"])
@verified_required
def new():
    user = current_user()
    if request.method == "POST" and request.form.get("codigo"):
        match_id, error = matches.join_room(user["id"], request.form.get("codigo", ""))
        if error:
            from flask import flash

            flash(error, "error")
            return redirect(url_for("play.new"))
        match = matches.get_match(match_id)
        if match["status"] == "waiting":
            return redirect(url_for("play.lobby", match_id=match_id))
        return redirect(url_for("play.match", match_id=match_id))
    if request.method == "POST":
        mode = request.form.get("mode", "ai")
        try:
            hand_size = int(request.form.get("hand_size", "6"))
        except ValueError:
            hand_size = 6
        if hand_size not in (6, 7, 8):
            hand_size = 6
        difficulty = request.form.get("difficulty", "facil")
        if mode == "online":
            match_id, _code = matches.create_room(user["id"], hand_size)
            return redirect(url_for("play.lobby", match_id=match_id))
        match_id = matches.create_ai(user["id"], hand_size, difficulty)
        match = matches.get_match(match_id)
        if match["status"] == "finished":
            return redirect(url_for("play.result", match_id=match_id))
        return redirect(url_for("play.match", match_id=match_id))
    return render_template("play/new.html", opens=matches.open_matches(user["id"]))


@bp.route("/sala/<int:match_id>")
@verified_required
def lobby(match_id):
    match = matches.get_match(match_id)
    if match is None or matches.slot_of(match, current_user()["id"]) is None:
        return redirect(url_for("play.new"))
    if match["status"] != "waiting":
        return redirect(url_for("play.match", match_id=match_id))
    return render_template("play/lobby.html", match=match)


@bp.route("/sala/<int:match_id>/estado")
@verified_required
def lobby_state(match_id):
    match = matches.get_match(match_id)
    user = current_user()
    if match is None or matches.slot_of(match, user["id"]) is None:
        return jsonify({"ok": False}), 404
    if match["status"] == "waiting":
        return jsonify({"ok": True, "status": "waiting", "code": match["room_code"]})
    return jsonify(
        {
            "ok": True,
            "status": match["status"],
            "url": url_for("play.match", match_id=match_id),
        }
    )


@bp.route("/partida/<int:match_id>")
@verified_required
def match(match_id):
    row = matches.get_match(match_id)
    if row is None or matches.slot_of(row, current_user()["id"]) is None:
        return redirect(url_for("play.new"))
    if row["status"] == "waiting":
        return redirect(url_for("play.lobby", match_id=match_id))
    if row["status"] == "finished":
        return redirect(url_for("play.result", match_id=match_id))
    return render_template(
        "play/match.html",
        match=row,
        sound=bool(current_user()["sound_on"]),
    )


@bp.route("/partida/<int:match_id>/estado")
@verified_required
def state(match_id):
    payload, error = matches.view_for(match_id, current_user()["id"])
    if error:
        return jsonify({"ok": False, "error": error}), 404
    payload["result_url"] = url_for("play.result", match_id=match_id)
    return jsonify(payload)


@bp.route("/partida/<int:match_id>/jogar", methods=["POST"])
@verified_required
def act(match_id):
    body = request.get_json(silent=True) or {}
    kind = body.get("action")
    raw_tile = body.get("tile_id")
    try:
        tile_id = int(raw_tile) if raw_tile is not None else None
    except (TypeError, ValueError):
        tile_id = None
    payload, error = matches.action(
        match_id,
        current_user()["id"],
        kind,
        tile_id=tile_id,
        side=body.get("side"),
    )
    if error:
        return jsonify({"ok": False, "error": error}), 409
    payload["result_url"] = url_for("play.result", match_id=match_id)
    return jsonify(payload)


@bp.route("/partida/<int:match_id>/fim")
@verified_required
def result(match_id):
    row = matches.get_match(match_id)
    user = current_user()
    if row is None or matches.slot_of(row, user["id"]) is None:
        return redirect(url_for("play.new"))
    if row["status"] != "finished":
        return redirect(url_for("play.match", match_id=match_id))
    viewer = matches.slot_of(row, user["id"])
    names = matches.player_names(row)
    winner = row["winner_slot"]
    if winner == 0:
        mood = "triste"
        title = "Empate!"
        blurb = "Foi quase! Estude mais um pouco."
    elif winner == viewer:
        mood = "feliz"
        title = "Você ganhou!"
        blurb = "Ebaaa! Você ligou as fórmulas direitinho."
    else:
        mood = "triste"
        placed = row["p1_points"] if viewer == 1 else row["p2_points"]
        # placed count is not stored separately; points are pips played.
        state = matches.load_state(row["state_json"])
        count = state["placed"][str(viewer)] if state else 0
        title = "Você perdeu!"
        blurb = f"Aah... Recomendo que estude mais um pouco! Você ligou {count} peças certas!"
    return render_template(
        "play/result.html",
        match=row,
        names=names,
        viewer=viewer,
        mood=mood,
        title=title,
        blurb=blurb,
        winner=winner,
    )
