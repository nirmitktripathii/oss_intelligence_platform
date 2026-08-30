'use client';

import * as React from 'react';
import { PRICING_PLANS } from '@/lib/constants';
import { useCheckout } from '@/hooks/use-checkout';
import { Button } from '@/components/ui/button';
import { PlanTier, PaymentProvider } from '@/types/billing';
import {
  Zap,
  Check,
  Shield,
  CreditCard,
  Sparkles,
  HelpCircle,
  Calculator,
  TrendingUp,
  DollarSign,
} from 'lucide-react';

export default function PricingPage() {
  const [billingCycle, setBillingCycle] = React.useState<'monthly' | 'annual'>('annual');
  const [provider, setProvider] = React.useState<PaymentProvider>('dodo');
  const { startCheckout, isLoading } = useCheckout();

  // ROI Calculator State
  const [bountiesPerMonth, setBountiesPerMonth] = React.useState<number>(3);
  const [avgBountyValue, setAvgBountyValue] = React.useState<number>(250);

  const monthlyGrossEarnings = bountiesPerMonth * avgBountyValue;
  const proMonthlyCost = billingCycle === 'annual' ? 15 : 19;
  const netEarnings = monthlyGrossEarnings - proMonthlyCost;
  const roiPercentage = Math.round((netEarnings / proMonthlyCost) * 100);

  const handleSelectPlan = (planId: PlanTier) => {
    if (planId === 'free') {
      window.location.href = '/';
      return;
    }
    startCheckout({
      planId,
      billingCycle,
      provider,
    });
  };

  const faqs = [
    {
      q: 'How fast are Pro real-time issue alerts?',
      a: 'GitScout Pro alerts are dispatched within 45 seconds of an issue being posted or funded on GitHub, Polar, or Algora—giving you the crucial first-mover advantage on high-value bounties.',
    },
    {
      q: 'How does the Graphify AST visualizer pinpoint files?',
      a: 'GitScout uses AST symbol parsing and stack trace heuristics to map callers, callees, and dependencies, calculating a precision confidence match for each localized file.',
    },
    {
      q: 'What payment methods do you support?',
      a: 'We support all major credit cards, Apple Pay, Google Pay, UPI (in India), and global multi-currency checkout via Dodo Payments and Lemon Squeezy.',
    },
    {
      q: 'Can I cancel my subscription anytime?',
      a: 'Yes, you can cancel with 1-click at any time. You will retain Pro terminal access until the end of your current billing cycle.',
    },
  ];

  return (
    <div className="container py-12 max-w-6xl space-y-16 font-mono text-foreground mx-auto">
      {/* Header */}
      <div className="text-center space-y-4 max-w-2xl mx-auto">
        <div className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-400 font-bold shadow-sm">
          <Zap className="h-3.5 w-3.5" />
          <span>PRO & TEAM PLANS</span>
        </div>
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-foreground">
          Turn open-source bugs into{' '}
          <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent">
            recurring bounty income
          </span>
        </h1>
        <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
          Upgrade your intelligence terminal. Gain sub-45s push alerts, AST dependency maps, and AI-engineered PR blueprints.
        </p>

        {/* Billing cycle toggle */}
        <div className="pt-4 flex items-center justify-center gap-3">
          <div className="inline-flex rounded-xl border border-border bg-card/80 p-1 text-xs shadow-inner">
            <button
              type="button"
              onClick={() => setBillingCycle('monthly')}
              className={`px-4 py-2 rounded-lg transition-all ${
                billingCycle === 'monthly'
                  ? 'bg-primary text-primary-foreground font-semibold shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Monthly Billing
            </button>
            <button
              type="button"
              onClick={() => setBillingCycle('annual')}
              className={`px-4 py-2 rounded-lg transition-all flex items-center gap-1.5 ${
                billingCycle === 'annual'
                  ? 'bg-emerald-600 text-white font-semibold shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <span>Annual Billing</span>
              <span className="rounded bg-emerald-400/20 px-2 py-0.5 text-[10px] text-emerald-200 font-bold uppercase">
                Save 20%
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Pricing Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {PRICING_PLANS.map((plan) => {
          const isPopular = plan.popular;
          const price = billingCycle === 'annual' ? plan.priceAnnualUsd : plan.priceMonthlyUsd;

          return (
            <div
              key={plan.id}
              className={`relative flex flex-col justify-between rounded-2xl border p-6 transition-all duration-200 ${
                isPopular
                  ? 'border-emerald-500 bg-gradient-to-b from-emerald-950/20 via-card to-card shadow-[0_0_35px_rgba(16,185,129,0.15)] ring-2 ring-emerald-500/50'
                  : 'border-border bg-card/60 hover:border-border/80'
              }`}
            >
              {isPopular && (
                <div className="absolute -top-3.5 left-1/2 -translate-x-1/2 rounded-full bg-emerald-500 px-4 py-0.5 text-[11px] font-extrabold uppercase tracking-wider text-black shadow-md">
                  Most Popular For Bounty Hunters
                </div>
              )}

              <div>
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-lg text-foreground">{plan.name}</h3>
                  {plan.id === 'pro' && <Sparkles className="h-5 w-5 text-emerald-400 animate-pulse" />}
                </div>
                <p className="text-xs text-muted-foreground mt-1.5 min-h-[36px]">{plan.tagline}</p>

                <div className="mt-6 mb-6 flex items-baseline gap-1">
                  <span className="text-4xl sm:text-5xl font-extrabold text-foreground">${price}</span>
                  <span className="text-xs text-muted-foreground">
                    /mo {billingCycle === 'annual' && plan.priceMonthlyUsd > 0 ? '(billed annually)' : ''}
                  </span>
                </div>

                <div className="space-y-3 border-t border-border pt-5">
                  <span className="text-[11px] uppercase font-bold text-muted-foreground tracking-wider">
                    Included Features:
                  </span>
                  <ul className="space-y-3 text-xs">
                    {plan.features.map((f, i) => (
                      <li
                        key={i}
                        className={`flex items-start gap-2.5 ${
                          f.included
                            ? f.highlight
                              ? 'text-emerald-400 font-medium'
                              : 'text-foreground/90'
                            : 'text-muted-foreground/40 line-through'
                        }`}
                      >
                        <Check
                          className={`h-4 w-4 shrink-0 mt-0.5 ${
                            f.included
                              ? f.highlight
                                ? 'text-emerald-400'
                                : 'text-emerald-500/80'
                              : 'text-muted-foreground/30'
                          }`}
                        />
                        <span className="text-xs leading-snug">{f.title}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="pt-8">
                <Button
                  variant={isPopular ? 'glow' : plan.id === 'free' ? 'outline' : 'default'}
                  size="lg"
                  className="w-full text-xs font-bold shadow-md"
                  disabled={isLoading}
                  onClick={() => handleSelectPlan(plan.id)}
                >
                  {isLoading ? 'Connecting...' : plan.ctaText}
                </Button>
              </div>
            </div>
          );
        })}
      </div>

      {/* Interactive Bounty ROI Simulator Widget */}
      <div className="rounded-2xl border border-border bg-gradient-to-br from-card via-card/90 to-card/50 p-6 sm:p-8 space-y-6 shadow-xl backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border pb-5">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              <Calculator className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-foreground">Interactive Bounty ROI Simulator</h3>
              <p className="text-xs text-muted-foreground">Calculate your estimated monthly earnings using GitScout Pro alerts</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-bold bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full self-start sm:self-auto">
            <TrendingUp className="h-4 w-4" />
            <span>Est. Net ROI: +{roiPercentage}%</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
          {/* Sliders */}
          <div className="space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground font-semibold">Bounties Solved / Month:</span>
                <span className="font-extrabold text-foreground text-sm">{bountiesPerMonth} issues</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={bountiesPerMonth}
                onChange={(e) => setBountiesPerMonth(Number(e.target.value))}
                className="w-full accent-emerald-500 cursor-pointer h-2 bg-muted rounded-lg"
              />
              <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>1 issue</span>
                <span>5 issues</span>
                <span>10 issues</span>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground font-semibold">Average Bounty Payout:</span>
                <span className="font-extrabold text-emerald-400 text-sm">${avgBountyValue} USD</span>
              </div>
              <input
                type="range"
                min="50"
                max="1000"
                step="25"
                value={avgBountyValue}
                onChange={(e) => setAvgBountyValue(Number(e.target.value))}
                className="w-full accent-emerald-500 cursor-pointer h-2 bg-muted rounded-lg"
              />
              <div className="flex justify-between text-[10px] text-muted-foreground">
                <span>$50</span>
                <span>$500</span>
                <span>$1,000+</span>
              </div>
            </div>
          </div>

          {/* Result Card */}
          <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-6 flex flex-col justify-between space-y-4">
            <div className="space-y-1">
              <span className="text-[11px] uppercase font-bold text-emerald-400 tracking-wider">Estimated Net Profit</span>
              <div className="text-3xl sm:text-4xl font-extrabold text-foreground flex items-center">
                <DollarSign className="h-7 w-7 text-emerald-400 -mr-1" />
                <span>{netEarnings.toLocaleString()}</span>
                <span className="text-xs text-muted-foreground ml-1">/ month</span>
              </div>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Based on solving <strong className="text-foreground">{bountiesPerMonth} bounties</strong> at an average of <strong className="text-emerald-400">${avgBountyValue}</strong> each, after deducting the GitScout Pro subscription (<strong className="text-foreground">${proMonthlyCost}/mo</strong>).
            </p>

            <Button
              variant="glow"
              size="default"
              className="w-full text-xs font-bold"
              onClick={() => handleSelectPlan('pro')}
            >
              Claim Pro Early Access
            </Button>
          </div>
        </div>
      </div>

      {/* Payment Gateway Toggle & Guarantee Bar */}
      <div className="rounded-2xl border border-border bg-card p-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-foreground font-semibold">Payment Engine:</span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setProvider('dodo')}
              className={`px-3 py-1.5 rounded-lg border text-xs font-mono transition-colors ${
                provider === 'dodo'
                  ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300 font-bold'
                  : 'border-border bg-background text-muted-foreground hover:text-foreground'
              }`}
            >
              Dodo Payments (Cards / UPI / Global)
            </button>
            <button
              type="button"
              onClick={() => setProvider('lemonsqueezy')}
              className={`px-3 py-1.5 rounded-lg border text-xs font-mono transition-colors ${
                provider === 'lemonsqueezy'
                  ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300 font-bold'
                  : 'border-border bg-background text-muted-foreground hover:text-foreground'
              }`}
            >
              Lemon Squeezy (Merchant of Record)
            </button>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div className="flex items-center gap-1.5">
            <Shield className="h-4 w-4 text-emerald-400" />
            <span>256-Bit SSL Encrypted</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CreditCard className="h-4 w-4 text-emerald-400" />
            <span>7-Day Money Back</span>
          </div>
        </div>
      </div>

      {/* FAQ Section */}
      <div className="space-y-6 pt-6">
        <div className="text-center space-y-1">
          <h2 className="text-2xl font-bold text-foreground">Frequently Asked Questions</h2>
          <p className="text-xs text-muted-foreground">Everything you need to know about GitScout billing and capabilities.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {faqs.map((faq, i) => (
            <div key={i} className="rounded-xl border border-border bg-card/60 p-5 space-y-2">
              <h4 className="font-semibold text-xs text-foreground flex items-center gap-2">
                <HelpCircle className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>{faq.q}</span>
              </h4>
              <p className="text-xs text-muted-foreground leading-relaxed pl-6">{faq.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
