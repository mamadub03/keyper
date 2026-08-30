// Mirrors agent/schemas.py — keep these two in sync by hand for the MVP.

export type ContinuityStatus = "SAFE" | "AT_RISK" | "UNKNOWN";

export interface Evidence {
  observation: string;
  source: string;
}

export interface AuthenticationFindings {
  institutional_methods_found: string[];
  independent_method_found: boolean;
  independent_method: string | null;
  verified: boolean;
}

export interface RecoveryFindings {
  institutional_dependency_found: boolean;
  independent_method_found: boolean;
  verified: boolean;
}

export interface RemediationOption {
  action: string;
  requires_secret_input: boolean;
}

export interface ScanResult {
  service_name: string;
  service_url: string;
  status: ContinuityStatus;
  authentication: AuthenticationFindings;
  recovery: RecoveryFindings;
  dependencies: string[];
  evidence: Evidence[];
  remediation_options: RemediationOption[];
  human_action_required: boolean;
  summary: string;
}

export interface ScanRequest {
  institutional_identity: string;
  institutional_aliases: string[];
  service_url: string;
  mode: "SCAN";
}

export interface FixRequest extends Omit<ScanRequest, "mode"> {
  mode: "FIX";
  approved: true;
}
