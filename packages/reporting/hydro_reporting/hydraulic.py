"""Génération de la note de calcul hydraulique RPT-02.

Le document est construit uniquement à partir de l'entrée canonique et du résultat persisté.
Il reste donc reproductible même si le projet, le catalogue ou le scénario évoluent ensuite.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from threading import Lock
from typing import Any

import matplotlib

matplotlib.use("Agg")

from matplotlib import font_manager
from matplotlib import pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    HRFlowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#12263A")
BLUE = colors.HexColor("#1F5A7A")
TEAL = colors.HexColor("#1A8A8A")
PALE_BLUE = colors.HexColor("#EAF2F6")
PALE_GREEN = colors.HexColor("#E9F7F3")
PALE_RED = colors.HexColor("#FCECEC")
GRAY = colors.HexColor("#5C6770")
LIGHT_GRAY = colors.HexColor("#E4E9ED")
WHITE = colors.white

_FONT_LOCK = Lock()
_FONTS_READY = False


@dataclass(frozen=True, slots=True)
class HydraulicReportData:
    """Données figées nécessaires à la note de calcul."""

    report_id: str
    calculation_id: str
    project_name: str
    project_code: str
    model_name: str
    model_version: int
    scenario_name: str
    generated_at: datetime
    input_payload: dict[str, Any]
    result_payload: dict[str, Any]
    template_version: str = "rpt-02/1.0"
    locale: str = "fr"


def _register_fonts() -> None:
    """Enregistre une police Unicode embarquée avec Matplotlib."""

    global _FONTS_READY
    if _FONTS_READY:
        return
    with _FONT_LOCK:
        if _FONTS_READY:
            return
        regular = font_manager.findfont(
            font_manager.FontProperties(family="DejaVu Sans", weight="normal")
        )
        bold = font_manager.findfont(
            font_manager.FontProperties(family="DejaVu Sans", weight="bold")
        )
        pdfmetrics.registerFont(TTFont("HydroSans", regular))
        pdfmetrics.registerFont(TTFont("HydroSans-Bold", bold))
        _FONTS_READY = True


def _text(value: Any) -> str:
    if value is None:
        return "-"
    return html.escape(str(value)).replace("\n", "<br/>")


def _number(value: Any, decimals: int = 2, suffix: str = "") -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _text(value)
    rendered = f"{number:,.{decimals}f}".replace(",", " ").replace(".", ",")
    return f"{rendered}{suffix}"


def _status_label(status: str) -> str:
    labels = {
        "SIM_QUEUED": "En attente",
        "SIM_RUNNING": "En cours",
        "SIM_CONVERGED": "Convergé",
        "SIM_CONVERGED_WARN": "Convergé avec avertissements",
        "SIM_INVALID_INPUT": "Entrées invalides",
        "SIM_NO_PHYSICAL_SOLUTION": "Aucune solution physique",
        "SIM_NOT_CONVERGED": "Non convergé",
        "SIM_CANCELLED": "Annulé",
    }
    return labels.get(status, status)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName="HydroSans-Bold",
            fontSize=24,
            leading=29,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=8 * mm,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base["Normal"],
            fontName="HydroSans",
            fontSize=12,
            leading=17,
            textColor=GRAY,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="HydroSans-Bold",
            fontSize=16,
            leading=20,
            textColor=NAVY,
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="HydroSans-Bold",
            fontSize=11,
            leading=14,
            textColor=BLUE,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="HydroSans",
            fontSize=8.5,
            leading=12,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="HydroSans",
            fontSize=7,
            leading=9,
            textColor=GRAY,
        ),
        "table": ParagraphStyle(
            "Table",
            parent=base["BodyText"],
            fontName="HydroSans",
            fontSize=7,
            leading=9,
            textColor=NAVY,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName="HydroSans-Bold",
            fontSize=7,
            leading=9,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "kpi": ParagraphStyle(
            "KPI",
            parent=base["BodyText"],
            fontName="HydroSans-Bold",
            fontSize=14,
            leading=17,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "kpi_label": ParagraphStyle(
            "KPILabel",
            parent=base["BodyText"],
            fontName="HydroSans",
            fontSize=6.5,
            leading=8,
            textColor=GRAY,
            alignment=TA_CENTER,
        ),
        "right": ParagraphStyle(
            "Right",
            parent=base["BodyText"],
            fontName="HydroSans",
            fontSize=7,
            leading=9,
            textColor=GRAY,
            alignment=TA_RIGHT,
        ),
    }


def _paragraph(value: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_text(value), style)


def _data_table(
    rows: list[tuple[Any, Any]],
    styles: dict[str, ParagraphStyle],
    *,
    widths: tuple[float, float] = (58 * mm, 116 * mm),
) -> Table:
    data = [
        [_paragraph(label, styles["table_header"]), _paragraph(value, styles["table"])]
        for label, value in rows
    ]
    table = Table(data, colWidths=list(widths), hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), BLUE),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, LIGHT_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _generic_table(
    headers: list[str],
    rows: list[list[Any]],
    widths: list[float],
    styles: dict[str, ParagraphStyle],
) -> Table:
    data: list[list[Paragraph]] = [
        [_paragraph(header, styles["table_header"]) for header in headers]
    ]
    data.extend([[_paragraph(value, styles["table"]) for value in row] for row in rows])
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BLUE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
                ("GRID", (0, 0), (-1, -1), 0.3, LIGHT_GRAY),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _profile_chart(profile: list[dict[str, Any]]) -> BytesIO | None:
    if not profile:
        return None
    chainage_km = [float(point["chainage_m"]) / 1000.0 for point in profile]
    pressure_bar = [float(point["pressure_pa"]) / 100_000.0 for point in profile]
    elevation_m = [float(point["elevation_m"]) for point in profile]

    figure, pressure_axis = plt.subplots(figsize=(8.2, 3.4), dpi=160)
    figure.patch.set_facecolor("white")
    pressure_axis.plot(chainage_km, pressure_bar, color="#1A8A8A", linewidth=2.1)
    pressure_axis.fill_between(chainage_km, pressure_bar, color="#1A8A8A", alpha=0.12)
    pressure_axis.set_xlabel("Abscisse curviligne (km)")
    pressure_axis.set_ylabel("Pression absolue (bar)", color="#1A8A8A")
    pressure_axis.tick_params(axis="y", labelcolor="#1A8A8A")
    pressure_axis.grid(True, color="#D8E1E6", linewidth=0.6, alpha=0.85)

    elevation_axis = pressure_axis.twinx()
    elevation_axis.plot(
        chainage_km,
        elevation_m,
        color="#5C6770",
        linewidth=1.2,
        linestyle="--",
    )
    elevation_axis.set_ylabel("Altitude (m)", color="#5C6770")
    elevation_axis.tick_params(axis="y", labelcolor="#5C6770")
    pressure_axis.set_title("Profil de pression et relief", color="#12263A", weight="bold")
    figure.tight_layout()

    image = BytesIO()
    figure.savefig(image, format="png", bbox_inches="tight", facecolor="white")
    plt.close(figure)
    image.seek(0)
    return image


def _page_decorations(canvas, document) -> None:
    canvas.saveState()
    page_width, page_height = A4
    if document.page > 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, page_height - 13 * mm, page_width, 13 * mm, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("HydroSans-Bold", 7.5)
        canvas.drawString(18 * mm, page_height - 8.5 * mm, "NOTE DE CALCUL HYDRAULIQUE")
    canvas.setStrokeColor(LIGHT_GRAY)
    canvas.line(18 * mm, 13 * mm, page_width - 18 * mm, 13 * mm)
    canvas.setFillColor(GRAY)
    canvas.setFont("HydroSans", 6.5)
    canvas.drawString(18 * mm, 8.5 * mm, "Document technique - Vérification ingénieur requise")
    canvas.drawRightString(
        page_width - 18 * mm,
        8.5 * mm,
        f"Page {document.page}",
    )
    canvas.restoreState()


def _build_story(data: HydraulicReportData, styles: dict[str, ParagraphStyle]) -> list[Any]:
    result = data.result_payload
    input_payload = data.input_payload
    manifest = input_payload.get("manifest", {})
    network = input_payload.get("network", {})
    fluid = input_payload.get("fluid", {})
    scenario = input_payload.get("scenario", {})
    diagnostics = result.get("diagnostics", {})
    violations = result.get("violations", [])
    warnings = result.get("warnings", [])
    profile = result.get("profile", [])
    stations = result.get("stations", [])
    segments = result.get("segments", [])
    explanation = result.get("explanation", {})
    environment = result.get("environment", {})
    assumptions = result.get("assumptions", {})
    fluid_state = assumptions.get("fluid_state", {})
    checks = assumptions.get("checks", {})
    dependencies = environment.get("dependencies", {})
    dependency_versions = ", ".join(
        f"{name} {version}" for name, version in sorted(dependencies.items())
    )

    story: list[Any] = [
        Spacer(1, 25 * mm),
        HRFlowable(width="100%", thickness=4, color=TEAL, spaceAfter=10 * mm),
        Paragraph("NOTE DE CALCUL<br/>HYDRAULIQUE", styles["cover_title"]),
        Paragraph(
            f"Pipeline liquide en régime permanent<br/><b>{_text(data.project_name)}</b>",
            styles["cover_subtitle"],
        ),
        Spacer(1, 25 * mm),
        _data_table(
            [
                ("Projet", f"{data.project_code} - {data.project_name}"),
                ("Version du modèle", f"{data.model_version} - {data.model_name}"),
                ("Scénario", data.scenario_name),
                ("Calcul", data.calculation_id),
                ("Rapport", data.report_id),
                ("Modèle de document", data.template_version),
                (
                    "Généré le",
                    data.generated_at.astimezone().strftime("%d/%m/%Y à %H:%M:%S %Z"),
                ),
                ("Statut", _status_label(str(result.get("status", "-")))),
            ],
            styles,
        ),
        Spacer(1, 18 * mm),
        Paragraph(
            "Ce document présente une aide à la décision technique. Son approbation exige "
            "la revue des hypothèses, des données d'entrée, des limites du modèle et des "
            "exigences réglementaires applicables par un ingénieur habilité.",
            styles["small"],
        ),
        PageBreak(),
        Paragraph("1. Objet, périmètre et limites", styles["h1"]),
        Paragraph(
            "La présente note restitue un calcul hydraulique stationnaire, isotherme et "
            "monophasique d'un pipeline liquide. Elle couvre les pertes régulières et "
            "singulières, le relief, les stations de pompage, les limites de pression, le "
            "NPSH et les diagnostics numériques. Les phénomènes transitoires, thermiques, "
            "multiproduits et gaz-liquide ne sont pas couverts.",
            styles["body"],
        ),
        Paragraph("2. Traçabilité et reproductibilité", styles["h1"]),
        _data_table(
            [
                ("Empreinte d'entrée", result.get("input_hash")),
                ("Schéma d'entrée", manifest.get("schema_version")),
                ("Moteur", result.get("engine")),
                ("Version du moteur", result.get("engine_version")),
                ("Pipeline", manifest.get("pipeline_id")),
                ("Produit", manifest.get("fluid_id")),
                ("Scénario", manifest.get("scenario_id")),
            ],
            styles,
        ),
        Paragraph("3. Description du système", styles["h1"]),
        _data_table(
            [
                ("Pipeline", network.get("name")),
                ("Longueur totale", _number(network.get("total_length_m"), 0, " m")),
                ("Nombre de tronçons", len(network.get("segments", []))),
                ("Nombre de stations", len(network.get("stations", []))),
                ("Produit", fluid.get("name")),
                ("Température", _number(scenario.get("temperature_k"), 2, " K")),
                ("Débit imposé", _number(scenario.get("imposed_flow_m3_s"), 5, " m³/s")),
            ],
            styles,
        ),
        Paragraph("4. Données d'entrée et hypothèses", styles["h1"]),
        _data_table(
            [
                ("Masse volumique de référence", _number(fluid.get("density_kg_m3"), 2, " kg/m³")),
                (
                    "Viscosité cinématique",
                    _number(fluid.get("kinematic_viscosity_m2_s"), 9, " m²/s"),
                ),
                ("Pression de vapeur", _number(fluid.get("vapor_pressure_pa"), 0, " Pa abs.")),
                ("Source produit", fluid.get("data_source")),
                (
                    "Pression amont",
                    _number(scenario.get("inlet_pressure_pa"), 0, " Pa abs."),
                ),
                (
                    "Pression aval",
                    _number(scenario.get("outlet_pressure_pa"), 0, " Pa abs."),
                ),
            ],
            styles,
        ),
        Paragraph("5. Méthode numérique", styles["h1"]),
        _data_table(
            [
                ("Méthode", diagnostics.get("method")),
                ("Convergence", "Oui" if diagnostics.get("converged") else "Non"),
                ("Itérations", diagnostics.get("iterations")),
                ("Résidu final", _number(diagnostics.get("residual"), 6)),
                ("Tolérance", _number(diagnostics.get("tolerance"), 6)),
                (
                    "Résidu bilan matière",
                    _number(diagnostics.get("mass_balance_residual"), 9),
                ),
            ],
            styles,
        ),
        Paragraph("6. Résultats globaux", styles["h1"]),
    ]

    kpis = [
        ("Débit", _number(result.get("flow_m3_s"), 4, " m³/s")),
        ("Pression min.", _number(result.get("min_pressure_pa"), 0, " Pa")),
        ("Pression max.", _number(result.get("max_pressure_pa"), 0, " Pa")),
        ("Puissance", _number(result.get("total_power_w"), 0, " W")),
    ]
    kpi_cells = [
        [
            [
                Paragraph(value, styles["kpi"]),
                Paragraph(label, styles["kpi_label"]),
            ]
            for label, value in kpis
        ]
    ]
    kpi_table = Table(kpi_cells, colWidths=[43.5 * mm] * 4)
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_GREEN),
                ("BOX", (0, 0), (-1, -1), 0.6, TEAL),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([kpi_table, Spacer(1, 4 * mm)])

    if segments:
        story.extend(
            [
                Paragraph("6.1 Tronçons", styles["h2"]),
                _generic_table(
                    ["Tronçon", "Débit", "Vitesse", "Reynolds", "Perte de charge"],
                    [
                        [
                            segment.get("segment_id"),
                            _number(segment.get("flow_m3_s"), 4, " m³/s"),
                            _number(segment.get("velocity_m_s"), 3, " m/s"),
                            _number(segment.get("reynolds"), 0),
                            _number(segment.get("total_head_loss_m"), 2, " m"),
                        ]
                        for segment in segments
                    ],
                    [29 * mm, 34 * mm, 34 * mm, 34 * mm, 43 * mm],
                    styles,
                ),
            ]
        )

    if stations:
        story.extend(
            [
                Paragraph("7. Stations et pompes", styles["h1"]),
                _generic_table(
                    ["Station", "Pompes actives", "Hauteur", "Puissance", "Rendement"],
                    [
                        [
                            station.get("station_id"),
                            station.get("active_pump_count"),
                            _number(station.get("head_m"), 2, " m"),
                            _number(station.get("absorbed_power_w"), 0, " W"),
                            _number(
                                None
                                if station.get("efficiency") is None
                                else float(station["efficiency"]) * 100,
                                1,
                                " %",
                            ),
                        ]
                        for station in stations
                    ],
                    [34 * mm, 30 * mm, 34 * mm, 42 * mm, 34 * mm],
                    styles,
                ),
            ]
        )

    chart = _profile_chart(profile)
    if chart is not None:
        story.extend(
            [
                Paragraph("8. Profils et graphiques", styles["h1"]),
                Image(chart, width=174 * mm, height=72 * mm),
                Paragraph(
                    "La pression est exprimée en bar absolus sur l'axe gauche ; le relief est "
                    "présenté sur l'axe droit. Les valeurs détaillées restent disponibles dans "
                    "le résultat numérique associé au calcul.",
                    styles["small"],
                ),
            ]
        )

    story.append(Paragraph("9. Contrôles et marges", styles["h1"]))
    control_rows: list[list[Any]] = []
    for violation in violations:
        control_rows.append(
            [
                "Violation",
                violation.get("check_id") or violation.get("code"),
                violation.get("message"),
                violation.get("recommendation"),
            ]
        )
    for warning in warnings:
        control_rows.append(
            [
                "Avertissement",
                warning.get("code"),
                warning.get("message"),
                "Examen requis avant approbation.",
            ]
        )
    if control_rows:
        story.append(
            _generic_table(
                ["Niveau", "Contrôle", "Constat", "Action recommandée"],
                control_rows,
                [28 * mm, 30 * mm, 62 * mm, 54 * mm],
                styles,
            )
        )
    else:
        story.append(
            Paragraph(
                "Aucune violation ni aucun avertissement n'a été enregistré.",
                styles["body"],
            )
        )

    feasible = bool(result.get("feasible"))
    approvable = bool(result.get("approvable"))
    conclusion_color = PALE_GREEN if approvable else PALE_RED
    conclusion = (
        "Le résultat est convergé, physiquement réalisable et approuvable après revue humaine."
        if approvable
        else (
            "Le résultat est physiquement réalisable, mais son approbation exige la levée "
            "des avertissements ou réserves."
            if feasible
            else "Le scénario n'est pas déclaré réalisable dans les hypothèses du modèle."
        )
    )
    story.extend(
        [
            Paragraph("10. Conclusion et recommandations", styles["h1"]),
            Table(
                [[Paragraph(_text(conclusion), styles["body"])]],
                colWidths=[174 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), conclusion_color),
                        ("BOX", (0, 0), (-1, -1), 0.7, TEAL if approvable else colors.red),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
            Spacer(1, 3 * mm),
            Paragraph(explanation.get("summary", conclusion), styles["body"]),
            Paragraph("Annexe A - Environnement de calcul", styles["h1"]),
            _data_table(
                [
                    ("Empreinte d'entrée", result.get("input_hash")),
                    ("Version plateforme", environment.get("platform_version")),
                    ("Version moteur", result.get("engine_version")),
                    ("Schéma de résultat", environment.get("result_schema_version")),
                    ("Python", environment.get("python")),
                    ("Système", environment.get("os")),
                    ("Dépendances scientifiques", dependency_versions),
                    (
                        "État du produit",
                        (
                            f"{_number(fluid_state.get('temperature_k'), 2, ' K')}, "
                            f"{_number(fluid_state.get('density_kg_m3'), 2, ' kg/m³')}, "
                            f"{_number(fluid_state.get('kinematic_viscosity_m2_s'), 9, ' m²/s')}"
                        ),
                    ),
                    ("Modèle de frottement", assumptions.get("friction_model")),
                    (
                        "Modèle gravitaire appliqué",
                        "Oui" if assumptions.get("gravity_model_applied") else "Non",
                    ),
                    (
                        "Contrôles exécutés",
                        ", ".join(checks.get("executed", [])),
                    ),
                    (
                        "Contrôles non applicables",
                        ", ".join(sorted(checks.get("skipped", {}))) or "Aucun",
                    ),
                ],
                styles,
            ),
        ]
    )
    return story


def _invariant_canvas(*args: Any, **kwargs: Any) -> Canvas:
    """Crée un canevas sans date implicite afin de stabiliser le hash du PDF."""

    kwargs["invariant"] = 1
    return Canvas(*args, **kwargs)


def build_hydraulic_calculation_pdf(data: HydraulicReportData) -> bytes:
    """Produit la note RPT-02 au format PDF, prête à être hachée et archivée."""

    if data.locale != "fr":
        raise ValueError("Le modèle RPT-02 du MVP est disponible uniquement en français.")
    _register_fonts()
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=19 * mm,
        bottomMargin=18 * mm,
        title=f"Note de calcul hydraulique - {data.project_code}",
        author="Equipe Plateforme Hydrocarbures",
        subject=f"Calcul {data.calculation_id}",
    )
    styles = _styles()
    story = _build_story(data, styles)
    document.build(
        story,
        onFirstPage=_page_decorations,
        onLaterPages=_page_decorations,
        canvasmaker=_invariant_canvas,
    )
    return output.getvalue()


__all__ = ["HydraulicReportData", "build_hydraulic_calculation_pdf"]
