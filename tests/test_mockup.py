from pathlib import Path
import re

RAIZ = Path(__file__).resolve().parents[1]
HTML = (RAIZ / "mockup" / "index.html").read_text(encoding="utf-8")


def test_tem_as_cinco_telas():
    for nome in ["telaInicio", "telaAcao", "telaCriar", "telaMinhas", "telaFila"]:
        assert f"function {nome}" in HTML, nome


def test_nav_e_doar():
    assert 'id="app"' in HTML
    assert "<nav" in HTML
    assert "Doar" in HTML
