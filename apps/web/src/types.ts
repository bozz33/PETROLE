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

export type OrganizationRole =
  | "admin"
  | "engineer"
  | "operator"
  | "approver"
  | "viewer";

export interface OrganizationMember {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  role: OrganizationRole;
  membership_id: string;
  created_at: string;
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
  project_type: "liquid_pipeline" | "terminal" | "gas_pipeline" | "combined";
  country_code: string | null;
  unit_system: "SI";
  rule_set_ids: string[];
  responsible_user_ids: string[];
  status: "draft" | "active" | "archived";
  created_at: string;
  updated_at: string;
}

export interface StandardReference {
  id: string;
  organization_id: string;
  parent_id: string | null;
  code: string;
  title: string;
  issuing_body: string;
  edition: string;
  publication_date: string | null;
  effective_date: string | null;
  status: "draft" | "active" | "withdrawn" | "archived";
  licensed_copy_ref: string | null;
  source_url: string | null;
  content_hash: string;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RuleSet {
  id: string;
  organization_id: string;
  parent_id: string | null;
  code: string;
  title: string;
  country_code: string | null;
  domain: string;
  version_number: number;
  description: string | null;
  status: "draft" | "approved" | "archived";
  standard_ids: string[];
  content_hash: string;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RuleDefinition {
  id: string;
  rule_set_id: string;
  standard_id: string | null;
  code: string;
  title: string;
  severity: "information" | "warning" | "error" | "blocking";
  domain: string;
  metric_path: string;
  operator: "le" | "lt" | "ge" | "gt" | "eq" | "between";
  limit_value: number;
  upper_limit_value: number | null;
  unit: string | null;
  applicability: { type: "always" };
  parameters: Record<string, unknown>;
  message: string;
  source_clause_ref: string | null;
  status: "draft" | "approved" | "archived";
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  organization_id: string | null;
  actor_id: string | null;
  action: string;
  object_type: string;
  object_id: string;
  correlation_id: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export type CatalogCollection =
  | "fluids"
  | "pumps"
  | "valves"
  | "materials"
  | "accessories";

export interface CatalogItem {
  id: string;
  organization_id: string;
  parent_id: string | null;
  kind: "fluid" | "pump" | "valve" | "material" | "accessory";
  code: string;
  name: string;
  version_number: number;
  status: "draft" | "approved" | "archived";
  payload: Record<string, unknown>;
  source: string | null;
  content_hash: string;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface NetworkNode {
  id: string;
  model_version_id: string;
  code: string;
  name: string;
  kind: "source" | "tank" | "station" | "junction" | "terminal" | "injection" | "offtake";
  elevation_m: number;
  latitude: number | null;
  longitude: number | null;
  status: "available" | "maintenance" | "unavailable";
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ProfilePoint {
  chainage_m: number;
  elevation_m: number;
  latitude: number | null;
  longitude: number | null;
}

export interface NetworkEdge {
  id: string;
  model_version_id: string;
  from_node_id: string;
  to_node_id: string;
  material_catalog_item_id: string | null;
  code: string;
  name: string;
  sequence: number;
  length_m: number;
  inner_diameter_m: number;
  roughness_m: number;
  mawp_pa: number;
  status: "available" | "maintenance" | "unavailable";
  profile_payload: ProfilePoint[];
  fittings_payload: Array<Record<string, unknown>>;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AssetInstance {
  id: string;
  model_version_id: string;
  catalog_item_id: string;
  node_id: string | null;
  edge_id: string | null;
  code: string;
  name: string;
  role: "main" | "standby" | "auxiliary" | "isolation" | "control" | "measurement";
  status: "available" | "maintenance" | "unavailable" | "bypassed";
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface NetworkValidationIssue {
  code: string;
  message: string;
  object_type: string;
  object_id: string | null;
}

export interface NetworkValidationReport {
  model_version_id: string;
  valid: boolean;
  errors: NetworkValidationIssue[];
  warnings: NetworkValidationIssue[];
  node_count: number;
  edge_count: number;
  asset_count: number;
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

/** Modèles de frottement acceptés par le solveur stationnaire (D-v2 § 5.3). */
export type FrictionModel = "colebrook_white" | "haaland" | "swamee_jain" | "altshul";

/** Objectifs proposés par l'optimiseur de configurations (D-v2 § 4.10). */
export type ScenarioObjective =
  | "min_energy"
  | "min_cost"
  | "min_pump_count"
  | "min_starts"
  | "max_flow";

/** État imposé à un équipement pour la durée du scénario (D09 § 4). */
export type EquipmentScenarioStatus =
  | "available"
  | "unavailable"
  | "maintenance"
  | "bypassed";

export interface PumpOverride {
  pump_id: string;
  status: EquipmentScenarioStatus | null;
  running: boolean | null;
  speed_ratio: number | null;
}

export interface StationOverride {
  station_id: string;
  status: EquipmentScenarioStatus | null;
}

export interface SegmentOverride {
  segment_id: string;
  status: EquipmentScenarioStatus | null;
  additional_k: number | null;
}

export interface SolverOptions {
  friction_model: FrictionModel;
  pressure_tolerance_pa: number;
  flow_tolerance_m3_s: number;
  mass_balance_tolerance: number;
  max_iterations: number;
  profile_step_m: number;
  store_iterations: boolean;
  use_quadratic_pump_fit: boolean;
  max_flow_m3_s: number | null;
  detect_gravity_zones: boolean;
  apply_gravity_model: boolean;
  min_velocity_m_s: number | null;
  max_velocity_m_s: number | null;
}

/** Conditions d'étude d'un scénario, alignées sur `ScenarioPayloadInput`. */
export interface ScenarioPayload {
  temperature_k: number | null;
  imposed_flow_m3_s: number | null;
  inlet_pressure_pa: number | null;
  outlet_pressure_pa: number | null;
  inlet_tank_level_m: number | null;
  outlet_tank_level_m: number | null;
  pump_overrides: PumpOverride[];
  station_overrides: StationOverride[];
  segment_overrides: SegmentOverride[];
  solver: SolverOptions;
  objective: ScenarioObjective | null;
  energy_price_per_joule: number | null;
}

export interface Calculation {
  id: string;
  job_id: string | null;
  scenario_id: string;
  engine: string;
  engine_version: string;
  status: string;
  phase: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress_percent: number;
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
  physical_approvable: boolean;
  compliance_status:
    | "not_evaluated"
    | "compliant"
    | "compliant_with_reservations"
    | "non_compliant"
    | "indeterminate";
  decision_eligible: boolean;
  approvable: boolean;
  compliance: {
    status: string;
    counts: {
      total: number;
      compliant: number;
      non_compliant: number;
      not_applicable: number;
      errors: number;
    };
    blocking_failure_count: number;
    reservation_count: number;
    blocking_rule_ids: string[];
  };
  rule_evaluations: Array<{
    id: string;
    rule_set_id: string;
    rule_id: string;
    rule_code: string | null;
    rule_set_hash: string | null;
    status: "compliant" | "non_compliant" | "not_applicable" | "error";
    severity: "information" | "warning" | "error" | "blocking" | null;
    measured_value: number | null;
    limit_value: number | null;
    margin: number | null;
    unit: string | null;
    message: string;
    source_clause_ref: string | null;
  }>;
  violations: CalculationIssue[];
  warnings: CalculationIssue[];
  profile: CalculationProfilePoint[];
  [key: string]: unknown;
}

export interface CalculationResult {
  calculation_id: string;
  status: string;
  result: CalculationPayload | null;
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
  created_at: string;
  approved_at: string | null;
  approval_comment: string | null;
}

export interface Health {
  status: string;
  service: string;
  version: string;
  environment: string;
  build: BuildMetadata;
  deployment: DeploymentMetadata;
}

export interface BuildMetadata {
  application_version: string;
  git_sha: string;
  ref: string;
  build_date: string;
  scientific_engine_version: string;
  database_migration_version: string;
}

export interface DeploymentMetadata {
  mode: "single_org" | "multi_org" | "saas";
  organization_label: string;
}

export interface ScientificValidation {
  suite: string;
  passed: number;
  total: number;
  proof_hash: string;
  engine_version: string;
  executed_at: string;
  environment: string;
  source: string;
}

export interface Readiness {
  status: "ready";
  database: "ready";
  object_storage: "ready";
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

/** Origine d'une valeur de propriété de fluide (D-v2 § 5.5). */
export type PropertySource =
  | "laboratory"
  | "internal_table"
  | "correlation"
  | "coolprop"
  | "constant";

/** Statut qualité d'un point de propriété (D09 § 6). */
export type PropertyQuality = "measured" | "approved" | "estimated" | "extrapolated";

/** Catégories de produits gérées par le MVP (D09 § 6). */
export type FluidCategory =
  | "crude"
  | "gasoline"
  | "diesel"
  | "kerosene"
  | "fuel_oil_light"
  | "fuel_oil_heavy"
  | "condensate"
  | "water"
  | "custom";

export interface PropertyPoint {
  temperature_k: number;
  value: number;
  pressure_pa: number;
  uncertainty: number | null;
  method: string | null;
  quality: PropertyQuality;
}

export interface PropertyTable {
  points: PropertyPoint[];
  source: PropertySource;
  reference: string | null;
}

/** Charge utile d'un produit du catalogue, alignée sur `FluidInput`. */
export interface FluidPayload {
  category: FluidCategory;
  reference_temperature_k: number;
  reference_pressure_pa: number;
  density_kg_m3: number | null;
  kinematic_viscosity_m2_s: number | null;
  vapor_pressure_pa: number | null;
  density_table: PropertyTable | null;
  kinematic_viscosity_table: PropertyTable | null;
  vapor_pressure_table: PropertyTable | null;
  thermal_expansion_1_k: number | null;
  coolprop_name: string | null;
  data_source: string | null;
  batch_reference: string | null;
}

export interface PumpCurve {
  flows_m3_s: number[];
  heads_m: number[];
  efficiencies: number[] | null;
  powers_w: number[] | null;
  npshr_m: number[] | null;
  reference_speed_rpm: number | null;
  interpolation: "linear" | "pchip";
}

/** Charge utile d'une pompe du catalogue, alignée sur `PumpModelInput`. */
export interface PumpPayload {
  curve: PumpCurve;
  manufacturer: string | null;
  motor_rated_power_w: number | null;
  npsh_margin_m: number;
  min_speed_ratio: number;
  max_speed_ratio: number;
  minimum_continuous_flow_m3_s: number | null;
  data_source: string | null;
}
