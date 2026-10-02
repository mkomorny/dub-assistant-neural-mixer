"""Convert Dub Assistant markdown docs into print-ready PDF guides."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
FONTS = Path(r"C:\Windows\Fonts")

# Mixing-desk palette: cool aluminium, graphite chassis, one fader-cap accent.
PAPER = HexColor("#E8EBEE")
INK = HexColor("#14181C")
MUTED = HexColor("#4E5963")
GRAPHITE = HexColor("#161D22")
STEEL = HexColor("#2A333A")
FADER = HexColor("#E15A24")
TEAL = HexColor("#0E7A72")
RULE = HexColor("#B4BCC3")
ROW_ALT = HexColor("#F4F6F7")
TIP_BG = HexColor("#D7E8E6")
NOTE_BG = HexColor("#D6E0EA")
WARN_BG = HexColor("#F0D8D2")
IMP_BG = HexColor("#F3DDD2")
CODE_BG = HexColor("#161D22")
CODE_FG = HexColor("#C8DED9")

TRACK_COLORS = [
    "#FF5A36",
    "#3D8BFF",
    "#F2F2F2",
    "#C9A227",
    "#7A5C3C",
    "#9B59B6",
    "#E67E22",
    "#7F8C8D",
]

CALLOUT_STYLE = {
    "TIP": (TEAL, TIP_BG, "TIP"),
    "NOTE": (HexColor("#2B5F8A"), NOTE_BG, "NOTE"),
    "WARNING": (HexColor("#A33B24"), WARN_BG, "WARNING"),
    "IMPORTANT": (FADER, IMP_BG, "IMPORTANT"),
    "CAUTION": (HexColor("#A33B24"), WARN_BG, "CAUTION"),
}


def register_fonts() -> None:
    pairs = {
        "Agency": "AGENCYR.TTF",
        "Agency-Bold": "AGENCYB.TTF",
        "Lato": "Lato-Regular.ttf",
        "Lato-Bold": "Lato-Bold.ttf",
        "Lato-Italic": "Lato-Italic.ttf",
        "Lato-BoldItalic": "Lato-BoldItalic.ttf",
        "OCR": "OCRAEXT.TTF",
        "Fira": "FiraMono-Regular.ttf",
    }
    for name, filename in pairs.items():
        pdfmetrics.registerFont(TTFont(name, str(FONTS / filename)))
    pdfmetrics.registerFontFamily(
        "Lato",
        normal="Lato",
        bold="Lato-Bold",
        italic="Lato-Italic",
        boldItalic="Lato-BoldItalic",
    )


def styles() -> dict[str, ParagraphStyle]:
    return {
        "body": ParagraphStyle(
            "body",
            fontName="Lato",
            fontSize=9.6,
            leading=13.4,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "dek": ParagraphStyle(
            "dek",
            fontName="Lato-Italic",
            fontSize=11,
            leading=15,
            textColor=MUTED,
            spaceAfter=0,
        ),
        "h3": ParagraphStyle(
            "h3",
            fontName="Lato-Bold",
            fontSize=11,
            leading=14,
            textColor=TEAL,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "cell": ParagraphStyle(
            "cell",
            fontName="Lato",
            fontSize=8.4,
            leading=11.2,
            textColor=INK,
        ),
        "cell_head": ParagraphStyle(
            "cell_head",
            fontName="Lato-Bold",
            fontSize=8.2,
            leading=11,
            textColor=white,
        ),
        "li": ParagraphStyle(
            "li",
            fontName="Lato",
            fontSize=9.4,
            leading=12.8,
            textColor=INK,
        ),
        "callout": ParagraphStyle(
            "callout",
            fontName="Lato",
            fontSize=9.2,
            leading=12.6,
            textColor=INK,
        ),
        "code": ParagraphStyle(
            "code",
            fontName="Fira",
            fontSize=8,
            leading=11,
            textColor=CODE_FG,
        ),
        "caption": ParagraphStyle(
            "caption",
            fontName="Lato",
            fontSize=8,
            leading=10.5,
            textColor=MUTED,
        ),
    }


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

@dataclass
class Block:
    kind: str
    text: str = ""
    level: int = 0
    items: list = field(default_factory=list)
    ordered: bool = False
    rows: list = field(default_factory=list)
    callout: str = ""
    language: str = ""


def parse_markdown(source: str) -> list[Block]:
    source = re.sub(r"<!--.*?-->", "", source, flags=re.S)
    lines = source.replace("\r\n", "\n").split("\n")
    blocks: list[Block] = []
    i = 0
    n = len(lines)

    def take_fence() -> Block:
        nonlocal i
        lang = lines[i][3:].strip()
        i += 1
        body: list[str] = []
        while i < n and not lines[i].startswith("```"):
            body.append(lines[i])
            i += 1
        if i < n:
            i += 1
        return Block(kind="code", text="\n".join(body), language=lang)

    def take_table() -> Block:
        nonlocal i
        rows: list[list[str]] = []
        while i < n and "|" in lines[i] and lines[i].strip():
            raw = lines[i].strip()
            if re.match(r"^\|?\s*:?-{3,}", raw):
                i += 1
                continue
            cells = [c.strip() for c in raw.strip("|").split("|")]
            rows.append(cells)
            i += 1
        return Block(kind="table", rows=rows)

    def take_callout() -> Block:
        nonlocal i
        first = lines[i].lstrip()
        m = re.match(r">\s*\[!(\w+)\]\s*$", first)
        kind = m.group(1).upper() if m else "NOTE"
        if m:
            i += 1
        body: list[str] = []
        while i < n and lines[i].lstrip().startswith(">"):
            body.append(re.sub(r"^\s*>\s?", "", lines[i]))
            i += 1
        return Block(kind="callout", text=" ".join(p.strip() for p in body if p.strip()), callout=kind)

    def take_list() -> Block:
        nonlocal i
        items: list[str] = []
        ordered = bool(re.match(r"\s*\d+\.\s", lines[i]))
        item_re = re.compile(r"\s*\d+\.\s+(.*)" if ordered else r"\s*[-*]\s+(.*)")
        while i < n:
            m = item_re.match(lines[i])
            if not m:
                break
            items.append(m.group(1).strip())
            i += 1
            while i < n:
                nxt = lines[i]
                if not nxt.strip():
                    j = i + 1
                    while j < n and not lines[j].strip():
                        j += 1
                    if j < n and (item_re.match(lines[j]) or re.match(r"\s{2,}\S", lines[j])):
                        i += 1
                        continue
                    break
                if item_re.match(nxt):
                    break
                stripped = nxt.strip()
                if stripped.startswith("#") or stripped.startswith("```") or stripped.startswith("|"):
                    break
                if (not ordered and re.match(r"\s*[-*]\s", nxt)) or (
                    ordered and re.match(r"\s*[-*]\s", nxt)
                ):
                    break
                items[-1] += " " + stripped
                i += 1
        return Block(kind="list", items=items, ordered=ordered)

    while i < n:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("```"):
            blocks.append(take_fence())
            continue
        if stripped.startswith(">") and (re.match(r">\s*\[!", stripped) or (
            blocks and False
        ) or stripped.startswith(">")):
            if stripped.startswith(">"):
                blocks.append(take_callout())
                continue
        if stripped.startswith("|") or (
            "|" in stripped and i + 1 < n and re.match(r"^\s*\|?\s*:?-{3,}", lines[i + 1])
        ):
            blocks.append(take_table())
            continue
        if re.match(r"#{1,3}\s+", stripped):
            hashes, title = stripped.split(None, 1)
            blocks.append(Block(kind="heading", text=title.strip(), level=len(hashes)))
            i += 1
            continue
        if re.match(r"\s*\d+\.\s", line) or re.match(r"\s*[-*]\s", line):
            blocks.append(take_list())
            continue
        para: list[str] = []
        while i < n and lines[i].strip():
            nxt = lines[i].strip()
            if nxt.startswith("#") or nxt.startswith("```") or nxt.startswith(">") or nxt.startswith("|"):
                break
            if re.match(r"\d+\.\s", nxt) or re.match(r"[-*]\s", nxt):
                break
            para.append(nxt)
            i += 1
        if para:
            blocks.append(Block(kind="para", text=" ".join(para)))
    return blocks


_INLINE = re.compile(
    r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|(?<!\*)\*(?!\*)([^*]+)\*(?!\*))"
)


def inline_xml(text: str) -> str:
    parts: list[str] = []
    last = 0
    for match in _INLINE.finditer(text):
        parts.append(_escape(text[last : match.start()]))
        token = match.group(0)
        if token.startswith("**"):
            parts.append(f"<b>{_escape(token[2:-2])}</b>")
        elif token.startswith("`"):
            inner = _escape(token[1:-1])
            parts.append(
                f'<font name="Lato" size="8.5" color="#0E7A72">{inner}</font>'
            )
        elif token.startswith("["):
            label, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token).groups()
            label = _escape(_pretty_link_label(label, url))
            parts.append(f'<font color="#0E7A72"><b>{label}</b></font>')
        else:
            inner = match.group(2) if match.group(2) is not None else token.strip("*")
            parts.append(f"<i>{_escape(inner)}</i>")
        last = match.end()
    parts.append(_escape(text[last:]))
    return "".join(parts)


def _pretty_link_label(label: str, url: str) -> str:
    name = Path(url).name.lower()
    mapping = {
        "user-guide.md": "User Guide",
        "operator-card.md": "Operator Card",
        "template-set.md": "Template Set",
        "readme.md": "Install Guide",
        "../readme.md": "Install Guide",
    }
    if name in mapping:
        return mapping[name]
    if url.lower().endswith(".md"):
        return label.replace(".md", "")
    return label


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# ---------------------------------------------------------------------------
# Flowables
# ---------------------------------------------------------------------------

class HeadingStrip(Flowable):
    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text.upper()

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = 26
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(GRAPHITE)
        c.rect(0, 4, self.width, 18, fill=1, stroke=0)
        c.setFillColor(FADER)
        c.rect(0, 4, 5, 18, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Agency-Bold", 11)
        c.drawString(14, 8.5, self.text)


class TitleBlock(Flowable):
    def __init__(self, eyebrow: str, title: str, dek: str, sty: dict) -> None:
        super().__init__()
        self.eyebrow = eyebrow.upper()
        self.title = title.upper()
        self.dek = Paragraph(dek, sty["dek"])

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        dw, dh = self.dek.wrap(availWidth, availHeight)
        self._dek_h = dh
        self.height = 78 + dh
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(FADER)
        c.rect(0, self.height - 4, 36, 4, fill=1, stroke=0)
        c.setFillColor(TEAL)
        c.setFont("OCR", 7)
        c.drawString(0, self.height - 22, self.eyebrow)
        c.setFillColor(INK)
        c.setFont("Agency-Bold", 28)
        c.drawString(0, self.height - 54, self.title)
        self.dek.drawOn(c, 0, 0)


class CalloutBox(Flowable):
    def __init__(self, kind: str, body: Paragraph) -> None:
        super().__init__()
        color, bg, label = CALLOUT_STYLE.get(kind, CALLOUT_STYLE["NOTE"])
        self.color = color
        self.bg = bg
        self.label = label
        self.body = body

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        bw, bh = self.body.wrap(availWidth - 28, availHeight)
        self._bh = bh
        self.height = bh + 28
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(self.bg)
        c.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        c.setFillColor(self.color)
        c.rect(0, 0, 5, self.height, fill=1, stroke=0)
        c.setFont("OCR", 6.5)
        c.drawString(14, self.height - 14, self.label)
        self.body.drawOn(c, 14, 8)


class CodeBlock(Flowable):
    def __init__(self, text: str, sty: ParagraphStyle) -> None:
        super().__init__()
        self.lines = text.splitlines() or [""]
        self.sty = sty

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = 16 + 11 * len(self.lines)
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(CODE_BG)
        c.roundRect(0, 0, self.width, self.height, 2, fill=1, stroke=0)
        c.setFillColor(FADER)
        c.rect(0, 0, 4, self.height, fill=1, stroke=0)
        c.setFillColor(CODE_FG)
        c.setFont("Fira", 7.5)
        y = self.height - 14
        max_chars = max(8, int((self.width - 20) / 4.5))
        for line in self.lines:
            shown = line if len(line) <= max_chars else line[: max_chars - 1] + "…"
            c.drawString(14, y, shown)
            y -= 11


class Rule(Flowable):
    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        self.height = 10
        return self.width, self.height

    def draw(self):
        self.canv.setStrokeColor(RULE)
        self.canv.setLineWidth(0.4)
        self.canv.line(0, 5, self.width, 5)


class Swatch(Flowable):
    def __init__(self, hex_color: str) -> None:
        super().__init__()
        raw = hex_color.strip().strip("`").lstrip("#")
        if len(raw) == 6:
            self.color = Color(
                int(raw[0:2], 16) / 255,
                int(raw[2:4], 16) / 255,
                int(raw[4:6], 16) / 255,
            )
        else:
            self.color = RULE

    def wrap(self, availWidth, availHeight):
        self.width = 14
        self.height = 11
        return self.width, self.height

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(1, 1, 11, 9, fill=1, stroke=0)
        self.canv.setStrokeColor(STEEL)
        self.canv.setLineWidth(0.5)
        self.canv.rect(1, 1, 11, 9, fill=0, stroke=1)


class GuideList(Flowable):
    def __init__(self, items: list[str], ordered: bool, sty: dict) -> None:
        super().__init__()
        self.ordered = ordered
        self.paras = [Paragraph(inline_xml(item), sty["li"]) for item in items]

    def wrap(self, availWidth, availHeight):
        self.width = availWidth
        marker = 20
        self._heights = []
        total = 2
        for para in self.paras:
            _, h = para.wrap(availWidth - marker, availHeight)
            h = max(h, 12)
            self._heights.append(h)
            total += h + 5
        self.height = total
        return self.width, self.height

    def draw(self):
        y = self.height - 2
        for i, para in enumerate(self.paras):
            h = self._heights[i]
            y -= h
            if self.ordered:
                self.canv.setFillColor(FADER)
                self.canv.setFont("Lato-Bold", 8.5)
                self.canv.drawRightString(14, y + h - 10, str(i + 1))
            else:
                self.canv.setFillColor(FADER)
                self.canv.rect(6, y + h - 11, 5.5, 5.5, fill=1, stroke=0)
            para.drawOn(self.canv, 20, y)
            y -= 5


# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------

def draw_ticks(c: pdfcanvas.Canvas, x: float, y: float, h: float = 10) -> float:
    for color in TRACK_COLORS:
        c.setFillColor(HexColor(color))
        c.rect(x, y, 7, h, fill=1, stroke=0)
        c.setStrokeColor(GRAPHITE)
        c.setLineWidth(0.3)
        c.rect(x, y, 7, h, fill=0, stroke=1)
        x += 9
    return x


def make_on_page(doc_title: str):
    def _on_page(c: pdfcanvas.Canvas, doc) -> None:
        w, h = letter
        c.saveState()
        c.setFillColor(PAPER)
        c.rect(0, 0, w, h, fill=1, stroke=0)

        c.setFillColor(GRAPHITE)
        c.rect(0, h - 34, w, 34, fill=1, stroke=0)
        c.setFillColor(FADER)
        c.rect(0, h - 36, w, 2, fill=1, stroke=0)
        x = draw_ticks(c, 16, h - 24, 10)
        c.setFillColor(white)
        c.setFont("Agency-Bold", 11)
        c.drawString(x + 10, h - 22, "DUB ASSISTANT")
        c.setFillColor(HexColor("#8C979F"))
        c.setFont("OCR", 6.5)
        c.drawRightString(w - 16, h - 21, doc_title.upper())

        c.setFillColor(GRAPHITE)
        c.rect(0, 0, w, 22, fill=1, stroke=0)
        c.setFillColor(HexColor("#8C979F"))
        c.setFont("OCR", 6)
        c.drawString(16, 8, "SEND A   |   HEART   |   DRY/WET")
        c.drawRightString(w - 16, 8, f"{doc.page:02d}")
        c.restoreState()

    return _on_page


def build_table(rows: list[list[str]], avail: float, sty: dict) -> Table:
    if not rows:
        return Table([[""]])
    cols = max(len(r) for r in rows)
    norm = [r + [""] * (cols - len(r)) for r in rows]
    headers = [cell.lower() for cell in norm[0]]
    if cols == 2 and headers[0] in {"file", "message", "track"}:
        first = 2.45 * inch
        widths = [first, avail - first]
    elif cols == 2:
        widths = [1.55 * inch, avail - 1.55 * inch]
    elif cols == 3:
        widths = [1.15 * inch, 1.55 * inch, avail - 2.7 * inch]
    elif cols == 4:
        widths = [0.85 * inch, 0.85 * inch, 0.85 * inch, avail - 2.55 * inch]
    else:
        widths = [avail / cols] * cols

    swatches = cols == 2 and headers == ["track", "hex"]
    data = []
    for i, row in enumerate(norm):
        style = sty["cell_head"] if i == 0 else sty["cell"]
        cells = [Paragraph(inline_xml(cell), style) for cell in row]
        if swatches and i > 0:
            label = Table(
                [[Swatch(row[1]), Paragraph(inline_xml(row[0]), style)]],
                colWidths=[16, widths[0] - 16],
            )
            label.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            cells[0] = label
        data.append(cells)

    table = Table(data, colWidths=widths, repeatRows=1)
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), GRAPHITE),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 3 if swatches else 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 if swatches else 5),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, RULE),
        ("BACKGROUND", (0, 1), (-1, -1), white),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            commands.append(("BACKGROUND", (0, i), (-1, i), ROW_ALT))
    table.setStyle(TableStyle(commands))
    return table


def story_from_blocks(
    blocks: list[Block],
    eyebrow: str,
    title: str,
    dek: str,
    sty: dict,
    avail: float,
) -> list:
    story: list = [
        Spacer(1, 8),
        TitleBlock(eyebrow, title, dek, sty),
        Spacer(1, 14),
        Rule(),
        Spacer(1, 10),
    ]
    skipped_h1 = False
    pending_keep: list = []

    def flush_keep(extra=None):
        nonlocal pending_keep
        items = pending_keep + ([extra] if extra is not None else [])
        pending_keep = []
        if not items:
            return
        if len(items) == 1:
            story.append(items[0])
        else:
            story.append(KeepTogether(items))

    for block in blocks:
        if block.kind == "heading" and block.level == 1 and not skipped_h1:
            skipped_h1 = True
            continue
        if block.kind == "heading" and block.level == 2:
            flush_keep()
            pending_keep = [Spacer(1, 8), HeadingStrip(block.text), Spacer(1, 8)]
            continue
        if block.kind == "heading":
            flush_keep()
            story.append(Paragraph(inline_xml(block.text), sty["h3"]))
            continue

        flow: Flowable
        if block.kind == "para":
            flow = Paragraph(inline_xml(block.text), sty["body"])
        elif block.kind == "list":
            flow = KeepTogether([GuideList(block.items, block.ordered, sty), Spacer(1, 8)])
        elif block.kind == "table":
            flush_keep()
            story.append(build_table(block.rows, avail, sty))
            story.append(Spacer(1, 10))
            continue
        elif block.kind == "callout":
            flow = KeepTogether(
                [
                    CalloutBox(block.callout, Paragraph(inline_xml(block.text), sty["callout"])),
                    Spacer(1, 10),
                ]
            )
        elif block.kind == "code":
            flow = KeepTogether([CodeBlock(block.text, sty["code"]), Spacer(1, 10)])
        else:
            continue

        if pending_keep:
            flush_keep(flow)
        else:
            story.append(flow)

    flush_keep()
    return story


def write_flow_guide(
    src: Path,
    dst: Path,
    eyebrow: str,
    title: str,
    dek: str,
) -> None:
    sty = styles()
    blocks = parse_markdown(src.read_text(encoding="utf-8"))
    left = right = 0.7 * inch
    avail = letter[0] - left - right
    story = story_from_blocks(blocks, eyebrow, title, dek, sty, avail)

    doc = BaseDocTemplate(
        str(dst),
        pagesize=letter,
        leftMargin=left,
        rightMargin=right,
        topMargin=0.72 * inch,
        bottomMargin=0.48 * inch,
        title=f"Dub Assistant — {title}",
        author="Dub Assistant",
        subject=dek,
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        id="normal",
        showBoundary=0,
    )
    doc.addPageTemplates(
        [PageTemplate(id="guide", frames=frame, onPage=make_on_page(title))]
    )
    doc.build(story)


# ---------------------------------------------------------------------------
# Operator card (single landscape page)
# ---------------------------------------------------------------------------

def wrap_text(c: pdfcanvas.Canvas, text: str, font: str, size: float, max_w: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = word if not cur else f"{cur} {word}"
        if c.stringWidth(trial, font, size) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def draw_strip(c: pdfcanvas.Canvas, x: float, y: float, w: float, label: str) -> None:
    c.setFillColor(GRAPHITE)
    c.rect(x, y, w, 18, fill=1, stroke=0)
    c.setFillColor(FADER)
    c.rect(x, y, 5, 18, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Agency-Bold", 10)
    c.drawString(x + 12, y + 5, label.upper())


def draw_card_table(
    c: pdfcanvas.Canvas,
    x: float,
    y_top: float,
    w: float,
    rows: list[tuple[str, str]],
    col0: float,
) -> float:
    row_h_min = 26
    y = y_top
    c.setFillColor(GRAPHITE)
    c.rect(x, y - 18, w, 18, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Lato-Bold", 8)
    c.drawString(x + 8, y - 12, rows[0][0].upper())
    c.drawString(x + col0, y - 12, rows[0][1].upper())
    y -= 18
    for i, (a, b) in enumerate(rows[1:]):
        b_lines = wrap_text(c, b, "Lato", 8.6, w - col0 - 12)
        rh = max(row_h_min, 10 + 11 * len(b_lines))
        y -= rh
        c.setFillColor(white if i % 2 == 0 else ROW_ALT)
        c.rect(x, y, w, rh, fill=1, stroke=0)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.3)
        c.line(x, y, x + w, y)
        c.setFillColor(FADER)
        c.setFont("Lato-Bold", 8.6)
        c.drawString(x + 8, y + rh - 15, a)
        c.setFillColor(INK)
        c.setFont("Lato", 8.6)
        ty = y + rh - 15
        for line in b_lines:
            c.drawString(x + col0, ty, line)
            ty -= 11
    return y


def write_operator_card(dst: Path) -> None:
    w, h = landscape(letter)
    c = pdfcanvas.Canvas(
        str(dst),
        pagesize=landscape(letter),
        title="Dub Assistant — Operator Card",
        author="Dub Assistant",
    )
    # paper
    c.setFillColor(PAPER)
    c.rect(0, 0, w, h, fill=1, stroke=0)

    # header chassis
    c.setFillColor(GRAPHITE)
    c.rect(0, h - 52, w, 52, fill=1, stroke=0)
    c.setFillColor(FADER)
    c.rect(0, h - 54, w, 2, fill=1, stroke=0)
    x = draw_ticks(c, 22, h - 36, 14)
    c.setFillColor(white)
    c.setFont("Agency-Bold", 20)
    c.drawString(x + 12, h - 34, "DUB ASSISTANT")
    c.setFillColor(HexColor("#8C979F"))
    c.setFont("OCR", 8)
    c.drawRightString(w - 22, h - 24, "OPERATOR CARD")
    c.setFont("Lato", 8)
    c.drawRightString(w - 22, h - 40, "One page for the desk")
    c.setFillColor(HexColor("#8C979F"))
    c.setFont("Lato", 8)
    c.drawString(x + 12, h - 46, "Full procedures: User Guide   ·   Install: Install Guide")

    margin = 22
    gutter = 16
    col_w = (w - margin * 2 - gutter) / 2
    left = margin
    right = margin + col_w + gutter
    top = h - 72
    bottom = 28

    # footer
    c.setFillColor(GRAPHITE)
    c.rect(0, 0, w, 20, fill=1, stroke=0)
    c.setFillColor(HexColor("#8C979F"))
    c.setFont("OCR", 6)
    c.drawString(22, 7, "SEND A   |   HEART   |   DRY/WET")
    c.drawRightString(w - 22, 7, "DESK SHEET")

    # LEFT: before play
    y = top
    draw_strip(c, left, y - 18, col_w, "Before play")
    y -= 28
    steps = [
        "MIDI track Dub Assistant holds the device. Not in the audio path.",
        "Audio tracks named Drums Bass Vox Keys Guitar FX Perc Other.",
        "Return A = Delay. Device writes send A.",
        "Click Bind. Want bound 8/8 tracks.",
        "Load your CSV, then Train. Or Learn this! at least 8 times first.",
    ]
    for i, step in enumerate(steps, start=1):
        lines = wrap_text(c, step, "Lato", 9, col_w - 30)
        c.setFillColor(FADER)
        c.circle(left + 11, y - 4, 8, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Lato-Bold", 8)
        c.drawCentredString(left + 11, y - 7, str(i))
        c.setFillColor(INK)
        c.setFont("Lato", 9)
        ty = y - 7
        for line in lines:
            c.drawString(left + 26, ty, line)
            ty -= 12
        y = ty - 8

    y -= 6
    box_h = 58
    c.setFillColor(IMP_BG)
    c.rect(left, y - box_h, col_w, box_h, fill=1, stroke=0)
    c.setFillColor(FADER)
    c.rect(left, y - box_h, 5, box_h, fill=1, stroke=0)
    c.setFont("OCR", 6.5)
    c.drawString(left + 14, y - 15, "TAKE THE MIXER BACK")
    c.setFillColor(INK)
    c.setFont("Lato", 9)
    back = "Drop Dry/Wet to 0. Writes stop. Snapshot is taken again the next time you raise it."
    ty = y - 30
    for line in wrap_text(c, back, "Lato", 9, col_w - 24):
        c.drawString(left + 14, ty, line)
        ty -= 12
    y = y - box_h - 16

    draw_strip(c, left, y - 18, col_w, "If nothing moves")
    y -= 30
    fails = [
        "Dry/Wet is at 0.",
        "Transport is stopped (faders need play; sends still follow knobs).",
        "Bind is 0/8. Rename tracks.",
        "dub-assistant.js is not beside the .amxd.",
    ]
    for item in fails:
        c.setFillColor(FADER)
        c.rect(left + 4, y - 3, 6, 6, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont("Lato", 9)
        lines = wrap_text(c, item, "Lato", 9, col_w - 22)
        ty = y - 4
        for line in lines:
            c.drawString(left + 16, ty, line)
            ty -= 12
        y = ty - 7

    # bottom reminder across both columns
    banner_y = 32
    c.setFillColor(WARN_BG)
    c.rect(margin, banner_y, w - margin * 2, 28, fill=1, stroke=0)
    c.setFillColor(HexColor("#A33B24"))
    c.rect(margin, banner_y, 5, 28, fill=1, stroke=0)
    c.setFont("OCR", 6)
    c.drawString(margin + 14, banner_y + 16, "WHILE YOU SET UP")
    c.setFillColor(INK)
    c.setFont("Lato", 8.5)
    c.drawString(
        margin + 14,
        banner_y + 5,
        "Leave Dry/Wet at 0% while you set up tracks, record, or edit clips. The device writes volume and send A whenever Dry/Wet is up and transport is running.",
    )

    # RIGHT: knobs + buttons
    y = top
    draw_strip(c, right, y - 18, col_w, "Knobs")
    y -= 22
    knobs = [
        ("Control", "Job"),
        ("col", "Colour / wetness. Drives the eight sends."),
        ("rhy", "How isolated and rhythmic the cuts feel."),
        ("dyn", "How hard faders jump when they move."),
        ("Heart", "Scales motion on Drums and Bass only. 0 = they hold."),
        ("Dry/Wet", "0 = you own the mixer. 100 = full assistant."),
    ]
    y = draw_card_table(c, right, y, col_w, knobs, 68)

    y -= 16
    draw_strip(c, right, y - 18, col_w, "Buttons")
    y -= 22
    buttons = [
        ("Button", "Job"),
        ("Learn this!", "Save this knob + send/prob/dyn snapshot as a row."),
        ("Train", "Fit the network. Blocked below 8 rows. Aim for 100+."),
        ("Bind", "Re-find tracks by name after you rename or reload."),
        ("Save / Load", "Dataset CSV. Keep it next to the Live Set."),
        ("Clear", "Wipe the dataset in memory. Does not delete the file."),
        ("1/4 / 1/8", "Fader grid. Eighths are the default dub feel."),
    ]
    draw_card_table(c, right, y, col_w, buttons, 82)

    c.showPage()
    c.save()


def main() -> None:
    register_fonts()
    guides = [
        {
            "src": ROOT / "docs" / "USER-GUIDE.md",
            "dst": ROOT / "docs" / "USER-GUIDE.pdf",
            "eyebrow": "Performance",
            "title": "User Guide",
            "dek": "How to train the network, perform with five knobs, and map a Launchkey.",
        },
        {
            "src": ROOT / "README.md",
            "dst": ROOT / "docs" / "INSTALL-GUIDE.pdf",
            "eyebrow": "Setup",
            "title": "Install Guide",
            "dek": "Install the device, run the first-load check, and rebuild after you edit the engine.",
        },
        {
            "src": ROOT / "template" / "TEMPLATE-SET.md",
            "dst": ROOT / "docs" / "TEMPLATE-SET.pdf",
            "eyebrow": "Session",
            "title": "Template Set",
            "dek": "The eight-track, two-return Live Set this device expects, including optional stems.",
        },
    ]
    for spec in guides:
        write_flow_guide(
            spec["src"],
            spec["dst"],
            spec["eyebrow"],
            spec["title"],
            spec["dek"],
        )
        print(f"wrote {spec['dst'].relative_to(ROOT)}")

    card = ROOT / "docs" / "OPERATOR-CARD.pdf"
    write_operator_card(card)
    print(f"wrote {card.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
