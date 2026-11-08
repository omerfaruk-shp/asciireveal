"""Komut satırı arayüzü: ``asciireveal foto.jpg``."""
from __future__ import annotations

import argparse
import shutil
import sys
from typing import List, Optional

from . import __version__
from .core import RAMPS, AsciiArt
from .effects import available_effects


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="asciireveal",
        description="Fotoğrafı terminalde animasyonlu, renkli ASCII art olarak oynatır.",
    )
    ap.add_argument("image", nargs="?", help="fotoğraf dosyası")
    ap.add_argument("--effect", default="resolve", choices=available_effects() + ["random"],
                    help="giriş efekti (varsayılan: resolve)")
    ap.add_argument("--width", type=int, default=None,
                    help="karakter genişliği (varsayılan: terminal genişliği)")
    ap.add_argument("--duration", type=float, default=4.0, help="giriş animasyonu süresi (sn)")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--bg", type=float, default=0.45,
                    help="arka plan koyuluğu; 0 = arka planı boyama (varsayılan: 0.45)")
    ap.add_argument("--ramp", default="classic",
                    help=f"karakter seti: {', '.join(RAMPS)} ya da kendi karakter diziniz")
    ap.add_argument("--mode", default="color", choices=["color", "bw", "green"])
    ap.add_argument("--256", dest="use256", action="store_true",
                    help="truecolor yoksa 256 renk kullan")
    ap.add_argument("--no-crop", action="store_true", help="düz renkli çerçeveyi kırpma")
    ap.add_argument("--contrast", type=float, default=1.1)
    ap.add_argument("--gamma", type=float, default=1.0, help="karakter yoğunluğu eğrisi")
    ap.add_argument("--lift", type=int, default=25, help="koyu renkleri aydınlatma miktarı")
    ap.add_argument("--once", action="store_true",
                    help="giriş animasyonundan sonra parıltı döngüsü olmasın")
    ap.add_argument("--print", dest="static", action="store_true",
                    help="animasyonsuz, tek kare bas (çıktıyı dosyaya yönlendirebilirsiniz)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--list-effects", action="store_true", help="efektleri listele ve çık")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if args.list_effects:
        print("\n".join(available_effects() + ["random"]))
        return 0
    if not args.image:
        ap.error("fotoğraf dosyası gerekli (ör. asciireveal foto.jpg)")

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    try:
        art = AsciiArt.from_image(
            args.image,
            width=args.width,
            crop=not args.no_crop,
            ramp=args.ramp,
            mode=args.mode,
            contrast=args.contrast,
            gamma=args.gamma,
            lift=args.lift,
        )
    except (OSError, ValueError) as e:
        print(f"asciireveal: {e}", file=sys.stderr)
        return 1

    cols = shutil.get_terminal_size((100, 40)).columns
    if args.width and args.width > cols and sys.stdout.isatty():
        print(
            f"uyarı: --width {args.width} terminal genişliğinden ({cols}) büyük; "
            "satırlar kayabilir. Fontu küçültün ya da pencereyi büyütün.",
            file=sys.stderr,
        )

    if args.static:
        print(art.to_ansi(bg=args.bg, use256=args.use256))
        return 0

    art.play(
        args.effect,
        duration=args.duration,
        fps=args.fps,
        loop=not args.once,
        bg=args.bg,
        use256=args.use256,
        seed=args.seed,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
