import { describe, expect, it } from "vitest";

import { maopEnvelopePoints } from "./HydraulicCharts";
import type { CalculationProfilePoint, SegmentResultRow } from "../../types";

const profile: CalculationProfilePoint[] = [
  {
    chainage_m: 0,
    elevation_m: 10,
    pressure_pa: 3_000_000,
    hydraulic_grade_m: 370,
    flow_m3_s: 0.2,
    velocity_m_s: 1,
    below_vapor_pressure: false,
    gravity_zone: false,
  },
  {
    chainage_m: 10_000,
    elevation_m: 30,
    pressure_pa: 2_800_000,
    hydraulic_grade_m: 350,
    flow_m3_s: 0.2,
    velocity_m_s: 1,
    below_vapor_pressure: false,
    gravity_zone: false,
  },
  {
    chainage_m: 20_000,
    elevation_m: 15,
    pressure_pa: 2_700_000,
    hydraulic_grade_m: 335,
    flow_m3_s: 0.2,
    velocity_m_s: 1,
    below_vapor_pressure: false,
    gravity_zone: false,
  },
];

function segment(overrides: Partial<SegmentResultRow>): SegmentResultRow {
  return {
    segment_id: "L-001",
    label: null,
    flow_m3_s: 0.2,
    velocity_m_s: 1,
    reynolds: 100_000,
    friction_factor: 0.02,
    friction_model: "colebrook_white",
    friction_head_loss_m: 5,
    minor_head_loss_m: 0,
    total_head_loss_m: 5,
    elevation_change_m: 0,
    inlet_pressure_pa: 3_000_000,
    outlet_pressure_pa: 2_800_000,
    min_pressure_pa: 2_800_000,
    max_pressure_pa: 3_000_000,
    maop_margin_pa: 5_000_000,
    flow_regime: "turbulent",
    ...overrides,
  };
}

describe("enveloppe MAOP/MAWP", () => {
  it("utilise uniquement la limite et les bornes effectivement publiées par les segments", () => {
    const values = maopEnvelopePoints(profile, [
      segment({ start_chainage_m: 0, end_chainage_m: 10_000, maop_pa: 8_000_000 }),
      segment({
        segment_id: "L-002",
        start_chainage_m: 10_000,
        end_chainage_m: 20_000,
        maop_pa: 6_000_000,
      }),
    ]);

    expect(values).toEqual([
      [0, 80],
      [10, 80],
      [20, 60],
    ]);
  });

  it("laisse une lacune lorsqu'une limite ou son chaînage n'est pas publié", () => {
    expect(
      maopEnvelopePoints(profile, [
        segment({ maop_margin_pa: 5_000_000, maop_pa: undefined }),
      ]),
    ).toEqual([
      [0, null],
      [10, null],
      [20, null],
    ]);
  });
});
