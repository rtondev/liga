"""Persistência das partidas. A mesa em si mora no motor, não no SQL."""

from __future__ import annotations

import json
import secrets
import threading
from copy import deepcopy

from liga.db import get_db, transaction, utc_now
from liga.game.chemistry import FUNCTIONS
from liga.game.engine import describe, draw, legal_moves, new_state, pass_turn, play, pips

_guard = threading.Lock()
_locks: dict[int, threading.Lock] = {}
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _mutex(match_id: int) -> threading.Lock:
    with _guard:
        if match_id not in _locks:
            _locks[match_id] = threading.Lock()
        return _locks[match_id]


def dump_state(state: dict) -> str:
    raw = deepcopy(state)
    raw["tiles"] = {str(key): value for key, value in raw["tiles"].items()}
    return json.dumps(raw, ensure_ascii=False)


def load_state(text: str | None) -> dict | None:
    if not text:
        return None
    raw = json.loads(text)
    raw["tiles"] = {int(key): value for key, value in raw["tiles"].items()}
    return raw


def create_ai(user_id: int, hand_size: int, difficulty: str) -> int:
    if difficulty not in ("facil", "medio", "dificil"):
        difficulty = "facil"
    state = new_state(hand_size)
    if state["turn"] == 2:
        from liga.game.ai import run_ai_turn

        run_ai_turn(state, difficulty, 2)
    with transaction() as db:
        cursor = db.execute(
            """
            INSERT INTO matches (
                mode, difficulty, hand_size, status, player1_id, state_json, created_at
            ) VALUES ('ai', ?, ?, 'playing', ?, ?, ?)
            """,
            (difficulty, hand_size, user_id, dump_state(state), utc_now()),
        )
        match_id = cursor.lastrowid
        _store_finish(db, match_id, state)
    return match_id


def create_room(user_id: int, hand_size: int) -> tuple[int, str]:
    code = _unique_code()
    with transaction() as db:
        cursor = db.execute(
            """
            INSERT INTO matches (
                mode, hand_size, status, room_code, player1_id, created_at
            ) VALUES ('online', ?, 'waiting', ?, ?, ?)
            """,
            (hand_size, code, user_id, utc_now()),
        )
        return cursor.lastrowid, code


def join_room(user_id: int, code: str):
    cleaned = (code or "").strip().upper()
    with transaction() as db:
        match = db.execute(
            "SELECT * FROM matches WHERE room_code = ?",
            (cleaned,),
        ).fetchone()
        if match is None:
            return None, "Sala não encontrada."
        if match["player1_id"] == user_id:
            return match["id"], None
        if match["player2_id"] and match["player2_id"] != user_id:
            return None, "Essa sala já está completa."
        if match["player2_id"] == user_id:
            return match["id"], None
        if match["status"] != "waiting":
            return None, "Essa partida já começou."
        state = new_state(match["hand_size"])
        db.execute(
            """
            UPDATE matches
            SET player2_id = ?, status = 'playing', state_json = ?
            WHERE id = ? AND status = 'waiting'
            """,
            (user_id, dump_state(state), match["id"]),
        )
        return match["id"], None


def get_match(match_id: int):
    return get_db().execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()


def slot_of(match, user_id: int) -> int | None:
    if match["player1_id"] == user_id:
        return 1
    if match["player2_id"] == user_id:
        return 2
    return None


def open_matches(user_id: int):
    return get_db().execute(
        """
        SELECT * FROM matches
        WHERE status IN ('waiting', 'playing')
          AND (player1_id = ? OR player2_id = ?)
        ORDER BY id DESC
        """,
        (user_id, user_id),
    ).fetchall()


def player_names(match) -> dict[int, str]:
    from liga.services.accounts import user_by_id

    first = user_by_id(match["player1_id"])
    names = {1: first["display_name"] if first else "Jogador 1"}
    if match["mode"] == "ai":
        names[2] = "Liga IA"
    else:
        second = user_by_id(match["player2_id"]) if match["player2_id"] else None
        names[2] = second["display_name"] if second else "Jogador 2"
    return names


def view_for(match_id: int, user_id: int) -> tuple[dict | None, str | None]:
    with _mutex(match_id):
        with transaction() as db:
            match = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
            if match is None:
                return None, "Partida não encontrada."
            viewer = slot_of(match, user_id)
            if viewer is None:
                return None, "Essa mesa não é sua."
            if match["status"] == "waiting":
                return {"status": "waiting", "match_id": match_id, "room_code": match["room_code"]}, None
            state = load_state(match["state_json"])
            if match["mode"] == "ai" and state["status"] == "playing" and state["turn"] == 2:
                from liga.game.ai import run_ai_turn

                run_ai_turn(state, match["difficulty"] or "facil", 2)
                _save(db, match_id, state)
            names = _names_in(db, match)
            return _public(match, state, viewer, names), None


def action(match_id: int, user_id: int, kind: str, tile_id=None, side=None):
    with _mutex(match_id):
        with transaction() as db:
            match = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
            if match is None:
                return None, "Partida não encontrada."
            viewer = slot_of(match, user_id)
            if viewer is None:
                return None, "Essa mesa não é sua."
            if match["status"] != "playing":
                return None, "Essa partida não está em jogo."
            state = load_state(match["state_json"])
            if kind == "play":
                ok, error = play(state, viewer, int(tile_id), side or "")
            elif kind == "draw":
                ok, error = draw(state, viewer)
            elif kind == "pass":
                ok, error = pass_turn(state, viewer)
            else:
                return None, "Ação desconhecida."
            if not ok:
                return None, error
            detail = json.dumps({"tile_id": tile_id, "side": side}, ensure_ascii=False)
            db.execute(
                """
                INSERT INTO moves (match_id, player_slot, action, detail, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (match_id, viewer, kind, detail, utc_now()),
            )
            if match["mode"] == "ai" and state["status"] == "playing" and state["turn"] == 2:
                from liga.game.ai import run_ai_turn

                run_ai_turn(state, match["difficulty"] or "facil", 2)
            _save(db, match_id, state)
            names = _names_in(db, match)
            return _public(match, state, viewer, names), None


def _save(db, match_id: int, state: dict) -> None:
    db.execute(
        "UPDATE matches SET state_json = ?, status = ? WHERE id = ?",
        (dump_state(state), state["status"], match_id),
    )
    _store_finish(db, match_id, state)


def _store_finish(db, match_id: int, state: dict) -> None:
    if state["status"] != "finished":
        return
    row = db.execute("SELECT * FROM matches WHERE id = ?", (match_id,)).fetchone()
    end = state["end"]
    db.execute(
        """
        UPDATE matches
        SET status = 'finished', winner_slot = ?, p1_points = ?, p2_points = ?,
            p1_pips = ?, p2_pips = ?, finished_at = COALESCE(finished_at, ?)
        WHERE id = ?
        """,
        (
            end["winner"],
            end["points"]["1"],
            end["points"]["2"],
            end["pips"]["1"],
            end["pips"]["2"],
            utc_now(),
            match_id,
        ),
    )
    if row["stats_applied"]:
        return
    _award(db, row["player1_id"], slot=1, end=end)
    if row["player2_id"]:
        _award(db, row["player2_id"], slot=2, end=end)
    db.execute("UPDATE matches SET stats_applied = 1 WHERE id = ?", (match_id,))


def _award(db, user_id: int, slot: int, end: dict) -> None:
    winner = end["winner"]
    gained = end["points"][str(slot)]
    if winner == 0:
        column = "draws"
    elif winner == slot:
        column = "wins"
    else:
        column = "losses"
    db.execute(
        f"UPDATE users SET {column} = {column} + 1, points = points + ? WHERE id = ?",
        (gained, user_id),
    )


def _names_in(db, match) -> dict[int, str]:
    first = db.execute("SELECT display_name FROM users WHERE id = ?", (match["player1_id"],)).fetchone()
    names = {1: first["display_name"] if first else "Jogador 1"}
    if match["mode"] == "ai":
        names[2] = "Liga IA"
        return names
    if match["player2_id"]:
        second = db.execute(
            "SELECT display_name FROM users WHERE id = ?",
            (match["player2_id"],),
        ).fetchone()
        names[2] = second["display_name"] if second else "Jogador 2"
    else:
        names[2] = "Jogador 2"
    return names


def _face(state: dict, tile_id: int, left: int | None = None, right: int | None = None) -> dict:
    tile = state["tiles"][tile_id]
    a = tile["a"] if left is None else left
    b = tile["b"] if right is None else right
    return {
        "id": tile_id,
        "a": a,
        "b": b,
        "a_name": FUNCTIONS[a]["tile"],
        "b_name": FUNCTIONS[b]["tile"],
        "a_struct": FUNCTIONS[a]["struct"],
        "b_struct": FUNCTIONS[b]["struct"],
        "a_full": FUNCTIONS[a]["name"],
        "b_full": FUNCTIONS[b]["name"],
    }


def _public(match, state: dict, viewer: int, names: dict[int, str]) -> dict:
    your_moves = legal_moves(state, viewer) if state["status"] == "playing" else []
    log = []
    for item in state["log"]:
        log.append(describe(item | {"seq": 0}, viewer, names))
    return {
        "ok": True,
        "match_id": match["id"],
        "mode": match["mode"],
        "status": state["status"],
        "you": viewer,
        "turn": state["turn"],
        "your_turn": state["status"] == "playing" and state["turn"] == viewer,
        "your_hand": [_face(state, tile_id) for tile_id in state["hands"][str(viewer)]],
        "board": [
            _face(state, item["id"], item["left"], item["right"]) for item in state["board"]
        ],
        "boneyard": len(state["boneyard"]),
        "pieces": {"1": len(state["hands"]["1"]), "2": len(state["hands"]["2"])},
        "scores": state["scores"],
        "pips": {"1": pips(state, 1), "2": pips(state, 2)} if state["status"] == "finished" else None,
        "legal": your_moves,
        "opening_id": state["opening_id"] if not state["board"] else None,
        "names": {"1": names[1], "2": names[2]},
        "seq": state["seq"],
        "message": describe(state["last"], viewer, names),
        "log": [line for line in log if line],
        "end": state["end"],
        "can_draw": state["status"] == "playing"
        and state["turn"] == viewer
        and not your_moves
        and bool(state["boneyard"]),
        "can_pass": state["status"] == "playing"
        and state["turn"] == viewer
        and not your_moves
        and not state["boneyard"],
    }


def _unique_code() -> str:
    db = get_db()
    for _ in range(20):
        code = "".join(secrets.choice(ALPHABET) for _ in range(6))
        if db.execute("SELECT 1 FROM matches WHERE room_code = ?", (code,)).fetchone() is None:
            return code
    return "".join(secrets.choice(ALPHABET) for _ in range(8))
