"""Mesa de dominó: distribuição, encaixe, compra, passe e fim de jogo."""

from __future__ import annotations

import random
from copy import deepcopy

from liga.game.chemistry import FUNCTIONS


def new_state(hand_size: int, seed: int | None = None) -> dict:
    if hand_size not in (6, 7, 8):
        raise ValueError("Cada jogador começa com 6, 7 ou 8 peças.")
    rng = random.Random(seed)
    tiles = {}
    order = []
    number = 0
    for left in range(7):
        for right in range(left, 7):
            tiles[number] = {"id": number, "a": left, "b": right}
            order.append(number)
            number += 1
    rng.shuffle(order)
    hands = {
        "1": order[:hand_size],
        "2": order[hand_size : hand_size * 2],
    }
    boneyard = order[hand_size * 2 :]
    starter, opening = _opening(hands, tiles)
    return {
        "tiles": tiles,
        "hands": hands,
        "boneyard": boneyard,
        "board": [],
        "turn": starter,
        "opening_id": opening,
        "status": "playing",
        "scores": {"1": 0, "2": 0},
        "placed": {"1": 0, "2": 0},
        "seq": 0,
        "last": None,
        "log": [],
        "end": None,
    }


def legal_moves(state: dict, player: int) -> list[dict]:
    if state["status"] != "playing" or state["turn"] != player:
        return []
    hand = state["hands"][str(player)]
    if not state["board"]:
        opening = state["opening_id"]
        if opening is not None:
            if opening in hand:
                return [{"tile_id": opening, "sides": ["center"]}]
            return []
        return [{"tile_id": tile_id, "sides": ["center"]} for tile_id in hand]

    left_end = state["board"][0]["left"]
    right_end = state["board"][-1]["right"]
    moves = []
    for tile_id in hand:
        tile = state["tiles"][tile_id]
        sides = []
        if tile["a"] == left_end or tile["b"] == left_end:
            sides.append("left")
        if tile["a"] == right_end or tile["b"] == right_end:
            sides.append("right")
        if sides:
            moves.append({"tile_id": tile_id, "sides": sides})
    return moves


def play(state: dict, player: int, tile_id: int, side: str) -> tuple[bool, str | None]:
    options = {item["tile_id"]: item for item in legal_moves(state, player)}
    if tile_id not in options:
        return False, "Essa peça não encaixa nesta vez."
    sides = options[tile_id]["sides"]
    if side not in sides:
        if len(sides) == 1:
            side = sides[0]
        else:
            return False, "Escolha em qual ponta da mesa ligar."

    tile = state["tiles"][tile_id]
    verb = "play"
    name = ""
    if side == "center":
        placed = {"id": tile_id, "left": tile["a"], "right": tile["b"]}
        state["board"].append(placed)
        if tile["a"] == tile["b"]:
            verb = "open-double"
            name = FUNCTIONS[tile["a"]]["tile"]
        else:
            verb = "open"
            name = f"{FUNCTIONS[tile['a']]['tile']}–{FUNCTIONS[tile['b']]['tile']}"
    elif side == "left":
        end = state["board"][0]["left"]
        left, right = orient_left(tile, end)
        state["board"].insert(0, {"id": tile_id, "left": left, "right": right})
        name = FUNCTIONS[end]["tile"]
    else:
        end = state["board"][-1]["right"]
        left, right = orient_right(tile, end)
        state["board"].append({"id": tile_id, "left": left, "right": right})
        name = FUNCTIONS[end]["tile"]

    slot = str(player)
    state["hands"][slot].remove(tile_id)
    state["opening_id"] = None
    state["scores"][slot] += tile["a"] + tile["b"]
    state["placed"][slot] += 1
    _touch(state, player, verb, name)
    if not state["hands"][slot]:
        _finish(state, player, "vazia")
    else:
        state["turn"] = 2 if player == 1 else 1
    return True, None


def draw(state: dict, player: int) -> tuple[bool, str | None]:
    if state["status"] != "playing" or state["turn"] != player:
        return False, "Ainda não é a sua vez."
    if legal_moves(state, player):
        return False, "Você tem uma jogada. Ligue uma peça."
    if not state["boneyard"]:
        return False, "O cemitério está vazio."
    tile_id = state["boneyard"].pop()
    state["hands"][str(player)].append(tile_id)
    _touch(state, player, "draw", "")
    return True, None


def pass_turn(state: dict, player: int) -> tuple[bool, str | None]:
    if state["status"] != "playing" or state["turn"] != player:
        return False, "Ainda não é a sua vez."
    if legal_moves(state, player):
        return False, "Você tem uma jogada. Ligue uma peça."
    if state["boneyard"]:
        return False, "Ainda há peças no cemitério."
    other = 2 if player == 1 else 1
    _touch(state, player, "pass", "")
    if not legal_moves_for(state, other):
        _finish(state, 0, "travada")
    else:
        state["turn"] = other
    return True, None


def legal_moves_for(state: dict, player: int) -> list[dict]:
    """Jogadas do jogador mesmo fora da vez, usadas para saber se a mesa travou."""
    probe = deepcopy(state)
    probe["status"] = "playing"
    probe["turn"] = player
    return legal_moves(probe, player)


def pips(state: dict, player: int) -> int:
    total = 0
    for tile_id in state["hands"][str(player)]:
        tile = state["tiles"][tile_id]
        total += tile["a"] + tile["b"]
    return total


def orient_left(tile: dict, end: int) -> tuple[int, int]:
    if tile["b"] == end:
        return tile["a"], tile["b"]
    if tile["a"] == end:
        return tile["b"], tile["a"]
    raise ValueError("peça não encaixa à esquerda")


def orient_right(tile: dict, end: int) -> tuple[int, int]:
    if tile["a"] == end:
        return tile["a"], tile["b"]
    if tile["b"] == end:
        return tile["b"], tile["a"]
    raise ValueError("peça não encaixa à direita")


def describe(last: dict | None, viewer: int, names: dict[int, str]) -> str:
    if not last:
        return ""
    actor = last["actor"]
    who = "Você" if actor == viewer else names.get(actor, "Oponente")
    verb = last["verb"]
    name = last.get("name") or ""
    if verb == "play":
        return f"{who} ligou {name} com {name}."
    if verb == "open":
        return f"{who} abriu a mesa com {name}."
    if verb == "open-double":
        return f"{who} abriu com a dupla de {name}."
    if verb == "draw":
        return f"{who} comprou uma peça."
    if verb == "pass":
        return f"{who} passou a vez."
    return ""


def _opening(hands: dict, tiles: dict) -> tuple[int, int | None]:
    double_one = _best_double(hands["1"], tiles)
    double_two = _best_double(hands["2"], tiles)
    if double_one is None and double_two is None:
        return 1, None
    if double_two is None:
        return 1, double_one
    if double_one is None:
        return 2, double_two
    if tiles[double_one]["a"] >= tiles[double_two]["a"]:
        return 1, double_one
    return 2, double_two


def _best_double(hand: list[int], tiles: dict) -> int | None:
    best = None
    for tile_id in hand:
        tile = tiles[tile_id]
        if tile["a"] == tile["b"] and (best is None or tile["a"] > tiles[best]["a"]):
            best = tile_id
    return best


def _touch(state: dict, actor: int, verb: str, name: str) -> None:
    state["seq"] += 1
    state["last"] = {"actor": actor, "verb": verb, "name": name, "seq": state["seq"]}
    state["log"].append({"actor": actor, "verb": verb, "name": name})
    state["log"] = state["log"][-15:]


def _finish(state: dict, winner: int, reason: str) -> None:
    if reason == "travada":
        left = pips(state, 1)
        right = pips(state, 2)
        if left < right:
            winner = 1
        elif right < left:
            winner = 2
        else:
            winner = 0
    state["status"] = "finished"
    state["end"] = {
        "winner": winner,
        "reason": reason,
        "pips": {"1": pips(state, 1), "2": pips(state, 2)},
        "points": dict(state["scores"]),
        "placed": dict(state["placed"]),
    }


def _auto(seed: int, difficulty: str, hand_size: int) -> dict:
    from liga.game.ai import choose_action

    state = new_state(hand_size, seed=seed)
    guard = 0
    while state["status"] == "playing" and guard < 400:
        guard += 1
        player = state["turn"]
        kind, payload = choose_action(state, player, difficulty)
        if kind == "play":
            ok, error = play(state, player, payload["tile_id"], payload["side"])
        elif kind == "draw":
            ok, error = draw(state, player)
        else:
            ok, error = pass_turn(state, player)
        if not ok:
            raise RuntimeError(error or "jogada inválida")
    if state["status"] != "finished":
        raise RuntimeError(f"partida não terminou (seed {seed}, {difficulty})")
    return state


if __name__ == "__main__":
    for difficulty in ("facil", "medio", "dificil"):
        for seed in range(12):
            ended = _auto(seed, difficulty, 7)
            winner = ended["end"]["winner"]
            print(f"{difficulty} seed={seed} vencedor={winner} mesa={len(ended['board'])}")
    print("motor ok")
