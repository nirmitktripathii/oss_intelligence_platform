'use client';

import { useState, useEffect, useCallback } from 'react';
import { TriageReport } from '@/types/triage';
import { apiClient } from '@/lib/api-client';

export function useTriage(issueId: string | null) {
  const [report, setReport] = useState<TriageReport | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchTriage = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiClient.getTriage(id);
      setReport(data);
    } catch (err: any) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (issueId) {
      fetchTriage(issueId);
    } else {
      setReport(null);
    }
  }, [issueId, fetchTriage]);

  return {
    report,
    isLoading,
    error,
    refetch: () => issueId && fetchTriage(issueId),
  };
}
