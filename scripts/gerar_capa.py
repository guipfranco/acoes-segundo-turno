"""Gera a imagem de compartilhamento (app/capa.png, 1200x630) e a marca da barra do computador (app/marca-barra.svg).
O favicon é a mão do Comitê, não sai daqui.

Uso: python scripts/gerar_capa.py
Cores do guia do Comitê Popular (app/tokens.css: vermelho #C3090A, amarelo #FBCE02, vinho #8E0607), marca chapada.
Toda a composição cabe no quadrado central de 630x630: o WhatsApp recorta a prévia nesse quadrado, então nada
importante fica nas laterais. AGENDA e BORA LULA na Transducer Extended, a letra do título da agenda Bora Lula do
Comitê (comitepopular.org.br/agenda), com o "A" estrelado do título; a fonte é comercial, então não fica no repo:
o script baixa do site do Comitê na hora (precisa de fonttools e brotli). O resto: a primeira de FONTES que existir.
"""
import io
import re
import urllib.request
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


TRANSDUCER = "https://comitepopular.org.br/wp-content/plugins/agenda-bora-lula/assets/fonts/transducer-extended-100-1000.woff2"
# o "A" do título da agenda (a estrela é um furo), em milésimos de em, y para cima, da tag <svg class="a-st">
A_ESTRELA = ("M307 710C238 548 59 136 -2 0L251 0L286 93L695 93L731 0L992 0C931 136 754 548 685 710Z "
             "M490 584 L544 428 L709 425 L577 325 L625 167 L490 262 L355 167 L403 325 L271 425 L436 428Z")
_transducer = None


def transducer():
    """A Transducer Extended baixada do Comitê, como TTF em memória (fontTools)."""
    global _transducer
    if _transducer is None:
        from fontTools.ttLib import TTFont
        pedido = urllib.request.Request(TRANSDUCER, headers={"User-Agent": "Mozilla/5.0"})  # sem isso, 403
        with urllib.request.urlopen(pedido, timeout=30) as r:
            _transducer = TTFont(io.BytesIO(r.read()))
        _transducer.flavor = None
    return _transducer


def fonte_marca(tam):
    ttf = io.BytesIO()
    transducer().save(ttf)
    ttf.seek(0)
    return ImageFont.truetype(ttf, tam)


def a_estrela(tam, cor, fundo):
    """O "A" estrelado na altura de uma fonte de `tam` px: imagem RGBA cuja base é a linha de base do texto."""
    sub = []
    for cmd, nums in re.findall(r"([MLCZ])([^MLCZ]*)", A_ESTRELA):
        v = [float(n) for n in nums.split()]
        if cmd == "M":
            sub.append([(v[0], v[1])])
        elif cmd == "L":
            sub[-1].append((v[0], v[1]))
        elif cmd == "C":
            (x0, y0), (x1, y1, x2, y2, x3, y3) = sub[-1][-1], v
            for i in range(1, 17):
                t = i / 16
                a, b, c, e = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
                sub[-1].append((a * x0 + b * x1 + c * x2 + e * x3, a * y0 + b * y1 + c * y2 + e * y3))
    k = 4  # desenha 4x maior e reduz, para a borda sair suave
    esc = tam * k / 1000
    im = Image.new("RGBA", (round(994 * esc), round(710 * esc)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for n, pts in enumerate(sub):
        d.polygon([((x + 2) * esc, (710 - y) * esc) for x, y in pts], fill=cor if n == 0 else fundo)
    return im.resize((im.width // k, im.height // k), Image.LANCZOS)


def medir(f, texto):
    c = f.getbbox(texto)
    return c[2] - c[0], c[3] - c[1], c[0], c[1]


def texto_centrado(d, texto, f, cy, largura, cor):
    """Escreve `texto` centrado horizontalmente em `largura`, com o centro vertical em `cy`."""
    w, h, dx, dy = medir(f, texto)
    d.text(((largura - w) // 2 - dx, cy - h // 2 - dy), texto, font=f, fill=cor)


def caixa_inclinada(texto, f, fundo, cor, folga=(44, 28), angulo=6):
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
    # só AGENDA inclinado, na tarja amarela, pesando para a esquerda; BORA e LULA retos, centrados, um em cada linha
    agenda = caixa_inclinada("AGENDA", fonte_marca(44), AMARELO, TINTA, folga=(26, 14))
    im.alpha_composite(agenda, ((w - agenda.width) // 2, 150 - agenda.height // 2))
    f = fonte_marca(132)
    texto_centrado(d, "BORA", f, 283, w, BRANCO)
    # LUL em texto e o A estrelado colado, como no título da agenda
    a = a_estrela(132, BRANCO, VERMELHO)
    lw, lh, ldx, ldy = medir(f, "LUL")
    x = (w - (lw + a.width)) // 2
    base = 397 + lh // 2  # linha de base da segunda linha (as maiúsculas não descem)
    d.text((x - ldx, base - lh - ldy), "LUL", font=f, fill=BRANCO)
    im.alpha_composite(a, (x + lw + round(132 * 0.04), base - a.height))
    f = fonte(34)
    texto_centrado(d, "Ações do 2º turno", f, 535, w, BRANCO)
    texto_centrado(d, "perto de você", f, 578, w, BRANCO)
    im.convert("RGB").save(APP / "capa.png", optimize=True)


def contorno(texto, x, base, tam):
    """Caminho SVG (d) das letras de `texto` na Transducer, a partir de (x, base); devolve (d, x final, altura das maiúsculas)."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    f = transducer()
    esc = tam / f["head"].unitsPerEm
    glifos, cmap, larguras = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
    partes = []
    for letra in texto:
        nome = cmap[ord(letra)]
        pen = SVGPathPen(glifos, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        glifos[nome].draw(TransformPen(pen, (esc, 0, 0, -esc, x, base)))
        partes.append(pen.getCommands())
        x += larguras[nome][0] * esc
    return " ".join(partes), x, f["OS/2"].sCapHeight * esc


def a_estrela_svg(x, base, tam):
    """O A estrelado como caminho SVG (regra evenodd: a estrela fica vazada)."""
    esc = tam / 1000
    def ponto(m):
        xs, ys = m.group(1), m.group(2)
        return f"{x + (float(xs) + 2) * esc:.2f} {base - float(ys) * esc:.2f}"
    return re.sub(r"(-?[\d.]+) (-?[\d.]+)", ponto, A_ESTRELA.replace("C", " C ").replace("L", " L ").replace("M", " M "))


def marca_barra():
    """AGENDA na tarja amarela inclinada, à esquerda; BORA sobre LULA à direita, brancos, na letra da agenda."""
    tam = 30  # BORA e LULA
    _, xb, cap = contorno("BORA", 0, 0, tam)
    _, xl, _ = contorno("LUL", 0, 0, tam)
    largura_lula = xl + tam * 0.04 + tam * 0.994
    entre = tam * 0.16  # espaço entre as linhas
    alto = cap * 2 + entre
    ta = 15  # AGENDA
    _, xa, cap_a = contorno("AGENDA", 0, 0, ta)
    folga_x, folga_y = 9, 6
    tw, th = xa + folga_x * 2, cap_a + folga_y * 2
    gap = 12
    x0 = tw + gap + 4  # bloco BORA/LULA depois da tarja (4 de folga para o giro)
    larg = x0 + max(xb, largura_lula)
    bloco_x = lambda w: x0 + (max(xb, largura_lula) - w) / 2
    b1 = cap  # linha de base de BORA
    b2 = cap * 2 + entre
    bora, *_ = contorno("BORA", bloco_x(xb), b1, tam)
    lx = bloco_x(largura_lula)
    lul, xl, _ = contorno("LUL", lx, b2, tam)
    a = a_estrela_svg(xl + tam * 0.04, b2, tam)
    ty = (alto - th) / 2
    agenda, *_ = contorno("AGENDA", 2 + folga_x, ty + folga_y + cap_a, ta)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -4 {larg:.0f} {alto + 8:.0f}" role="img" aria-label="Agenda Bora Lula">'
           f'<g transform="rotate(-6 {2 + tw / 2:.1f} {alto / 2:.1f})"><rect x="2" y="{ty:.1f}" width="{tw:.1f}" height="{th:.1f}" fill="{AMARELO}"/>'
           f'<path fill="{TINTA}" d="{agenda}"/></g>'
           f'<path fill="#fff" d="{bora} {lul}"/><path fill="#fff" fill-rule="evenodd" d="{a}"/></svg>\n')
    (APP / "marca-barra.svg").write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    capa()
    marca_barra()
    print("ok:", APP / "capa.png", APP / "marca-barra.svg")
