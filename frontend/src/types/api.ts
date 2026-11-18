export type TaskType = "classification" | "regression";
export type SizePreset = "small" | "medium" | "large" | "very_large";
export type Domain =
  | "finance"
  | "healthcare"
  | "ecommerce"
  | "marketing"
  | "automotive"
  | "iot"
  | "hr"
  | "generic";

export interface HealthResponse {
  status: string;
  api_version: string;
  engine_available: boolean;
}

export interface GenerationMetadata {
  generation_id: string;
  plan_id: string;
  created_at: string;
  dataset_name: string;
  task: TaskType;
  rows: number;
  feature_count: number;
  files: Record<string, boolean>;
}

export interface GenerationResponse {
  status: string;
  generation: GenerationMetadata;
}

export interface PreviewResponse {
  generation_id: string;
  columns: string[];
  row_count: number;
  data_types: Record<string, string>;
  records: Array<Record<string, unknown>>;
}

export interface ReportResponse {
  generation_id: string;
  report: QualityReport;
}

export interface HistoryResponse {
  items: GenerationMetadata[];
  total: number;
  limit: number;
  offset: number;
}

export interface PlanSummary {
  plan_id: string;
  created_at: string;
  name: string;
  dataset_name: string;
  task: TaskType;
}

export interface PlanListResponse {
  items: PlanSummary[];
}

export interface DatasetPlan {
  plan_version?: number;
  task: TaskType;
  name: string;
  description: string;
  dataset_name: string;
  features: Array<Record<string, unknown>>;
  target_name: string;
  target_formula: Array<Record<string, unknown>>;
  domain: Domain;
  seed: number;
  rows?: number | null;
  [key: string]: unknown;
}

export interface PlanResponse {
  plan_id: string;
  created_at: string;
  plan: DatasetPlan;
}

export interface QualityReport {
  metadata?: {
    rows?: number;
    columns?: number;
    generation_time_seconds?: number;
    seed?: number;
    domain?: string;
    task?: TaskType;
    plan_version?: number;
  };
  target_stats?: {
    class_distribution?: Record<string, number>;
    class_balance?: number;
    mean?: number;
    std?: number;
    min?: number;
    max?: number;
  };
  feature_stats?: Record<string, FeatureStat>;
  relationship_stats?: Record<string, RelationshipStat>;
  data_quality?: {
    missingness_rates?: Record<string, number>;
    outlier_counts?: Record<string, number>;
    bound_violations?: Record<string, number>;
  };
  [key: string]: unknown;
}

export interface FeatureStat {
  type?: string;
  mean?: number | null;
  std?: number | null;
  missing_rate?: number;
  unique_values?: number;
  top_values?: Record<string, number>;
}

export interface RelationshipStat {
  coefficient?: number;
  correlation?: number;
}

export interface GenerateRequest {
  description: string;
  task: TaskType;
  size: SizePreset;
  seed: number;
  domain: Domain;
  plan_id?: string;
}

export interface AnalysisFinding {
  severity: "issue" | "warning" | string;
  category: string;
  message: string;
  details: Record<string, unknown>;
}

export interface AnalysisResponse {
  generation_id: string;
  dataset_name: string;
  task: TaskType;
  rows: number;
  column_count: number;
  target_name?: string | null;
  columns: Array<{ name: string; dtype: string; kind: string; missing_percentage: number; unique_count: number; constant: boolean; [key: string]: unknown }>;
  numerical: Array<{ name: string; mean?: number | null; median?: number | null; std?: number | null; min?: number | null; max?: number | null; skew?: number | null; kurtosis?: number | null; outlier_percentage?: number; distribution?: Array<{ label: string; count: number }>; [key: string]: unknown }>;
  categorical: Array<{ name: string; unique_count: number; top_value?: string | null; top_percentage?: number; high_cardinality?: boolean; frequencies?: Array<{ value: string; count: number; percentage: number }>; [key: string]: unknown }>;
  quality: { score: number; grade: string; dimensions: Record<string, { score: number; weight: number; applicable: boolean; detail: string }>; formula: string; issue_count: number; warning_count: number };
  findings: AnalysisFinding[];
  recommendations: string[];
  correlations: { matrix: Record<string, Record<string, number | null>>; spearman_matrix?: Record<string, Record<string, number | null>>; high_correlations: Array<{ left: string; right: string; pearson: number | null; spearman: number | null }>; target_associations: Array<{ feature: string; pearson: number | null; spearman: number | null; method: string }> };
  target: { name?: string | null; distribution: Record<string, number> };
  privacy_note: string;
}
