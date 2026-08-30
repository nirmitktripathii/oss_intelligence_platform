export interface LocalizedFile {
  filePath: string;
  confidence: number;
  reason: string;
  astSymbol?: string;
  lineRange?: [number, number];
  diffSnippet?: string;
  changeType?: 'modify' | 'add' | 'refactor';
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
}
