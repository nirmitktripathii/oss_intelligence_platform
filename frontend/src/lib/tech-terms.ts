// Speech recognition is trained on everyday speech, so it turns "Ollama" into "Ulama" and "PyTorch"
// into "pie torch". This repairs those slips with a vocabulary of the project, language and tool
// names the app deals with. It only rewrites words it is confident about; everything else is left
// exactly as heard, and the user can still edit the text before sending.

/** Canonical spelling -> what the recognizer commonly produces for it (lower case, spoken form). */
const TERMS: Record<string, string[]> = {
  Ollama: ['ulama', 'olama', 'ullama', 'o llama', 'oh llama', 'alama', 'olamma'],
  PyTorch: ['pie torch', 'pi torch', 'py torch', 'pytorch'],
  TensorFlow: ['tensor flow', 'tensorflow'],
  LangChain: ['lang chain', 'long chain', 'langchain', 'lane chain'],
  LlamaIndex: ['llama index', 'lama index'],
  vLLM: ['v llm', 'vee llm', 'vlm', 'v l l m'],
  AutoGen: ['auto gen', 'autogen', 'auto jen'],
  'Hugging Face': ['hugging face', 'huggingface'],
  NumPy: ['numb pie', 'num pie', 'numpy', 'numb pi'],
  SciPy: ['sigh pie', 'sci pie', 'scipy'],
  'scikit-learn': ['sigh kit learn', 'psykit learn', 'scikit learn', 'sci kit learn'],
  FastAPI: ['fast api', 'fast a p i'],
  Django: ['jango'],
  'Next.js': ['next js', 'nextjs', 'next jay s', 'next dot js'],
  'Node.js': ['node js', 'nodejs', 'node dot js'],
  TypeScript: ['type script', 'typescript'],
  JavaScript: ['java script', 'javascript'],
  Golang: ['go lang', 'golang'],
  Kubernetes: ['cooper nettys', 'kuber netties', 'cooper netties'],
  kubectl: ['cube control', 'cube cuddle', 'cube c t l', 'kube control', 'kube ctl'],
  Terraform: ['terra form'],
  Postgres: ['post gress', 'postgress', 'post grass'],
  PostgreSQL: ['post gress q l', 'postgres sql', 'postgres q l'],
  SQLite: ['sequel lite', 'sql lite', 'sea quel lite'],
  Redis: ['reddis'],
  GraphQL: ['graph q l', 'graph ql', 'graph queue l'],
  gRPC: ['g r p c', 'g rpc'],
  WebAssembly: ['web assembly'],
  WASM: ['wazm'],
  GitHub: ['git hub', 'get hub'],
  GitScout: ['git scout', 'get scout', 'gitscout'],
  GitLab: ['git lab', 'get lab'],
  LLM: ['l l m', 'el el em'],
  LLMs: ['l l ms', 'el el ems'],
  MCP: ['m c p', 'em see pee'],
  API: ['a p i'],
  CLI: ['c l i'],
  'CI/CD': ['c i c d', 'ci cd'],
  'AI/ML': ['ai ml', 'a i m l', 'ai and ml'],
  Qwen: ['quen', 'kwen'],
  Mistral: ['mistrial'],
  OpenAI: ['open a i', 'open ai'],
  Bedrock: ['bed rock'],
  Vercel: ['versel', 'vercell'],
  Upstash: ['up stash'],
  Tailwind: ['tail wind'],
  Webpack: ['web pack'],
  ESLint: ['e s lint', 'es lint'],
  pytest: ['pie test', 'pi test'],
  npm: ['n p m', 'en pee em'],
  YAML: ['yammel', 'y a m l'],
  JSON: ['jason', 'j son'],
  OAuth: ['o auth', 'oh auth', 'oauth'],
  JWT: ['j w t'],
  SQL: ['sequel', 's q l'],
  NoSQL: ['no sequel', 'no sql'],
};

function norm(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}

// Spoken form -> canonical, longest phrases first so "next js" wins over any shorter rule.
const ALIASES: Array<[string[], string]> = [];
for (const [canonical, spoken] of Object.entries(TERMS)) {
  for (const s of spoken) ALIASES.push([norm(s).split(' '), canonical]);
}
ALIASES.sort((a, b) => b[0].length - a[0].length);

function lev(a: string, b: string): number {
  const dp = Array.from({ length: a.length + 1 }, (_, i) => [i, ...Array<number>(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) dp[0][j] = j;
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++)
      dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return dp[a.length][b.length];
}

// Single-word names long enough that a one-letter slip is not a guess. Short or ordinary-English
// names (Go, Rust, Swift, React...) are deliberately never fuzzy-matched.
const FUZZY = Object.keys(TERMS)
  .filter((t) => /^[A-Za-z0-9]+$/.test(t) && t.length >= 7)
  .map((t) => [t.toLowerCase(), t] as const);

const trailing = (w: string) => w.match(/[^A-Za-z0-9]+$/)?.[0] ?? '';

/** Fix technical terms the recognizer mangled. Plain text in, plain text out. */
export function sanitizeTranscript(text: string): string {
  const tokens = text.split(/\s+/).filter(Boolean);
  const out: string[] = [];
  let i = 0;
  while (i < tokens.length) {
    const rule = ALIASES.find(
      ([words]) => i + words.length <= tokens.length && norm(tokens.slice(i, i + words.length).join(' ')) === words.join(' '),
    );
    if (rule) {
      out.push(rule[1] + trailing(tokens[i + rule[0].length - 1]));
      i += rule[0].length;
      continue;
    }
    const word = tokens[i];
    const core = norm(word);
    const hit = core.length >= 7 && !core.includes(' ') ? FUZZY.find(([low]) => low !== core && lev(low, core) === 1) : undefined;
    out.push(hit ? hit[1] + trailing(word) : word);
    i++;
  }
  return out.join(' ');
}

/**
 * The recognizer offers several guesses per phrase. Prefer the first one the vocabulary can improve
 * (it likely contains a technical term), otherwise the top guess; the winner is then sanitized.
 */
export function pickBestAlternative(alternatives: string[]): string {
  if (alternatives.length === 0) return '';
  const flat = (a: string) => a.split(/\s+/).filter(Boolean).join(' ');
  const improvable = alternatives.find((a) => sanitizeTranscript(a) !== flat(a));
  return sanitizeTranscript(improvable ?? alternatives[0]);
}
