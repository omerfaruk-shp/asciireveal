"""Karakter + renk dizilerini ANSI kaçış dizilerine çevirir."""
from __future__ import annotations

from typing import Callable, Optional, Sequence

import numpy as np

__all__ = ["to_ansi", "make_sgr", "ESC"]

ESC = "\x1b"

Color = Sequence[int]


def make_sgr(use256: bool = False) -> Callable[[Color, Optional[Color]], str]:
    """(ön renk, arka renk) -> SGR kaçış dizisi. Arka renk ``None`` olabilir."""
    if use256:

        def c(v: Color) -> int:
            return 16 + 36 * round(v[0] / 51) + 6 * round(v[1] / 51) + round(v[2] / 51)

        def sgr(f: Color, b: Optional[Color]) -> str:
            s = f"{ESC}[38;5;{c(f)}"
            if b is not None:
                s += f";48;5;{c(b)}"
            return s + "m"

    else:

        def sgr(f: Color, b: Optional[Color]) -> str:
            s = f"{ESC}[38;2;{f[0]};{f[1]};{f[2]}"
            if b is not None:
                s += f";48;2;{b[0]};{b[1]};{b[2]}"
            return s + "m"

    return sgr


def to_ansi(
    chars: np.ndarray,
    colors: np.ndarray,
    *,
    bg: float = 0.45,
    use256: bool = False,
    home: bool = False,
) -> str:
    """Bir kareyi ANSI metnine çevirir.

    ``bg`` > 0 ise her hücrenin arka planı ön rengin ``bg`` katı koyulukta boyanır
    (koyu bölgelerde ayrıntı kaybını önler). ``home=True`` imleci sol üste alır,
    böylece animasyon karelerinin üst üste çizilmesini sağlar.
    """
    sgr = make_sgr(use256)
    chs_l = chars.tolist()
    rgb_a = np.asarray(colors, dtype=np.uint8)
    rgb_l = rgb_a.tolist()
    bg_l = (rgb_a * bg).astype(np.uint8).tolist() if bg and bg > 0 else None

    lines = []
    for y, row in enumerate(chs_l):
        parts, prev = [], None
        crow = rgb_l[y]
        brow = bg_l[y] if bg_l else None
        for x, ch in enumerate(row):
            if ch == " " and brow is None:
                parts.append(" ")
                continue
            col = sgr(crow[x], brow[x] if brow else None)
            if col != prev:
                parts.append(col)
                prev = col
            parts.append(ch)
        lines.append("".join(parts) + f"{ESC}[0m")
    return (f"{ESC}[H" if home else "") + "\n".join(lines)
