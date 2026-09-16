'use client';

import * as React from 'react';
import { LocalizedFile } from '@/types/triage';
import { Badge } from '@/components/ui/badge';
import { Crosshair, ExternalLink, FileCode, ShieldCheck, Sparkles, Target } from 'lucide-react';

/**
 * Per-issue "blast radius" map.
 *
 * Replaces the old static, mock AST graph (which referenced files that didn't exist and
 * conveyed nothing actionable) with a view built entirely from THIS issue's real localized
 * files. Files the LLM re-ranked as the primary edit site sit at the center; supporting files
 * and tests/config ripple outward. Everything shown is grounded in the triage response —
 * nothing is fabricated. The goal is a newcomer can look once and know where to start.
 */

type Tier = 'primary' | 'supporting' | 'tests';

interface TierMeta {
  label: string;
  blurb: string;
  color: string;
  ring: number;
  angleOffset: number;
}

// Ring radii + accent per tier, in the SVG's own coordinate space (see viewBox below).
const TIER_META: Record<Tier, TierMeta> = {
  primary: {
    label: 'Edit here first',
    blurb: 'The primary edit site for this fix.',
    color: 'hsl(var(--primary))',
    ring: 118,
    angleOffset: -90,
  },
  supporting: {
    label: 'Also likely to touch',
    blurb: 'Supporting files the change ripples into.',
    color: 'hsl(var(--accent))',
    ring: 200,
    angleOffset: -60,
  },
  tests: {
    label: 'Tests & config',
    blurb: 'Where to add coverage / update config.',
    color: 'hsl(var(--bounty-gold))',
    ring: 268,
    angleOffset: -75,
  },
};

const TIER_ORDER: Tier[] = ['primary', 'supporting', 'tests'];

interface PlacedNode {
  file: LocalizedFile;
  tier: Tier;
  x: number;
  y: number;
  r: number;
  color: string;
}

const CENTER = { x: 380, y: 285 };

function basename(path: string): string {
  const parts = path.split('/').filter(Boolean);
  return parts[parts.length - 1] || path;
}

/** Map a file to a tier: LLM priority when re-ranked, else rank order (top = primary). */
function tierOf(file: LocalizedFile, index: number, anyRanked: boolean): Tier {
  if (file.priority === 1) return 'primary';
  if (file.priority === 2) return 'supporting';
  if (file.priority === 3) return 'tests';
  if (anyRanked) return 'supporting';
  // No re-ranking available: the top AST candidate is the start point, the rest are related.
  return index === 0 ? 'primary' : 'supporting';
}

interface BlastRadiusMapProps {
  localizedFiles: LocalizedFile[];
  repoOwner?: string;
  repoName?: string;
  issueNumber?: number;
  isEnhanced?: boolean;
  initialTargetFile?: string;
}

export function BlastRadiusMap({
  localizedFiles,
  repoOwner,
  repoName,
  issueNumber,
  isEnhanced,
  initialTargetFile,
}: BlastRadiusMapProps) {
  const files = React.useMemo(
    () => (Array.isArray(localizedFiles) ? localizedFiles : []),
    [localizedFiles]
  );
  const anyRanked = React.useMemo(() => files.some((f) => f.aiRanked), [files]);

  const nodes = React.useMemo<PlacedNode[]>(() => {
    // Bucket files by tier, then lay each bucket out evenly around its ring.
    const byTier: Record<Tier, LocalizedFile[]> = { primary: [], supporting: [], tests: [] };
    files.forEach((f, i) => byTier[tierOf(f, i, anyRanked)].push(f));

    const placed: PlacedNode[] = [];
    for (const tier of TIER_ORDER) {
      const bucket = byTier[tier];
      const meta = TIER_META[tier];
      const n = bucket.length;
      bucket.forEach((file, i) => {
        // Spread nodes around the full circle; a single node sits at the tier's offset angle.
        const angleDeg = n === 1 ? meta.angleOffset : meta.angleOffset + (360 / n) * i;
        const a = (angleDeg * Math.PI) / 180;
        const r = 15 + Math.round((file.confidence || 0) * 11);
        placed.push({
          file,
          tier,
          x: CENTER.x + meta.ring * Math.cos(a),
          y: CENTER.y + meta.ring * Math.sin(a),
          r,
          color: meta.color,
        });
      });
    }
    return placed;
  }, [files, anyRanked]);

  const [selectedPath, setSelectedPath] = React.useState<string | null>(
    initialTargetFile || files[0]?.filePath || null
  );

  React.useEffect(() => {
    // Keep selection valid as the report loads / changes.
    if (initialTargetFile && files.some((f) => f.filePath === initialTargetFile)) {
      setSelectedPath(initialTargetFile);
    } else if (!files.some((f) => f.filePath === selectedPath)) {
      setSelectedPath(files[0]?.filePath || null);
    }
  }, [files, initialTargetFile, selectedPath]);

  const selected = files.find((f) => f.filePath === selectedPath) || null;

  if (files.length === 0) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center gap-3 p-8 text-center">
        <Crosshair className="h-8 w-8 text-muted-foreground" />
        <p className="max-w-sm text-sm text-muted-foreground">
          No files were localized for this issue yet. The blast radius appears once AST
          localization (and any AI re-ranking) has run.
        </p>
      </div>
    );
  }

  const selectedTier = selected ? tierOf(selected, files.indexOf(selected), anyRanked) : 'primary';
  const githubUrl =
    selected && repoOwner && repoName
      ? `https://github.com/${repoOwner}/${repoName}/blob/HEAD/${selected.filePath}`
      : null;

  return (
    <div className="flex h-full w-full flex-col lg:flex-row">
      {/* ── Radial map ─────────────────────────────────────────────── */}
      <div className="relative flex min-h-[320px] flex-1 items-center justify-center overflow-hidden bg-gradient-to-br from-card/40 via-background to-background">
        <svg
          viewBox="0 0 760 570"
          className="h-full w-full"
          role="img"
          aria-label="Per-issue blast radius map of localized files"
        >
          <defs>
            <radialGradient id="blast-core" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.35" />
              <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Blast glow + ring guides */}
          <circle cx={CENTER.x} cy={CENTER.y} r={300} fill="url(#blast-core)" />
          {TIER_ORDER.map((tier) => (
            <circle
              key={tier}
              cx={CENTER.x}
              cy={CENTER.y}
              r={TIER_META[tier].ring}
              fill="none"
              stroke="hsl(var(--border))"
              strokeOpacity={0.5}
              strokeDasharray="3 5"
            />
          ))}

          {/* Edges from the issue core to each file */}
          {nodes.map((node) => {
            const isSel = node.file.filePath === selectedPath;
            return (
              <line
                key={`edge-${node.file.filePath}`}
                x1={CENTER.x}
                y1={CENTER.y}
                x2={node.x}
                y2={node.y}
                stroke={isSel ? node.color : 'hsl(var(--border))'}
                strokeWidth={isSel ? 2 : 1}
                strokeOpacity={isSel ? 0.9 : 0.4}
              />
            );
          })}

          {/* File nodes */}
          {nodes.map((node) => {
            const isSel = node.file.filePath === selectedPath;
            return (
              <g
                key={`node-${node.file.filePath}`}
                transform={`translate(${node.x}, ${node.y})`}
                className="cursor-pointer"
                onClick={() => setSelectedPath(node.file.filePath)}
              >
                <circle
                  r={node.r + (isSel ? 4 : 0)}
                  fill="hsl(var(--card))"
                  stroke={node.color}
                  strokeWidth={isSel ? 3 : 1.5}
                  opacity={isSel ? 1 : 0.9}
                />
                {node.file.grounded && (
                  <circle r={4} cx={node.r - 3} cy={-(node.r - 3)} fill="hsl(var(--primary))" />
                )}
                <text
                  y={node.r + 13}
                  textAnchor="middle"
                  fontSize="10"
                  fontWeight={isSel ? 700 : 500}
                  fill={isSel ? 'hsl(var(--foreground))' : 'hsl(var(--muted-foreground))'}
                >
                  {basename(node.file.filePath).slice(0, 20)}
                </text>
              </g>
            );
          })}

          {/* Issue core */}
          <g transform={`translate(${CENTER.x}, ${CENTER.y})`}>
            <circle r={34} fill="hsl(var(--primary))" fillOpacity={0.18} stroke="hsl(var(--primary))" strokeWidth={2} />
            <text textAnchor="middle" y={-2} fontSize="12" fontWeight={800} fill="hsl(var(--primary))">
              {issueNumber ? `#${issueNumber}` : 'BUG'}
            </text>
            <text textAnchor="middle" y={13} fontSize="8" fill="hsl(var(--muted-foreground))">
              this issue
            </text>
          </g>
        </svg>

        {/* Tier legend overlay */}
        <div className="pointer-events-none absolute left-3 top-3 space-y-1.5 rounded-xl border border-border/70 bg-background/85 p-2.5 text-[10px] backdrop-blur">
          {TIER_ORDER.map((tier) => (
            <div key={tier} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: TIER_META[tier].color }} />
              <span className="font-semibold text-foreground">{TIER_META[tier].label}</span>
            </div>
          ))}
          <div className="flex items-center gap-1.5 pt-0.5">
            <span className="h-2.5 w-2.5 rounded-full ring-2 ring-primary" style={{ backgroundColor: 'hsl(var(--primary))' }} />
            <span className="text-muted-foreground">dot = real source read</span>
          </div>
        </div>
      </div>

      {/* ── Detail panel ───────────────────────────────────────────── */}
      <div className="flex w-full flex-col gap-3 border-t border-border bg-card/40 p-4 lg:w-80 lg:border-l lg:border-t-0">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-foreground">
          <Target className="h-3.5 w-3.5 text-primary" />
          <span>Where to start</span>
        </div>

        <p className="text-[11px] leading-relaxed text-muted-foreground">
          Files closest to the center are where a fix begins; each ring outward is a wider blast
          radius. {anyRanked ? 'Ordering and the "why" come from the AI re-ranking of the real source.' : 'Ordering follows the deterministic AST match (no AI re-ranking on this report).'}
        </p>

        {selected && (
          <div className="space-y-3 rounded-xl border border-border bg-background/70 p-3.5">
            <div className="flex items-center gap-2">
              <span
                className="flex h-6 w-6 items-center justify-center rounded-lg"
                style={{ backgroundColor: `${TIER_META[selectedTier].color}`, opacity: 0.9 }}
              >
                <FileCode className="h-3.5 w-3.5 text-background" />
              </span>
              <span className="text-[11px] font-semibold" style={{ color: TIER_META[selectedTier].color }}>
                {TIER_META[selectedTier].label}
              </span>
            </div>

            <div className="break-all font-mono text-xs font-bold text-foreground">{selected.filePath}</div>

            {selected.lineRange && (
              <div className="text-[11px] text-muted-foreground">
                Lines{' '}
                {Array.isArray(selected.lineRange)
                  ? `${selected.lineRange[0]}-${selected.lineRange[1]}`
                  : selected.lineRange}
              </div>
            )}

            {/* Confidence bar */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                <span>Localization confidence</span>
                <span className="font-bold text-foreground">{Math.round((selected.confidence || 0) * 100)}%</span>
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-border">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${Math.round((selected.confidence || 0) * 100)}%`,
                    backgroundColor: TIER_META[selectedTier].color,
                  }}
                />
              </div>
            </div>

            {/* Why this file */}
            <div className="space-y-1">
              <div className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                <Sparkles className="h-3 w-3 text-accent" />
                <span>Why this file</span>
              </div>
              <p className="text-[11px] leading-relaxed text-foreground/90">
                {selected.whyThisFile || selected.reason || 'Matched the issue signature during AST localization.'}
              </p>
            </div>

            {/* Provenance chips */}
            <div className="flex flex-wrap gap-1.5">
              {selected.grounded && (
                <Badge variant="emerald" className="gap-1 text-[9px]">
                  <ShieldCheck className="h-2.5 w-2.5" />
                  Grounded in real source
                </Badge>
              )}
              <Badge variant={selected.aiRanked ? 'amber' : 'outline'} className="text-[9px]">
                {selected.aiRanked ? 'AI-ranked' : 'AST order'}
              </Badge>
            </div>

            {githubUrl && (
              <a
                href={githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-primary hover:text-primary/80"
              >
                <span>Open file on GitHub</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        )}

        {!isEnhanced && (
          <p className="rounded-lg border border-border/70 bg-background/60 p-2 text-[10px] leading-relaxed text-muted-foreground">
            This report is the deterministic AST floor. Connect an LLM provider to get AI
            re-ranking and grounded &quot;why this file&quot; explanations.
          </p>
        )}
      </div>
    </div>
  );
}
