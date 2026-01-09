// apps/frontend/src/shared/types/squad.ts

/**
 * Squad Configuration Types for ROI Calculations
 *
 * Squads are global entities that define configurable values for ROI calculations.
 * They can be associated with multiple projects.
 */

// Seniority levels for team members
export type Seniority = 'junior' | 'mid' | 'senior' | 'staff' | 'principal';

// Role types for team members
export type Role =
  | 'developer'
  | 'qa'
  | 'devops'
  | 'pm'
  | 'architect'
  | 'tech_lead';

// All seniority levels
export const SENIORITY_LEVELS: Seniority[] = ['junior', 'mid', 'senior', 'staff', 'principal'];

// All role types
export const ROLE_TYPES: Role[] = ['developer', 'qa', 'devops', 'pm', 'architect', 'tech_lead'];

// Display names for seniorities
export const SENIORITY_DISPLAY_NAMES: Record<Seniority, string> = {
  junior: 'Junior',
  mid: 'Mid-Level',
  senior: 'Senior',
  staff: 'Staff',
  principal: 'Principal',
};

// Display names for roles
export const ROLE_DISPLAY_NAMES: Record<Role, string> = {
  developer: 'Developer',
  qa: 'QA Engineer',
  devops: 'DevOps',
  pm: 'Project Manager',
  architect: 'Architect',
  tech_lead: 'Tech Lead',
};

/**
 * Create a stakeholder key from seniority and role
 */
export function createStakeholderKey(seniority: Seniority, role: Role): string {
  return `${seniority}_${role}`;
}

/**
 * Parse a stakeholder key into seniority and role
 */
export function parseStakeholderKey(key: string): { seniority: Seniority; role: Role } | null {
  const parts = key.split('_');
  if (parts.length !== 2) return null;

  const seniority = parts[0] as Seniority;
  const role = parts[1] as Role;

  if (!SENIORITY_LEVELS.includes(seniority) || !ROLE_TYPES.includes(role)) {
    return null;
  }

  return { seniority, role };
}

/**
 * Time savings estimates per activity (in minutes)
 */
export interface TimeSavingsConfig {
  prReview: number;
  issueTriage: number;
  ideaGeneration: number;
  roadmapPlanning: number;
  specWriting: number;
  codebaseExploration: number;
  conflictResolution: number;
}

/**
 * Display names for time savings activities
 */
export const TIME_SAVINGS_DISPLAY_NAMES: Record<keyof TimeSavingsConfig, string> = {
  prReview: 'PR Review',
  issueTriage: 'Issue Triage',
  ideaGeneration: 'Idea Generation',
  roadmapPlanning: 'Roadmap Planning',
  specWriting: 'Spec Writing',
  codebaseExploration: 'Codebase Exploration',
  conflictResolution: 'Conflict Resolution',
};

/**
 * Prevention values (estimated cost of bugs/issues in production)
 */
export interface PreventionValuesConfig {
  securityCritical: number;
  securityHigh: number;
  securityMedium: number;
  performanceCritical: number;
  performanceHigh: number;
  bugCritical: number;
  bugHigh: number;
  bugMedium: number;
}

/**
 * Display names for prevention value categories
 */
export const PREVENTION_VALUES_DISPLAY_NAMES: Record<keyof PreventionValuesConfig, string> = {
  securityCritical: 'Security (Critical)',
  securityHigh: 'Security (High)',
  securityMedium: 'Security (Medium)',
  performanceCritical: 'Performance (Critical)',
  performanceHigh: 'Performance (High)',
  bugCritical: 'Bug (Critical)',
  bugHigh: 'Bug (High)',
  bugMedium: 'Bug (Medium)',
};

/**
 * Quality multipliers for ROI adjustments
 * Values are percentages (e.g., 0.30 = +30%, -0.30 = -30%)
 */
export interface QualityMultipliersConfig {
  firstPassQaBonus: number;
  secondPassQaBonus: number;
  qaFailedPenalty: number;
  hasTestsBonus: number;
  hasDocsBonus: number;
  hasTypesBonus: number;
  highCoverageBonus: number;
  mediumCoverageBonus: number;
  manyLintErrorsPenalty: number;
  reworkPenalty: number;
}

/**
 * Display names for quality multipliers
 */
export const QUALITY_MULTIPLIERS_DISPLAY_NAMES: Record<keyof QualityMultipliersConfig, string> = {
  firstPassQaBonus: 'First-Pass QA Bonus',
  secondPassQaBonus: 'Second-Pass QA Bonus',
  qaFailedPenalty: 'QA Failed Penalty',
  hasTestsBonus: 'Has Tests Bonus',
  hasDocsBonus: 'Has Documentation Bonus',
  hasTypesBonus: 'Has Types Bonus',
  highCoverageBonus: 'High Coverage Bonus (≥80%)',
  mediumCoverageBonus: 'Medium Coverage Bonus (≥60%)',
  manyLintErrorsPenalty: 'Many Lint Errors Penalty',
  reworkPenalty: 'Rework Penalty',
};

/**
 * Complete Squad configuration
 */
export interface Squad {
  id: string;
  name: string;
  description?: string;

  // Stakeholder hourly rates (keyed by "seniority_role", e.g., "senior_developer")
  stakeholderRates: Record<string, number>;

  // Default hourly rate (fallback when specific rate not defined)
  defaultHourlyRate: number;

  // Time savings configuration
  timeSavings: TimeSavingsConfig;

  // Prevention values configuration
  preventionValues: PreventionValuesConfig;

  // Quality multipliers configuration
  qualityMultipliers: QualityMultipliersConfig;

  // Feature value multipliers (optional overrides)
  featureMultipliers?: Record<string, number>;

  // Metadata
  createdAt: number;
  updatedAt: number;
}

/**
 * Squad file structure (stored in squads.json)
 */
export interface SquadsFile {
  squads: Squad[];
  version: number;
}

/**
 * Form data for creating/editing squads
 */
export interface SquadFormData {
  name: string;
  description?: string;
  stakeholderRates: Record<string, number>;
  defaultHourlyRate: number;
  timeSavings: TimeSavingsConfig;
  preventionValues: PreventionValuesConfig;
  qualityMultipliers: QualityMultipliersConfig;
  featureMultipliers?: Record<string, number>;
}

/**
 * Default time savings configuration (in minutes)
 */
export const DEFAULT_TIME_SAVINGS: TimeSavingsConfig = {
  prReview: 30,
  issueTriage: 10,
  ideaGeneration: 60,
  roadmapPlanning: 120,
  specWriting: 180,
  codebaseExploration: 45,
  conflictResolution: 20,
};

/**
 * Default prevention values (in USD)
 */
export const DEFAULT_PREVENTION_VALUES: PreventionValuesConfig = {
  securityCritical: 10000,
  securityHigh: 5000,
  securityMedium: 1000,
  performanceCritical: 5000,
  performanceHigh: 2000,
  bugCritical: 3000,
  bugHigh: 1000,
  bugMedium: 300,
};

/**
 * Default quality multipliers (as percentages, e.g., 0.30 = +30%)
 */
export const DEFAULT_QUALITY_MULTIPLIERS: QualityMultipliersConfig = {
  firstPassQaBonus: 0.30,
  secondPassQaBonus: 0.15,
  qaFailedPenalty: -0.30,
  hasTestsBonus: 0.20,
  hasDocsBonus: 0.10,
  hasTypesBonus: 0.10,
  highCoverageBonus: 0.15,
  mediumCoverageBonus: 0.05,
  manyLintErrorsPenalty: -0.10,
  reworkPenalty: -0.20,
};

/**
 * Default stakeholder rates (in USD per hour)
 * Generates all combinations of seniority x role
 */
export function generateDefaultStakeholderRates(): Record<string, number> {
  const rates: Record<string, number> = {};

  // Base rates by seniority
  const seniorityBaseRates: Record<Seniority, number> = {
    junior: 50,
    mid: 75,
    senior: 125,
    staff: 175,
    principal: 225,
  };

  // Role multipliers (relative to developer baseline)
  const roleMultipliers: Record<Role, number> = {
    developer: 1.0,
    qa: 0.9,
    devops: 1.1,
    pm: 0.95,
    architect: 1.2,
    tech_lead: 1.15,
  };

  for (const seniority of SENIORITY_LEVELS) {
    for (const role of ROLE_TYPES) {
      const key = createStakeholderKey(seniority, role);
      const rate = Math.round(seniorityBaseRates[seniority] * roleMultipliers[role]);
      rates[key] = rate;
    }
  }

  return rates;
}

/**
 * Default stakeholder rates
 */
export const DEFAULT_STAKEHOLDER_RATES = generateDefaultStakeholderRates();

/**
 * Default squad configuration (used for new squads)
 */
export const DEFAULT_SQUAD_CONFIG: Omit<Squad, 'id' | 'name' | 'createdAt' | 'updatedAt'> = {
  stakeholderRates: DEFAULT_STAKEHOLDER_RATES,
  defaultHourlyRate: 150,
  timeSavings: DEFAULT_TIME_SAVINGS,
  preventionValues: DEFAULT_PREVENTION_VALUES,
  qualityMultipliers: DEFAULT_QUALITY_MULTIPLIERS,
};

/**
 * Squads file schema version
 */
export const SQUADS_FILE_VERSION = 1;

/**
 * Create a new squad with default values
 */
export function createNewSquad(name: string, description?: string): Squad {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    name,
    description,
    ...DEFAULT_SQUAD_CONFIG,
    createdAt: now,
    updatedAt: now,
  };
}

/**
 * Get hourly rate for a specific stakeholder type
 */
export function getStakeholderRate(
  squad: Squad,
  seniority?: Seniority,
  role?: Role
): number {
  if (seniority && role) {
    const key = createStakeholderKey(seniority, role);
    if (key in squad.stakeholderRates) {
      return squad.stakeholderRates[key];
    }
  }
  return squad.defaultHourlyRate;
}
