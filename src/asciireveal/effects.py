"""Giriş animasyonu efektleri.

Bir efekt, ``(art, rng)`` alıp ``frame(p) -> (chars, colors)`` döndüren bir
fabrikadır; ``p`` 0 (boş) ile 1 (görüntü tamamen açığa çıkmış) arasındadır.

Kendi efektinizi eklemek için::

    import asciireveal as ar

    @ar.register_effect("fade")
    def fade(art, rng):
        def frame(p):
            return art.chars, (art.colors * p).astype("uint8")
        return frame
"""
from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple

import numpy as np

from .core import AsciiArt

__all__ = ["register_effect", "available_effects", "get_effect", "shimmer"]

Frame = Tuple[np.ndarray, np.ndarray]
EffectFactory = Callable[[AsciiArt, np.random.Generator], Callable[[float], Frame]]

_EFFECTS: Dict[str, EffectFactory] = {}
_NOISE = np.array(list("01#@%&*+=<>/\\|{}[]?!$"))


def register_effect(name: str) -> Callable[[EffectFactory], EffectFactory]:
    """Bir efekt fabrikasını ``name`` adıyla kaydeden dekoratör."""

    def deco(fn: EffectFactory) -> EffectFactory:
        _EFFECTS[name] = fn
        return fn

    return deco


def available_effects() -> List[str]:
    return list(_EFFECTS)


def get_effect(name: str) -> EffectFactory:
    try:
        return _EFFECTS[name]
    except KeyError:
        raise ValueError(f"bilinmeyen efekt {name!r}; seçenekler: {available_effects()}") from None


def _noise(rng: np.random.Generator, shape: Tuple[int, int]) -> np.ndarray:
    return _NOISE[rng.integers(0, len(_NOISE), shape)]


@register_effect("resolve")
def _resolve(art: AsciiArt, rng: np.random.Generator):
    """Rastgele karakter gürültüsünden görüntü belirir."""
    h, w = art.height, art.width
    thr = rng.random((h, w))
    dim = (art.colors * 0.35).astype(np.uint8)

    def frame(p: float) -> Frame:
        pending = thr > p
        chs = np.where(pending, _noise(rng, (h, w)), art.chars)
        rgb = np.where(pending[..., None], dim, art.colors)
        flash = (~pending) & (thr > p - 0.06)
        rgb = np.where(flash[..., None], 255, rgb).astype(np.uint8)
        return chs, rgb

    return frame


@register_effect("rain")
def _rain(art: AsciiArt, rng: np.random.Generator):
    """Matrix yağmuru: sütunlar yukarıdan aşağı akarken görüntüyü açığa çıkarır."""
    h, w = art.height, art.width
    start = -rng.random(w) * h * 0.8 - 2
    rows = np.arange(h)[:, None]
    bright = np.array([140, 255, 160], dtype=np.float32)
    ahead_col = np.array([0, 170, 70], dtype=np.uint8)

    def frame(p: float) -> Frame:
        head = start[None, :] + p * (h + 5 - start[None, :])
        d = head - rows
        revealed = d > 0
        chs = np.where(revealed, art.chars, " ")
        k = np.clip(1 - d / 5, 0, 1)[..., None] * revealed[..., None]
        rgb = (art.colors * (1 - k) + bright * k).astype(np.uint8)
        ahead = (~revealed) & (-d < 4)
        chs = np.where(ahead, _noise(rng, (h, w)), chs)
        rgb = np.where(ahead[..., None], ahead_col, rgb).astype(np.uint8)
        return chs, rgb

    return frame


@register_effect("typewriter")
def _typewriter(art: AsciiArt, rng: np.random.Generator):
    """Daktilo: satır satır, soldan sağa yazılır."""
    h, w = art.height, art.width
    flat = np.arange(h * w).reshape(h, w)

    def frame(p: float) -> Frame:
        pos = p * h * w
        rev = flat < pos
        chs = np.where(rev, art.chars, " ")
        rgb = np.where(rev[..., None], art.colors, 0).astype(np.uint8)
        if p < 1:
            cur = (flat >= pos) & (flat < pos + 1)
            chs = np.where(cur, "█", chs)
            rgb = np.where(cur[..., None], 255, rgb).astype(np.uint8)
        return chs, rgb

    return frame


@register_effect("radial")
def _radial(art: AsciiArt, rng: np.random.Generator):
    """Merkezden dışa doğru yayılan parlak halka."""
    h, w = art.height, art.width
    yy, xx = np.mgrid[0:h, 0:w]
    dist = np.hypot((xx - w / 2) / (w / 2), (yy - h / 2) / (h / 2)) / math.sqrt(2)

    def frame(p: float) -> Frame:
        front = p * 1.15
        rev = dist < front
        ring = rev & (dist > front - 0.06)
        chs = np.where(rev, art.chars, " ")
        chs = np.where(ring, _noise(rng, (h, w)), chs)
        rgb = np.where(rev[..., None], art.colors, 0)
        rgb = np.where(ring[..., None], 255, rgb).astype(np.uint8)
        return chs, rgb

    return frame


def shimmer(art: AsciiArt, t: float) -> np.ndarray:
    """Animasyon bittikten sonra görüntünün üzerinden geçen parlak şerit (renk dizisi)."""
    h, w = art.height, art.width
    yy, xx = np.mgrid[0:h, 0:w]
    u = xx / w * 0.75 + yy / h * 0.25
    c = (t * 0.30) % 1.6 - 0.3
    k = np.exp(-(((u - c) / 0.06) ** 2))[..., None]
    out = art.colors.astype(np.float32) * (1 + 0.8 * k) + 70 * k
    return np.clip(out, 0, 255).astype(np.uint8)
