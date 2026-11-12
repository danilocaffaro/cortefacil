"""Heurísticas de linguagem (PT-BR): palavras-chave, emojis e vícios de linguagem."""
import re
import unicodedata

STOPWORDS = set("""
a à as às ao aos o os um uma uns umas de da das do dos dum duma em na nas no nos num numa
por pela pelas pelo pelos para pra pro pros com sem sob sobre entre até após ante contra desde
e ou mas porém nem que se como quando onde porque pois então já ainda só também muito muita
muitos muitas pouco pouca mais menos tão tanto bem mal aqui ali lá isso isto aquilo esse essa
esses essas este esta estes estas aquele aquela aqueles aquelas eu tu ele ela nós vós eles elas
você vocês me te se nos vos lhe lhes meu minha meus minhas teu tua seu sua seus suas nosso nossa
ser é são era foi fui foram sou somos está estão estou estava estar ter tem têm tinha tenho
ir vai vou vamos fazer faz fiz feito ver vi dar dá dei ficar fica fiquei
né tipo assim aí daí gente coisa coisas cara olha sabe sabia vez vezes agora hoje sempre nunca
qual quais quem cujo cuja todo toda todos todas outro outra outros outras mesmo mesma
o que é sim não ok tá ta
""".split())

POWER_WORDS = {
    "segredo", "segredos", "erro", "erros", "errado", "nunca", "sempre", "dinheiro", "grátis",
    "gratuito", "importante", "rápido", "rapidamente", "melhor", "melhores", "pior", "piores",
    "resultado", "resultados", "verdade", "mentira", "atenção", "cuidado", "problema", "solução",
    "simples", "fácil", "difícil", "incrível", "absurdo", "chocante", "ninguém", "todo", "milhões",
    "mil", "lucro", "vender", "vendas", "venda", "cliente", "clientes", "sucesso", "fracasso",
    "paciência", "dica", "dicas", "passo", "método", "estratégia", "hack", "truque", "agora",
    "hoje", "urgente", "proibido", "perigo", "saúde", "beleza", "pele", "corpo", "amor",
    "investir", "investimento", "investimentos", "salário", "economizar", "ganhar", "perder",
    "primeiro", "segundo", "terceiro", "último", "única", "único", "principal", "essencial",
    "comenta", "comente", "salva", "salve", "compartilha", "segue", "siga", "link",
}

EMOJI_MAP = {
    "dinheiro": "💰", "salário": "💰", "lucro": "💰", "investir": "📈", "investimento": "📈",
    "investimentos": "📈", "ganhar": "🤑", "economizar": "🐷", "segredo": "🤫", "segredos": "🤫",
    "erro": "❌", "erros": "❌", "errado": "❌", "erram": "❌", "importante": "⚠️", "atenção": "⚠️",
    "cuidado": "⚠️", "perigo": "🚨", "urgente": "🚨", "nunca": "🚫", "proibido": "🚫",
    "sucesso": "🏆", "resultado": "🎯", "resultados": "🎯", "meta": "🎯", "dica": "💡",
    "dicas": "💡", "ideia": "💡", "simples": "✅", "fácil": "✅", "certo": "✅", "verdade": "✅",
    "rápido": "⚡", "rapidamente": "⚡", "tempo": "⏰", "paciência": "⏳", "amor": "❤️",
    "coração": "❤️", "pele": "✨", "beleza": "✨", "brilho": "✨", "incrível": "🤯",
    "absurdo": "🤯", "chocante": "😱", "medo": "😱", "saúde": "💪", "treino": "💪",
    "força": "💪", "corpo": "💪", "comida": "🍽️", "dormir": "😴", "sono": "😴", "vida": "🌱",
    "crescer": "🚀", "crescimento": "🚀", "vender": "🛒", "vendas": "🛒", "cliente": "🤝",
    "clientes": "🤝", "comenta": "💬", "comente": "💬", "salva": "📌", "salve": "📌",
    "segue": "👉", "siga": "👉", "link": "🔗", "casa": "🏠", "viagem": "✈️", "fogo": "🔥",
    "melhor": "🔥", "top": "🔥", "estratégia": "♟️", "método": "🧠", "cérebro": "🧠",
    "pensar": "🧠", "celular": "📱", "instagram": "📱", "vídeo": "🎬", "procedimento": "💉",
    "procedimentos": "💉", "clínica": "🏥",
}

FILLER_RE = re.compile(r"^(a+h+n*|ã+h*n*|h+[ãa]+|h+u+m+|h+m+|u+m+|é{2,}|e{2,}|ah+|eh+)$", re.I)


def norm(word: str) -> str:
    """Minúsculas, sem pontuação nas pontas."""
    return re.sub(r"^[^\wÀ-ÿ%]+|[^\wÀ-ÿ%]+$", "", word.strip().lower())


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def is_filler(word: str) -> bool:
    return bool(FILLER_RE.match(norm(word)))


def keyword_score(word: str, next_word: str = "") -> float:
    n = norm(word)
    if not n or n in STOPWORDS:
        return 0.0
    score = 0.0
    if re.search(r"\d", n):
        score += 3.0  # números/percentuais prendem atenção
    if n in POWER_WORDS:
        score += 2.5
    if n in EMOJI_MAP:
        score += 1.0
    if len(n) >= 7:
        score += 1.0 + min(len(n) - 7, 5) * 0.15
    if word.strip().endswith("!"):
        score += 1.0
    if word.strip()[:1].isupper() and len(n) > 3:
        score += 0.3
    return score


def pick_keywords(words: list[dict], every: int = 5) -> None:
    """Marca ~1 palavra-chave a cada `every` palavras, escolhendo a de maior pontuação
    dentro de janelas deslizantes (in-place: word['kw'] = True)."""
    i = 0
    n = len(words)
    while i < n:
        window = [w for w in words[i:i + every] if not w.get("removed")]
        if window:
            best = max(window, key=lambda w: keyword_score(w["text"]))
            if keyword_score(best["text"]) >= 2.0:
                best["kw"] = True
        i += every


def emoji_for(word: str) -> str:
    n = norm(word)
    if n in EMOJI_MAP:
        return EMOJI_MAP[n]
    n2 = strip_accents(n)
    for k, v in EMOJI_MAP.items():
        if strip_accents(k) == n2:
            return v
    return ""
