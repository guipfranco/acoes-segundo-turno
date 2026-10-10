"""Gera a imagem de compartilhamento (app/capa.png, 1200x630). O favicon é a mão do Comitê, não sai daqui.

Uso: python scripts/gerar_capa.py
Cores do guia do Comitê Popular (app/tokens.css: vermelho #C3090A, amarelo #FBCE02, vinho #8E0607), marca chapada.
Toda a composição cabe no quadrado central de 630x630: o WhatsApp recorta a prévia nesse quadrado, então nada
importante fica nas laterais. Fonte: a primeira que existir na lista FONTES (Windows ou Linux).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

APP = Path(__file__).resolve().parent.parent / "app"
VERMELHO, VINHO, AMARELO, BRANCO, TINTA = "#C3090A", "#8E0607", "#FBCE02", "#ffffff", "#2A2A2A"
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


def caixa_inclinada(texto, f, fundo, cor, folga=(44, 28), angulo=20):
    """Tarja chapada com texto (fundo None: só o texto), girada no sentido anti-horário, pesando para a esquerda
    (RGBA transparente para colar sobre a capa)."""
    w, h, dx, dy = medir(f, texto)
    cw, ch = w + folga[0] * 2, h + folga[1] * 2
    im = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if fundo:
        d.rectangle([0, 0, cw, ch], fill=fundo)
    d.text((folga[0] - dx, folga[1] - dy), texto, font=f, fill=cor)
    return im.rotate(angulo, resample=Image.BICUBIC, expand=True)


def capa():
    w, h = 1200, 630
    im = Image.new("RGBA", (w, h), VERMELHO)
    d = ImageDraw.Draw(im)
    # tudo dentro do quadrado central (x de 285 a 915)
    texto_centrado(d, "AGENDA", fonte(56), 62, w, BRANCO)
    # BORA e LULA no mesmo ângulo, pesando para a esquerda; LULA desce no eixo inclinado (por isso fica mais à direita)
    bora = caixa_inclinada("BORA", fonte(118), None, BRANCO, folga=(30, 14))
    im.alpha_composite(bora, ((w - bora.width) // 2 - 32, 232 - bora.height // 2))
    lula = caixa_inclinada("LULA", fonte(118), AMARELO, TINTA, folga=(30, 14))
    im.alpha_composite(lula, ((w - lula.width) // 2 + 32, 382 - lula.height // 2))
    f = fonte(34)
    texto_centrado(d, "Ações do 2º turno", f, 543, w, BRANCO)
    texto_centrado(d, "perto de você", f, 586, w, BRANCO)
    im.convert("RGB").save(APP / "capa.png", optimize=True)


if __name__ == "__main__":
    capa()
    print("ok:", APP / "capa.png")
