/**
 * Graphiques métier exigés par la définition du MVP.
 *
 * Chaque courbe est tracée à partir de valeurs réellement produites par les
 * moteurs. Lorsqu'une courbe est reconstituée faute de données directes, elle
 * est explicitement désignée comme telle dans sa légende.
 */

import type { EChartsOption, LineSeriesOption, ScatterSeriesOption } from "echarts";

import { EChart } from "./EChart";
import type {
  CalculationGravityZone,
  CalculationProfilePoint,
  Comparison,
  PumpResultRow,
  SegmentResultRow,
  StationResultRow,
  Transfer,
} from "../../types";

const AXIS_LABEL = { fontSize: 11 } as const;

export interface EngineeringChartContext {
  calculationId: string;
  scenarioName: string;
  resultTimestamp: string | null;
}

export interface VaporPressureLimit {
  pressurePa: number;
  source: string | null;
  extrapolated: boolean;
}

type ChartPoint = [number, number];
type NullableChartPoint = [number, number | null];
type GravityArea = [{ xAxis: number }, { xAxis: number }];

function isFiniteNumber(value: number | null | undefined): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function chartSubtitle(context: EngineeringChartContext): string {
  const timestamp = context.resultTimestamp
    ? new Intl.DateTimeFormat("fr-FR", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(context.resultTimestamp))
    : "date du calcul non publiée";
  return `Calcul ${context.calculationId.slice(0, 8)} · ${context.scenarioName} · ${timestamp}`;
}

function stationMarkLines(stations: StationResultRow[]) {
  return stations
    .filter((station) => isFiniteNumber(station.chainage_m))
    .map((station) => ({ name: station.station_id, xAxis: station.chainage_m / 1000 }));
}

function gravityAreas(zones: CalculationGravityZone[]): GravityArea[] {
  return zones
    .filter(
      (zone) =>
        isFiniteNumber(zone.start_chainage_m) &&
        isFiniteNumber(zone.end_chainage_m) &&
        zone.end_chainage_m >= zone.start_chainage_m,
    )
    .map((zone) => [
      { xAxis: zone.start_chainage_m / 1000 },
      // Une zone ponctuelle reste visible sans étendre artificiellement son emprise.
      { xAxis: Math.max(zone.end_chainage_m, zone.start_chainage_m + 1e-6) / 1000 },
    ]);
}

/**
 * Projette les seules limites configurées et publiées par segment sur le profil.
 * Un point non couvert conserve ``null`` : aucun MAOP/MAWP n'est inventé.
 */
export function maopEnvelopePoints(
  points: CalculationProfilePoint[],
  segments: SegmentResultRow[],
): NullableChartPoint[] {
  const rangedSegments = segments.filter(
    (segment) =>
      isFiniteNumber(segment.start_chainage_m) &&
      isFiniteNumber(segment.end_chainage_m) &&
      isFiniteNumber(segment.maop_pa),
  );
  return points.map((point) => {
    const segment = rangedSegments.find(
      (candidate) =>
        point.chainage_m >= candidate.start_chainage_m! - 1e-6 &&
        point.chainage_m <= candidate.end_chainage_m! + 1e-6,
    );
    return [
      point.chainage_m / 1000,
      segment && isFiniteNumber(segment.maop_pa) ? segment.maop_pa / 100000 : null,
    ];
  });
}

/** Profil hydraulique : ligne piézométrique et terrain suivant le chaînage. */
export function HydraulicProfileChart({
  points,
  stations = [],
  gravityZones = [],
  context,
  exportFileName,
}: {
  points: CalculationProfilePoint[];
  stations?: StationResultRow[];
  gravityZones?: CalculationGravityZone[];
  context?: EngineeringChartContext;
  exportFileName?: string;
}) {
  const stationLines = stationMarkLines(stations);
  const zones = gravityAreas(gravityZones);
  const vaporPoints: ChartPoint[] = points
    .filter((point) => point.below_vapor_pressure)
    .map((point) => [point.chainage_m / 1000, point.hydraulic_grade_m]);
  const hydraulicGradeSeries: LineSeriesOption = {
    name: "Ligne piézométrique",
    type: "line",
    showSymbol: false,
    smooth: false,
    data: points.map((point): ChartPoint => [point.chainage_m / 1000, point.hydraulic_grade_m]),
    markLine: stationLines.length
      ? {
          symbol: ["none", "none"],
          lineStyle: { color: "#7c5cc4", type: "dashed" },
          label: { formatter: "{b}", position: "insideEndTop", rotate: 45 },
          data: stationLines,
        }
      : undefined,
    markArea: zones.length
      ? {
          silent: true,
          itemStyle: { color: "rgba(217, 142, 4, 0.15)" },
          label: { show: true, formatter: "Zone gravitaire signalée" },
          data: zones,
        }
      : undefined,
  };
  const terrainSeries: LineSeriesOption = {
    name: "Profil du terrain",
    type: "line",
    showSymbol: false,
    areaStyle: { opacity: 0.25 },
    data: points.map((point): ChartPoint => [point.chainage_m / 1000, point.elevation_m]),
  };
  const belowVaporSeries: ScatterSeriesOption | null = vaporPoints.length
    ? {
        name: "Point sous vapeur",
        type: "scatter",
        symbol: "triangle",
        symbolSize: 10,
        itemStyle: { color: "#d9485f" },
        data: vaporPoints,
      }
    : null;
  const option: EChartsOption = {
    title: context
      ? { text: "Profil hydraulique enrichi", subtext: chartSubtitle(context), left: "center" }
      : undefined,
    grid: { left: 60, right: 24, top: context ? 82 : 40, bottom: 48 },
    tooltip: { trigger: "axis" },
    // La légende ne doit pas partager la marge basse avec le titre de l'axe X.
    legend: { top: context ? 48 : 0 },
    xAxis: {
      type: "value",
      name: "Chaînage (km)",
      nameLocation: "middle",
      nameGap: 28,
      axisLabel: AXIS_LABEL,
    },
    yAxis: { type: "value", name: "Altitude (m)", axisLabel: AXIS_LABEL },
    series: [hydraulicGradeSeries, terrainSeries, ...(belowVaporSeries ? [belowVaporSeries] : [])],
  };

  return (
    <EChart
      option={option}
      ariaLabel="Profil hydraulique, terrain, stations et zones signalées"
      exportFileName={exportFileName}
      exportLabel="Exporter le profil hydraulique PNG"
    />
  );
}

/** Pression absolue, enveloppes publiées et vitesse suivant le chaînage. */
export function PressureDistanceChart({
  points,
  segments = [],
  stations = [],
  gravityZones = [],
  vaporPressure,
  context,
  exportFileName,
}: {
  points: CalculationProfilePoint[];
  segments?: SegmentResultRow[];
  stations?: StationResultRow[];
  gravityZones?: CalculationGravityZone[];
  vaporPressure?: VaporPressureLimit | null;
  context?: EngineeringChartContext;
  exportFileName?: string;
}) {
  const stationLines = stationMarkLines(stations);
  const zones = gravityAreas(gravityZones);
  const maopPoints = maopEnvelopePoints(points, segments);
  const hasMaop = maopPoints.some(([, value]) => value !== null);
  const vaporPoints: ChartPoint[] = points
    .filter((point) => point.below_vapor_pressure)
    .map((point) => [point.chainage_m / 1000, point.pressure_pa / 100000]);
  const stationJumps: LineSeriesOption[] = stations
    .filter(
      (station) =>
        isFiniteNumber(station.chainage_m) &&
        isFiniteNumber(station.suction_pressure_pa) &&
        isFiniteNumber(station.discharge_pressure_pa),
    )
    .map((station) => ({
      name: station.station_id,
      type: "line" as const,
      yAxisIndex: 0,
      showSymbol: true,
      symbolSize: 7,
      lineStyle: { color: "#7c5cc4", type: "dashed" },
      itemStyle: { color: "#7c5cc4" },
      data: [
        [station.chainage_m / 1000, station.suction_pressure_pa / 100000],
        [station.chainage_m / 1000, station.discharge_pressure_pa / 100000],
      ] as ChartPoint[],
    }));
  const pressureSeries: LineSeriesOption = {
    name: "Pression absolue",
    type: "line",
    showSymbol: false,
    data: points.map((point): ChartPoint => [point.chainage_m / 1000, point.pressure_pa / 100000]),
    markLine: {
      symbol: ["none", "none"],
      lineStyle: { color: "#7c5cc4", type: "dashed" },
      label: { formatter: "{b}", position: "insideEndTop", rotate: 45 },
      data: [
        ...stationLines,
        ...(vaporPressure
          ? [
              {
                name: vaporPressure.source
                  ? `Vapeur (${vaporPressure.source})`
                  : "Pression vapeur (source publiée)",
                yAxis: vaporPressure.pressurePa / 100000,
                lineStyle: { color: "#d9485f", type: "dotted" as const },
              },
            ]
          : []),
      ],
    },
    markArea: zones.length
      ? {
          silent: true,
          itemStyle: { color: "rgba(217, 142, 4, 0.15)" },
          label: { show: true, formatter: "Zone gravitaire signalée" },
          data: zones,
        }
      : undefined,
  };
  const velocitySeries: LineSeriesOption = {
    name: "Vitesse",
    type: "line",
    yAxisIndex: 1,
    showSymbol: false,
    data: points.map((point): ChartPoint => [point.chainage_m / 1000, point.velocity_m_s]),
  };
  const maopSeries: LineSeriesOption | null = hasMaop
    ? {
        name: "Limite MAOP/MAWP configurée",
        type: "line",
        showSymbol: false,
        connectNulls: false,
        lineStyle: { color: "#bc3d45", type: "dashed", width: 2 },
        data: maopPoints,
      }
    : null;
  const belowVaporPressureSeries: ScatterSeriesOption | null = vaporPoints.length
    ? {
        name: "Point sous vapeur",
        type: "scatter",
        symbol: "triangle",
        symbolSize: 10,
        itemStyle: { color: "#d9485f" },
        data: vaporPoints,
      }
    : null;
  const option: EChartsOption = {
    title: context
      ? { text: "Pression et enveloppes opératoires", subtext: chartSubtitle(context), left: "center" }
      : undefined,
    grid: { left: 60, right: 60, top: context ? 82 : 40, bottom: 48 },
    tooltip: { trigger: "axis" },
    // Même disposition que le profil hydraulique : légende distincte du titre X.
    legend: { top: context ? 48 : 0 },
    xAxis: {
      type: "value",
      name: "Chaînage (km)",
      nameLocation: "middle",
      nameGap: 28,
      axisLabel: AXIS_LABEL,
    },
    yAxis: [
      { type: "value", name: "Pression (bar abs.)", axisLabel: AXIS_LABEL },
      { type: "value", name: "Vitesse (m/s)", axisLabel: AXIS_LABEL },
    ],
    series: [
      pressureSeries,
      velocitySeries,
      ...(maopSeries ? [maopSeries] : []),
      ...(belowVaporPressureSeries ? [belowVaporPressureSeries] : []),
      ...stationJumps,
    ],
  };

  return (
    <EChart
      option={option}
      ariaLabel="Pression absolue, limites configurées, stations et zones suivant le chaînage"
      exportFileName={exportFileName}
      exportLabel="Exporter la pression et les enveloppes PNG"
    />
  );
}

/**
 * Courbe pompe et courbe réseau au point de fonctionnement.
 *
 * La courbe constructeur provient du catalogue. La courbe réseau n'est pas
 * publiée par le moteur : elle est reconstituée par une parabole
 * ``H = H_statique + k·Q²`` passant par le point de fonctionnement calculé, et
 * sert uniquement à situer ce point.
 */
export function PumpSystemCurveChart({
  pump,
  curveFlowsM3S,
  curveHeadsM,
  staticHeadM,
}: {
  pump: PumpResultRow;
  curveFlowsM3S: number[];
  curveHeadsM: number[];
  staticHeadM: number;
}) {
  const operatingFlow = pump.flow_m3_s;
  const operatingHead = pump.head_m;
  const k =
    operatingFlow > 0 ? Math.max(operatingHead - staticHeadM, 0) / (operatingFlow * operatingFlow) : 0;
  const maxFlow = Math.max(operatingFlow, ...curveFlowsM3S, 1e-6);
  const systemCurve = Array.from({ length: 25 }, (_, index) => {
    const flow = (maxFlow * index) / 24;
    return [flow * 3600, staticHeadM + k * flow * flow];
  });

  const option: EChartsOption = {
    grid: { left: 60, right: 24, top: 40, bottom: 56 },
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    xAxis: {
      type: "value",
      name: "Débit (m³/h)",
      nameLocation: "middle",
      nameGap: 28,
      axisLabel: AXIS_LABEL,
    },
    yAxis: { type: "value", name: "Hauteur (m)", axisLabel: AXIS_LABEL },
    series: [
      {
        name: "Courbe constructeur",
        type: "line",
        smooth: true,
        data: curveFlowsM3S.map((flow, index) => [flow * 3600, curveHeadsM[index] ?? null]),
      },
      {
        name: "Courbe réseau (reconstituée)",
        type: "line",
        smooth: true,
        lineStyle: { type: "dashed" },
        data: systemCurve,
      },
      {
        name: "Point de fonctionnement",
        type: "scatter",
        symbolSize: 14,
        data: [[operatingFlow * 3600, operatingHead]],
      },
    ],
  };

  return (
    <EChart
      option={option}
      ariaLabel={`Courbe de la pompe ${pump.pump_id} et point de fonctionnement`}
    />
  );
}

/** Rendement et puissance absorbée de chaque pompe en marche. */
export function PumpEfficiencyPowerChart({ pumps }: { pumps: PumpResultRow[] }) {
  const running = pumps.filter((pump) => pump.running);
  const option: EChartsOption = {
    grid: { left: 60, right: 60, top: 40, bottom: 56 },
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    xAxis: {
      type: "category",
      data: running.map((pump) => pump.pump_id),
      axisLabel: AXIS_LABEL,
    },
    yAxis: [
      { type: "value", name: "Rendement (%)", max: 100, axisLabel: AXIS_LABEL },
      { type: "value", name: "Puissance (kW)", axisLabel: AXIS_LABEL },
    ],
    series: [
      {
        name: "Rendement",
        type: "bar",
        data: running.map((pump) => (pump.efficiency === null ? null : pump.efficiency * 100)),
      },
      {
        name: "Puissance absorbée",
        type: "line",
        yAxisIndex: 1,
        data: running.map((pump) =>
          pump.absorbed_power_w === null ? null : pump.absorbed_power_w / 1000,
        ),
      },
    ],
  };

  return <EChart option={option} ariaLabel="Rendement et puissance absorbée par pompe" />;
}

/** NPSH disponible, requis et marge résultante. */
export function NpshChart({ pumps }: { pumps: PumpResultRow[] }) {
  const running = pumps.filter(
    (pump) => pump.running && (pump.npsh_available_m !== null || pump.npsh_required_m !== null),
  );
  if (!running.length) {
    return null;
  }

  const option: EChartsOption = {
    grid: { left: 60, right: 24, top: 40, bottom: 56 },
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    xAxis: { type: "category", data: running.map((pump) => pump.pump_id), axisLabel: AXIS_LABEL },
    yAxis: { type: "value", name: "NPSH (m)", axisLabel: AXIS_LABEL },
    series: [
      {
        name: "NPSH disponible",
        type: "bar",
        data: running.map((pump) => pump.npsh_available_m),
      },
      {
        name: "NPSH requis",
        type: "bar",
        data: running.map((pump) => pump.npsh_required_m),
      },
      {
        name: "Marge",
        type: "line",
        data: running.map((pump) => pump.npsh_margin_m),
      },
    ],
  };

  return <EChart option={option} ariaLabel="NPSH disponible, requis et marge par pompe" />;
}

/** Niveaux, volumes et débit d'un transfert au fil du temps. */
export function TransferTimelineChart({ transfer }: { transfer: Transfer }) {
  const samples = transfer.result_payload.samples;
  if (!samples.length) {
    return null;
  }

  const minutes = (sample: Record<string, number | null>) => Number(sample.time_s ?? 0) / 60;
  const option: EChartsOption = {
    grid: { left: 60, right: 60, top: 40, bottom: 56 },
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    xAxis: {
      type: "value",
      name: "Temps (min)",
      nameLocation: "middle",
      nameGap: 28,
      axisLabel: AXIS_LABEL,
    },
    yAxis: [
      { type: "value", name: "Niveau (m)", axisLabel: AXIS_LABEL },
      { type: "value", name: "Débit (m³/h)", axisLabel: AXIS_LABEL },
    ],
    series: [
      {
        name: "Niveau source",
        type: "line",
        showSymbol: false,
        data: samples.map((sample) => [minutes(sample), sample.source_level_m]),
      },
      {
        name: "Niveau destination",
        type: "line",
        showSymbol: false,
        data: samples.map((sample) => [minutes(sample), sample.destination_level_m]),
      },
      {
        name: "Débit",
        type: "line",
        yAxisIndex: 1,
        showSymbol: false,
        data: samples.map((sample) => [
          minutes(sample),
          sample.flow_m3_s === null || sample.flow_m3_s === undefined
            ? null
            : Number(sample.flow_m3_s) * 3600,
        ]),
      },
    ],
  };

  return <EChart option={option} ariaLabel="Évolution des niveaux et du débit du transfert" />;
}

/** Comparaison des calculs classés : débit et puissance absorbée. */
export function ScenarioComparisonChart({ comparison }: { comparison: Comparison }) {
  const ranked = comparison.result_payload.ranked;
  if (!ranked.length) {
    return null;
  }

  const option: EChartsOption = {
    grid: { left: 60, right: 60, top: 40, bottom: 56 },
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    xAxis: {
      type: "category",
      data: ranked.map((item) => item.calculation_id.slice(0, 8)),
      axisLabel: AXIS_LABEL,
    },
    yAxis: [
      { type: "value", name: "Débit (m³/h)", axisLabel: AXIS_LABEL },
      { type: "value", name: "Puissance (kW)", axisLabel: AXIS_LABEL },
    ],
    series: [
      {
        name: "Débit",
        type: "bar",
        data: ranked.map((item) => (item.flow_m3_s === null ? null : item.flow_m3_s * 3600)),
      },
      {
        name: "Puissance absorbée",
        type: "line",
        yAxisIndex: 1,
        data: ranked.map((item) =>
          item.total_power_w === null ? null : item.total_power_w / 1000,
        ),
      },
    ],
  };

  return <EChart option={option} ariaLabel="Comparaison du débit et de la puissance par calcul" />;
}
