"""Genera el pitch deck de SignalRoom (pptx editable) con la identidad visual de la web.

Uso (desde la raíz del repo):
    python pitch/build_deck.py          # -> pitch/SignalRoom_PitchDeck.pptx
    powershell -File pitch/export_pdf.ps1   # -> pitch/SignalRoom_PitchDeck.pdf (requiere PowerPoint)

Fuentes: Space Grotesk (títulos) e Inter (texto), las mismas que la web.
"""

from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent
A = ROOT / "assets"
OUT = ROOT / "SignalRoom_PitchDeck.pptx"

# ----------------------------------------------------------------- marca (frontend/src/index.css)
BG = RGBColor(0x08, 0x09, 0x0D)
SURFACE = RGBColor(0x10, 0x12, 0x19)
EL = RGBColor(0x17, 0x19, 0x22)
LINE = RGBColor(0x26, 0x29, 0x36)
LINE2 = RGBColor(0x34, 0x38, 0x48)
P = RGBColor(0x8B, 0x5C, 0xF6)
PS = RGBColor(0xA7, 0x8B, 0xFA)
ACC = RGBColor(0xEC, 0x48, 0x99)
INK = RGBColor(0xF5, 0xF5, 0xF7)
INK2 = RGBColor(0xA1, 0xA1, 0xAA)
INK3 = RGBColor(0x71, 0x71, 0x7A)
POS = RGBColor(0x22, 0xC5, 0x5E)
NEG = RGBColor(0xEF, 0x44, 0x44)
WARN = RGBColor(0xF5, 0x9E, 0x0B)
P_TINT = RGBColor(0x1E, 0x17, 0x33)  # violeta sobre fondo oscuro

HEAD = "Space Grotesk"
BODY = "Inter"
SEMI = "Inter SemiBold"

W, H = 13.333, 7.5
M = 0.6

prs = Presentation()
prs.slide_width = Inches(W)
prs.slide_height = Inches(H)
BLANK = prs.slide_layouts[6]


# ----------------------------------------------------------------- helpers
def new_slide(notes: str = "", number: bool = True):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BG
    if notes:
        s.notes_slide.notes_text_frame.text = notes
    if number:
        idx = len(prs.slides)
        txt(s, W - 1.2, H - 0.42, 0.75, 0.25, f"{idx:02d}", size=9, color=INK3, align=PP_ALIGN.RIGHT)
        pic(s, "logo_mark.png", M, H - 0.45, 0.2)
        txt(s, M + 0.27, H - 0.43, 2.5, 0.25, "SignalRoom", size=9, color=INK3, font=SEMI)
    return s


TOKEN = re.compile(r"(\*\*.+?\*\*|\{\{.+?\}\}|<<.+?>>|\[\[.+?\]\])")


def _runs(p, text, size, color, font, bold):
    for part in TOKEN.split(text):
        if not part:
            continue
        r = p.add_run()
        c, f, b = color, font, bold
        if part.startswith("**"):
            part, c, f, b = part[2:-2], INK, SEMI, False
        elif part.startswith("{{"):
            part, c, f, b = part[2:-2], ACC, SEMI, False
        elif part.startswith("<<"):
            part, c, f, b = part[2:-2], PS, SEMI, False
        elif part.startswith("[["):
            part, c, f, b = part[2:-2], POS, SEMI, False
        r.text = part
        r.font.size = Pt(size)
        r.font.color.rgb = c
        r.font.name = f
        r.font.bold = b


def txt(s, x, y, w, h, text, size=12, color=INK2, font=BODY, bold=False, align=PP_ALIGN.LEFT,
        anchor=MSO_ANCHOR.TOP, spacing=1.12, space_after=0, spc=None):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    for side in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, side, 0)
    tf.vertical_anchor = anchor
    paras = text if isinstance(text, list) else [text]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(space_after)
        _runs(p, para, size, color, font, bold)
        if spc is not None:
            for r in p.runs:
                r._r.get_or_add_rPr().set("spc", str(spc))
    return tb


def shape(s, kind, x, y, w, h, fill=EL, line=LINE, lw=0.75, radius=None):
    sh = s.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.shadow.inherit = False
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(lw)
    if radius is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = radius
    sh.text_frame.text = ""
    return sh


def card(s, x, y, w, h, fill=EL, line=LINE, r=0.06, lw=0.75):
    rad = min(0.5, r / min(w, h) * 1.0) if min(w, h) > 0 else r
    return shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill, line, lw, radius=rad * 0.9 + 0.01)


def gradient(sh, angle=45, c1=P, c2=ACC):
    sh.fill.gradient()
    sh.fill.gradient_angle = angle
    stops = sh.fill.gradient_stops
    stops[0].color.rgb = c1
    stops[0].position = 0
    stops[1].color.rgb = c2
    stops[1].position = 1.0


def pic(s, name, x, y, w=None, h=None, border=None):
    kw = {}
    if w is not None:
        kw["width"] = Inches(w)
    if h is not None:
        kw["height"] = Inches(h)
    pc = s.shapes.add_picture(str(A / name), Inches(x), Inches(y), **kw)
    if border is not None:
        pc.line.color.rgb = border
        pc.line.width = Pt(0.75)
    return pc


def line(s, x1, y1, x2, y2, color=LINE, width=0.75):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    return c


def arrow(s, x1, y1, x2, y2, color=PS, width=1.25):
    c = line(s, x1, y1, x2, y2, color, width)
    ln = c.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)
    return c


def title(s, text, sub=None, y=0.5):
    txt(s, M, y, W - 2 * M, 0.6, text, size=28, color=PS, font=HEAD, bold=True, spacing=1.0)
    if sub:
        txt(s, M, y + 0.66, W - 2 * M, 0.5, sub, size=13, color=INK2)


def label(s, x, y, w, text, color=PS, size=9.5, align=PP_ALIGN.LEFT):
    return txt(s, x, y, w, 0.25, text.upper(), size=size, color=color, font=SEMI, spc=120, align=align)


def badge(s, x, y, text, d=0.42, size=11):
    c = shape(s, MSO_SHAPE.OVAL, x, y, d, d, fill=P, line=None)
    gradient(c, 45)
    txt(s, x, y, d, d, text, size=size, color=INK, font=SEMI, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    return c


def chip(s, x, y, w, text, fill=EL, line=LINE2, color=INK2, size=9.5, h=0.32, font=SEMI):
    card(s, x, y, w, h, fill=fill, line=line, r=h / 2)
    txt(s, x + 0.08, y, w - 0.16, h, text, size=size, color=color, font=font, align=PP_ALIGN.CENTER,
        anchor=MSO_ANCHOR.MIDDLE)


def kpi(s, x, y, w, h, big, small, big_color=ACC, big_size=26):
    card(s, x, y, w, h)
    txt(s, x + 0.22, y + 0.16, w - 0.4, 0.55, big, size=big_size, color=big_color, font=HEAD, bold=True)
    txt(s, x + 0.22, y + 0.2 + big_size / 72 * 1.25, w - 0.4, h - 0.7, small, size=10, color=INK2)


def info_card(s, x, y, w, h, num, head, body, body_size=10.5):
    card(s, x, y, w, h)
    badge(s, x + 0.25, y + 0.22, num, d=0.38, size=10)
    txt(s, x + 0.25, y + 0.7, w - 0.5, 0.35, head, size=14, color=INK, font=SEMI)
    txt(s, x + 0.25, y + 1.06, w - 0.5, h - 1.12, body, size=body_size, color=INK2, spacing=1.16)


# =================================================================== 1 · Portada
s = new_slide(
    "Abrimos con la frase de una línea: SignalRoom es tu analista de mercados con IA. "
    "No es un chatbot más: vigila tus activos, investiga solo y explica cada movimiento con pruebas. "
    "Destacar que el producto ya funciona (12 agentes) y que levantamos €750K pre-seed.",
    number=False,
)
s.shapes.add_picture(str(A / "cover_bg.png"), 0, 0, width=prs.slide_width, height=prs.slide_height)
pic(s, "logo_mark.png", 0.85, 2.05, 1.05)
txt(s, 2.1, 1.82, 8, 1.3, "Signal<<Room>>", size=72, color=INK, font=HEAD, bold=True, spacing=1.0)
s.shapes[-1].text_frame.paragraphs[0].runs[1].font.color.rgb = INK2
txt(s, 0.9, 3.4, 8.6, 0.6, "Tu analista de mercados con IA", size=26, color=INK, font=HEAD, bold=True)
txt(s, 0.9, 4.05, 8.0, 0.9,
    "Vigila tus activos 24/7, te explica cada movimiento con pruebas y, mañana, "
    "actúa por ti dentro de los límites que tú marques.", size=15, color=INK2, spacing=1.2)
card(s, 0.9, 5.15, 8.3, 0.46, fill=SURFACE, line=LINE2, r=0.12)
txt(s, 1.1, 5.15, 8.0, 0.46,
    "Producto funcionando · 12 agentes de IA · 0,003–0,03 $ por investigación   ·   {{Levantando €750K pre-seed}}",
    size=11, color=INK2, font=SEMI, anchor=MSO_ANCHOR.MIDDLE)
txt(s, 0.9, 6.7, 8, 0.3, "Proyecto MIAX · Instituto BME  ·  Madrid, octubre 2026", size=10, color=INK3)

# =================================================================== 2 · Equipo
s = new_slide(
    "Tres co-fundadores técnicos del MIAX. Iván (CEO) ya ha construido sistemas multi-agente en producción en "
    "un banco regulado (Renta 4). Joseph (CTO) aporta ingeniería de "
    "software y rendimiento (Accenture, NTT DATA). Gonzalo (CMO) gestión de proyectos (INECO) y formación en "
    "emprendimiento. La ronda cubre lo que nos falta: partnerships con brokers y compliance."
)
title(s, "Equipo", "Tres ingenieros del Máster en IA aplicada a Mercados Financieros (MIAX, Instituto BME). "
      "Full-time desde el cierre de la ronda.")
people = [
    ("ivan.png", "Iván Nevado Martín", "Co-fundador y CEO", [
        "**AI Engineer & GenAI Solutions Architect, Renta 4 Banco.** 2 sistemas multi-agente en producción en un "
        "banco regulado: ~3.000 consultas/semana y −30–50 % de tiempo de resolución.",
        "**Liderazgo técnico de IA en banca:** arquitectura de soluciones GenAI en un entorno regulado, de la "
        "idea a producción.",
        "MIAX (BME) · Ingeniería de Software (UPM), TFG 10/10 con MH · ex-profesor ayudante de IA.",
    ]),
    ("joseph.png", "Joseph Egusquiza", "Co-fundador y CTO", [
        "**Analista en Accenture:** ingeniería de rendimiento y pruebas de carga (NeoLoad) de sistemas críticos.",
        "**Ingeniero de software en NTT DATA:** APIs REST, SQL y desarrollo backend.",
        "MIAX (BME) · Ingeniería de Software (UPM) · certificaciones ServiceNow en testing automatizado.",
    ]),
    ("gonzalo.png", "Gonzalo De Ramón Murillo", "Co-fundador y CMO", [
        "**Gestión de proyectos en INECO** (negocio ferroviario): planificación y coordinación de proyectos.",
        "**Emprendimiento:** certificado EELISA – Xiji Incubator.",
        "MIAX (BME) · Ingeniería Industrial (UPM) · Beca de Excelencia Académica de la Comunidad de Madrid.",
    ]),
]
cw, cy, ch = 3.0, 1.75, 4.55
for i, (img, name, role, bullets) in enumerate(people):
    x = M + i * (cw + 0.18)
    card(s, x, cy, cw, ch)
    pic(s, img, x + 0.22, cy + 0.22, 1.1)
    txt(s, x + 0.22, cy + 1.45, cw - 0.4, 0.3, name, size=14, color=INK, font=SEMI)
    txt(s, x + 0.22, cy + 1.76, cw - 0.4, 0.25, role, size=10.5, color=ACC, font=SEMI)
    txt(s, x + 0.22, cy + 2.12, cw - 0.4, 2.35, bullets, size=9.5, color=INK2, spacing=1.15, space_after=5)
hx, hw = M + 3 * (cw + 0.18) + 0.05, W - M - (M + 3 * (cw + 0.18) + 0.05)
card(s, hx, cy, hw, ch, fill=SURFACE, line=LINE2)
label(s, hx + 0.22, cy + 0.2, hw - 0.4, "Con esta ronda", color=ACC)
hires = [
    ("Head of Partnerships", "Perfil ex-broker o banca → primeros acuerdos B2B2C"),
    ("Compliance y Riesgos", "MiFID II, AI Act y CNMV desde el día 1"),
    ("2× AI / Data Engineers", "Datos licenciados, app móvil e integraciones con brokers"),
]
for j, (role, desc) in enumerate(hires):
    yy = cy + 0.55 + j * 1.05
    card(s, hx + 0.18, yy, hw - 0.36, 0.92, fill=EL, line=LINE)
    label(s, hx + 0.32, yy + 0.1, hw - 0.6, "Contratando", color=INK3, size=8)
    txt(s, hx + 0.32, yy + 0.32, hw - 0.6, 0.25, role, size=11.5, color=INK, font=SEMI)
    txt(s, hx + 0.32, yy + 0.58, hw - 0.6, 0.32, desc, size=9, color=INK2)
txt(s, hx + 0.22, cy + ch - 0.62, hw - 0.4, 0.45, "Objetivo: {{primer broker en producción con un equipo de 7}}",
    size=9.5, color=INK2)
card(s, M, 6.45, W - 2 * M, 0.42, fill=SURFACE, line=LINE2, r=0.1)
txt(s, M + 0.2, 6.45, W - 2 * M - 0.4, 0.42,
    "Ya construido por el equipo: **plataforma completa con 12 agentes y 7 modalidades**, 150+ tests automáticos "
    "e infraestructura AWS lista en Terraform.", size=10, color=INK2, anchor=MSO_ANCHOR.MIDDLE)

# =================================================================== 3 · Problema
s = new_slide(
    "El problema no es la falta de información, es que está dispersa y sin pruebas. Los chatbots esperan a que "
    "preguntes, los finfluencers no se pueden verificar (la CNMV ha encontrado incumplimientos) y el research "
    "profesional cuesta miles de euros. El enemigo es la opinión sin pruebas."
)
title(s, "El inversor particular recibe opiniones, no pruebas",
      "Millones de europeos invierten por su cuenta, y sus herramientas les dicen qué pasó, nunca por qué.")
probs = [
    ("La información está dispersa",
     "Cotizaciones, titulares, informes regulatorios, conference calls, webinars y gráficos: cada formato en un "
     "sitio distinto, y nadie los cruza por ti."),
    ("Los chatbots responden, pero no vigilan",
     "Hay que saber qué preguntar. Nadie te avisa cuando tu activo se mueve ni te explica el porqué con fuentes."),
    ("Los finfluencers enganchan, pero no se pueden verificar",
     "Sin fuentes y con posibles conflictos de interés: la CNMV revisó ~100 creadores en 2026 y "
     "{{1 de cada 10 incumplía la normativa}}."),
    ("El análisis profesional cuesta miles",
     "Los terminales y el research institucional cuestan miles de euros al año por usuario: "
     "fuera del alcance de un particular."),
]
for i, (h_, b_) in enumerate(probs):
    x = M + (i % 2) * 6.13
    y = 1.8 + (i // 2) * 2.05
    info_card(s, x, y, 5.95, 1.88, f"0{i + 1}", h_, b_, body_size=11)
txt(s, M, 6.05, W - 2 * M, 0.5,
    "{{El enemigo:}} la opinión sin pruebas, es decir, decisiones con dinero real basadas en un titular o en un "
    "vídeo de 30 segundos.", size=12.5, color=INK)

# =================================================================== 4 · Solución
s = new_slide(
    "La solución es un ciclo: vigilar, investigar, explicar y aprender. La IA hace el trabajo pesado (12 agentes en "
    "paralelo) pero las cifras se calculan en código y cada afirmación lleva su fuente. Mencionar ejemplos del "
    "usuario: cripto (ETH, SOL), petróleo, S&P 500."
)
title(s, "Un analista que no duerme",
      "Para cada activo que te importa: acciones, ETFs, cripto (ETH, SOL), petróleo, S&P 500…   "
      "[[En verde]], lo que ya está construido.")
steps = [
    ("01", "Vigilar", "**Hoy:** briefing diario programado sobre tu watchlist. <<Visión:>> vigilancia 24/7 que "
     "investiga sola cuando un activo hace un movimiento anómalo.", "Hoy + visión"),
    ("02", "Investigar", "12 agentes especializados en paralelo: mercado, noticias, informes, macro, calls, "
     "webinars, PDFs y gráficos.", "Hoy"),
    ("03", "Explicar", "Causas puntuadas por evidencia y cada afirmación con su fuente. En texto, audio narrado o "
     "email.", "Hoy"),
    ("04", "Recordar", "Cada investigación queda guardada e indexada: búsqueda semántica (texto o imagen) y "
     "preguntas de seguimiento con todo el contexto.", "Hoy"),
]
sw, sy, sh_ = 2.82, 1.8, 2.65
for i, (n, h_, b_, tag) in enumerate(steps):
    x = M + i * (sw + 0.23)
    card(s, x, sy, sw, sh_)
    badge(s, x + 0.22, sy + 0.22, n)
    txt(s, x + 0.22, sy + 0.78, sw - 0.4, 0.35, h_, size=16, color=INK, font=HEAD, bold=True)
    txt(s, x + 0.22, sy + 1.17, sw - 0.4, 1.0, b_, size=10, color=INK2, spacing=1.14)
    built = tag == "Hoy"
    chip(s, x + 0.22, sy + sh_ - 0.48, 1.55, tag, fill=RGBColor(0x0E, 0x2A, 0x1A) if built else P_TINT,
         line=POS if built else P, color=POS if built else PS, size=8.5, h=0.28)
    if i < 3:
        arrow(s, x + sw + 0.02, sy + sh_ / 2, x + sw + 0.21, sy + sh_ / 2)
# bucle de aprendizaje
ly = sy + sh_ + 0.28
line(s, M + 4 * sw + 3 * 0.23 - sw / 2, sy + sh_, M + 4 * sw + 3 * 0.23 - sw / 2, ly, color=PS, width=1.25)
line(s, M + sw / 2, ly, M + 4 * sw + 3 * 0.23 - sw / 2, ly, color=PS, width=1.25)
arrow(s, M + sw / 2, ly, M + sw / 2, sy + sh_ + 0.02)
txt(s, M + 4.0, ly - 0.02, 5, 0.3, "el archivo de causas crece con cada investigación", size=9.5, color=PS, font=SEMI,
    align=PP_ALIGN.CENTER)
s.shapes[-1].fill.solid()
s.shapes[-1].fill.fore_color.rgb = BG
k = [("~60 s", "de la pregunta a una respuesta con fuentes"),
     ("0,003–0,03 $", "coste de IA facturado por investigación, de texto a vídeo (sin datos ni infraestructura)"),
     ("0 cifras inventadas", "las métricas se calculan en código; los modelos solo interpretan y las citas se "
      "verifican literalmente")]
kw_ = (W - 2 * M - 2 * 0.2) / 3
for i, (b, sm) in enumerate(k):
    kpi(s, M + i * (kw_ + 0.2), 5.2, kw_, 1.15, b, sm, big_size=24)

# =================================================================== 5 · Producto
s = new_slide(
    "Esto es el producto real, no un diseño. Cada investigación muestra el porqué con pesos y fuentes, el grafo de "
    "evidencias, el mercado y los riesgos. El usuario lo recibe como briefing diario en texto, audio o email. "
    "Precio: gratis y Pro desde 9,99 €/mes, frente a decenas de miles de un terminal profesional."
)
title(s, "Análisis con pruebas. Cada activo. Cada día.",
      "Lo que recibe el usuario: el porqué de cada movimiento, con fuentes, en el formato que prefiera.")
blocks = [
    ("Con pruebas", "Cada causa lleva su peso y sus fuentes enlazadas. Grafo de evidencias, riesgos y qué vigilar "
     "después."),
    ("Multimodal", "Entiende cotizaciones, noticias, informes, PDFs, gráficos, conference calls y webinars en "
     "vídeo. Responde en texto, audio y email."),
    ("Personal", "Briefing diario sobre tus activos y búsqueda semántica en todo lo investigado. Próximo paso: "
     "alertas automáticas cuando algo se mueve."),
]
for i, (h_, b_) in enumerate(blocks):
    y = 1.8 + i * 1.05
    label(s, M, y, 4.4, h_, color=ACC)
    txt(s, M, y + 0.28, 4.3, 0.7, b_, size=10.5, color=INK2, spacing=1.16)
card(s, M, 5.02, 4.3, 1.25, fill=P_TINT, line=P)
txt(s, M + 0.22, 5.14, 4.0, 0.5, "Gratis · Pro desde €9,99/mes", size=19, color=ACC, font=HEAD, bold=True)
txt(s, M + 0.22, 5.62, 4.0, 0.55, "frente a ~30.000 $/año de un terminal profesional. Y gratis para el usuario "
    "cuando llega vía su broker.", size=9.5, color=INK2)
pic(s, "shot_summary.png", 5.2, 1.75, w=5.35, border=LINE2)
pic(s, "shot_graph.png", 7.25, 3.62, w=3.9, border=LINE2)
pic(s, "shot_mobile.png", W - M - 1.85, 1.75, h=3.8, border=LINE2)
txt(s, 5.2, 6.62, 7.5, 0.25, "Capturas reales de la app: investigación sobre NVIDIA, grafo de evidencias y vista "
    "móvil (5 oct 2026).", size=8.5, color=INK3)

# =================================================================== 6 · Construido y medido
s = new_slide(
    "Aclarar el alcance: funciona en local, la nube está escrita pero no desplegada y no hay usuarios ni alertas "
    "automáticas. No tenemos clientes de pago todavía, así que enseñamos lo que sí es verificable: producto completo, probado y "
    "con costes medidos en ejecuciones reales. El dato clave es el coste: céntimos por investigación, lo que hace "
    "viable un modelo freemium y el B2B2C. Cerramos con el plan de 90 días."
)
title(s, "Construido, probado y medido: no es un mockup",
      "Funciona de extremo a extremo en local; la nube está escrita (Terraform) pero sin desplegar. Aún no hay "
      "usuarios ni alertas automáticas.")
ks = [("12", "agentes de IA especializados, orquestados con LangGraph"),
      ("7", "modalidades: texto, mercado, noticias, PDF, imagen, audio y vídeo"),
      ("150+", "tests automáticos más E2E sobre la app real"),
      ("~1,2 $/mes", "coste de IA de un usuario Pro intensivo")]
kw_ = (W - 2 * M - 3 * 0.2) / 4
for i, (b, sm) in enumerate(ks):
    kpi(s, M + i * (kw_ + 0.2), 1.75, kw_, 1.2, b, sm, big_size=26)
tx, tw = M, 7.25
card(s, tx, 3.18, tw, 3.55)
label(s, tx + 0.25, 3.33, tw - 0.5, "Coste de IA facturado por OpenRouter · ejecuciones reales, oct 2026")
rows = [("Investigación «¿por qué se movió?» (texto)", "0,003 $", "~60 s"),
        ("+ briefing narrado en audio (~2 min)", "0,007 $", "~14 s"),
        ("Conference call + PDF de resultados (multimodal)", "0,020 $", "~50 s"),
        ("Webinar en vídeo de 2 min (voz + diapositivas)", "0,031 $", "~60 s"),
        ("Briefing diario con audio", "0,009 $", "~60 s"),
        ("Indexado para la búsqueda semántica", "0,0004 $", "~1 s"),
        ("Infografía generada (imagen, opcional)", "0,067 $", "~8 s")]
for j, (a, b, c) in enumerate(rows):
    yy = 3.7 + j * 0.42
    line(s, tx + 0.25, yy - 0.04, tx + tw - 0.25, yy - 0.04)
    txt(s, tx + 0.25, yy + 0.06, 4.6, 0.3, a, size=10.5, color=INK2)
    txt(s, tx + 4.9, yy + 0.06, 1.1, 0.3, b, size=11, color=ACC, font=SEMI, align=PP_ALIGN.RIGHT)
    txt(s, tx + 6.05, yy + 0.06, 0.9, 0.3, c, size=10, color=INK3, align=PP_ALIGN.RIGHT)
rx, rw = tx + tw + 0.2, W - M - (tx + tw + 0.2)
card(s, rx, 3.18, rw, 3.55, fill=SURFACE, line=LINE2)
label(s, rx + 0.25, 3.33, rw - 0.5, "Próximos 90 días (plan)", color=ACC)
plan90 = ["Beta cerrada con 100 inversores (comunidad MIAX / BME)",
          "Carta de intención de un broker para un piloto B2B2C",
          "Datos de mercado europeos con licencia",
          "Despliegue en AWS: la infraestructura ya está escrita en Terraform"]
for j, t in enumerate(plan90):
    yy = 3.78 + j * 0.7
    badge(s, rx + 0.25, yy, str(j + 1), d=0.32, size=9)
    txt(s, rx + 0.72, yy - 0.01, rw - 0.95, 0.6, t, size=10.5, color=INK2, anchor=MSO_ANCHOR.TOP)

# =================================================================== 8 · Visión: autonomía
s = new_slide(
    "Esta es la visión de startup: el analista evoluciona hacia un piloto automático, pero siempre con el usuario al "
    "mando y con la licencia en el partner. Hoy estamos en la fase 1: prototipo construido, sin desplegar. Los raíles técnicos ya existen "
    "(Robinhood, Scalable, eToro). Respuesta anticipada a «¿esto es asesoramiento?»: no, nosotros somos el cerebro y "
    "el partner pone la licencia."
)
title(s, "La visión: de analista a piloto automático, contigo al mando",
      "Hoy explica cuando se lo pides y una vez al día. La autonomía crece por fases ligadas a la financiación.")
levels = [
    ("Fase 1 · Hoy", "Explicar", "Investigación bajo demanda y briefing diario programado. Research, no "
     "asesoramiento.", True),
    ("Fase 2 · 0–18 meses", "Vigilar", "Con esta ronda: si un activo de tu watchlist se mueve de forma anómala, "
     "investiga solo y te avisa.", False),
    ("Fase 3 · Años 2–3", "Proponer", "Con la seed: escenarios y alertas según reglas tuyas (stop, exposición, "
     "rebalanceo), vía un broker con licencia.", False),
    ("Fase 4 · Año 3+", "Actuar", "Ejecución con mandato: tú fijas activos, importes y límites; el broker ejecuta "
     "y cada acción se explica.", False),
]
lw_ = 2.42
for i, (lv, h_, b_, live) in enumerate(levels):
    x = M + i * (lw_ + 0.15)
    y = 3.8 - i * 0.55
    hh = 6.0 - y
    c = card(s, x, y, lw_, hh, fill=P_TINT if i == 3 else EL, line=P if i == 3 else LINE)
    label(s, x + 0.2, y + 0.18, lw_ - 0.4, lv, color=ACC if i == 3 else PS, size=8.5)
    txt(s, x + 0.2, y + 0.45, lw_ - 0.4, 0.4, h_, size=17, color=INK, font=HEAD, bold=True)
    txt(s, x + 0.2, y + 0.9, lw_ - 0.35, 1.2, b_, size=10, color=INK2, spacing=1.15)
    if live:
        chip(s, x + 0.2, y + hh - 0.45, 1.35, "Construido", fill=RGBColor(0x0E, 0x2A, 0x1A), line=POS,
             color=POS, size=8.5, h=0.28)
rx = M + 4 * (lw_ + 0.15)
rw = W - M - rx
card(s, rx, 2.15, rw, 3.85, fill=SURFACE, line=LINE2)
label(s, rx + 0.2, 2.42, rw - 0.4, "Raíles ya listos", color=ACC)
rails = ["**Robinhood** · trading con agentes vía MCP (may 2026)",
         "**Scalable Capital** · conecta ChatGPT o Claude a cuentas reales (ago 2026)",
         "**eToro** · API pública y MCP para agentes"]
txt(s, rx + 0.2, 2.8, rw - 0.4, 3.0, rails, size=10, color=INK2, spacing=1.15, space_after=9)
card(s, M, 6.22, W - 2 * M, 0.55, fill=SURFACE, line=LINE2, r=0.1)
txt(s, M + 0.22, 6.22, W - 2 * M - 0.44, 0.55,
    "{{Perímetro regulatorio:}} nosotros aportamos el cerebro; la licencia MiFID II para asesorar o gestionar la "
    "pone el broker o banco partner.", size=10.5, color=INK2, anchor=MSO_ANCHOR.MIDDLE)

# =================================================================== 9 · Modelo de negocio
s = new_slide(
    "Dos motores de ingresos. B2C freemium para construir marca y captar usuarios, con márgenes altos porque la IA "
    "cuesta céntimos. B2B2C: licenciamos el analista en marca blanca a brokers por usuario activo; el partner "
    "distribuye (CAC casi cero) y pone la licencia. Los costes de IA son medidos; precios y CAC son supuestos."
)
title(s, "Modelo de negocio y unit economics",
      "**Freemium directo** (marca y captación) + **B2B2C**: licenciamos el analista en marca blanca a brokers y "
      "neobancos.")
cx1, cw1 = M, 6.05
card(s, cx1, 1.75, cw1, 3.55)
label(s, cx1 + 0.25, 1.92, cw1 - 0.5, "Pro (B2C) · por suscriptor / mes")
txt(s, cx1 + 3.6, 1.92, 1.0, 0.25, "HOY", size=8.5, color=INK3, font=SEMI, align=PP_ALIGN.RIGHT)
txt(s, cx1 + 4.7, 1.92, 1.1, 0.25, "A ESCALA", size=8.5, color=INK3, font=SEMI, align=PP_ALIGN.RIGHT)
b2c = [("Precio medio (€9,99/mes o €99/año)", "€8,75", "€8,75"),
       ("Coste de IA (estimado con costes medidos)", "€1,10", "€0,60"),
       ("Datos de mercado y cloud", "€1,50", "€0,40"),
       ("Margen de contribución", "70 %", "88 %"),
       ("CAC (contenido orgánico)", "€20", "€20"),
       ("Payback del CAC", "3,3 meses", "2,6 meses")]
for j, (a, b, c) in enumerate(b2c):
    yy = 2.3 + j * 0.47
    line(s, cx1 + 0.25, yy - 0.04, cx1 + cw1 - 0.25, yy - 0.04)
    hl = j == 3
    txt(s, cx1 + 0.25, yy + 0.07, 3.4, 0.3, a, size=10.5, color=INK if hl else INK2, font=SEMI if hl else BODY)
    txt(s, cx1 + 3.6, yy + 0.07, 1.0, 0.3, b, size=10.5, color=INK2, align=PP_ALIGN.RIGHT)
    txt(s, cx1 + 4.7, yy + 0.07, 1.1, 0.3, c, size=10.5, color=ACC, font=SEMI, align=PP_ALIGN.RIGHT)
cx2, cw2 = cx1 + cw1 + 0.2, W - M - (cx1 + cw1 + 0.2)
card(s, cx2, 1.75, cw2, 3.55, fill=P_TINT, line=P)
label(s, cx2 + 0.25, 1.92, cw2 - 0.5, "Partner (B2B2C) · por usuario activo / mes", color=ACC)
b2b = [("Licencia por usuario activo (MAU)", "€1,00"),
       ("Cuota mínima de plataforma", "€2.000/mes"),
       ("Coste de IA por MAU (briefing diario + preguntas)", "€0,15–0,25"),
       ("Margen bruto", "75–85 %"),
       ("CAC por usuario", "~€0"),
       ("Quién pone la licencia MiFID", "el partner")]
for j, (a, b) in enumerate(b2b):
    yy = 2.3 + j * 0.47
    line(s, cx2 + 0.25, yy - 0.04, cx2 + cw2 - 0.25, yy - 0.04, color=RGBColor(0x3B, 0x2F, 0x63))
    txt(s, cx2 + 0.25, yy + 0.07, 4.1, 0.3, a, size=10.5, color=INK2)
    txt(s, cx2 + 4.3, yy + 0.07, cw2 - 4.55, 0.3, b, size=10.5, color=ACC, font=SEMI, align=PP_ALIGN.RIGHT)
wins = [("El partner gana", "engagement, operativa y retención con contenido que cumple la normativa"),
        ("El usuario gana", "su analista personal dentro de la app que ya usa"),
        ("Nosotros ganamos", "distribución sin CAC, y la licencia la pone el partner")]
ww = (W - 2 * M - 2 * 0.2) / 3
for i, (h_, b_) in enumerate(wins):
    x = M + i * (ww + 0.2)
    card(s, x, 5.5, ww, 0.95)
    txt(s, x + 0.22, 5.6, ww - 0.4, 0.3, h_, size=11.5, color=INK, font=SEMI)
    txt(s, x + 0.22, 5.9, ww - 0.4, 0.5, b_, size=9.5, color=INK2)
txt(s, M, 6.58, W - 2 * M, 0.25, "Costes de IA medidos en ejecuciones reales (oct 2026). Precios, CAC y coste de "
    "datos licenciados son supuestos del plan.", size=8.5, color=INK3)

# =================================================================== 10 · Mercado
s = new_slide(
    "Bottom-up: cuentas de inversión autogestionadas por un ARPU Pro de 105 €/año. Empezamos en España (~3 M de "
    "inversores digitales, estimación) y escalamos a Europa (39 M de cuentas) vía brokers. El top-down de IA en "
    "wealth management (14.000 M$ en 2030) y el mercado global de inversión autogestionada (109.000 M$) dan el "
    "techo."
)
title(s, "Mercado: empezar en España, escalar a Europa")
txt(s, M, 1.2, 9.2, 0.9, [
    "**Visión:** el analista de IA de cada inversor particular, con la calidad que antes solo tenían los "
    "profesionales.",
    "**Entrada:** inversores autogestionados digitales en España (Trade Republic, MyInvestor, eToro…); después "
    "Europa a través de brokers."], size=11, color=INK2, space_after=4)
txt(s, M, 2.1, 9.5, 0.3, "Bottom-up: cuentas autogestionadas × ARPU Pro de €105/año · España: <18 % de ~40 M de "
    "adultos invierte (~7 M), ~3 M digitales (estimación)", size=9.5, color=ACC, font=SEMI)
RC = (11.8, 1.45)
for r_, col in ((0.95, LINE2), (0.72, P), (0.5, ACC)):
    shape(s, MSO_SHAPE.OVAL, RC[0] - r_, RC[1] - r_, 2 * r_, 2 * r_, fill=None, line=col, lw=2.25)
inner = shape(s, MSO_SHAPE.OVAL, RC[0] - 0.34, RC[1] - 0.34, 0.68, 0.68, fill=P, line=None)
gradient(inner, 45)
txt(s, RC[0] - 0.34, RC[1] - 0.34, 0.68, 0.68, "ES", size=12, color=INK, font=SEMI, align=PP_ALIGN.CENTER,
    anchor=MSO_ANCHOR.MIDDLE)
layers = [
    ("1 · Ahora · España: ~3 M de inversores digitales",
     "Freemium directo y primeros brokers españoles · watchlists de acciones, ETFs, cripto y materias primas"),
    ("2 · Año 1–3 · Europa: 39 M de cuentas autogestionadas",
     "Más de 21 mercados (DE, FR, IT, NL…) a través de partnerships con neobrokers"),
    ("3 · Año 3–5 · Piloto automático",
     "Vigilancia y ejecución con mandato a través de partners con licencia: IA en wealth management"),
    ("4 · Año 5+ · Todo inversor y asesor",
     "Herramientas para asesores y gestoras · mercado global de inversión autogestionada"),
]
for i, (h_, b_) in enumerate(layers):
    x = M + (i % 2) * 6.13
    y = 2.6 + (i // 2) * 1.12
    card(s, x, y, 5.95, 0.98)
    badge(s, x + 0.2, y + 0.25, str(i + 1), d=0.42)
    txt(s, x + 0.8, y + 0.14, 5.0, 0.3, h_, size=11, color=INK, font=SEMI)
    txt(s, x + 0.8, y + 0.45, 5.0, 0.5, b_, size=9.5, color=INK2)
nw = (W - 2 * M) / 4
big = [("€0,3B", "Cabeza de playa · España"), ("€4,1B", "Autogestionados · Europa"),
       ("$14B", "IA en wealth management · 2030"), ("$109B", "Inversión autogestionada · global")]
for i, (b, sm) in enumerate(big):
    x = M + i * nw
    txt(s, x, 5.07, nw - 0.2, 0.3, sm, size=9.5, color=INK3, align=PP_ALIGN.CENTER)
    txt(s, x, 5.35, nw - 0.2, 0.75, b, size=40, color=ACC, font=HEAD, bold=True, align=PP_ALIGN.CENTER)
    if i:
        line(s, x - 0.1, 5.2, x - 0.1, 6.05, color=LINE2)
txt(s, M, 6.4, W - 2 * M, 0.3, "Fuentes: estudios de mercado de inversión autogestionada (2026) · The Business Research "
    "Company (IA en wealth management) · AMF · prensa sectorial. España y ARPU: estimaciones propias.",
    size=8, color=INK3)

# =================================================================== 11 · Competencia
s = new_slide(
    "Cada alternativa obliga a renunciar a algo. Los asistentes de los brokers son reactivos y están atados a su app; "
    "ChatGPT y Perplexity no vigilan; los terminales son caros; los finfluencers no tienen pruebas. Nuestra apuesta: "
    "ser el motor que los brokers licencian, no competir con su app. Lo defendible: el archivo de causas, la "
    "confianza verificable, los contratos con brokers y el contexto del usuario; los modelos no son foso."
)
title(s, "Panorama competitivo",
      "Todos obligan a elegir. Nuestra ventaja: proactivo, con pruebas, multimodal y al precio de un particular.")
cols = ["Asistentes de brokers\n(Cortex, Tori…)", "ChatGPT /\nPerplexity Finance", "Terminales pro\n(AlphaSense, Bloomberg)",
        "Finfluencers y\nnewsletters", "● SignalRoom"]
rowsc = [("Vigila tus activos y te avisa (proactivo)", "~✗✓~✓"),
         ("Explica por qué se movió, con evidencia puntuada", "~~✓✗✓"),
         ("Cada afirmación enlazada a su fuente", "~✓✓✗✓"),
         ("Multimodal: calls, webinars, PDFs y gráficos", "✗~✓✗✓"),
         ("Briefing en audio, vídeo y email", "✗✗✗✓✓"),
         ("Independiente del broker y con activos europeos", "✗✓✓✓✓"),
         ("Precio de particular (< €10/mes)", "✓✓✗✓✓"),
         ("Sin conflictos de interés, cumplimiento por diseño", "~✓✓✗✓")]
tx0, tw0 = M, W - 2 * M
c0 = 4.1
cwc = (tw0 - c0) / 5
ty = 1.72
card(s, tx0 + c0 + 4 * cwc, ty, cwc, 0.62 + len(rowsc) * 0.44 + 0.05, fill=P_TINT, line=P)
for i, cname in enumerate(cols):
    txt(s, tx0 + c0 + i * cwc, ty + 0.06, cwc, 0.55, cname.split("\n"), size=9, color=ACC if i == 4 else INK2,
        font=SEMI, align=PP_ALIGN.CENTER, spacing=1.0)
txt(s, tx0, ty + 0.2, c0, 0.3, "CAPACIDAD", size=8.5, color=INK3, font=SEMI, spc=100)
sym = {"✓": ("✓", POS), "✗": ("✗", INK3), "~": ("~", WARN)}
for j, (name, marks) in enumerate(rowsc):
    yy = ty + 0.65 + j * 0.44
    line(s, tx0, yy - 0.02, tx0 + tw0, yy - 0.02)
    txt(s, tx0 + 0.05, yy + 0.08, c0 - 0.1, 0.3, name, size=10.5, color=INK2)
    for i, m in enumerate(marks):
        t, col = sym[m]
        if i == 4:
            col = ACC
        txt(s, tx0 + c0 + i * cwc, yy + 0.04, cwc, 0.35, t, size=14, color=col, font=SEMI, align=PP_ALIGN.CENTER)
card(s, M, 5.95, W - 2 * M, 0.55, fill=SURFACE, line=LINE2, r=0.1)
txt(s, M + 0.22, 5.95, W - 2 * M - 0.44, 0.55,
    "{{Lo que se acumula:}} archivo propio de causas, confianza verificable, contratos con brokers y contexto de "
    "cada usuario. {{Lo que no es foso:}} los modelos de IA, que cambiamos según precio y calidad.",
    size=10.5, color=INK2, anchor=MSO_ANCHOR.MIDDLE)
txt(s, M, 6.6, 8, 0.25, "✓ sí   ~ parcial   ✗ no", size=8.5, color=INK3)

# =================================================================== 13 · Go-to-market
s = new_slide(
    "Aquí entra la idea del «influencer»: el briefing diario que genera el producto se publica como vídeo y audio "
    "corto. Es un finfluencer con pruebas, con coste marginal casi cero. En paralelo, comunidad (MIAX, BME, foros) "
    "y pilotos B2B2C con brokers españoles. El embudo es el plan del año 1."
)
title(s, "Go-to-market")
txt(s, M, 1.18, W - 2 * M, 0.3, "{{Cabeza de playa:}} inversores autogestionados en España (25–45 años; Trade "
    "Republic, MyInvestor, eToro) → brokers españoles → Europa", size=11, color=INK2, font=SEMI)
gtm = [("1 · Contenido que se genera solo", [
    "El briefing diario se publica como vídeo y audio corto en TikTok, YouTube y Spotify: el «finfluencer con pruebas»",
    "Cada pieza enlaza al análisis completo con fuentes",
    "Coste marginal ≈ 0: lo produce el propio producto"]),
    ("2 · Comunidad y credibilidad", [
        "Ecosistema MIAX / Instituto BME y clubs de inversión universitarios",
        "Comunidades de inversión (Rankia, Finect, Discord, Telegram)",
        "Metodología pública y transparente"]),
    ("3 · Partnerships B2B2C", [
        "Pilotos con neobrokers y bancos españoles",
        "Widget en marca blanca + API / MCP",
        "Un caso de éxito abre el resto de Europa"])]
gw = (W - 2 * M - 2 * 0.2) / 3
for i, (h_, items) in enumerate(gtm):
    x = M + i * (gw + 0.2)
    card(s, x, 1.65, gw, 2.0)
    txt(s, x + 0.22, 1.8, gw - 0.4, 0.3, h_, size=12.5, color=INK, font=SEMI)
    txt(s, x + 0.22, 2.2, gw - 0.4, 1.4, ["· " + t for t in items], size=9.5, color=PS, spacing=1.12,
        space_after=4)
label(s, M, 3.85, 8, "Embudo necesario · mensual, año 1 (plan)", color=ACC)
fun = [("Alcance de contenido", "500K / mes"), ("Registros gratis", "5.000 / mes"), ("Activados", "2.500 / mes"),
       ("Nuevos Pro", "250 / mes"), ("CAC · ciclo", "€20 · 2 sem")]
fw = (W - 2 * M - 4 * 0.25) / 5
for i, (a, b) in enumerate(fun):
    x = M + i * (fw + 0.25)
    card(s, x, 4.15, fw, 0.75)
    txt(s, x + 0.18, 4.22, fw - 0.3, 0.25, a, size=9, color=INK3)
    txt(s, x + 0.18, 4.47, fw - 0.3, 0.35, b, size=13, color=ACC, font=HEAD, bold=True)
    if i < 4:
        arrow(s, x + fw + 0.03, 4.52, x + fw + 0.22, 4.52)
label(s, M, 5.1, 8, "Entrar con el briefing, crecer dentro de la cuenta", color=ACC)
le = ["Briefing diario (gratis)", "Investigaciones «¿por qué?» (Pro)", "Vigilancia de cartera",
      "Documentos y vídeo", "Piloto automático (partner)"]
for i, t in enumerate(le):
    x = M + i * (fw + 0.25)
    chip(s, x, 5.4, fw, t, fill=P_TINT if i == 0 else EL, line=P if i == 0 else LINE2,
         color=PS if i == 0 else INK2, size=9, h=0.42)
    if i < 4:
        arrow(s, x + fw + 0.03, 5.61, x + fw + 0.22, 5.61)
txt(s, M, 6.1, W - 2 * M, 0.4, "El mismo contexto del usuario en cada paso: cada nivel es un upsell sobre una "
    "relación que ya tenemos, con coste de adquisición casi cero.", size=10.5, color=INK2)

# =================================================================== 14 · Plan a 5 años
s = new_slide(
    "Un único plan en todas las slides. El año 1 sale de 2.500 suscriptores Pro y un broker piloto con 15.000 "
    "usuarios activos. A partir del año 3 el B2B2C pesa más que el B2C. El break-even llega en el mes 30. Todo "
    "salvo el año 1 son proyecciones."
)
title(s, "Plan a 5 años", "Caso base · un único plan, usado en todas las slides")
yrs = ["A1", "A2", "A3", "A4", "A5"]
prow = [("Suscriptores Pro (fin de año)", ["2.500", "9.000", "22.000", "45.000", "80.000"]),
        ("Brokers partner", ["1", "3", "7", "12", "18"]),
        ("Usuarios activos vía partners", ["15K", "90K", "300K", "700K", "1,4M"]),
        ("ARR (fin de año)", ["€0,4M", "€2,0M", "€5,9M", "€13,1M", "€25,2M"]),
        ("Margen bruto", ["62 %", "72 %", "77 %", "79 %", "80 %"]),
        ("EBITDA", ["−€0,6M", "−€0,8M", "€0,3M", "€2,6M", "€6,5M"]),
        ("Equipo (FTE)", ["7", "14", "26", "40", "58"])]
c0 = 4.0
cwy = (W - 2 * M - c0) / 5
card(s, M, 1.72, W - 2 * M, 0.5 + len(prow) * 0.44 + 0.1)
card(s, M + c0, 1.72, cwy, 0.5 + len(prow) * 0.44 + 0.1, fill=P_TINT, line=P)
for i, y_ in enumerate(yrs):
    txt(s, M + c0 + i * cwy, 1.85, cwy, 0.3, y_, size=11, color=ACC if i == 0 else INK2, font=SEMI,
        align=PP_ALIGN.CENTER)
for j, (name, vals) in enumerate(prow):
    yy = 2.25 + j * 0.44
    line(s, M + 0.2, yy - 0.02, W - M - 0.2, yy - 0.02)
    hl = name.startswith("ARR")
    txt(s, M + 0.25, yy + 0.08, c0 - 0.3, 0.3, name, size=10.5, color=INK if hl else INK2, font=SEMI if hl else BODY)
    for i, v in enumerate(vals):
        col = ACC if i == 0 else (INK if hl else INK2)
        txt(s, M + c0 + i * cwy, yy + 0.08, cwy, 0.3, v, size=11 if hl else 10.5, color=col,
            font=SEMI if (hl or i == 0) else BODY, align=PP_ALIGN.CENTER)
kk = [("Mes 30", "break-even"), ("€60K", "burn mensual máximo"), ("18 meses", "de runway con esta ronda")]
kw_ = (W - 2 * M - 2 * 0.2) / 3
for i, (b, sm) in enumerate(kk):
    kpi(s, M + i * (kw_ + 0.2), 5.58, kw_, 0.9, b, sm, big_size=22)
txt(s, M, 6.6, W - 2 * M, 0.35,
    "A1 = 2.500 Pro × €8,75 × 12 + 15K MAU × €1 × 12. A2–A5, break-even, burn y runway son proyecciones. Escenario "
    "conservador (mitad de crecimiento): ~€0,2M de ARR en A1; se retrasan contrataciones para mantener 18+ meses de "
    "runway.", size=8, color=INK3)

# =================================================================== 15 · Ronda
s = new_slide(
    "Pedimos €750K pre-seed para 18 meses. Referencia de valoración: €5M pre-money, por debajo de la mediana "
    "europea pre-seed/seed (€6M en el T1 2026). Uso de fondos: 45 % producto, 30 % crecimiento y partnerships, "
    "25 % cumplimiento, datos y runway. Hitos para la seed: 2.500 Pro, primer broker y €0,4M de ARR."
)
title(s, "Lo que levantamos")
card(s, 3.9, 1.45, 5.55, 1.35, fill=EL, line=LINE2)
badge(s, 4.1, 1.62, "€", d=0.42)
txt(s, 4.65, 1.6, 2.5, 0.35, "Financiación", size=15, color=INK, font=SEMI)
txt(s, 4.65, 1.98, 2.6, 0.6, ["Pre-seed equity", "Plan operativo de 18 meses"], size=9.5, color=INK2)
txt(s, 6.9, 1.55, 2.4, 1.0, "€750K", size=40, color=ACC, font=HEAD, bold=True, align=PP_ALIGN.RIGHT,
    anchor=MSO_ANCHOR.MIDDLE)
txt(s, M, 2.92, W - 2 * M, 0.3, "{{+ préstamo participativo ENISA}} (a solicitar)  ·  valoración de referencia: €5M "
    "pre-money (mediana pre-seed/seed en Europa: €6M, T1 2026)", size=10.5, color=INK2, align=PP_ALIGN.CENTER)
label(s, M, 3.45, 6, "Esta ronda nos lleva a", color=ACC)
mil = ["2.500 suscriptores Pro", "1.er broker en producción", "€0,4M de ARR", "Datos UE con licencia",
       "MiFID / AI Act ready", "Listos para la seed"]
mwid = (W - 2 * M - 5 * 0.15) / 6
for i, t in enumerate(mil):
    chip(s, M + i * (mwid + 0.15), 3.75, mwid, t, size=9, h=0.36)
txt(s, M, 4.35, 6, 0.35, "Uso de fondos", size=14, color=INK, font=SEMI)
uses = [("45 %", "Ingeniería y producto", "Datos con licencia, app móvil, integraciones con brokers (API/MCP) · "
         "2 AI/Data engineers"),
        ("30 %", "Crecimiento y partnerships", "Motor de contenido, pilotos B2B2C · Head of Partnerships"),
        ("25 %", "Cumplimiento, operaciones y runway", "Asesoría MiFID II / AI Act, compliance y cloud tras los "
         "créditos")]
uw = (W - 2 * M - 2 * 0.2) / 3
for i, (pct, h_, b_) in enumerate(uses):
    x = M + i * (uw + 0.2)
    card(s, x, 4.8, uw, 1.4)
    txt(s, x + 0.22, 4.92, 1.5, 0.6, pct, size=30, color=ACC, font=HEAD, bold=True)
    txt(s, x + 1.65, 5.02, uw - 1.85, 0.5, h_, size=11.5, color=INK, font=SEMI)
    txt(s, x + 0.22, 5.62, uw - 0.4, 0.75, b_, size=9.5, color=INK2)

# =================================================================== 16 · Gracias
s = new_slide("Cierre: repetir la frase de una línea y la ronda. Ofrecer la demo en vivo.", number=False)
s.shapes.add_picture(str(A / "cover_bg.png"), 0, 0, width=prs.slide_width, height=prs.slide_height)
pic(s, "logo_mark.png", 0.85, 1.25, 0.95)
txt(s, 2.0, 1.05, 8, 1.2, "Signal<<Room>>", size=64, color=INK, font=HEAD, bold=True, spacing=1.0)
s.shapes[-1].text_frame.paragraphs[0].runs[1].font.color.rgb = INK2
card(s, 0.85, 2.55, 8.6, 0.95, fill=SURFACE, line=LINE2, r=0.12)
txt(s, 1.1, 2.62, 8.2, 0.4, "Tu analista de mercados con IA", size=17, color=INK, font=HEAD, bold=True)
txt(s, 1.1, 3.02, 8.2, 0.35, "{{Levantando €750K pre-seed · producto funcionando con 12 agentes de IA}}", size=11.5,
    color=ACC, font=SEMI)
txt(s, 0.9, 4.25, 4, 0.5, "Gracias", size=22, color=INK, font=HEAD, bold=True)
line(s, 0.9, 4.8, 3.9, 4.8, color=INK, width=1.5)
txt(s, 0.9, 5.0, 7, 1.2, ["**Iván Nevado Martín** · CEO", "**Joseph Egusquiza** · CTO",
                          "**Gonzalo De Ramón Murillo** · CMO"], size=13, color=INK2, space_after=4)
txt(s, 0.9, 6.55, 8, 0.3, "Demo en vivo disponible · Proyecto MIAX, Instituto BME", size=10, color=INK3)

# =================================================================== 17 · Anexo objeciones
s = new_slide("Anexo: respuestas preparadas a las objeciones más habituales, sobre todo la regulatoria.")
title(s, "Anexo · Objeciones que escuchamos", "Cómo respondemos a lo que preguntan inversores y partners antes de "
      "decir que sí.")
obj = [("«¿Esto es asesoramiento financiero?»", "No: es research. Sin recomendaciones personalizadas; cualquier "
        "acción ocurre a través de partners con licencia y bajo mandato del usuario."),
       ("«¿Por qué no ChatGPT o Perplexity?»", "Responden cuando preguntas. SignalRoom vigila tus activos, investiga "
        "solo, puntúa la evidencia y entiende calls y webinars."),
       ("«¿Y las alucinaciones?»", "Las cifras se calculan en código, los modelos solo interpretan, las citas se "
        "verifican literalmente y cada afirmación enlaza su fuente."),
       ("«Los brokers harán el suyo.»", "La mayoría añade capas de preguntas y respuestas. Nosotros vendemos el motor "
        "de análisis en marca blanca: más rápido y barato que construirlo."),
       ("«¿Pagará la gente?»", "Motley Fool tiene 500K suscriptores a 99 $/año; Seeking Alpha cobra 299 $/año. Y el "
        "B2B2C monetiza a quien no paga."),
       ("«¿Y los datos de mercado?»", "El prototipo usa datos gratuitos; esta ronda presupuesta feeds europeos con "
        "licencia.")]
txt(s, M, 1.75, 4.3, 0.3, "OBJECIÓN", size=8.5, color=INK3, font=SEMI, spc=100)
txt(s, M + 4.5, 1.75, 4, 0.3, "NUESTRA RESPUESTA", size=8.5, color=ACC, font=SEMI, spc=100)
for j, (q, a) in enumerate(obj):
    yy = 2.1 + j * 0.66
    line(s, M, yy - 0.04, W - M, yy - 0.04)
    txt(s, M, yy + 0.1, 4.3, 0.5, q, size=11, color=INK, font=SEMI)
    txt(s, M + 4.5, yy + 0.1, W - 2 * M - 4.5, 0.55, a, size=10.5, color=INK2)
txt(s, M, 6.25, W - 2 * M, 0.3, "La IA escala el análisis. Las pruebas garantizan la confianza.", size=11.5,
    color=PS, font=SEMI)

prs.save(OUT)
print(f"OK -> {OUT} ({len(prs.slides)} slides)")
