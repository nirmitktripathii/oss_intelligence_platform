'use client';

import * as React from 'react';
import { useFilters } from '@/hooks/use-filters';
import { useIssues } from '@/hooks/use-issues';
import { useKeyboardNav } from '@/hooks/use-keyboard-nav';
import { SearchInput } from './search-input';
import { FilterBar } from './filter-bar';
import { IssueStatsBar } from './issue-stats-bar';
import { IssueCard } from './issue-card';
import { IssueTable } from './issue-table';
import { IssueCompact } from './issue-compact';
import { EmptyState } from './empty-state';
import { IssueWorkbenchDrawer } from '@/components/workbench/issue-workbench-drawer';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import type { Issue } from '@/types';

interface IssueExplorerProps {
  onOpenCommandMenu?: () => void;
}

export function IssueExplorer({ onOpenCommandMenu }: IssueExplorerProps) {
  const {
    filters,
    isPending,
    setDomain,
    setDifficulty,
    toggleTechStack,
    setHasBountyOnly,
    setMinBounty,
    setTimeToSolve,
    setSearch,
    setSortBy,
    setPage,
    setViewMode,
    resetFilters,
    isFiltered,
  } = useFilters();

  const { issues, total, totalPages, page, isLoading, isDemo } = useIssues(filters);

  const [selectedIndex, setSelectedIndex] = React.useState<number>(0);
  const [activeDrawerIssue, setActiveDrawerIssue] = React.useState<Issue | null>(null);
  const searchInputRef = React.useRef<HTMLInputElement>(null);

  // Keep selected index within bounds
  React.useEffect(() => {
    if (selectedIndex >= issues.length && issues.length > 0) {
      setSelectedIndex(0);
    }
  }, [issues.length, selectedIndex]);

  // Global Keyboard Navigation
  useKeyboardNav({
    onSearchFocus: () => {
      searchInputRef.current?.focus();
    },
    onNext: () => {
      if (issues.length > 0) {
        setSelectedIndex((prev) => (prev + 1 < issues.length ? prev + 1 : prev));
      }
    },
    onPrev: () => {
      if (issues.length > 0) {
        setSelectedIndex((prev) => (prev - 1 >= 0 ? prev - 1 : 0));
      }
    },
    onSelect: () => {
      if (issues.length > 0 && issues[selectedIndex]) {
        setActiveDrawerIssue(issues[selectedIndex]);
      }
    },
    onClose: () => {
      if (activeDrawerIssue) {
        setActiveDrawerIssue(null);
      }
    },
    onToggleCommandMenu: onOpenCommandMenu,
    enabled: true,
  });

  return (
    <div className="space-y-6 font-mono">
      {/* Offline demo-data notice — shown only when the live backend is unreachable */}
      {isDemo && (
        <div className="rounded-lg border border-bounty-gold/40 bg-bounty-gold/10 px-3 py-2 text-xs text-bounty-gold">
          ⚠️ Showing offline demo data — the live backend is unreachable (it may be waking from sleep). These are sample issues, not the live stream. Refresh in a moment.
        </div>
      )}

      {/* Top Telemetry Counters */}
      <IssueStatsBar totalIssuesCount={total} />

      {/* Search Input */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <SearchInput
          value={filters.search}
          onChange={setSearch}
          isPending={isPending}
          inputRef={searchInputRef}
        />
      </div>

      {/* Faceted Filter Toolbar */}
      <FilterBar
        filters={filters}
        onSetDomain={setDomain}
        onSetDifficulty={setDifficulty}
        onToggleTechStack={toggleTechStack}
        onSetHasBountyOnly={setHasBountyOnly}
        onSetMinBounty={setMinBounty}
        onSetTimeToSolve={setTimeToSolve}
        onSetSortBy={setSortBy}
        onSetViewMode={setViewMode}
        onResetFilters={resetFilters}
        isFiltered={isFiltered}
      />

      {/* Issue Listing Container */}
      {isLoading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div
                key={i}
                className="rounded-xl border border-border bg-background p-4 space-y-3"
              >
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-16" />
                </div>
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="h-10 w-full" />
                <div className="flex gap-2 pt-2 border-t border-border">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-16" />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : issues.length === 0 ? (
        <EmptyState onReset={resetFilters} searchQuery={filters.search} />
      ) : (
        <div className="space-y-4">
          {/* Active View Rendering */}
          {filters.viewMode === 'grid' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {issues.map((issue, idx) => (
                <IssueCard
                  key={issue.id}
                  issue={issue}
                  isSelected={idx === selectedIndex}
                  onSelect={(iss) => {
                    setSelectedIndex(idx);
                    setActiveDrawerIssue(iss);
                  }}
                />
              ))}
            </div>
          )}

          {filters.viewMode === 'table' && (
            <IssueTable
              issues={issues}
              selectedIndex={selectedIndex}
              onSelect={(iss) => {
                const idx = issues.findIndex((i) => i.id === iss.id);
                if (idx >= 0) setSelectedIndex(idx);
                setActiveDrawerIssue(iss);
              }}
            />
          )}

          {filters.viewMode === 'compact' && (
            <IssueCompact
              issues={issues}
              selectedIndex={selectedIndex}
              onSelect={(iss) => {
                const idx = issues.findIndex((i) => i.id === iss.id);
                if (idx >= 0) setSelectedIndex(idx);
                setActiveDrawerIssue(iss);
              }}
            />
          )}

          {/* Pagination Footer */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border/80 pt-4 text-xs text-muted-foreground">
              <div>
                Showing {(page - 1) * filters.pageSize + 1}–
                {Math.min(page * filters.pageSize, total)} of {total} live issues
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  className="h-8 text-xs gap-1"
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                  <span>Previous</span>
                </Button>

                <span className="px-2 font-semibold text-foreground">
                  Page {page} of {totalPages}
                </span>

                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                  className="h-8 text-xs gap-1"
                >
                  <span>Next</span>
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Slide-out AI Workbench Drawer */}
      <IssueWorkbenchDrawer
        issue={activeDrawerIssue}
        isOpen={!!activeDrawerIssue}
        onClose={() => setActiveDrawerIssue(null)}
      />
    </div>
  );
}
