"""Três níveis da Liga IA, em cima das mesmas regras da mesa."""

from __future__ import annotations

import random

from liga.game.engine import legal_moves, orient_left, orient_right


def choose_action(state: dict, player: int, difficulty: str) -> tuple[str, dict | None]:
    moves = legal_moves(state, player)
    if moves:
        return "play", _pick(state, player, moves, difficulty)
    if state["boneyard"]:
        return "draw", None
    return "pass", None


def run_ai_turn(state: dict, difficulty: str, slot: int = 2) -> dict:
    from liga.game.engine import draw, pass_turn, play

    guard = 0
    while state["status"] == "playing" and state["turn"] == slot and guard < 40:
        guard += 1
        kind, payload = choose_action(state, slot, difficulty)
        if kind == "play":
            ok, _error = play(state, slot, payload["tile_id"], payload["side"])
        elif kind == "draw":
            ok, _error = draw(state, slot)
        else:
            ok, _error = pass_turn(state, slot)
        if not ok:
            break
    return state


def _pick(state: dict, player: int, moves: list[dict], difficulty: str) -> dict:
    options = [(item["tile_id"], side) for item in moves for side in item["sides"]]
    if difficulty == "facil":
        tile_id, side = random.choice(options)
        return {"tile_id": tile_id, "side": side}

    def rank(option: tuple[int, str]) -> tuple[int, int]:
        tile_id, side = option
        tile = state["tiles"][tile_id]
        pips = tile["a"] + tile["b"]
        weight = 1 if difficulty == "medio" else 5
        follow = _followers(state, player, tile_id, side) * weight
        double = 3 if tile["a"] == tile["b"] else 0
        return pips + follow + double, pips

    tile_id, side = max(options, key=rank)
    return {"tile_id": tile_id, "side": side}


def _followers(state: dict, player: int, tile_id: int, side: str) -> int:
    exposed = _exposed_after(state, tile_id, side)
    total = 0
    for other_id in state["hands"][str(player)]:
        if other_id == tile_id:
            continue
        other = state["tiles"][other_id]
        if other["a"] in exposed or other["b"] in exposed:
            total += 1
    return total


def _exposed_after(state: dict, tile_id: int, side: str) -> set[int]:
    tile = state["tiles"][tile_id]
    if side == "center" or not state["board"]:
        return {tile["a"], tile["b"]}
    if side == "left":
        left, _right = orient_left(tile, state["board"][0]["left"])
        return {left}
    _left, right = orient_right(tile, state["board"][-1]["right"])
    return {right}
