"""Gera a imagem de compartilhamento (app/capa.png, 1200x630) e o ícone (app/favicon.png, 192x192).

Uso: python scripts/gerar_capa.py
Cores da marca em app/marca.css (vermelho #fd0000, amarelo #ffd400, vinho #a20301).
Fonte: a primeira que existir na lista FONTES (Windows ou Linux).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

APP = Path(__file__).resolve().parent.parent / "app"
VERMELHO, VINHO, AMARELO, BRANCO = "#fd0000", "#a20301", "#ffd400", "#ffffff"
FONTES = [
    "C:/Windows/Fonts/Montserrat-Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def fonte(tam):
    for caminho in FONTES:
        if Path(caminho).exists():
            return ImageFont.truetype(caminho, tam)
    return ImageFont.load_default(tam)


def centralizado(d, texto, f, y, largura, cor, sombra=None):
    caixa = d.textbbox((0, 0), texto, font=f)
    x = (largura - (caixa[2] - caixa[0])) // 2 - caixa[0]
    if sombra:
        d.text((x + 6, y + 6), texto, font=f, fill=sombra)
    d.text((x, y), texto, font=f, fill=cor)


def capa():
    w, h = 1200, 630
    im = Image.new("RGB", (w, h), VERMELHO)
    d = ImageDraw.Draw(im)
    d.rectangle([0, h - 28, w, h], fill=VINHO)  # faixa de base
    d.rectangle([0, h - 40, w, h - 28], fill=AMARELO)
    centralizado(d, "Eleja o Lula", fonte(190), 150, w, BRANCO, sombra=VINHO)
    centralizado(d, "Ações do 2º turno perto de você", fonte(54), 400, w, BRANCO)
    im.save(APP / "capa.png", optimize=True)


def favicon():
    t = 192
    im = Image.new("RGBA", (t, t), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, t - 1, t - 1], radius=42, fill=VERMELHO)
    f = fonte(140)
    caixa = d.textbbox((0, 0), "L", font=f)
    x = (t - (caixa[2] - caixa[0])) // 2 - caixa[0]
    y = (t - (caixa[3] - caixa[1])) // 2 - caixa[1]
    d.text((x, y), "L", font=f, fill=BRANCO)
    im.save(APP / "favicon.png", optimize=True)


if __name__ == "__main__":
    capa()
    favicon()
    print("ok:", APP / "capa.png", APP / "favicon.png")
