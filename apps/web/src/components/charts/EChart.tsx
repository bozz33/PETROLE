import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";

import { cn } from "@/lib/utils";

interface EChartProps {
  option: EChartsOption;
  className?: string;
  ariaLabel: string;
}

export function EChart({ option, className, ariaLabel }: EChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const chart = echarts.init(container, undefined, { renderer: "canvas" });
    chart.setOption(option, { notMerge: true });

    const resizeObserver = new ResizeObserver(() => chart.resize());
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.dispose();
    };
  }, [option]);

  return (
    <div
      ref={containerRef}
      className={cn("min-h-64 w-full", className)}
      role="img"
      aria-label={ariaLabel}
    />
  );
}
