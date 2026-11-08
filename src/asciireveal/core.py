"""Görüntü -> karakter ızgarası dönüşümü."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image, ImageEnhance

__all__ = ["AsciiArt", "RAMPS", "autocrop"]

#: Açıktan koyuya değil, "boştan yoğuna" sıralı karakter setleri.
RAMPS = {
    "classic": " .:-=+*#%@",
    "detailed": " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    "blocks": " ░▒▓█",
}

MODES = ("color", "bw", "green")

ImageSource = Union[str, Path, Image.Image]


def _load(source: ImageSource) -> Image.Image:
    if isinstance(source, Image.Image):
        return source.convert("RGB")
    with Image.open(source) as im:
        return im.convert("RGB")


def autocrop(img: Image.Image, tol: int = 40, inset: int = 2, edge: int = 4) -> Image.Image:
    """Fotoğrafın etrafındaki düz renkli çerçeveyi kırpar.

    Arka plan rengi kenar piksellerinin medyanından bulunur. Tek bozuk piksel ya
    da JPEG kenar çizgisi yanıltmasın diye en dıştaki ``edge`` piksel yok sayılır.
    Çerçeve bulunamazsa görüntü aynen döner.
    """
    a = np.asarray(img.convert("RGB")).astype(np.int16)
    h, w, _ = a.shape
    if h <= 2 * edge + 20 or w <= 2 * edge + 20:
        return img
    core = a[edge : h - edge, edge : w - edge]
    border = np.concatenate([core[0], core[-1], core[:, 0], core[:, -1]])
    bg = np.median(border, axis=0)
    mask = np.abs(core - bg).sum(axis=2) > tol
    rows = np.where(mask.mean(axis=1) > 0.2)[0]
    cols = np.where(mask.mean(axis=0) > 0.2)[0]
    if len(rows) == 0 or len(cols) == 0:
        return img
    ch, cw = mask.shape
    # Yalnızca gerçekten çerçeve bulunan kenarlardan kırp; diğerlerine dokunma.
    y0 = rows.min() + edge + inset if rows.min() > 0 else 0
    y1 = rows.max() + edge + 1 - inset if rows.max() < ch - 1 else h
    x0 = cols.min() + edge + inset if cols.min() > 0 else 0
    x1 = cols.max() + edge + 1 - inset if cols.max() < cw - 1 else w
    if x1 - x0 < 20 or y1 - y0 < 20:
        return img
    if (x0, y0, x1, y1) == (0, 0, w, h):
        return img
    return img.crop((int(x0), int(y0), int(x1), int(y1)))


@dataclass(frozen=True)
class AsciiArt:
    """Karakter ızgarası ve her hücrenin rengi.

    ``chars``  : (yükseklik, genişlik) ``<U1`` dizisi
    ``colors`` : (yükseklik, genişlik, 3) ``uint8`` RGB dizisi
    """

    chars: np.ndarray
    colors: np.ndarray

    @property
    def height(self) -> int:
        return int(self.chars.shape[0])

    @property
    def width(self) -> int:
        return int(self.chars.shape[1])

    @classmethod
    def from_image(
        cls,
        source: ImageSource,
        *,
        width: int | None = None,
        max_height: int | None = None,
        crop: bool = True,
        ramp: str = "classic",
        mode: str = "color",
        contrast: float = 1.1,
        gamma: float = 1.0,
        lift: int = 25,
        char_aspect: float = 0.5,
    ) -> "AsciiArt":
        """Bir görüntüden ``AsciiArt`` üretir.

        Parameters
        ----------
        source : dosya yolu ya da ``PIL.Image.Image``
        width : karakter genişliği. ``None`` ise terminal genişliği kullanılır.
        max_height : en fazla satır sayısı. ``None`` ise ``width`` verilmediyse
            terminal yüksekliği, verildiyse sınırsız.
        crop : düz renkli dış çerçeveyi otomatik kırp.
        ramp : ``RAMPS`` içindeki bir ad ya da kendi karakter diziniz (boştan yoğuna).
        mode : ``"color"``, ``"bw"`` ya da ``"green"``.
        contrast : ön işleme kontrastı (1.0 = değişiklik yok).
        gamma : karakter yoğunluğu eğrisi.
        lift : koyu renkleri aydınlatma miktarı.
        char_aspect : terminal hücresinin en/boy oranı (genelde 0.5).
        """
        if mode not in MODES:
            raise ValueError(f"mode {MODES} değerlerinden biri olmalı, verilen: {mode!r}")
        ramp_chars = RAMPS.get(ramp, ramp)
        if len(ramp_chars) < 2:
            raise ValueError("ramp en az 2 karakter içermeli")

        img = _load(source)
        if crop:
            img = autocrop(img)
        iw, ih = img.size

        if width is None:
            cols, rows = shutil.get_terminal_size((100, 40))
            w = cols
            limit = max_height or max(rows - 2, 10)
        else:
            w = width
            limit = max_height
        h = round(w * ih / iw * char_aspect)
        if limit and h > limit:
            h = limit
            w = round(h * iw / (ih * char_aspect))
        w, h = max(int(w), 10), max(int(h), 5)

        img = img.resize((w, h), Image.Resampling.LANCZOS)
        if contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(contrast)

        rgb = np.asarray(img, dtype=np.uint8)
        lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255.0

        # Histogram germe: karakter yoğunluğu görüntünün kendi aralığını tam kullansın.
        lo, hi = np.percentile(lum, [2, 98])
        ln = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1)
        n = len(ramp_chars)
        idx = np.clip(np.round((ln**gamma) * (n - 1)).astype(int), 0, n - 1)
        chars = np.array(list(ramp_chars))[idx]

        if mode == "bw":
            g = np.clip(lum * 255 + lift, 0, 255).astype(np.uint8)
            colors = np.stack([g, g, g], axis=-1)
        elif mode == "green":
            colors = np.stack([lum * 70, 90 + lum * 165, lum * 70 + 10], axis=-1)
            colors = np.clip(colors, 0, 255).astype(np.uint8)
        else:
            colors = np.clip(rgb.astype(np.float32) * 1.15 + lift, 0, 255).astype(np.uint8)
        return cls(chars=chars, colors=colors)

    # -- çıktı yardımcıları -------------------------------------------------
    def to_text(self) -> str:
        """Renksiz, düz metin."""
        return "\n".join("".join(row) for row in self.chars.tolist())

    def to_ansi(self, *, bg: float = 0.45, use256: bool = False) -> str:
        """ANSI renk kodlu metin (``print`` ile terminale basılabilir)."""
        from .render import to_ansi

        return to_ansi(self.chars, self.colors, bg=bg, use256=use256)

    def play(self, effect: str = "resolve", **kwargs) -> None:
        """Animasyonu terminalde oynatır. Bkz. :func:`asciireveal.play`."""
        from .player import play

        play(self, effect, **kwargs)
