/** Graphiques V1-B : observation, référence stationnaire et résidu signé. */

import { useMemo } from "react";
import type { EChartsOption } from "echarts";

import type { MeasurementResidual } from "../../types";
import { EChart } from "./EChart";

export function MeasurementVsSimulationChart({
  points,
  siUnit,
}: {
  points: MeasurementResidual[];
  siUnit: string;
}) {
  const option = useMemo<EChartsOption>(
    () => ({
      grid: { left: 78, right: 28, top: 48, bottom: 60 },
      tooltip: { trigger: "axis" },
      legend: { top: 0 },
      xAxis: {
        type: "time",
        name: "Horodatage (UTC)",
        nameLocation: "middle",
        nameGap: 34,
      },
      yAxis: { type: "value", name: `Valeur (${siUnit})` },
      series: [
        {
          name: "Mesure SI",
          type: "line",
          showSymbol: true,
          symbolSize: 7,
          connectNulls: false,
          data: points.map((point) => [point.timestamp, point.measured_value_si]),
        },
        {
          name: "Simulation stationnaire",
          type: "line",
          showSymbol: false,
          lineStyle: { type: "dashed", width: 2 },
          data: points.map((point) => [point.timestamp, point.simulated_value_si]),
        },
        {
          name: "Exclue des KPI",
          type: "scatter",
          symbol: "diamond",
          symbolSize: 10,
          itemStyle: { color: "#d97706" },
          data: points
            .filter((point) => !point.included_in_kpi)
            .map((point) => [point.timestamp, point.measured_value_si]),
        },
      ],
    }),
    [points, siUnit],
  );

  return (
    <EChart
      option={option}
      className="time-series-chart"
      ariaLabel="Mesures SI et référence de simulation stationnaire"
    />
  );
}

export function ResidualChart({ points, siUnit }: { points: MeasurementResidual[]; siUnit: string }) {
  const option = useMemo<EChartsOption>(
    () => ({
      grid: { left: 78, right: 28, top: 48, bottom: 60 },
      tooltip: { trigger: "axis" },
      legend: { top: 0 },
      xAxis: {
        type: "time",
        name: "Horodatage (UTC)",
        nameLocation: "middle",
        nameGap: 34,
      },
      yAxis: { type: "value", name: `Résidu (${siUnit})` },
      series: [
        {
          name: "Résidu = mesure − simulation",
          type: "bar",
          itemStyle: { color: "#2563eb" },
          data: points.map((point) => [point.timestamp, point.residual_si]),
          markLine: { data: [{ yAxis: 0, name: "Zéro" }] },
        },
      ],
    }),
    [points, siUnit],
  );

  return (
    <EChart
      option={option}
      className="time-series-chart"
      ariaLabel="Résidus signés, mesure moins simulation"
    />
  );
}
