export interface LocalizedFile {
  filePath: string;
  confidence: number;
  reason: string;
  astSymbol?: string;
  lineRange?: [number, number];
  diffSnippet?: string;
  changeType?: 'modify' | 'add' | 'refactor';
  /** LLM re-rank priority: 1 = primary edit site, 2 = supporting, 3 = test/config. */
  priority?: number;
  /** Newcomer-readable "why this file" from the LLM re-ranking, grounded in real source. */
  whyThisFile?: string;
  /** True when the LLM re-ordered/annotated this file (vs the raw deterministic AST order). */
  aiRanked?: boolean;
  /** True when this file's real source was fetched and fed to the model. */
  grounded?: boolean;
}

export interface FixStep {
  stepNumber: number;
  title: string;
  description: string;
  codeSnippet?: string;
  guidelineRule?: string; // Reference to repo's CONTRIBUTING.md rule
  validationCommand?: string;
}

export interface ReproSnippet {
  language: 'python' | 'typescript' | 'bash' | 'rust' | 'go' | 'cpp';
  code: string;
  runCommand: string;
  expectedFailure: string;
  environmentNotes?: string;
  filename?: string;
  /** provider:model when the repro was LLM-synthesized & grounded; absent = deterministic scaffold. */
  provider?: string;
  /** True when the script calls the repo's REAL symbols (LLM-grounded), not a generic scaffold. */
  grounded?: boolean;
}

/** A grounded unified-diff patch for the primary edit site, produced from the file's real source. */
export interface GroundedPatch {
  primaryFile: string;
  diffSnippet: string;
  /** Plain-language explanation of the change, written for a first-time contributor. */
  explanation?: string;
  /** "Low/Medium/High + one-line justification" of regression risk. */
  regressionRisk?: string;
  /** provider:model that produced the patch. */
  provider?: string;
}

/** Where the summarized CONTRIBUTING guidelines actually came from in the repo. */
export interface ContributingSource {
  path: string;
  url: string;
}

export interface TriageReport {
  issueId: string;
  summary: string;
  rootCauseAnalysis: string;
  affectedSubsystems: string[];
  localizedFiles: LocalizedFile[];
  reproduction: ReproSnippet;
  fixBlueprint: FixStep[];
  contributingGuidelinesSummary: string[];
  branchingConvention: string;
  suggestedPrTitle: string;
  generatedAt: string;
  confidenceScore: number;
  /** True when a real LLM produced the semantic analysis; false/undefined = deterministic AST-only. */
  llmEnhanced?: boolean;
  /** Provider:model that produced the enhancement, e.g. "gemini:gemini-3.5-flash-lite". */
  provider?: string;
  /** Repo files whose real source grounded the analysis (empty => issue-text only). */
  groundedFiles?: string[];
  /** Grounded unified-diff patch for the primary edit site (absent => no patch offered). */
  patch?: GroundedPatch;
  /** Source of the CONTRIBUTING guidelines when distilled from the repo's REAL guide. */
  contributingSource?: ContributingSource;
  /** provider:model that summarized the real CONTRIBUTING guide (absent => deterministic template). */
  contributingProvider?: string;
  /** True when this report is an offline illustrative sample, not real backend analysis. */
  isDemo?: boolean;
}
