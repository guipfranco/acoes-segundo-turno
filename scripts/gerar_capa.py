"""Gera a imagem de compartilhamento (app/capa.png, 1200x630) e o ícone (app/favicon.png, 192x192).

Uso: python scripts/gerar_capa.py
Cores e estilo de app/marca.css (vermelho #fd0000, amarelo #ffd400, vinho #a20301, caixa inclinada com degrau).
Toda a composição cabe no quadrado central de 630x630: o WhatsApp recorta a prévia nesse quadrado, então nada
importante fica nas laterais. Fonte: a primeira que existir na lista FONTES (Windows ou Linux).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

APP = Path(__file__).resolve().parent.parent / "app"
VERMELHO, VINHO, AMARELO, AMARELO_3D, BRANCO, TINTA = "#fd0000", "#a20301", "#ffd400", "#d9b400", "#ffffff", "#141414"
USUARIO = Path.home() / "AppData/Local/Microsoft/Windows/Fonts"
FONTES = [
    USUARIO / "Montserrat-Black.otf",
    USUARIO / "Montserrat-ExtraBold.otf",
    Path("C:/Windows/Fonts/Montserrat-Bold.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def fonte(tam):
    for caminho in FONTES:
        if caminho.exists():
            return ImageFont.truetype(str(caminho), tam)
    return ImageFont.load_default(tam)


def medir(f, texto):
    c = f.getbbox(texto)
    return c[2] - c[0], c[3] - c[1], c[0], c[1]


def texto_centrado(d, texto, f, cy, largura, cor):
    """Escreve `texto` centrado horizontalmente em `largura`, com o centro vertical em `cy`."""
    w, h, dx, dy = medir(f, texto)
    d.text(((largura - w) // 2 - dx, cy - h // 2 - dy), texto, font=f, fill=cor)


def caixa_inclinada(texto, f, fundo, cor, sombra, folga=(44, 28), angulo=-3):
    """Caixa cheia com degrau 3D e texto, girada (RGBA transparente para colar sobre a capa)."""
    w, h, dx, dy = medir(f, texto)
    deg = 12
    cw, ch = w + folga[0] * 2, h + folga[1] * 2
    im = Image.new("RGBA", (cw + deg, ch + deg), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([deg, deg, cw + deg, ch + deg], fill=sombra)
    d.rectangle([0, 0, cw, ch], fill=fundo)
    d.text((folga[0] - dx, folga[1] - dy), texto, font=f, fill=cor)
    return im.rotate(angulo, resample=Image.BICUBIC, expand=True)


def capa():
    w, h = 1200, 630
    im = Image.new("RGBA", (w, h), VERMELHO)
    d = ImageDraw.Draw(im)
    # tudo dentro do quadrado central (x de 285 a 915)
    texto_centrado(d, "ELEJA O", fonte(90), 140, w, BRANCO)
    caixa = caixa_inclinada("LULA", fonte(165), AMARELO, TINTA, VINHO, folga=(40, 22))
    im.alpha_composite(caixa, ((w - caixa.width) // 2, 300 - caixa.height // 2))
    f = fonte(34)
    texto_centrado(d, "Ações do 2º turno", f, 505, w, BRANCO)
    texto_centrado(d, "perto de você", f, 550, w, BRANCO)
    im.convert("RGB").save(APP / "capa.png", optimize=True)


def favicon():
    t = 192
    im = Image.new("RGBA", (t, t), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, t - 1, t - 1], radius=42, fill=VERMELHO)
    f = fonte(140)
    w, h, dx, dy = medir(f, "L")
    d.text(((t - w) // 2 - dx, (t - h) // 2 - dy), "L", font=f, fill=BRANCO)
    im.save(APP / "favicon.png", optimize=True)


if __name__ == "__main__":
    capa()
    favicon()
    print("ok:", APP / "capa.png", APP / "favicon.png")
