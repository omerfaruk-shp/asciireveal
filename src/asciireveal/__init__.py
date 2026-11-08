"""asciireveal: fotoğrafları terminalde animasyonlu, renkli ASCII art'a çevirin.

Hızlı başlangıç::

    import asciireveal as ar

    art = ar.AsciiArt.from_image("foto.jpg", width=160)
    art.play("rain")            # animasyon, Ctrl+C ile çıkış
    print(art.to_ansi())        # ya da tek kare bas
"""
from .core import RAMPS, AsciiArt, autocrop
from .effects import available_effects, register_effect
from .player import frames, play
from .render import to_ansi

__version__ = "0.1.0"

__all__ = [
    "AsciiArt",
    "RAMPS",
    "autocrop",
    "available_effects",
    "register_effect",
    "frames",
    "play",
    "to_ansi",
    "__version__",
]
