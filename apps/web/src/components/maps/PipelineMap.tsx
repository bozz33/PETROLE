import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

import { cn } from "@/lib/utils";

export interface PipelineMapPoint {
  longitude: number;
  latitude: number;
}

interface PipelineMapProps {
  points: PipelineMapPoint[];
  styleUrl: string;
  className?: string;
}

export function PipelineMap({ points, styleUrl, className }: PipelineMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !points.length) {
      return;
    }

    const coordinates = points.map((point) => [point.longitude, point.latitude] as [number, number]);
    const map = new maplibregl.Map({
      container,
      style: styleUrl,
      center: coordinates[0],
      zoom: 6,
      attributionControl: false,
    });

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    map.on("load", () => {
      map.addSource("pipeline", {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates,
          },
        },
      });
      map.addLayer({
        id: "pipeline-casing",
        type: "line",
        source: "pipeline",
        paint: {
          "line-color": "#ffffff",
          "line-width": 7,
          "line-opacity": 0.85,
        },
      });
      map.addLayer({
        id: "pipeline-line",
        type: "line",
        source: "pipeline",
        paint: {
          "line-color": "#0F4C5C",
          "line-width": 4,
        },
      });

      const bounds = coordinates.reduce(
        (current, coordinate) => current.extend(coordinate),
        new maplibregl.LngLatBounds(coordinates[0], coordinates[0]),
      );
      map.fitBounds(bounds, { padding: 60, maxZoom: 12, duration: 0 });
    });

    return () => map.remove();
  }, [points, styleUrl]);

  if (!points.length) {
    return (
      <div
        className={cn(
          "grid min-h-80 place-items-center rounded-xl border bg-muted text-sm text-muted-foreground",
          className,
        )}
      >
        Aucun point géographique disponible.
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn("min-h-[420px] overflow-hidden rounded-xl border", className)}
      role="img"
      aria-label="Carte géographique du pipeline"
    />
  );
}
