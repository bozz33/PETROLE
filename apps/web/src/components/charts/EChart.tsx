import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";

import { cn } from "@/lib/utils";

interface EChartProps {
  option: EChartsOption;
  className?: string;
  ariaLabel: string;
  /** Nom de fichier proposé pour un export PNG local haute résolution. */
  exportFileName?: string;
  exportLabel?: string;
}

export function EChart({
  option,
  className,
  ariaLabel,
  exportFileName,
  exportLabel = "Exporter le graphique PNG",
}: EChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const chart = echarts.init(container, undefined, { renderer: "canvas" });
    chartRef.current = chart;
    chart.setOption(option, { notMerge: true });

    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.dispose();
      chartRef.current = null;
    };
  }, [option]);

  const exportPng = () => {
    const chart = chartRef.current;
    if (!chart || !exportFileName) {
      return;
    }
    const link = document.createElement("a");
    link.href = chart.getDataURL({
      type: "png",
      pixelRatio: 3,
      backgroundColor: "#ffffff",
    });
    link.download = exportFileName.endsWith(".png") ? exportFileName : exportFileName + ".png";
    link.click();
  };

  return (
    <div className="chart-export">
      <div
        ref={containerRef}
        className={cn("min-h-64 w-full", className)}
        role="img"
        aria-label={ariaLabel}
      />
      {exportFileName ? (
        <button type="button" className="button button-ghost" onClick={exportPng}>
          {exportLabel}
        </button>
      ) : null}
    </div>
  );
}
