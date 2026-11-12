"""Estilos de legenda. Compartilhados entre o render (Pillow) e o preview (CSS)."""

from pathlib import Path

_F = Path(__file__).parent / "fonts"
BLACK = str(_F / "Montserrat-Black.ttf")
XBOLD = str(_F / "Montserrat-ExtraBold.ttf")
SEMI = str(_F / "Montserrat-SemiBold.ttf")
ANTON = str(_F / "Anton-Regular.ttf")

STYLES = {
    "viral": {
        "name": "Viral", "desc": "Palavra a palavra, destaque amarelo",
        "font": [BLACK, 0], "css_font": "Montserrat", "css_weight": 900,
        "size": 86, "upper": True, "max_words": 3, "max_chars": 18,
        "text": "#FFFFFF", "active": "#FFE600", "active_mode": "color",
        "kw": "#2EFF7B", "kw_scale": 1.18, "stroke": 10, "stroke_color": "#000000",
        "shadow": True, "pop": True, "y": 0.68,
    },
    "caixa": {
        "name": "Caixa", "desc": "Palavra atual dentro de um bloco colorido",
        "font": [XBOLD, 0], "css_font": "Montserrat", "css_weight": 800,
        "size": 76, "upper": True, "max_words": 4, "max_chars": 22,
        "text": "#FFFFFF", "active": "#FFFFFF", "active_mode": "box", "box": "#7B2FF7",
        "kw": "#FFD60A", "kw_scale": 1.1, "stroke": 6, "stroke_color": "#000000",
        "shadow": True, "pop": True, "y": 0.70,
    },
    "clean": {
        "name": "Clean", "desc": "Frases curtas, elegante (estilo da referência)",
        "font": [SEMI, 0], "css_font": "Montserrat", "css_weight": 600,
        "size": 62, "upper": False, "max_words": 7, "max_chars": 34,
        "text": "#FFFFFF", "active": "#FFFFFF", "active_mode": "none",
        "kw": "#FFE08A", "kw_scale": 1.0, "stroke": 0, "stroke_color": "#000000",
        "shadow": True, "pop": False, "y": 0.74,
    },
    "neon": {
        "name": "Neon", "desc": "Condensada, cores vibrantes",
        "font": [ANTON, 0], "css_font": "Anton", "css_weight": 400,
        "size": 112, "upper": True, "max_words": 2, "max_chars": 14,
        "text": "#FFFFFF", "active": "#00F0FF", "active_mode": "color",
        "kw": "#FF2BD6", "kw_scale": 1.15, "stroke": 7, "stroke_color": "#000000",
        "shadow": True, "pop": True, "y": 0.62,
    },
    "impacto": {
        "name": "Impacto", "desc": "Uma palavra por vez, gigante",
        "font": [ANTON, 0], "css_font": "Anton", "css_weight": 400,
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
    "topics": [],           # [{"word_id": int, "text": str}] títulos de tópico no topo
    "llm": "auto",          # auto | claude | codex | none
    "music": None,
    "music_volume": 0.12,
    "enhance": True,        # leve correção de cor + nitidez
}
