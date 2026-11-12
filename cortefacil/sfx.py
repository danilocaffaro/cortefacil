"""Efeitos sonoros dos cortes, sintetizados aqui mesmo (sem arquivos de terceiros nem direitos autorais).

- whoosh: ruído filtrado com varredura de frequência e pan — marca a mudança de enquadramento;
- pop: estalo curto e grave — marca a entrada de títulos e frases de destaque.

Os eventos viram uma única faixa WAV (tempo do vídeo editado) misturada à voz no render.
"""
from __future__ import annotations

import math
import random
import struct
import wave
from array import array
from functools import cache
from pathlib import Path

SR = 48000
LEVELS = {"sutil": 0.35, "marcante": 0.7}
MIN_GAP = 2.5        # no máximo um whoosh a cada 2,5 s: som em todo corte cansa
WHOOSH_LEAD = 0.20   # o pico do whoosh cai em cima do corte


@cache
def whoosh() -> tuple[list[float], list[float]]:
    rnd = random.Random(7)
    n = int(SR * 0.42)
    L, R = [0.0] * n, [0.0] * n
    low = band = 0.0
    for i in range(n):
        x = i / n
        env = math.sin(math.pi * min(1.0, x / 0.55) / 2) ** 2 if x < 0.55 else (1 - (x - 0.55) / 0.45) ** 2.2
        fc = 250 + 3200 * math.sin(math.pi * x) ** 1.5          # sobe e desce: "passa" pela câmera
        f = 2 * math.sin(math.pi * fc / SR)
        noise = rnd.uniform(-1, 1)
        high = noise - low - 0.55 * band                          # filtro de estado variável (passa-faixa)
        band += f * high
        low += f * band
        s = band * env * 0.9
        pan = 0.2 + 0.6 * x                                       # atravessa da esquerda para a direita
        L[i] = s * math.cos(pan * math.pi / 2)
        R[i] = s * math.sin(pan * math.pi / 2)
    peak = max(max(map(abs, L)), max(map(abs, R))) or 1
    return [v / peak * 0.8 for v in L], [v / peak * 0.8 for v in R]


@cache
def pop() -> tuple[list[float], list[float]]:
    n = int(SR * 0.11)
    out, ph = [0.0] * n, 0.0
    for i in range(n):
        t = i / SR
        fr = 180 + 520 * math.exp(-t * 55)                        # queda rápida de afinação
        ph += 2 * math.pi * fr / SR
        env = (1 - math.exp(-t * 900)) * math.exp(-t * 38)
        out[i] = (math.sin(ph) + 0.25 * math.sin(2 * ph)) * env * 0.85
    return out, out


SOUNDS = {"whoosh": whoosh, "pop": pop}


def events(segs, zooms, top, callouts) -> list[tuple[float, str]]:
    """[(t_editado, som)] — whoosh onde o enquadramento muda, pop em títulos e destaques."""
    ev, acc, last = [], 0.0, -99.0
    starts = []
    for (s, e) in segs:
        starts.append(acc)
        acc += e - s
    for i in range(1, len(segs)):
        if abs(zooms[i] - zooms[i - 1]) > 0.01 and starts[i] - last >= MIN_GAP:
            ev.append((max(0.0, starts[i] - WHOOSH_LEAD), "whoosh"))
            last = starts[i]
    for a, _b, _t in list(top) + list(callouts):
        ev.append((max(0.0, a + 0.02), "pop"))
    ev.sort()
    return ev


def build_track(ev, duration: float, path: Path, volume: float) -> Path:
    n = int(SR * (duration + 0.5)) * 2
    pcm = array("h", bytes(2 * n))  # silêncio; só os trechos com som são tocados (rápido em vídeos longos)
    g = volume * 32767
    for t, kind in ev:
        L, R = SOUNDS[kind]()
        o = int(t * SR) * 2
        for j in range(max(0, min(len(L), (n - o) // 2))):
            k = o + 2 * j
            pcm[k] = max(-32767, min(32767, pcm[k] + int(L[j] * g)))
            pcm[k + 1] = max(-32767, min(32767, pcm[k + 1] + int(R[j] * g)))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return path


def wav_bytes(kind: str) -> bytes:
    """Um som isolado (para a pré-visualização no navegador)."""
    L, R = SOUNDS[kind]()
    pcm = array("h", (max(-32767, min(32767, int(v * 32767))) for pair in zip(L, R) for v in pair))
    data = pcm.tobytes()
    head = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack(
        "<IHHIIHH", 16, 1, 2, SR, SR * 4, 4, 16) + b"data" + struct.pack("<I", len(data))
    return head + data
