const root = document.querySelector("#mesa");
if (root) {
  const matchId = root.dataset.match;
  const csrf = document.querySelector('meta[name="csrf"]').content;
  const soundOn = root.dataset.sound === "1";
  const slots = { "1": document.querySelector("#p1"), "2": document.querySelector("#p2") };
  const chatToggle = document.querySelector("#chat-toggle");
  const chatDrawer = document.querySelector("#chat-drawer");
  chatToggle.addEventListener("click", () => {
    chatDrawer.hidden = !chatDrawer.hidden;
    chatToggle.setAttribute("aria-expanded", String(!chatDrawer.hidden));
  });
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

  const timer = document.querySelector("#timer");
  const leaveForm = document.querySelector("[data-leave]");
  let deadline = null;
  leaveForm.addEventListener("submit", (event) => {
    const text = snapshot && snapshot.mode === "ai"
      ? "Sair da partida? Ela termina como derrota."
      : "Sair da partida? Você perde e o adversário vence.";
    if (!window.confirm(text)) event.preventDefault();
  });
  window.setInterval(() => {
    if (deadline == null) return;
    const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
    timer.textContent = `⏱ ${left}s`;
    timer.classList.toggle("low", left <= 10);
  }, 250);
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

  function half(part) {
    const node = document.createElement("div");
    node.className = `half ${part.kind}${part.fn != null ? ` fn-${part.fn}` : ""}`;
    const main = document.createElement(part.kind === "funcao" ? "pre" : "span");
    main.className = part.kind === "funcao" ? "struct" : "fname";
    main.textContent = part.text;
    node.append(main);
    if (part.hint) {
      const tip = document.createElement("small");
      tip.className = "hint";
      tip.textContent = part.hint;
      node.append(tip);
    }
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
    if (tile.a.mate) button.title = `Liga com ${tile.a.mate} ou ${tile.b.mate}`;
    button.append(half(tile.a), half(tile.b));
    return button;
  }

  function paint(data) {
    snapshot = data;
    deadline = data.seconds_left != null ? Date.now() + data.seconds_left * 1000 : null;
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
    if (data.your_turn && data.must_carroca) {
      turn.textContent = "Abra com uma carroça (nome e função da mesma família).";
    } else if (data.your_turn) {
      turn.textContent = data.board.length ? "Sua vez de ligar" : "Sua vez de abrir a mesa";
    } else {
      turn.textContent = `Vez de ${data.names[other]}`;
    }
    turn.classList.toggle("them", !data.your_turn);
    drawPlayers(data);
    chain.innerHTML = "";
    const legal = new Map(data.legal.map((item) => [item.tile_id, item.sides]));
    const chosen = selected != null ? (data.hints ? legal.get(selected) : ["left", "right"]) : null;
    if (!data.board.length) {
      const empty = document.createElement("p");
      empty.className = "empty-board";
      empty.textContent = data.your_turn
        ? "A mesa está vazia. A primeira peça abre as duas funções."
        : "A outra ponta abre a mesa.";
      chain.append(empty);
      if (selected != null) chain.append(endButton("center"));
    } else {
      if (chosen && chosen.includes("left")) chain.append(endButton("left"));
      let landedNode = null;
      data.board.forEach((tile) => {
        const button = piece(tile, true);
        if (tile.id === landedId) {
          button.classList.add("landed");
          landedNode = button;
        }
        chain.append(button);
      });
      if (chosen && chosen.includes("right")) chain.append(endButton("right"));
      if (landedNode) window.requestAnimationFrame(() => landedNode.scrollIntoView({ block: "nearest", inline: "nearest" }));
    }
    hand.innerHTML = "";
    data.your_hand.forEach((tile) => {
      const button = piece(tile, false);
      const sides = data.hints ? legal.get(tile.id) : null;
      if (!data.your_turn || (data.hints && !sides)) button.classList.add("dim");
      else if (data.hints) button.classList.add("playable");
      if (tile.id === selected) button.classList.add("selected");
      button.draggable = data.your_turn;
      button.addEventListener("dragstart", (event) => {
        event.dataTransfer.setData("text/plain", String(tile.id));
      });
      button.addEventListener("click", () => choose(tile.id, sides, data));
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
    ["1", "2"].forEach((slot) => {
      slots[slot].innerHTML = "";
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
      meta.textContent = `${data.scores[slot]} pts · ${data.pieces[slot]} pç`;
      who.append(name, meta);
      card.append(mark, who);
      slots[slot].append(card);
    });
  }

  function endButton(side) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "end";
    const labels = { left: "Ligar à esquerda", right: "Ligar à direita", center: "Abrir a mesa" };
    button.setAttribute("aria-label", labels[side]);
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "icon");
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", `${root.dataset.icons}#${side === "left" ? "chevron-left" : "chevron-right"}`);
    svg.append(use);
    const label = document.createElement("span");
    label.textContent = { left: "ESQ", right: "DIR", center: "MESA" }[side];
    button.append(svg, label);
    button.addEventListener("click", () => send("play", { tile_id: selected, side }));
    return button;
  }

  function choose(tileId, sides, data) {
    if (!data.your_turn) return;
    if (data.hints && !sides) {
      showToast("Essa peça não encaixa agora.");
      return;
    }
    if (data.hints && sides.length === 1) {
      selected = null;
      send("play", { tile_id: tileId, side: sides[0] });
      return;
    }
    selected = tileId;
    paint(snapshot);
  }

  chain.addEventListener("dragover", (event) => event.preventDefault());
  chain.addEventListener("drop", (event) => {
    event.preventDefault();
    const tileId = Number(event.dataTransfer.getData("text/plain"));
    if (Number.isNaN(tileId) || !snapshot || !snapshot.your_turn) return;
    const box = chain.getBoundingClientRect();
    let side = event.clientX - box.left < box.width / 2 ? "left" : "right";
    if (!snapshot.board.length) side = "center";
    selected = null;
    send("play", { tile_id: tileId, side });
  });

  window.setInterval(() => {
    if (!busy) pull().catch(() => showToast("Sem conexão."));
  }, 1200);
  pull().catch(() => showToast("Sem conexão."));
}
