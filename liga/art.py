"""Mascote do Liga!, um axolotl desenhado para as telas de vitória, espera e perfil."""

PALETTE = {
    "rosa": ("#f2a3b3", "#d97890"),
    "lilas": ("#c4b0ee", "#8d74c9"),
    "teal": ("#8fd9cf", "#2f9e94"),
    "sol": ("#f6d27a", "#e0a83a"),
}

MOODS = {"feliz", "triste", "neutro"}


def axolotl_svg(color: str = "rosa", mood: str = "feliz") -> str:
    body, gill = PALETTE.get(color, PALETTE["rosa"])
    if mood not in MOODS:
        mood = "feliz"
    if mood == "triste":
        mouth = "M78 124 Q100 114 122 124"
        eyes = _eyes(sad=True)
    elif mood == "neutro":
        mouth = "M82 120 H118"
        eyes = _eyes(sad=False)
    else:
        mouth = "M76 116 Q100 132 124 116"
        eyes = _eyes(sad=False)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" role="img" aria-label="Axolotl">
  <g fill="none" stroke="{gill}" stroke-width="6" stroke-linecap="round">
    <path d="M46 78 C28 62 26 40 40 34"/>
    <path d="M52 70 C34 50 48 32 62 36"/>
    <path d="M58 66 C52 44 70 30 78 42"/>
    <path d="M154 78 C172 62 174 40 160 34"/>
    <path d="M148 70 C166 50 152 32 138 36"/>
    <path d="M142 66 C148 44 130 30 122 42"/>
  </g>
  <ellipse cx="100" cy="118" rx="58" ry="46" fill="{body}"/>
  <ellipse cx="100" cy="132" rx="36" ry="22" fill="{body}"/>
  {eyes}
  <path d="{mouth}" fill="none" stroke="#5c3b45" stroke-width="4" stroke-linecap="round"/>
  <ellipse cx="70" cy="118" rx="8" ry="5" fill="#e8899a" opacity=".55"/>
  <ellipse cx="130" cy="118" rx="8" ry="5" fill="#e8899a" opacity=".55"/>
</svg>"""


def _eyes(sad: bool) -> str:
    if sad:
        return """<path d="M74 104 Q84 98 94 104" fill="none" stroke="#2c2428" stroke-width="4" stroke-linecap="round"/>
  <path d="M106 104 Q116 98 126 104" fill="none" stroke="#2c2428" stroke-width="4" stroke-linecap="round"/>"""
    return """<circle cx="82" cy="104" r="6" fill="#2c2428"/>
  <circle cx="118" cy="104" r="6" fill="#2c2428"/>
  <circle cx="84" cy="102" r="2" fill="#fff"/>
  <circle cx="120" cy="102" r="2" fill="#fff"/>"""
