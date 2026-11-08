import io
from contextlib import redirect_stdout

import numpy as np
import pytest
from PIL import Image

import asciireveal as ar
from asciireveal import cli
from asciireveal.render import ESC


def make_photo(size=(240, 160)):
    """Renkli gradyan: soldan sağa kırmızı, yukarıdan aşağı mavi."""
    w, h = size
    x = np.linspace(0, 255, w, dtype=np.uint8)[None, :].repeat(h, 0)
    y = np.linspace(0, 255, h, dtype=np.uint8)[:, None].repeat(w, 1)
    return Image.fromarray(np.stack([x, np.full_like(x, 90), y], axis=-1), "RGB")


def make_framed(border=(217, 162, 141)):
    """Düz renkli çerçeve içinde gradyan fotoğraf."""
    canvas = Image.new("RGB", (400, 300), border)
    canvas.paste(make_photo((200, 120)), (100, 90))
    return canvas


@pytest.fixture
def art():
    return ar.AsciiArt.from_image(make_photo(), width=60)


def test_from_image_shapes_and_dtypes(art):
    assert art.width == 60
    assert art.chars.shape == (art.height, 60)
    assert art.colors.shape == (art.height, 60, 3)
    assert art.colors.dtype == np.uint8
    # 240x160 oran 1.5 -> hücre 1:2 düzeltmesiyle yükseklik ~ 60/1.5/2 = 20
    assert abs(art.height - 20) <= 1


def test_accepts_path_and_pil(tmp_path):
    p = tmp_path / "a.png"
    make_photo().save(p)
    a = ar.AsciiArt.from_image(p, width=40)
    b = ar.AsciiArt.from_image(make_photo(), width=40)
    assert a.chars.shape == b.chars.shape


def test_max_height_respected():
    a = ar.AsciiArt.from_image(make_photo((100, 400)), width=80, max_height=20)
    assert a.height == 20
    assert a.width < 80


def test_autocrop_removes_flat_border():
    framed = make_framed()
    cropped = ar.autocrop(framed)
    assert cropped.size[0] < framed.size[0] and cropped.size[1] < framed.size[1]
    # Fotoğraf 200x120; kırpma en fazla birkaç piksel içeri girmeli
    assert 190 <= cropped.size[0] <= 200
    assert 110 <= cropped.size[1] <= 120


def test_autocrop_leaves_borderless_image_alone():
    # Düz çerçevesi olmayan görüntü: boyut korunur
    img = make_photo()
    assert ar.autocrop(img).size == img.size


def test_autocrop_ignores_bad_corner_pixel():
    framed = make_framed()
    framed.putpixel((0, 0), (30, 5, 0))  # JPEG artefaktı gibi tek koyu piksel
    cropped = ar.autocrop(framed)
    assert cropped.size[0] < 250


def test_modes_and_ramps():
    for mode in ("color", "bw", "green"):
        a = ar.AsciiArt.from_image(make_photo(), width=30, mode=mode)
        assert a.colors.shape[-1] == 3
    a = ar.AsciiArt.from_image(make_photo(), width=30, ramp="ab")
    assert set(np.unique(a.chars)) <= {"a", "b"}
    with pytest.raises(ValueError):
        ar.AsciiArt.from_image(make_photo(), width=30, mode="neon")
    with pytest.raises(ValueError):
        ar.AsciiArt.from_image(make_photo(), width=30, ramp="x")


def test_to_text(art):
    lines = art.to_text().split("\n")
    assert len(lines) == art.height
    assert all(len(line) == art.width for line in lines)


def test_to_ansi(art):
    s = art.to_ansi()
    assert s.count("\n") == art.height - 1
    # Ön ve arka renk tek bir SGR dizisinde birleşir: ESC[38;2;r;g;b;48;2;r;g;bm
    assert f"{ESC}[38;2;" in s and ";48;2;" in s
    assert ";48;" not in art.to_ansi(bg=0)
    assert f"{ESC}[38;5;" in art.to_ansi(use256=True) and ";48;5;" in art.to_ansi(use256=True)
    assert f"{ESC}[38;2;" not in art.to_ansi(use256=True)


@pytest.mark.parametrize("name", ["resolve", "rain", "typewriter", "radial"])
def test_effects_frames(art, name):
    fx = ar.effects.get_effect(name)(art, np.random.default_rng(0))
    for p in (0.0, 0.3, 0.7, 1.0):
        chs, rgb = fx(p)
        assert chs.shape == art.chars.shape
        assert rgb.shape == art.colors.shape and rgb.dtype == np.uint8
    # Son karede tüm görüntü açığa çıkmış olmalı
    chs, _ = fx(1.0)
    assert (chs == art.chars).all()
    # İlk karede görüntü henüz görünmemeli
    chs0, _ = fx(0.0)
    assert (chs0 != art.chars).any()


def test_available_effects_and_unknown():
    assert {"resolve", "rain", "typewriter", "radial"} <= set(ar.available_effects())
    with pytest.raises(ValueError):
        ar.effects.get_effect("yok-boyle-bir-sey")


def test_register_custom_effect(art):
    @ar.register_effect("fade-test")
    def fade(a, rng):
        return lambda p: (a.chars, (a.colors * p).astype(np.uint8))

    assert "fade-test" in ar.available_effects()
    out = list(ar.frames(art, "fade-test", duration=0.1, fps=10, seed=1))
    assert len(out) == 2  # n=1 -> kareler p=0 ve p=1


def test_frames_generator(art):
    out = list(ar.frames(art, "resolve", duration=0.5, fps=10, seed=3))
    assert len(out) == 6
    assert all(f.startswith(f"{ESC}[H") for f in out)
    # Aynı seed -> aynı kareler
    assert out == list(ar.frames(art, "resolve", duration=0.5, fps=10, seed=3))


def test_play_writes_and_restores_cursor(art):
    buf = io.StringIO()
    art.play("typewriter", duration=0.1, fps=20, loop=False, stream=buf)
    s = buf.getvalue()
    assert s.startswith(f"{ESC}[?25l")  # imleç gizlendi
    assert s.rstrip("\n").endswith(f"{ESC}[?25h")  # imleç geri geldi


def test_play_restores_cursor_on_ctrl_c(art, monkeypatch):
    import asciireveal.player as player

    def boom(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(player.time, "sleep", boom)
    buf = io.StringIO()
    art.play("resolve", duration=5, fps=10, stream=buf)  # KeyboardInterrupt yutulmalı
    assert buf.getvalue().rstrip("\n").endswith(f"{ESC}[?25h")


def test_random_effect(art):
    out = list(ar.frames(art, "random", duration=0.1, fps=10, seed=5))
    assert len(out) == 2


def test_cli_print(tmp_path):
    p = tmp_path / "foto.png"
    make_photo().save(p)
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.main([str(p), "--print", "--width", "40"])
    assert rc == 0
    assert f"{ESC}[38;2;" in buf.getvalue()


def test_cli_missing_file_returns_error(tmp_path, capsys):
    rc = cli.main([str(tmp_path / "yok.png"), "--print"])
    assert rc == 1
    assert "asciireveal:" in capsys.readouterr().err


def test_cli_list_effects(capsys):
    assert cli.main(["--list-effects"]) == 0
    assert "resolve" in capsys.readouterr().out


def test_cli_requires_image(capsys):
    with pytest.raises(SystemExit):
        cli.main([])
