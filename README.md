# asciireveal

Turn any photo into **animated, full-color ASCII art** right in your terminal.

Characters carry the texture, while each cell's background is tinted with the pixel's color, so even dark areas (eyelashes, shadows) keep their detail instead of collapsing to black.

```
pip install asciireveal
asciireveal photo.jpg
```

## Command line

```bash
asciireveal photo.jpg                          # default: "resolve" effect, then a shimmer loop
asciireveal photo.jpg --effect rain --width 180
asciireveal photo.jpg --mode bw --ramp detailed
asciireveal photo.jpg --print > art.ansi       # single static frame; `cat art.ansi` to view
asciireveal --list-effects
```

Also works as `python -m asciireveal photo.jpg`. Press **Ctrl+C** to exit; the final frame stays on screen.

| Option | Meaning |
|---|---|
| `--effect` | `resolve`, `rain`, `typewriter`, `radial`, `random` |
| `--width N` | Width in characters (default: terminal width). **Larger = more detail**: shrink your font and try 180+. |
| `--duration S` | Length of the intro animation in seconds (default 4) |
| `--fps N` | Frames per second (default 24). Lower it if your terminal lags. |
| `--mode` | `color` (default), `bw`, `green` |
| `--ramp` | `classic`, `detailed`, `blocks`, or your own string of characters, empty to dense |
| `--bg K` | Cell background darkness, `0` disables (default 0.45) |
| `--256` | Use 256 colors instead of 24-bit truecolor |
| `--no-crop` | Don't auto-crop a flat-colored frame around the photo |
| `--contrast`, `--gamma`, `--lift` | Tone controls |
| `--once` | No shimmer loop after the intro |
| `--print` | Print one static frame and exit |

Requires a terminal with truecolor support (most modern ones: kitty, alacritty, WezTerm, iTerm2, GNOME Terminal, Windows Terminal, ...). Otherwise use `--256`.

## Library

```python
import asciireveal as ar

art = ar.AsciiArt.from_image("photo.jpg", width=160)   # path or PIL.Image
art.play("rain", duration=5)                           # animate in the terminal

print(art.to_ansi())          # one colored frame as a string
print(art.to_text())          # plain text, no colors

# Frames as strings, e.g. to write to a file or stream elsewhere
for frame in ar.frames(art, "radial", duration=3, fps=24):
    ...
```

### Custom effects

An effect is a function `(art, rng) -> frame(p)` where `p` goes from `0` (hidden) to `1` (fully shown), and `frame` returns `(chars, colors)` arrays shaped like `art.chars` and `art.colors`.

```python
import numpy as np
import asciireveal as ar

@ar.register_effect("fade")
def fade(art, rng):
    def frame(p):
        return art.chars, (art.colors * p).astype(np.uint8)
    return frame

ar.AsciiArt.from_image("photo.jpg").play("fade")
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
