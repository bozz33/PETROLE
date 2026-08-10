/** Visualisation V1-A3 d'une projection temporelle SI, sans masquer ses alertes. */

import { useMemo } from "react";
import type { EChartsOption } from "echarts";

import type { SeriesAnalysisPoint } from "../../types";
import { EChart } from "./EChart";

export function TimeSeriesChart({
  points,
  siUnit,
  processingVersion,
}: {
  points: SeriesAnalysisPoint[];
  siUnit: string;
  processingVersion: string;
}) {
  const option = useMemo<EChartsOption>(
    () => ({
      grid: { left: 72, right: 28, top: 48, bottom: 60 },
      tooltip: {
        trigger: "axis",
        valueFormatter: (value) => (value === null || value === undefined ? "—" : String(value)),
      },
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
          name: "Projection SI",
          type: "line",
          showSymbol: false,
          connectNulls: false,
          data: points.map((point) => [point.timestamp, point.value_si]),
        },
        {
          name: "Doublon",
          type: "scatter",
          symbolSize: 9,
          itemStyle: { color: "#d97706" },
          data: points
            .filter((point) => point.duplicate)
            .map((point) => [point.timestamp, point.value_si]),
        },
        {
          name: "Aberrant signalé",
          type: "scatter",
          symbol: "diamond",
          symbolSize: 11,
          itemStyle: { color: "#dc2626" },
          data: points
            .filter((point) => point.outlier)
            .map((point) => [point.timestamp, point.value_si]),
        },
      ],
    }),
    [points, processingVersion, siUnit],
  );

  return (
    <EChart
      option={option}
      className="time-series-chart"
      ariaLabel={`Série temporelle en unité SI, projection ${processingVersion}`}
    />
  );
}
