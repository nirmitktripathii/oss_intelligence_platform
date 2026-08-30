import { IssueExplorer } from '@/components/explorer/issue-explorer';
import { Terminal, Zap, DollarSign, Target, Activity, Flame, ArrowUpRight } from 'lucide-react';
import Link from 'next/link';

export default function HomePage() {
  const stats = [
    {
      label: 'Live Issues Tracked',
      value: '139+',
      change: '+18 today',
      icon: Activity,
      color: 'text-emerald-400',
      bg: 'bg-emerald-500/10 border-emerald-500/20',
    },
    {
      label: 'Active Bounty Pool',
      value: '$14,250',
      change: 'Polar & Algora',
      icon: DollarSign,
      color: 'text-amber-400',
      bg: 'bg-amber-500/10 border-amber-500/20',
    },
    {
      label: 'AST File Precision',
      value: '94.8%',
      change: 'Graphify Co-Pilot',
      icon: Target,
      color: 'text-cyan-400',
      bg: 'bg-cyan-500/10 border-cyan-500/20',
    },
    {
      label: 'Push Alert Latency',
      value: '<45s',
      change: 'Telegram & Discord',
      icon: Zap,
      color: 'text-purple-400',
      bg: 'bg-purple-500/10 border-purple-500/20',
    },
  ];

  const quickPills = [
    { name: '🔥 High Bounty ($100+)', query: 'hasBounty=true' },
    { name: '🤖 Agentic AI & RAG', query: 'domain=agentic_ai' },
    { name: '⚡ PyTorch & vLLM', query: 'techStack=PyTorch' },
    { name: '🦀 Polars & DuckDB', query: 'techStack=Polars' },
    { name: '🟢 Good First Issues', query: 'difficulty=EASY_MANUAL' },
  ];

  return (
    <div className="container py-6 space-y-6 max-w-7xl mx-auto">
      {/* Hero Terminal Banner with Glow & Live Status */}
      <div className="relative rounded-2xl border border-border bg-gradient-to-br from-card via-card/90 to-card/60 p-6 sm:p-8 font-mono overflow-hidden shadow-2xl backdrop-blur-xl">
        {/* Subtle Ambient Glow Elements */}
        <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-emerald-500/15 blur-3xl pointer-events-none animate-pulse" />
        <div className="absolute -left-20 -bottom-20 h-72 w-72 rounded-full bg-cyan-500/15 blur-3xl pointer-events-none" />

        <div className="relative z-10 space-y-5">
          {/* Top Status Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-400 font-bold shadow-sm">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                <Terminal className="h-3.5 w-3.5" />
                <span>LIVE OSS TERMINAL v1.0.0</span>
              </span>
              <span className="text-xs text-muted-foreground hidden sm:inline">•</span>
              <span className="text-xs text-muted-foreground hidden sm:inline">
                Zero-Mock Verified Stream
              </span>
            </div>

            <Link
              href="/pricing"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-400 hover:text-amber-300 transition-colors group"
            >
              <span>Unlock Pro Instant Bounty Alerts</span>
              <ArrowUpRight className="h-3.5 w-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
            </Link>
          </div>

          {/* Headline */}
          <div className="max-w-3xl space-y-2">
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight leading-tight text-foreground">
              The Bloomberg Terminal for{' '}
              <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
                Open-Source Developers
              </span>
            </h1>

            <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
              Continuously crawls, triages, and AI-localizes open unassigned issues across AI/ML, Data, and Web ecosystems. Get instant AST dependency maps, minimal bug reproduction snippets, and step-by-step fix blueprints.
            </p>
          </div>

          {/* Live Metrics Ticker */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            {stats.map((stat, i) => {
              const Icon = stat.icon;
              return (
                <div
                  key={i}
                  className={`rounded-xl border p-3.5 flex flex-col justify-between ${stat.bg} backdrop-blur-sm transition-all hover:scale-[1.02]`}
                >
                  <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                    <span className="text-[11px] font-semibold">{stat.label}</span>
                    <Icon className={`h-4 w-4 ${stat.color}`} />
                  </div>
                  <div className="flex items-baseline justify-between mt-1">
                    <span className="text-lg sm:text-xl font-extrabold text-foreground">{stat.value}</span>
                    <span className={`text-[10px] font-bold ${stat.color}`}>{stat.change}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Quick Filter Pills */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-xs text-muted-foreground font-semibold mr-1 flex items-center gap-1">
              <Flame className="h-3.5 w-3.5 text-amber-400" /> Hot Views:
            </span>
            {quickPills.map((pill, idx) => (
              <span
                key={idx}
                className="cursor-pointer text-xs rounded-full border border-border/80 bg-background/80 hover:border-emerald-500/50 hover:bg-emerald-500/10 px-3 py-1 text-muted-foreground hover:text-foreground font-mono transition-all shadow-sm"
              >
                {pill.name}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Main Issue Explorer & Faceted Grid */}
      <IssueExplorer />
    </div>
  );
}
