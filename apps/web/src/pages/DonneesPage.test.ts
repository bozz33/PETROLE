import { describe, expect, it } from "vitest";

import { buildSeriesAnalysisPath } from "./DonneesPage";

describe("appel d'analyse des séries temporelles", () => {
  it("impose une version de traitement et ne mélange que les qualités choisies", () => {
    expect(
      buildSeriesAnalysisPath("tag-1", {
        processingVersion: "pilot-v1-a3",
        startTimestamp: "2026-08-09T10:00",
        endTimestamp: "2026-08-09T11:00",
        qualities: ["good", "bad"],
        referenceInterval: "60",
        gapFactor: "1.5",
        outlierMethod: "zscore",
        outlierThreshold: "2.5",
        offset: 500,
      }),
    ).toBe(
      "/measurement-tags/tag-1/series-analysis?processing_version=pilot-v1-a3&gap_factor=1.5&outlier_method=zscore&zscore_threshold=2.5&iqr_multiplier=1.5&limit=500&offset=500&start_timestamp=2026-08-09T10%3A00%3A00.000Z&end_timestamp=2026-08-09T11%3A00%3A00.000Z&reference_interval_seconds=60&qualities=good&qualities=bad",
    );
  });

  it("refuse un appel sans tag ou sans projection et conserve les seuils par défaut", () => {
    expect(
      buildSeriesAnalysisPath("", {
        processingVersion: "pilot-v1-a3",
        startTimestamp: "",
        endTimestamp: "",
        qualities: [],
        referenceInterval: "",
        gapFactor: "0.5",
        outlierMethod: "iqr",
        outlierThreshold: "",
        offset: 0,
      }),
    ).toBeNull();
    expect(
      buildSeriesAnalysisPath("tag-1", {
        processingVersion: "",
        startTimestamp: "",
        endTimestamp: "",
        qualities: [],
        referenceInterval: "",
        gapFactor: "0.5",
        outlierMethod: "iqr",
        outlierThreshold: "",
        offset: 0,
      }),
    ).toBeNull();
    expect(
      buildSeriesAnalysisPath("tag-1", {
        processingVersion: "pilot-v1-a3",
        startTimestamp: "",
        endTimestamp: "",
        qualities: [],
        referenceInterval: "",
        gapFactor: "0.5",
        outlierMethod: "iqr",
        outlierThreshold: "",
        offset: 0,
      }),
    ).toContain("gap_factor=1.5&outlier_method=iqr&zscore_threshold=3&iqr_multiplier=1.5");
  });
});
