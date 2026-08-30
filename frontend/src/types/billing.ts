export type PaymentProvider = 'dodo' | 'lemonsqueezy';

export type PlanTier = 'free' | 'pro' | 'team';

export interface PlanFeature {
  title: string;
  included: boolean;
  highlight?: boolean;
}

export interface PricingPlan {
  id: PlanTier;
  name: string;
  tagline: string;
  priceMonthlyUsd: number;
  priceAnnualUsd: number;
  features: PlanFeature[];
  ctaText: string;
  popular?: boolean;
}

export interface CheckoutRequest {
  planId: PlanTier;
  billingCycle: 'monthly' | 'annual';
  provider: PaymentProvider;
  userEmail?: string;
  redirectUrl?: string;
}

export interface CheckoutResponse {
  checkoutUrl: string;
  sessionId: string;
  provider: PaymentProvider;
  expiresAt?: string;
}

export interface SubscriptionStatus {
  isPro: boolean;
  tier: PlanTier;
  expiresAt?: string;
  cancelAtPeriodEnd?: boolean;
  provider?: PaymentProvider;
}
