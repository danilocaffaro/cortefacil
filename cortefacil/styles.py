"""Estilos de legenda. Compartilhados entre o render (Pillow) e o preview (CSS)."""

from pathlib import Path

_F = Path(__file__).parent / "fonts"
BLACK = str(_F / "Montserrat-Black.ttf")
XBOLD = str(_F / "Montserrat-ExtraBold.ttf")
SEMI = str(_F / "Montserrat-SemiBold.ttf")
ANTON = str(_F / "Anton-Regular.ttf")

# Fontes disponíveis no seletor (todas SIL OFL, embutidas em cortefacil/fonts)
FONTS = {
    "montserrat-black": {"label": "Montserrat Black", "file": "Montserrat-Black.ttf", "css": "Montserrat", "weight": 900},
    "montserrat-xbold": {"label": "Montserrat ExtraBold", "file": "Montserrat-ExtraBold.ttf", "css": "Montserrat", "weight": 800},
    "montserrat-bold": {"label": "Montserrat Bold", "file": "Montserrat-Bold.ttf", "css": "Montserrat", "weight": 700},
    "montserrat-semi": {"label": "Montserrat SemiBold", "file": "Montserrat-SemiBold.ttf", "css": "Montserrat", "weight": 600},
    "poppins-xbold": {"label": "Poppins ExtraBold", "file": "Poppins-ExtraBold.ttf", "css": "Poppins", "weight": 800},
    "poppins-bold": {"label": "Poppins Bold", "file": "Poppins-Bold.ttf", "css": "Poppins", "weight": 700},
    "poppins-medium": {"label": "Poppins Medium (nativa)", "file": "Poppins-Medium.ttf", "css": "Poppins", "weight": 500},
    "poppins-semi": {"label": "Poppins SemiBold", "file": "Poppins-SemiBold.ttf", "css": "Poppins", "weight": 600},
    "anton": {"label": "Anton (condensada)", "file": "Anton-Regular.ttf", "css": "Anton", "weight": 400},
    "bebas": {"label": "Bebas Neue (condensada)", "file": "BebasNeue-Regular.ttf", "css": "Bebas Neue", "weight": 400},
    "archivo-black": {"label": "Archivo Black", "file": "ArchivoBlack-Regular.ttf", "css": "Archivo Black", "weight": 400},
    "lilita": {"label": "Lilita One (arredondada)", "file": "LilitaOne-Regular.ttf", "css": "Lilita One", "weight": 400},
    "dm-serif": {"label": "DM Serif (elegante)", "file": "DMSerifDisplay-Regular.ttf", "css": "DM Serif Display", "weight": 400},
}
ANIMS = {"pop": "Pop (elástico)", "slide": "Subir", "fade": "Aparecer", "none": "Sem animação"}
CUSTOM_KEYS = {"font", "kw_font", "upper", "text", "active", "kw", "box", "stroke", "stroke_color", "max_words",
               "anim", "shadow", "active_mode", "kw_scale"}
TITLE_DEFAULT = {"font": "montserrat-bold", "scale": 1.0, "y": None, "color": "#FFFFFF", "bg": "none"}

STYLES = {
    "nativo": {
        "name": "Nativo", "desc": "Discreto, como o texto do Instagram (da referência)",
        "font_id": "poppins-medium", "kw_font": "poppins-semi", "anim": "fade",
        "size": 50, "upper": False, "max_words": 6, "max_chars": 34,
        "text": "#FFFFFF", "active": "#FFFFFF", "active_mode": "none",
        "kw": "#FFFFFF", "kw_scale": 1.0, "stroke": 0, "stroke_color": "#000000",
        "shadow": True, "pop": False, "y": 0.76,
        "title": {"font": "poppins-medium", "scale": 0.78, "y": 0.19},
        "zoom_mode": "topics",
    },
    "viral": {
        "name": "Viral", "desc": "Palavra a palavra, destaque amarelo",
        "font_id": "montserrat-black", "anim": "pop",
        "size": 86, "upper": True, "max_words": 3, "max_chars": 18,
        "text": "#FFFFFF", "active": "#FFE600", "active_mode": "color",
        "kw": "#2EFF7B", "kw_scale": 1.18, "stroke": 10, "stroke_color": "#000000",
        "shadow": True, "pop": True, "y": 0.68,
    },
    "caixa": {
        "name": "Caixa", "desc": "Palavra atual dentro de um bloco colorido",
        "font_id": "montserrat-xbold", "anim": "pop",
        "size": 76, "upper": True, "max_words": 4, "max_chars": 22,
        "text": "#FFFFFF", "active": "#FFFFFF", "active_mode": "box", "box": "#7B2FF7",
        "kw": "#FFD60A", "kw_scale": 1.1, "stroke": 6, "stroke_color": "#000000",
        "shadow": True, "pop": True, "y": 0.70,
    },
    "clean": {
        "name": "Clean", "desc": "Frases curtas, elegante (estilo da referência)",
        "font_id": "montserrat-semi", "anim": "slide",
        "size": 62, "upper": False, "max_words": 7, "max_chars": 34,
        "text": "#FFFFFF", "active": "#FFFFFF", "active_mode": "none",
        "kw": "#FFE08A", "kw_scale": 1.0, "stroke": 0, "stroke_color": "#000000",
        "shadow": True, "pop": False, "y": 0.74,
    },
    "neon": {
        "name": "Neon", "desc": "Condensada, cores vibrantes",
        "font_id": "anton", "anim": "pop",
        "size": 112, "upper": True, "max_words": 2, "max_chars": 14,
        "text": "#FFFFFF", "active": "#00F0FF", "active_mode": "color",
        "kw": "#FF2BD6", "kw_scale": 1.15, "stroke": 7, "stroke_color": "#000000",
        "shadow": True, "pop": True, "y": 0.62,
    },
    "impacto": {
        "name": "Impacto", "desc": "Uma palavra por vez, gigante",
        "font_id": "anton", "anim": "pop",
        "size": 160, "upper": True, "max_words": 1, "max_chars": 12,
        "text": "#FFFFFF", "active": "#FFFFFF", "active_mode": "none",
        "kw": "#FFE600", "kw_scale": 1.12, "stroke": 11, "stroke_color": "#000000",
        "shadow": True, "pop": True, "y": 0.58,
    },
}

FORMATS = {
    "9:16": (1080, 1920),
    "4:5": (1080, 1350),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
}

PACES = {  # ritmo dos cortes: (pausa máxima mantida, folga antes, folga depois)
    "suave": (0.70, 0.08, 0.18),
    "normal": (0.38, 0.05, 0.12),
    "acelerado": (0.18, 0.03, 0.07),
}

DEFAULT_SETTINGS = {
    "style": "viral",
    "format": "9:16",
    "fit": "crop",          # crop | blur
    "pace": "normal",
    "cut_silence": True,
    "remove_fillers": True,
    "zoom": True,
    "emojis": True,
    "progress_bar": True,
    "captions": True,
    "caption_y": None,      # None = padrão do estilo
    "caption_scale": 1.0,
    "accent": None,         # None = cor do estilo
    "title": "",
    "title_secs": 5,
    "custom": {},           # ajustes finos por cima do estilo (fonte, cores, contorno, animação…)
    "title_font": None,     # None = padrão do estilo
    "title_color": None,
    "title_bg": None,       # none | box (fundo arredondado, como o texto do Instagram)
    "title_y": None,
    "title_scale": None,
    "zoom_mode": None,      # None = padrão do estilo | cuts | topics | off
    "push_in": True,        # aproximação lenta e contínua dentro de cada trecho (Ken Burns)
    "callouts": [],         # frases de destaque: [{"start_id","end_id","text"}]
    "callout_y": 0.78,
    "safe_guides": False,
    "topics": [],           # [{"word_id": int, "text": str}] títulos de tópico no topo
    "llm": "auto",          # auto | claude | codex | none
    "music": None,
    "music_volume": 0.12,
    "enhance": True,        # leve correção de cor + nitidez
}


def resolve_style(settings: dict) -> dict:
    """Estilo efetivo = preset + ajustes do usuário (settings.custom) + cor de destaque legada."""
    base = dict(STYLES.get(settings.get("style"), STYLES["viral"]))
    custom = {k: v for k, v in (settings.get("custom") or {}).items() if k in CUSTOM_KEYS and v is not None}
    acc = settings.get("accent")
    if acc and "active" not in custom and "box" not in custom and "kw" not in custom:
        key = {"color": "active", "box": "box", "none": "kw"}[base["active_mode"]]
        base[key] = acc
    fid = custom.pop("font", None) or base["font_id"]
    base.update(custom)
    f = FONTS.get(fid, FONTS["montserrat-black"])
    base["font_id"] = fid if fid in FONTS else "montserrat-black"
    base["font_file"] = str(_F / f["file"])
    base["css_font"] = f'"{f["css"]}"'
    base["css_weight"] = f["weight"]
    kf = FONTS.get(base.get("kw_font") or "", None)
    base["kw_font_file"] = str(_F / kf["file"]) if kf else base["font_file"]
    base["kw_css_weight"] = kf["weight"] if kf else base["css_weight"]
    base["max_words"] = int(max(1, min(8, base.get("max_words", 3))))
    base["max_chars"] = max(base.get("max_chars", 18), base["max_words"] * 6)
    return base


def resolve_title(settings: dict) -> dict:
    """Aparência do título/tópicos/frases de destaque: ajuste do usuário > padrão do estilo > padrão geral."""
    base = dict(TITLE_DEFAULT)
    base.update(STYLES.get(settings.get("style"), {}).get("title", {}))
    for k in ("font", "scale", "y", "color", "bg"):
        v = settings.get("title_" + k)
        if v is not None:
            base[k] = v
    f = FONTS.get(base["font"], FONTS["montserrat-bold"])
    base["font_file"] = str(_F / f["file"])
    base["css_font"] = f'"{f["css"]}"'
    base["css_weight"] = f["weight"]
    return base


def zoom_mode(settings: dict) -> str:
    if not settings.get("zoom", True):
        return "off"
    return settings.get("zoom_mode") or STYLES.get(settings.get("style"), {}).get("zoom_mode", "cuts")
