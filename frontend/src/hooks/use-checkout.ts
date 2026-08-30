'use client';

import { useState } from 'react';
import { PlanTier, PaymentProvider } from '@/types/billing';
import { apiClient } from '@/lib/api-client';

export function useCheckout() {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const startCheckout = async ({
    planId,
    billingCycle,
    provider = 'dodo',
    userEmail,
  }: {
    planId: PlanTier;
    billingCycle: 'monthly' | 'annual';
    provider?: PaymentProvider;
    userEmail?: string;
  }) => {
    if (planId === 'free') {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const res = await apiClient.createCheckout({
        planId,
        billingCycle,
        provider,
        userEmail,
      });

      if (res.checkoutUrl) {
        window.location.href = res.checkoutUrl;
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to initialize checkout session');
      console.error('Checkout error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return { startCheckout, isLoading, error };
}
