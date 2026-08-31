'use client';

import { useState, useEffect, useCallback } from 'react';
import { Issue, PaginatedIssuesResponse, FilterState } from '@/types/issue';
import { apiClient } from '@/lib/api-client';

export function useIssues(filters: Partial<FilterState>) {
  const [data, setData] = useState<PaginatedIssuesResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchIssues = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiClient.getIssues(filters);
      setData(response);
    } catch (err: any) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, [
    filters.domain,
    filters.difficulty,
    filters.hasBountyOnly,
    filters.minBounty,
    filters.timeToSolve,
    filters.search,
    filters.sortBy,
    filters.page,
    filters.pageSize,
    filters.techStack?.join(','),
  ]);

  useEffect(() => {
    fetchIssues();
  }, [fetchIssues]);

  return {
    issues: data?.items || [],
    total: data?.total || 0,
    totalPages: data?.totalPages || 1,
    page: data?.page || 1,
    totalBountyPoolUsd: data?.totalBountyPoolUsd || 0,
    domainCounts: data?.domainCounts || {},
    isDemo: data?.isDemo || false,
    isLoading,
    error,
    refetch: fetchIssues,
  };
}
