"""Générateur PDF commun des rapports opérationnels RPT-01 et RPT-03 à RPT-06."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

BRAND = colors.HexColor("#0C735B")
BRAND_DARK = colors.HexColor("#14342C")
INK = colors.HexColor("#1C2925")
MUTED = colors.HexColor("#61706B")
LINE = colors.HexColor("#D9E4E0")
SOFT = colors.HexColor("#EFF7F4")


@dataclass(frozen=True, slots=True)
class ReportTable:
    """Table structurée avec en-têtes et lignes déjà normalisées."""

    title: str
    headers: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]


@dataclass(frozen=True, slots=True)
class OperationalReportData:
    """Données immuables d'un rapport opérationnel en français."""

    code: str
    title: str
    subject: str
    generated_at: datetime
    reference: str
    template_version: str
    key_values: tuple[tuple[str, Any], ...] = ()
    tables: tuple[ReportTable, ...] = ()
    observations: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    footer_note: str = (
        "Document généré depuis des données archivées. Toute décision d'exploitation "
        "reste soumise à la validation de l'ingénieur responsable."
    )
    metadata: dict[str, str] = field(default_factory=dict)


def _format(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Oui" if value else "Non"
    if isinstance(value, float):
        return f"{value:,.6g}".replace(",", " ").replace(".", ",")
    return str(value)


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(_format(value)), style)


def _invariant_canvas(*args: Any, **kwargs: Any) -> Canvas:
    """Supprime les métadonnées variables afin de stabiliser l'empreinte du PDF."""

    kwargs["invariant"] = 1
    return Canvas(*args, **kwargs)

def build_operational_report_pdf(data: OperationalReportData) -> bytes:
    """Produit un PDF A4 déterministe, paginé et directement archivable."""

    buffer = BytesIO()
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "CorpsHydro",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=INK,
        spaceAfter=4,
    )
    small = ParagraphStyle(
        "PetitHydro",
        parent=body,
        fontSize=7.5,
        leading=10,
        textColor=MUTED,
    )
    heading = ParagraphStyle(
        "TitreSectionHydro",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=BRAND_DARK,
        spaceBefore=12,
        spaceAfter=7,
    )
    cover_title = ParagraphStyle(
        "TitreHydro",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=25,
        leading=29,
        textColor=BRAND_DARK,
        spaceAfter=9,
    )
    label = ParagraphStyle(
        "LabelHydro",
        parent=small,
        fontName="Helvetica-Bold",
        textColor=BRAND,
    )
    right = ParagraphStyle("DroiteHydro", parent=small, alignment=TA_RIGHT)

    def decorate_page(canvas, document) -> None:
        canvas.saveState()
        width, height = A4
        canvas.setFillColor(BRAND_DARK)
        canvas.rect(0, height - 18 * mm, width, 18 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(18 * mm, height - 11.5 * mm, "HYDROPLATFORM")
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(width - 18 * mm, height - 11.5 * mm, data.code)
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(18 * mm, 9 * mm, data.reference)
        canvas.drawRightString(width - 18 * mm, 9 * mm, f"Page {document.page}")
        canvas.restoreState()

    document = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=25 * mm,
        bottomMargin=20 * mm,
        title=f"{data.code} — {data.title}",
        author="HydroPlatform",
        subject=data.subject,
        creator="HydroPlatform",
    )
    frame = Frame(
        document.leftMargin,
        document.bottomMargin,
        document.width,
        document.height,
        id="contenu",
    )
    document.addPageTemplates([PageTemplate(id="rapport", frames=[frame], onPage=decorate_page)])

    story: list[Any] = [
        Spacer(1, 8 * mm),
        Paragraph(data.code, label),
        Paragraph(escape(data.title), cover_title),
        Paragraph(escape(data.subject), body),
        Spacer(1, 6 * mm),
    ]
    identity_rows = [
        [_paragraph("Référence", label), _paragraph(data.reference, body)],
        [_paragraph("Modèle", label), _paragraph(data.template_version, body)],
        [
            _paragraph("Produit le", label),
            _paragraph(data.generated_at.strftime("%d/%m/%Y à %H:%M UTC"), body),
        ],
    ]
    for key, value in sorted(data.metadata.items()):
        identity_rows.append([_paragraph(key, label), _paragraph(value, body)])
    identity = Table(identity_rows, colWidths=[42 * mm, document.width - 42 * mm])
    identity.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([identity, Spacer(1, 7 * mm)])

    if data.key_values:
        story.append(Paragraph("Synthèse", heading))
        rows = [[_paragraph(key, label), _paragraph(value, body)] for key, value in data.key_values]
        table = Table(rows, colWidths=[58 * mm, document.width - 58 * mm])
        table.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, SOFT]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)

    for section in data.tables:
        story.append(Paragraph(escape(section.title), heading))
        column_count = max(len(section.headers), 1)
        rows = [
            [_paragraph(header, label) for header in section.headers],
            *[[_paragraph(value, small) for value in row] for row in section.rows],
        ]
        table = Table(
            rows,
            colWidths=[document.width / column_count] * column_count,
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)

    if data.observations:
        story.append(Paragraph("Observations et contrôles", heading))
        for observation in data.observations:
            story.append(Paragraph("• " + escape(observation), body))

    if data.assumptions:
        story.append(Paragraph("Hypothèses", heading))
        for assumption in data.assumptions:
            story.append(Paragraph("• " + escape(assumption), body))

    story.extend(
        [
            Spacer(1, 8 * mm),
            Paragraph("Limites d'usage", heading),
            Paragraph(escape(data.footer_note), small),
            Spacer(1, 3 * mm),
            Paragraph("Visa de l'ingénieur : ____________________________________", right),
        ]
    )
    document.build(story, canvasmaker=_invariant_canvas)
    return buffer.getvalue()


__all__ = ["OperationalReportData", "ReportTable", "build_operational_report_pdf"]
