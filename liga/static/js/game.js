const root = document.querySelector("#mesa");
if (root) {
  const matchId = root.dataset.match;
  const csrf = document.querySelector('meta[name="csrf"]').content;
  const soundOn = root.dataset.sound === "1";
  const players = document.querySelector("#players");
  const chain = document.querySelector("#chain");
  const hand = document.querySelector("#hand");
  const bone = document.querySelector("#bone");
  const turn = document.querySelector("#turn");
  const log = document.querySelector("#log");
  const toast = document.querySelector("#toast");
  const announce = document.querySelector("#announce");
  const chatLive = document.querySelector("#chat-live");
  const phrases = document.querySelector("#phrases");
  const emojis = document.querySelector("#emojis");
  const drawButton = document.querySelector("#draw");
  const passButton = document.querySelector("#pass");
  let seen = null;
  let seenChat = null;
  let selected = null;
  let busy = false;
  let snapshot = null;
  let audioCtx = null;
  let reactsReady = false;

  drawButton.addEventListener("click", () => send("draw"));
  passButton.addEventListener("click", () => send("pass"));

  document.addEventListener("pointerdown", () => {
    if (!soundOn) return;
    if (!audioCtx) audioCtx = new AudioContext();
    if (audioCtx.state === "suspended") audioCtx.resume();
  }, { once: true });

  function tone(notes, volume) {
    if (!soundOn) return;
    if (!audioCtx) audioCtx = new AudioContext();
    if (audioCtx.state === "suspended") audioCtx.resume();
    notes.forEach((freq, index) => {
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      const start = audioCtx.currentTime + index * 0.14;
      osc.type = notes.length > 1 ? "triangle" : "sine";
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(volume, start + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.34);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start(start);
      osc.stop(start + 0.36);
    });
  }

  function showToast(text) {
    if (!text) return;
    toast.textContent = text;
    toast.style.display = "block";
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => {
      toast.style.display = "none";
    }, 2200);
  }

  async function send(action, extra = {}) {
    if (busy) return;
    busy = true;
    try {
      const response = await fetch(`/partida/${matchId}/jogar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF": csrf,
          Accept: "application/json",
        },
        body: JSON.stringify({ action, csrf, ...extra }),
      });
      const data = await response.json();
      if (!data.ok) {
        showToast(data.error || "Não deu para jogar.");
        await pull();
        return;
      }
      tone([620], 0.08);
      selected = null;
      paint(data);
    } catch (_error) {
      showToast("Sem conexão.");
    } finally {
      busy = false;
    }
  }

  async function pull() {
    const response = await fetch(`/partida/${matchId}/estado`, {
      headers: { Accept: "application/json" },
    });
    const data = await response.json();
    if (data.ok) paint(data);
  }

  function half(value, name, struct) {
    const node = document.createElement("div");
    node.className = `half fn-${value}`;
    const formula = document.createElement("pre");
    formula.className = "struct";
    formula.textContent = struct;
    const label = document.createElement("span");
    label.className = "fname";
    label.textContent = name;
    node.append(formula, label);
    return node;
  }

  async function react(body) {
    try {
      const response = await fetch(`/partida/${matchId}/falar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRF": csrf,
          Accept: "application/json",
        },
        body: JSON.stringify({ body, csrf }),
      });
      const data = await response.json();
      if (!data.ok) {
        showToast(data.error || "Não deu para enviar.");
        return;
      }
      paint(data);
    } catch (_error) {
      showToast("Sem conexão.");
    }
  }

  function piece(tile, flat) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = flat ? "domino flat" : "domino";
    button.title = `${tile.a_full} / ${tile.b_full}`;
    button.append(half(tile.a, tile.a_name, tile.a_struct), half(tile.b, tile.b_name, tile.b_struct));
    return button;
  }

  function paint(data) {
    snapshot = data;
    if (data.status === "finished") {
      window.location.href = data.result_url;
      return;
    }
    const fresh = seen !== null && data.seq !== seen;
    const theirs = fresh && data.last_actor !== data.you;
    if (seen === null) seen = data.seq;
    else if (fresh) {
      if (theirs && data.message) {
        announce.textContent = data.message;
        announce.hidden = false;
        window.clearTimeout(announce.timer);
        announce.timer = window.setTimeout(() => {
          announce.hidden = true;
        }, 2800);
        tone([523, 659, 784], 0.16);
      }
      seen = data.seq;
    }
    const landedId = fresh ? data.last_tile : null;
    bone.textContent = data.boneyard;
    const other = data.you === 1 ? "2" : "1";
    if (data.your_turn && !data.board.length && data.opening_id) {
      turn.textContent = "Abra com a dupla mais alta.";
    } else if (data.your_turn) {
      turn.textContent = data.board.length ? "Sua vez de ligar" : "Sua vez de abrir a mesa";
    } else {
      turn.textContent = `Vez de ${data.names[other]}`;
    }
    turn.classList.toggle("them", !data.your_turn);
    drawPlayers(data);
    chain.innerHTML = "";
    const legal = new Map(data.legal.map((item) => [item.tile_id, item.sides]));
    const chosen = selected != null ? legal.get(selected) : null;
    if (!data.board.length) {
      const empty = document.createElement("p");
      empty.className = "empty-board";
      empty.textContent = data.your_turn
        ? "A mesa está vazia. A primeira peça abre as duas funções."
        : "A outra ponta abre a mesa.";
      chain.append(empty);
    } else {
      if (chosen && chosen.includes("left")) chain.append(endButton("left"));
      data.board.forEach((tile) => {
        const button = piece(tile, true);
        if (tile.id === landedId) {
          button.classList.add("landed");
          window.requestAnimationFrame(() => {
            button.scrollIntoView({ inline: "center", block: "nearest" });
          });
        }
        chain.append(button);
      });
      if (chosen && chosen.includes("right")) chain.append(endButton("right"));
    }
    hand.innerHTML = "";
    data.your_hand.forEach((tile) => {
      const button = piece(tile, false);
      const sides = legal.get(tile.id);
      if (!data.your_turn || !sides) button.classList.add("dim");
      else button.classList.add("playable");
      if (tile.id === selected) button.classList.add("selected");
      button.addEventListener("click", () => choose(tile.id, sides));
      hand.append(button);
    });
    drawButton.disabled = !data.can_draw;
    passButton.disabled = !data.can_pass;
    drawReacts(data);
    noteChat(data);
    log.innerHTML = "";
    data.log.forEach((line) => {
      const row = document.createElement("p");
      row.textContent = line;
      log.append(row);
    });
  }

  function drawReacts(data) {
    if (reactsReady) return;
    reactsReady = true;
    (data.phrases || []).forEach((text) => phrases.append(reactButton(text, text)));
    (data.emojis || []).forEach((text) => emojis.append(reactButton(text, text)));
  }

  function reactButton(label, body) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.addEventListener("click", () => react(body));
    return button;
  }

  function noteChat(data) {
    const items = data.chat || [];
    const last = items[items.length - 1];
    if (!last) return;
    if (seenChat !== null && last.id !== seenChat && !last.you) {
      chatLive.textContent = `${last.name}: ${last.body}`;
      chatLive.hidden = false;
      window.clearTimeout(noteChat.timer);
      noteChat.timer = window.setTimeout(() => {
        chatLive.hidden = true;
      }, 2600);
      tone([880], 0.07);
    }
    seenChat = last.id;
  }

  function drawPlayers(data) {
    players.innerHTML = "";
    ["1", "2"].forEach((slot) => {
      const card = document.createElement("article");
      card.className = `pcard p${slot}${Number(slot) === data.turn ? " active" : ""}`;
      const mark = document.createElement("div");
      mark.className = "mark";
      mark.textContent = data.names[slot].slice(0, 1).toUpperCase();
      const who = document.createElement("div");
      who.className = "who";
      const name = document.createElement("strong");
      name.textContent = data.names[slot];
      const meta = document.createElement("span");
      meta.textContent = `${data.scores[slot]} pontos · ${data.pieces[slot]} peças`;
      who.append(name, meta);
      card.append(mark, who);
      players.append(card);
    });
  }

  function endButton(side) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "end";
    button.setAttribute("aria-label", side === "left" ? "Ligar à esquerda" : "Ligar à direita");
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "icon");
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", `${root.dataset.icons}#${side === "left" ? "chevron-left" : "chevron-right"}`);
    svg.append(use);
    const label = document.createElement("span");
    label.textContent = side === "left" ? "ESQ" : "DIR";
    button.append(svg, label);
    button.addEventListener("click", () => send("play", { tile_id: selected, side }));
    return button;
  }

  function choose(tileId, sides) {
    if (!sides) {
      showToast("Essa peça não encaixa agora.");
      return;
    }
    if (sides.length === 1) {
      selected = null;
      send("play", { tile_id: tileId, side: sides[0] });
      return;
    }
    selected = tileId;
    paint(snapshot);
  }

  window.setInterval(() => {
    if (!busy) pull().catch(() => showToast("Sem conexão."));
  }, 1200);
  pull().catch(() => showToast("Sem conexão."));
}
