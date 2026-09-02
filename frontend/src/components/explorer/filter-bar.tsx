'use client';

import * as React from 'react';
import { FilterState, Domain, Difficulty, ViewMode } from '@/types/issue';
import { DOMAINS, TECH_STACKS, DIFFICULTIES, TIME_TO_SOLVE_OPTIONS, SORT_OPTIONS } from '@/lib/constants';
import { getDomainInfo } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  LayoutGrid,
  List,
  Terminal,
  RotateCcw,
  Sparkles,
  ChevronDown,
  Coins,
  Clock,
  Layers,
} from 'lucide-react';

interface FilterBarProps {
  filters: FilterState;
  onSetDomain: (domain: Domain | 'all') => void;
  onSetDifficulty: (diff: Difficulty | 'all') => void;
  onToggleTechStack: (tech: string) => void;
  onSetHasBountyOnly: (bountyOnly: boolean) => void;
  onSetMinBounty: (amount: number) => void;
  onSetTimeToSolve: (time: FilterState['timeToSolve']) => void;
  onSetSortBy: (sort: FilterState['sortBy']) => void;
  onSetViewMode: (mode: ViewMode) => void;
  onResetFilters: () => void;
  isFiltered: boolean;
}

export function FilterBar({
  filters,
  onSetDomain,
  onSetDifficulty,
  onToggleTechStack,
  onSetHasBountyOnly,
  onSetMinBounty,
  onSetTimeToSolve,
  onSetSortBy,
  onSetViewMode,
  onResetFilters,
  isFiltered,
}: FilterBarProps) {
  const [showBountySlider, setShowBountySlider] = React.useState(filters.minBounty > 0);

  return (
    <div className="space-y-3 font-mono text-xs">
      {/* Top Row: Domain Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
        <button
          type="button"
          onClick={() => onSetDomain('all')}
          className={`flex items-center gap-1 px-3 py-1.5 rounded-md border text-xs whitespace-nowrap transition-all ${
            filters.domain === 'all'
              ? 'border-primary bg-primary/15 text-primary font-semibold shadow-sm'
              : 'border-border bg-card/60 text-muted-foreground hover:border-border/80 hover:text-foreground'
          }`}
        >
          <Terminal className="h-3 w-3" />
          <span>All Ecosystems</span>
        </button>

        {DOMAINS.map((dom) => {
          const isSelected = filters.domain === dom.id;
          const info = getDomainInfo(dom.id);
          return (
            <button
              key={dom.id}
              type="button"
              onClick={() => onSetDomain(dom.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-xs whitespace-nowrap transition-all ${
                isSelected
                  ? `${info.borderClass} ${info.bgClass} ${info.textClass} font-semibold shadow-sm`
                  : 'border-border bg-card/60 text-muted-foreground hover:border-border/80 hover:text-foreground'
              }`}
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: info.hex }}
              />
              <span>{dom.label}</span>
            </button>
          );
        })}
      </div>

      {/* Second Row: Facets & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 rounded-lg border border-border bg-card/60 p-2.5 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          {/* Difficulty Dropdown */}
          <Select
            value={filters.difficulty}
            onValueChange={(val: any) => onSetDifficulty(val)}
          >
            <SelectTrigger className="h-8 w-40 border-border bg-background text-xs">
              <div className="flex items-center gap-1.5 truncate">
                <Sparkles className="h-3 w-3 text-primary" />
                <SelectValue placeholder="Difficulty" />
              </div>
            </SelectTrigger>
            <SelectContent className="border-border bg-card">
              <SelectItem value="all">All Difficulties</SelectItem>
              {DIFFICULTIES.map((d) => (
                <SelectItem key={d.id} value={d.id}>
                  {d.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Time to Solve Dropdown */}
          <Select
            value={filters.timeToSolve}
            onValueChange={(val: any) => onSetTimeToSolve(val)}
          >
            <SelectTrigger className="h-8 w-40 border-border bg-background text-xs">
              <div className="flex items-center gap-1.5 truncate">
                <Clock className="h-3 w-3 text-bounty-gold" />
                <SelectValue placeholder="Time to Solve" />
              </div>
            </SelectTrigger>
            <SelectContent className="border-border bg-card">
              {TIME_TO_SOLVE_OPTIONS.map((opt) => (
                <SelectItem key={opt.id} value={opt.id}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Tech Stack Multi-Select */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="h-8 border-border bg-background text-xs gap-1.5"
              >
                <Layers className="h-3 w-3 text-accent" />
                <span>
                  Stack {filters.techStack.length > 0 ? `(${filters.techStack.length})` : ''}
                </span>
                <ChevronDown className="h-3 w-3 text-muted-foreground" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-48 border-border bg-card">
              <DropdownMenuLabel className="text-[11px] text-muted-foreground font-mono">
                Select Technologies
              </DropdownMenuLabel>
              <DropdownMenuSeparator className="bg-border" />
              {TECH_STACKS.map((tech) => (
                <DropdownMenuCheckboxItem
                  key={tech}
                  checked={filters.techStack.includes(tech)}
                  onCheckedChange={() => onToggleTechStack(tech)}
                  className="text-xs font-mono"
                >
                  {tech}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Funded Bounty Toggle */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-md border border-border bg-background">
            <Coins className="h-3.5 w-3.5 text-bounty-gold" />
            <span className="text-[11px] text-foreground/90">Bounties Only</span>
            <Switch
              checked={filters.hasBountyOnly}
              onCheckedChange={(checked) => {
                onSetHasBountyOnly(checked);
                setShowBountySlider(checked);
              }}
            />
          </div>

          {/* Reset Filters */}
          {isFiltered && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onResetFilters}
              className="h-8 text-xs text-destructive hover:text-destructive hover:bg-destructive/30 gap-1"
            >
              <RotateCcw className="h-3 w-3" />
              <span>Reset</span>
            </Button>
          )}
        </div>

        {/* Right Side: Sorting & View Mode Switcher */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Sort Dropdown */}
          <Select
            value={filters.sortBy}
            onValueChange={(val: any) => onSetSortBy(val)}
          >
            <SelectTrigger className="h-8 w-44 border-border bg-background text-xs">
              <SelectValue placeholder="Sort By" />
            </SelectTrigger>
            <SelectContent className="border-border bg-card">
              {SORT_OPTIONS.map((opt) => (
                <SelectItem key={opt.id} value={opt.id}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* View Mode Toggle Buttons */}
          <div className="flex items-center rounded-md border border-border bg-muted p-0.5">
            <Button
              variant="ghost"
              size="icon"
              className={`h-7 w-7 rounded ${
                filters.viewMode === 'grid'
                  ? 'bg-card text-primary shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => onSetViewMode('grid')}
              title="Grid View"
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={`h-7 w-7 rounded ${
                filters.viewMode === 'table'
                  ? 'bg-card text-primary shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => onSetViewMode('table')}
              title="Table View"
            >
              <List className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={`h-7 w-7 rounded ${
                filters.viewMode === 'compact'
                  ? 'bg-card text-primary shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
              onClick={() => onSetViewMode('compact')}
              title="Terminal Monospace View"
            >
              <Terminal className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Optional Bounty Min Slider Drawer */}
      {showBountySlider && (
        <div className="flex items-center gap-4 px-3 py-2 rounded-md border border-bounty-gold/20 bg-bounty-gold/5 text-xs animate-in slide-in-from-top-2">
          <span className="text-muted-foreground shrink-0">
            Min Bounty: <span className="text-bounty-gold font-bold">${filters.minBounty}</span>
          </span>
          <div className="flex-1 max-w-xs">
            <Slider
              value={[filters.minBounty]}
              min={0}
              max={1000}
              step={50}
              onValueChange={(val) => onSetMinBounty(val[0])}
            />
          </div>
          <div className="flex gap-1">
            {[0, 100, 250, 500].map((amt) => (
              <button
                key={amt}
                type="button"
                onClick={() => onSetMinBounty(amt)}
                className={`px-1.5 py-0.5 rounded border text-[10px] ${
                  filters.minBounty === amt
                    ? 'border-bounty-gold bg-bounty-gold/20 text-bounty-gold font-bold'
                    : 'border-border bg-background text-muted-foreground'
                }`}
              >
                ${amt}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
