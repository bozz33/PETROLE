/** Types correspondant aux contrats OpenAPI utilisés par l'interface. */

export interface AuthStatus {
  authentication_required: boolean;
  initialized: boolean;
}

export interface Membership {
  id: string;
  organization_id: string;
  role: "admin" | "engineer" | "operator" | "approver" | "viewer";
  created_at: string;
}

export interface UserAccount {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  memberships: Membership[];
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
  user: UserAccount;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  default_locale: string;
  default_unit_system: string;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}


export interface Site {
  id: string;
  organization_id: string;
  name: string;
  code: string;
  country_code: string | null;
  latitude: number | null;
  longitude: number | null;
  status: "active" | "archived";
  created_at: string;
  updated_at: string;
}

export interface Tank {
  id: string;
  organization_id: string;
  site_id: string | null;
  name: string;
  code: string;
  tank_type: string;
  elevation_m: number;
  current_level_m: number;
  current_volume_m3: number;
  nominal_capacity_m3: number;
  available_capacity_m3: number;
  pumpable_volume_m3: number;
  fluid_id: string | null;
  compatible_fluid_ids: string[];
  status: string;
  dead_volume_m3: number;
  levels: Record<string, number | null>;
  strapping: Array<{ height_m: number; volume_m3: number }>;
  created_at: string;
  updated_at: string;
}

export interface Transfer {
  id: string;
  organization_id: string;
  source_tank_id: string;
  destination_tank_id: string;
  status: string;
  input_hash: string;
  input_payload: Record<string, unknown>;
  result_payload: {
    stop_reason: string;
    target_reached: boolean;
    duration_s: number;
    withdrawn_volume_m3: number;
    received_volume_m3: number;
    losses_m3: number;
    balance_residual_m3: number;
    energy_j: number | null;
    source_final_level_m: number;
    destination_final_level_m: number;
    messages: string[];
    warning_codes: string[];
    violation_codes: string[];
    samples: Array<Record<string, number | null>>;
  };
  balance_payload: Record<string, unknown> | null;
  created_at: string;
  started_at: string;
  finished_at: string;
}

export interface Comparison {
  id: string;
  organization_id: string;
  project_id: string;
  calculation_ids: string[];
  content_hash: string;
  result_payload: {
    reference_calculation_id: string;
    recommended_calculation_id: string;
    ranked: Array<{
      rank: number;
      calculation_id: string;
      scenario_id: string;
      status: string;
      flow_m3_s: number | null;
      minimum_pressure_pa: number | null;
      maximum_pressure_pa: number | null;
      total_head_loss_m: number | null;
      total_power_w: number | null;
      feasible: boolean;
      approvable: boolean;
      violation_count: number;
      warning_count: number;
      input_hash: string;
    }>;
  };
  created_at: string;
}

export interface Optimization {
  id: string;
  organization_id: string;
  scenario_id: string;
  status: string;
  input_hash: string;
  input_payload: Record<string, unknown>;
  result_payload: {
    status: string;
    solver_name: string;
    generated_count: number;
    evaluated_count: number;
    complete: boolean;
    optimality_gap: number | null;
    best: {
      rank: number;
      objective_value: number;
      configuration: {
        id: string;
        active_pump_ids: string[];
        speed_ratios: Record<string, number>;
        active_pump_count: number;
      };
      evaluation: {
        flow_m3_s: number;
        energy_kwh: number | null;
        cost: number | null;
        minimum_pressure_pa: number | null;
        maximum_pressure_pa: number | null;
        violation_codes: string[];
      };
    } | null;
    ranked: Array<Record<string, unknown>>;
    rejected: Array<Record<string, unknown>>;
  };
  engine_version: string;
  created_at: string;
  started_at: string;
  finished_at: string;
}

export interface Project {
  id: string;
  organization_id: string;
  site_id: string | null;
  name: string;
  code: string;
  description: string | null;
  country_code: string | null;
  status: "draft" | "active" | "archived";
  created_at: string;
  updated_at: string;
}

export interface ModelVersion {
  id: string;
  project_id: string;
  parent_id: string | null;
  version_number: number;
  name: string;
  status: "draft" | "approved" | "archived";
  content_hash: string;
  payload: Record<string, unknown>;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Scenario {
  id: string;
  model_version_id: string;
  parent_id: string | null;
  name: string;
  description: string | null;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Calculation {
  id: string;
  scenario_id: string;
  engine: string;
  engine_version: string;
  status: string;
  input_hash: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface CalculationProfilePoint {
  chainage_m: number;
  elevation_m: number;
  pressure_pa: number;
  hydraulic_grade_m: number;
  flow_m3_s: number;
  velocity_m_s: number;
  below_vapor_pressure: boolean;
  gravity_zone: boolean;
}

export interface CalculationIssue {
  code: string;
  message: string;
  severity?: string;
  [key: string]: unknown;
}

export interface CalculationPayload {
  status: string;
  flow_m3_s: number;
  min_pressure_pa: number;
  max_pressure_pa: number;
  total_head_loss_m: number;
  total_power_w: number;
  residual: number;
  feasible: boolean;
  approvable: boolean;
  violations: CalculationIssue[];
  warnings: CalculationIssue[];
  profile: CalculationProfilePoint[];
  [key: string]: unknown;
}

export interface CalculationResult {
  calculation_id: string;
  status: string;
  result: CalculationPayload;
  diagnostics: Record<string, unknown> | null;
}


export interface CalculationSummary {
  calculation_id: string;
  status: string;
  summary: Record<string, unknown>;
  diagnostics: Record<string, unknown> | null;
}

export interface StoredFile {
  id: string;
  organization_id: string;
  filename: string;
  media_type: string;
  size_bytes: number;
  content_hash: string;
  created_at: string;
}

export type DatasetKind =
  | "profile"
  | "pump_curve"
  | "strapping"
  | "measurements"
  | "generic";

export interface Dataset {
  id: string;
  organization_id: string;
  project_id: string | null;
  file_id: string;
  name: string;
  kind: DatasetKind;
  status: string;
  mapping: {
    fields?: Record<string, string>;
    constants?: Record<string, string | number | null>;
  };
  preview: DatasetPreview | Record<string, never>;
  created_at: string;
  updated_at: string;
}

export interface DatasetPreview {
  dataset_id: string;
  columns: string[];
  detected_types: Record<string, string>;
  rows: Array<Record<string, unknown>>;
  row_count: number;
  errors: Array<Record<string, unknown>>;
}

export interface DatasetImport {
  id: string;
  dataset_id: string;
  status: string;
  idempotency_key: string;
  row_count: number;
  accepted_count: number;
  rejected_count: number;
  content_hash: string;
  errors: Array<{
    row: number;
    field: string;
    code: string;
    message: string;
  }>;
  created_at: string;
  finished_at: string | null;
}

export interface Report {
  id: string;
  organization_id: string;
  calculation_id: string | null;
  source_type: string;
  source_id: string;
  file_id: string;
  report_type: string;
  template_version: string;
  format: string;
  locale: string;
  status: string;
  content_hash: string;
  filename: string;
  media_type: string;
  size_bytes: number;
  created_at: string;
  approved_at: string | null;
  approval_comment: string | null;
}

export interface Health {
  status: string;
  service: string;
  version: string;
  environment: string;
}

export function formatDate(value: string | null): string {
  if (!value) {
    return "—";
  }
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatNumber(value: number, maximumFractionDigits = 3): string {
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits }).format(value);
}
