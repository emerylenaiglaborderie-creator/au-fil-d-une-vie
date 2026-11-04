"""Mise en page du livre de famille en PDF (ReportLab, pur Python).

Couverture, sommaire, un chapitre par piste, renvois « Voir aussi » avec numéros de
page, index des mots-clés (`SimpleIndex`). `multiBuild` relance la mise en page
jusqu'à ce que sommaire, index et numéros de page soient stables.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    CondPageBreak,
    Flowable,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import SimpleIndex, TableOfContents

from au_fil_d_une_vie import i18n
from au_fil_d_une_vie.i18n import _, plural
from au_fil_d_une_vie.services.book import Book, BookStory

INK = colors.HexColor("#2F2F2F")
THREAD = colors.HexColor("#444444")
RED = colors.HexColor("#C73A45")
RED_SHADOW = colors.HexColor("#8F2530")
RED_TEXT = colors.HexColor("#B0303B")
GREEN_TEXT = colors.HexColor("#3E6B2A")
SOFT_GREEN = colors.HexColor("#F1F6E4")
SOFT_GREEN_BORDER = colors.HexColor("#DCE7C3")
MUTED = colors.HexColor("#5B5B5B")

MARGIN = 18 * mm


@dataclass(frozen=True)
class BookAssets:
    fonts_dir: Path
    logo: Path


def long_date(value: Any) -> str:
    local = value.astimezone()
    return i18n.long_date(local.day, local.month, local.year)


def _register_fonts(fonts_dir: Path) -> None:
    for name, file in (
        ("Lora", "Lora-Variable.ttf"),
        ("Lora-Italic", "Lora-Italic-Variable.ttf"),
        ("Jost", "Jost-Variable.ttf"),
        ("Sacramento", "Sacramento-Regular.ttf"),
    ):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(fonts_dir / file)))
    pdfmetrics.registerFontFamily(
        "Lora", normal="Lora", italic="Lora-Italic", bold="Lora", boldItalic="Lora-Italic"
    )


def _styles() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle("base", fontName="Lora", fontSize=10.5, leading=16, textColor=INK)
    return {
        "body": ParagraphStyle("body", base, alignment=TA_JUSTIFY, spaceAfter=7),
        "question": ParagraphStyle("question", base, fontSize=17, leading=22, spaceAfter=2),
        # Sacramento a de longs jambages : interlignes et espaces généreux.
        "teller": ParagraphStyle(
            "teller",
            fontName="Sacramento",
            fontSize=24,
            leading=30,
            textColor=RED_TEXT,
            spaceBefore=2,
            spaceAfter=6,
        ),
        "meta": ParagraphStyle(
            "meta", fontName="Jost", fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=10
        ),
        "eyebrow": ParagraphStyle(
            "eyebrow", fontName="Jost", fontSize=8, leading=10, textColor=GREEN_TEXT
        ),
        "chapter": ParagraphStyle(
            "chapter", fontName="Sacramento", fontSize=46, leading=54, textColor=INK, spaceAfter=18
        ),
        "title": ParagraphStyle(
            "title",
            fontName="Sacramento",
            fontSize=40,
            leading=48,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            base,
            fontName="Lora-Italic",
            fontSize=13,
            alignment=TA_CENTER,
            textColor=MUTED,
        ),
        "small_center": ParagraphStyle(
            "small_center",
            fontName="Jost",
            fontSize=9,
            leading=13,
            alignment=TA_CENTER,
            textColor=MUTED,
        ),
        "note": ParagraphStyle("note", base, fontName="Lora-Italic", fontSize=10, leading=15),
        "words": ParagraphStyle(
            "words", fontName="Jost", fontSize=8.5, leading=12, textColor=GREEN_TEXT, spaceBefore=4
        ),
        "toc1": ParagraphStyle("toc1", base, fontSize=12, leading=18, spaceBefore=8),
        "toc2": ParagraphStyle(
            "toc2", base, fontName="Lora-Italic", fontSize=10, leading=14, leftIndent=12
        ),
        "index": ParagraphStyle("index", base, fontSize=10, leading=14),
    }


class ThreadOrnament(Flowable):
    """Fil qui fait une boucle et finit par un point rouge (séparateur de récits)."""

    def __init__(self, width: float = 60 * mm, height: float = 12 * mm) -> None:
        super().__init__()
        self.width, self.height = width, height

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        self._offset = (avail_width - self.width) / 2
        return avail_width, self.height

    def draw(self) -> None:
        c = self.canv
        x0, y = self._offset, self.height / 2
        w = self.width
        c.setStrokeColor(THREAD)
        c.setLineWidth(1)
        c.setLineCap(1)
        path = c.beginPath()
        path.moveTo(x0, y)
        path.curveTo(x0 + w * 0.3, y + 2, x0 + w * 0.5, y - 2, x0 + w * 0.62, y)
        path.curveTo(x0 + w * 0.9, y + 1, x0 + w * 0.82, y + 9, x0 + w * 0.74, y + 6)
        path.curveTo(x0 + w * 0.68, y + 3, x0 + w * 0.78, y - 4, x0 + w - 4, y)
        c.drawPath(path, stroke=1, fill=0)
        c.setFillColor(RED_SHADOW)
        c.circle(x0 + w - 2, y - 0.8, 3, stroke=0, fill=1)
        c.setFillColor(RED)
        c.circle(x0 + w - 2, y, 3, stroke=0, fill=1)


class StoryAnchor(Flowable):
    """Repère invisible au début d'un récit : sa page est notée pour les renvois."""

    def __init__(self, story_id: int, title: str) -> None:
        super().__init__()
        self.story_id = story_id
        self.title = title

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        return 0, 0

    def draw(self) -> None:
        key = f"recit-{self.story_id}"
        self.canv.bookmarkPage(key)
        self.canv.addOutlineEntry(self.title, key, level=1)


class SeeAlsoLine(Flowable):
    """« Voir aussi » : titre du récit lié, points de conduite et numéro de page."""

    HEIGHT = 15

    def __init__(self, target: int, text: str, pages: dict[int, int]) -> None:
        super().__init__()
        self.target, self.text, self.pages = target, text, pages

    def wrap(self, avail_width: float, avail_height: float) -> tuple[float, float]:
        self.width = avail_width
        return avail_width, self.HEIGHT

    def draw(self) -> None:
        c = self.canv
        page = str(self.pages.get(self.target, ""))
        c.setFont("Jost", 9)
        page_width = c.stringWidth(page, "Jost", 9)
        c.setFont("Lora-Italic", 9.5)
        text = self.text
        room = self.width - page_width - 30
        while text and c.stringWidth(text, "Lora-Italic", 9.5) > room:
            text = text[:-2].rstrip() + "…"
            if len(text) < 4:
                break
        c.setFillColor(INK)
        c.drawString(10, 3, text)
        start = 10 + c.stringWidth(text, "Lora-Italic", 9.5) + 6
        c.setFillColor(MUTED)
        c.setFont("Jost", 9)
        dots = ""
        while c.stringWidth(dots + " .", "Jost", 9) < self.width - page_width - 6 - start:
            dots += " ."
        c.drawString(start, 3, dots)
        c.drawRightString(self.width, 3, page)
        c.setFillColor(RED)
        c.circle(3, 6, 2.2, stroke=0, fill=1)
        c.linkRect("", f"recit-{self.target}", (0, 0, self.width, self.HEIGHT), relative=1)


class BookTemplate(BaseDocTemplate):
    def __init__(self, path: str, pages: dict[int, int], **kwargs: Any) -> None:
        super().__init__(path, pagesize=A5, **kwargs)
        self.pages = pages
        width, height = A5
        frame = Frame(
            MARGIN, MARGIN + 6 * mm, width - 2 * MARGIN, height - 2 * MARGIN - 6 * mm, id="f"
        )
        self.addPageTemplates(
            [
                PageTemplate(id="cover", frames=[frame]),
                PageTemplate(id="page", frames=[frame], onPage=self._footer),
            ]
        )

    def afterFlowable(self, flowable: Flowable) -> None:  # noqa: N802 (nom imposé par ReportLab)
        if isinstance(flowable, StoryAnchor):
            self.pages[flowable.story_id] = self.page
            self.notify(
                "TOCEntry", (1, escape(flowable.title), self.page, f"recit-{flowable.story_id}")
            )
        elif isinstance(flowable, Paragraph) and getattr(flowable, "chapter_key", None):
            key = flowable.chapter_key
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(flowable.getPlainText(), key, level=0)
            self.notify("TOCEntry", (0, escape(flowable.getPlainText()), self.page, key))

    @staticmethod
    def _footer(canvas: Any, doc: Any) -> None:
        width, _height = A5
        canvas.saveState()
        canvas.setFont("Jost", 8)
        canvas.setFillColor(MUTED)
        canvas.drawCentredString(width / 2, MARGIN - 4 * mm, str(doc.page))
        canvas.setFillColor(RED)
        canvas.circle(width / 2, MARGIN - 7.5 * mm, 1.6, stroke=0, fill=1)
        canvas.restoreState()


def _paragraphs(text: str, style: ParagraphStyle) -> list[Paragraph]:
    blocks = [b.strip() for b in text.replace("\r", "").split("\n") if b.strip()]
    return [Paragraph(escape(b), style) for b in blocks]


def _story_flowables(
    story: BookStory, styles: dict[str, ParagraphStyle], pages: dict[int, int]
) -> list[Flowable]:
    head: list[Flowable] = [
        StoryAnchor(story.id, story.question),
        Paragraph(escape(story.question), styles["question"]),
        Paragraph(_("{name} raconte").format(name=escape(story.person_name)), styles["teller"]),
        Paragraph(long_date(story.recorded_at).upper(), styles["meta"]),
    ]
    body = _paragraphs(story.text, styles["body"])
    if body and story.keywords:
        # Les mots-clés vont dans l'index, avec la page où commence le récit.
        tags = "".join(f'<index item="{escape(k, {chr(34): "&quot;"})}"/>' for k in story.keywords)
        first = body[0]
        body[0] = Paragraph(tags + first.text, styles["body"])
    flow: list[Flowable] = [CondPageBreak(60 * mm), KeepTogether(head + body[:1]), *body[1:]]
    if story.note.strip():
        note = Table(
            [
                [Paragraph(escape(_("Ce que j'en retiens").upper()), styles["eyebrow"])],
                *[[p] for p in _paragraphs(story.note, styles["note"])],
            ],
            colWidths=["100%"],
        )
        note.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), SOFT_GREEN),
                    ("BOX", (0, 0), (-1, -1), 0.6, SOFT_GREEN_BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, 0), 8),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
                ]
            )
        )
        flow += [Spacer(1, 4), KeepTogether([note])]
    if story.keywords:
        words = _("Mots : {words}").format(words=", ".join(story.keywords))
        flow.append(Paragraph(escape(words), styles["words"]))
    if story.see_also:
        flow.append(Spacer(1, 6))
        flow.append(Paragraph(escape(_("Voir aussi").upper()), styles["eyebrow"]))
        flow.append(Spacer(1, 3))
        flow += [
            SeeAlsoLine(s.story_id, f"{s.question} ({s.person_name})", pages)
            for s in story.see_also
        ]
    flow += [Spacer(1, 6), ThreadOrnament(), Spacer(1, 8)]
    return flow


def render_book(
    book: Book,
    path: Path,
    assets: BookAssets,
    on_progress: Callable[[str], None] | None = None,
) -> Path:
    """Crée le PDF du livre et retourne son chemin."""
    _register_fonts(assets.fonts_dir)
    styles = _styles()
    pages: dict[int, int] = {}
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = BookTemplate(
        str(path),
        pages,
        title=_("Le livre de famille"),
        author=book.author or "",
        subject="Au fil d'une vie",
        creator="Au fil d'une vie",
    )

    story: list[Flowable] = []
    # Couverture
    story.append(Spacer(1, 18 * mm))
    if assets.logo.is_file():
        logo = Image(str(assets.logo), width=58 * mm, height=58 * mm * 1620 / 1260, mask="auto")
        story.append(logo)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(escape(_("Le livre de famille")), styles["title"]))
    if book.author:
        story.append(
            Paragraph(
                _("recueilli par {name}").format(name=escape(book.author)), styles["subtitle"]
            )
        )
    story.append(Spacer(1, 6 * mm))
    voices = ", ".join(book.people)
    story.append(
        Paragraph(
            escape(plural(book.story_count, "récit", "récits"))
            + f" · {escape(voices)}<br/>{long_date(book.created_at)}",
            styles["small_center"],
        )
    )
    story += [NextPageTemplate("page"), PageBreak()]

    # Sommaire
    story.append(Paragraph(escape(_("Sommaire")), styles["chapter"]))
    toc = TableOfContents(dotsMinLevel=1)
    toc.levelStyles = [styles["toc1"], styles["toc2"]]
    story += [toc, PageBreak()]

    # Chapitres
    for index, chapter in enumerate(book.chapters):
        if on_progress:
            on_progress(chapter.theme_label)
        story.append(Paragraph(escape(_("Piste").upper()), styles["eyebrow"]))
        title = Paragraph(escape(chapter.theme_label), styles["chapter"])
        title.chapter_key = f"piste-{index}"
        story.append(title)
        for book_story in chapter.stories:
            story += _story_flowables(book_story, styles, pages)
        story.append(PageBreak())

    if not book.chapters:
        story.append(
            Paragraph(
                escape(
                    _(
                        "Aucun récit n'a encore été ajouté au livre. Choisis-en dans "
                        "l'application, puis crée le livre à nouveau."
                    )
                ),
                styles["subtitle"],
            )
        )

    # Index (ReportLab n'accepte pas un index vide : seulement s'il y a des mots)
    has_words = any(s.keywords for c in book.chapters for s in c.stories)
    if has_words:
        index_flowable = SimpleIndex(dot=" . ", headers=False, style=[styles["index"]])
        story += [
            Paragraph(escape(_("Index des mots")), styles["chapter"]),
            Spacer(1, 4),
            index_flowable,
        ]
        doc.multiBuild(story, canvasmaker=index_flowable.getCanvasMaker())
    else:
        doc.multiBuild(story)
    return path
