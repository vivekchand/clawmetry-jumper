"""Film help/import must not depend on macOS system fonts."""
import importlib.util
from pathlib import Path


def test_fonts_are_lazy_and_have_a_portable_fallback(monkeypatch):
    from PIL import ImageFont
    calls = []
    def unavailable(*args, **kwargs):
        calls.append(args)
        raise OSError('No system fonts')
    monkeypatch.setattr(ImageFont, 'truetype', unavailable)
    path = Path(__file__).resolve().parents[1] / 'scripts/build_film.py'
    spec = importlib.util.spec_from_file_location('film_font_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert not calls and not module.FONTS
    marker = object()
    def portable(candidate, size):
        calls.append((candidate, size))
        if candidate == 'DejaVuSans.ttf':
            return marker
        raise OSError('No platform font')
    monkeypatch.setattr(ImageFont, 'truetype', portable)
    assert module.FONTS[32, False] is marker
    assert module.FONTS[32, False] is marker
    assert calls[-1] == ('DejaVuSans.ttf', 32)
    assert len(calls) == 2
