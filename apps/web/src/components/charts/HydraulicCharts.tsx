/**
 * Graphiques métier exigés par la définition du MVP.
 *
 * Chaque courbe est tracée à partir de valeurs réellement produites par les
 * moteurs. Lorsqu'une courbe est reconstituée faute de données directes, elle
 * est explicitement désignée comme telle dans sa légende.
 */

import type { EChartsOption } from "echarts";

import { EChart } from "./EChart";
import type {
  CalculationProfilePoint,
  Comparison,
  PumpResultRow,
  Transfer,
} from "../../types";

const AXIS_LABEL = { fontSize: 11 } as const;

/** Profil hydraulique : ligne piézométrique et terrain suivant le chaînage. */
export function HydraulicProfileChart({ points }: { points: CalculationProfilePoint[] }) {
  const option: EChartsOption = {
    grid: { left: 60, right: 24, top: 40, bottom: 48 },
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
    xAxis: {
      type: "value",
      name: "Chaînage (km)",
      nameLocation: "middle",
      nameGap: 28,
      axisLabel: AXIS_LABEL,
    },
    yAxis: { type: "value", name: "Altitude (m)", axisLabel: AXIS_LABEL },
    series: [
      {
        name: "Ligne piézométrique",
        type: "line",
        showSymbol: false,
        smooth: false,
        data: points.map((point) => [point.chainage_m / 1000, point.hydraulic_grade_m]),
      },
      {
        name: "Profil du terrain",
        type: "line",
        showSymbol: false,
        areaStyle: { opacity: 0.25 },
        data: points.map((point) => [point.chainage_m / 1000, point.elevation_m]),
      },
    ],
  };

  return <EChart option={option} ariaLabel="Profil hydraulique et profil du terrain" />;
}

/** Pression absolue et vitesse suivant le chaînage. */
export function PressureDistanceChart({ points }: { points: CalculationProfilePoint[] }) {
  const option: EChartsOption = {
    grid: { left: 60, right: 60, top: 40, bottom: 48 },
    tooltip: { trigger: "axis" },
    legend: { bottom: 0 },
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
      {
        name: "Pression absolue",
        type: "line",
        showSymbol: false,
        data: points.map((point) => [point.chainage_m / 1000, point.pressure_pa / 100000]),
      },
      {
        name: "Vitesse",
        type: "line",
        yAxisIndex: 1,
        showSymbol: false,
        data: points.map((point) => [point.chainage_m / 1000, point.velocity_m_s]),
      },
    ],
  };

  return <EChart option={option} ariaLabel="Pression absolue et vitesse suivant le chaînage" />;
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
