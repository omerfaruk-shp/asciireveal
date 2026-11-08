"""Terminalde animasyon oynatma ve kare üretme."""
from __future__ import annotations

import os
import sys
import time
from typing import Iterator, Optional, TextIO

import numpy as np

from .core import AsciiArt
from .effects import available_effects, get_effect, shimmer
from .render import ESC, to_ansi

__all__ = ["play", "frames"]


def _pick(effect: str, rng: np.random.Generator) -> str:
    if effect == "random":
        names = available_effects()
        return names[int(rng.integers(0, len(names)))]
    return effect


def frames(
    art: AsciiArt,
    effect: str = "resolve",
    *,
    duration: float = 4.0,
    fps: int = 24,
    seed: Optional[int] = None,
    bg: float = 0.45,
    use256: bool = False,
) -> Iterator[str]:
    """Giriş animasyonunun karelerini ANSI metni olarak üretir (``home`` kodlu).

    Terminale değil de bir dosyaya/başka bir çıktıya yazmak isteyenler için.
    """
    rng = np.random.default_rng(seed)
    fx = get_effect(_pick(effect, rng))(art, rng)
    n = max(1, round(duration * fps))
    for i in range(n + 1):
        chs, rgb = fx(i / n)
        yield to_ansi(chs, rgb, bg=bg, use256=use256, home=True)


def play(
    art: AsciiArt,
    effect: str = "resolve",
    *,
    duration: float = 4.0,
    fps: int = 24,
    loop: bool = True,
    bg: float = 0.45,
    use256: bool = False,
    seed: Optional[int] = None,
    stream: Optional[TextIO] = None,
) -> None:
    """Animasyonu terminalde oynatır.

    ``loop=True`` ise giriş bittikten sonra Ctrl+C'ye kadar parıltı şeridi gezer.
    Çıkışta son kare ekranda bırakılır ve imleç geri açılır.
    """
    out = stream or sys.stdout
    if os.name == "nt":
        os.system("")  # Windows'ta ANSI desteğini açar
    rng = np.random.default_rng(seed)
    fx = get_effect(_pick(effect, rng))(art, rng)
    dt = 1.0 / max(fps, 1)

    def draw(chs, rgb):
        out.write(to_ansi(chs, rgb, bg=bg, use256=use256, home=True))
        out.flush()

    out.write(f"{ESC}[?25l{ESC}[2J{ESC}[H")
    out.flush()
    try:
        t0 = time.perf_counter()
        while True:
            t = time.perf_counter() - t0
            p = min(t / duration, 1.0) if duration > 0 else 1.0
            draw(*fx(p))
            if p >= 1.0:
                break
            time.sleep(max(0.0, dt - ((time.perf_counter() - t0) - t)))

        if loop:
            t1 = time.perf_counter()
            while True:
                draw(art.chars, shimmer(art, time.perf_counter() - t1))
                time.sleep(dt)
    except KeyboardInterrupt:
        pass
    finally:
        draw(art.chars, art.colors)
        out.write(f"\n{ESC}[0m{ESC}[?25h")
        out.flush()
