export type Domain = 'ai_ml' | 'data' | 'web' | 'cloud_devops' | 'security' | 'systems';

export type Difficulty = 'easy' | 'medium' | 'hard' | 'good_first_issue' | 'intermediate' | 'advanced';

export type BountySource = 'polar' | 'algora' | 'github_sponsors' | 'issuehunt' | 'custom';

export type ViewMode = 'grid' | 'table' | 'compact';

export interface Repository {
  id?: string;
  name: string;
  owner: string;
  stars: number;
  forks: number;
  language: string;
  avatarUrl?: string;
  repoUrl: string;
  description?: string;
}

export interface Bounty {
  id?: string;
  amountUsd: number;
  currency: string;
  source: BountySource;
  sourceUrl: string;
  isFunded: boolean;
  claimed?: boolean;
}

export interface Issue {
  id: string; // e.g. "vllm-project/vllm#4928"
  githubIssueNumber: number;
  title: string;
  body: string;
  /**
   * LLM-condensed body, present only when the original description exceeded the
   * backend cap (LLM_BODY_MAX_CHARS). When set, it is a faithful <8000-char
   * summary of `body`; when absent, `body` is already the full description.
   */
  bodySummary?: string;
  issueUrl: string;
  repository: Repository;
  domain: Domain;
  difficulty: Difficulty;
  estimatedMinutesToSolve: number;
  effortHours?: number;
  techStack: string[];
  bounty?: Bounty;
  hourlyRoiUsd?: number;
  confidenceScore: number;
  createdAt: string;
  updatedAt: string;
  hasTriageReport: boolean;
  labels?: string[];
  author?: string;
}

export interface PaginatedIssuesResponse {
  items: Issue[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  domainCounts?: Record<string, number>;
  totalBountyPoolUsd?: number;
  /** True when this payload is offline demo/sample data, not the live backend stream. */
  isDemo?: boolean;
}

export interface FilterState {
  domain: Domain | 'all';
  difficulty: Difficulty | 'all';
  techStack: string[];
  hasBountyOnly: boolean;
  minBounty: number;
  timeToSolve: 'all' | 'lt_30m' | '30m_2h' | '2h_6h' | 'gt_6h';
  search: string;
  sortBy: 'created_desc' | 'bounty_desc' | 'roi_desc' | 'time_asc' | 'confidence_desc';
  page: number;
  pageSize: number;
  viewMode: ViewMode;
}
