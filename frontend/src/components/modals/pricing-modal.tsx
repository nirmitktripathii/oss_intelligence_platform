'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { PRICING_PLANS } from '@/lib/constants';
import { useCheckout } from '@/hooks/use-checkout';
import { Check, Zap, Sparkles, Shield, CreditCard } from 'lucide-react';
import { PlanTier, PaymentProvider } from '@/types/billing';

interface PricingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PricingModal({ isOpen, onClose }: PricingModalProps) {
  const [billingCycle, setBillingCycle] = React.useState<'monthly' | 'annual'>('annual');
  const [provider, setProvider] = React.useState<PaymentProvider>('dodo');
  const { startCheckout, isLoading } = useCheckout();

  const handleSelectPlan = (planId: PlanTier) => {
    if (planId === 'free') {
      onClose();
      return;
    }
    startCheckout({
      planId,
      billingCycle,
      provider,
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl border-zinc-800 bg-zinc-950/95 font-mono text-zinc-100 p-6 overflow-y-auto max-h-[90vh]">
        <DialogHeader className="text-center sm:text-center">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 mb-2">
            <Zap className="h-5 w-5" />
          </div>
          <DialogTitle className="text-xl font-bold text-zinc-100">
            Upgrade to GitScout Pro & Team Terminal
          </DialogTitle>
          <DialogDescription className="text-xs text-zinc-400 max-w-lg mx-auto">
            Unlock sub-60s zero-latency alerts, private Telegram/Discord bots, full AST blast radius graphs, and 4-step PR blueprints.
          </DialogDescription>
        </DialogHeader>

        {/* Billing cycle toggle */}
        <div className="flex items-center justify-center gap-3 pt-2">
          <div className="inline-flex rounded-lg border border-zinc-800 bg-zinc-900/80 p-1 text-xs">
            <button
              type="button"
              onClick={() => setBillingCycle('monthly')}
              className={`px-3 py-1 rounded transition-colors ${
                billingCycle === 'monthly'
                  ? 'bg-zinc-800 text-white font-medium shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Monthly Billing
            </button>
            <button
              type="button"
              onClick={() => setBillingCycle('annual')}
              className={`px-3 py-1 rounded transition-colors flex items-center gap-1.5 ${
                billingCycle === 'annual'
                  ? 'bg-emerald-600 text-white font-medium shadow-sm'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              <span>Annual Billing</span>
              <span className="rounded bg-emerald-400/20 px-1 py-0.2 text-[10px] text-emerald-200 font-bold uppercase">
                Save 20%
              </span>
            </button>
          </div>
        </div>

        {/* Plan comparison grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
          {PRICING_PLANS.map((plan) => {
            const isPopular = plan.popular;
            const price =
              billingCycle === 'annual' ? plan.priceAnnualUsd : plan.priceMonthlyUsd;

            return (
              <div
                key={plan.id}
                className={`relative flex flex-col justify-between rounded-xl border p-5 transition-all ${
                  isPopular
                    ? 'border-emerald-500/70 bg-gradient-to-b from-emerald-950/20 to-zinc-950 shadow-[0_0_25px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/50'
                    : 'border-zinc-800 bg-zinc-900/40 hover:border-zinc-700'
                }`}
              >
                {isPopular && (
                  <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 rounded-full bg-emerald-500 px-3 py-0.5 text-[10px] font-bold uppercase tracking-wider text-black">
                    Most Popular
                  </div>
                )}

                <div>
                  <div className="flex items-center justify-between">
                    <h3 className="font-bold text-sm text-zinc-100">{plan.name}</h3>
                    {plan.id === 'pro' && <Sparkles className="h-4 w-4 text-emerald-400" />}
                  </div>
                  <p className="text-[11px] text-zinc-400 mt-1 min-h-[32px]">{plan.tagline}</p>

                  <div className="mt-4 mb-4 flex items-baseline gap-1">
                    <span className="text-3xl font-extrabold text-zinc-100">${price}</span>
                    <span className="text-xs text-zinc-400">
                      /month {billingCycle === 'annual' && plan.priceMonthlyUsd > 0 ? '(billed annually)' : ''}
                    </span>
                  </div>

                  <div className="space-y-2 border-t border-zinc-800/80 pt-3">
                    <span className="text-[10px] uppercase font-bold text-zinc-400 tracking-wider">
                      Included Capabilities:
                    </span>
                    <ul className="space-y-2 text-xs">
                      {plan.features.map((f, i) => (
                        <li
                          key={i}
                          className={`flex items-start gap-2 ${
                            f.included
                              ? f.highlight
                                ? 'text-emerald-300 font-medium'
                                : 'text-zinc-300'
                              : 'text-zinc-600 line-through'
                          }`}
                        >
                          <Check
                            className={`h-3.5 w-3.5 shrink-0 mt-0.5 ${
                              f.included
                                ? f.highlight
                                  ? 'text-emerald-400'
                                  : 'text-zinc-400'
                              : 'text-zinc-700'
                            }`}
                          />
                          <span className="text-[11px] leading-tight">{f.title}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="pt-6">
                  <Button
                    variant={isPopular ? 'glow' : plan.id === 'free' ? 'outline' : 'default'}
                    size="sm"
                    className="w-full text-xs font-semibold"
                    disabled={isLoading}
                    onClick={() => handleSelectPlan(plan.id)}
                  >
                    {isLoading ? 'Processing...' : plan.ctaText}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Payment provider & trust bar */}
        <div className="mt-4 flex flex-col sm:flex-row items-center justify-between border-t border-zinc-800/80 pt-4 text-xs text-zinc-400 gap-3">
          <div className="flex items-center gap-3">
            <span className="text-[11px]">Payment Gateway:</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setProvider('dodo')}
                className={`px-2 py-0.5 rounded border text-[11px] font-mono ${
                  provider === 'dodo'
                    ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300'
                    : 'border-zinc-800 bg-zinc-900 text-zinc-400'
                }`}
              >
                Dodo Payments (Card/UPI/Crypto)
              </button>
              <button
                type="button"
                onClick={() => setProvider('lemonsqueezy')}
                className={`px-2 py-0.5 rounded border text-[11px] font-mono ${
                  provider === 'lemonsqueezy'
                    ? 'border-emerald-500 bg-emerald-500/20 text-emerald-300'
                    : 'border-zinc-800 bg-zinc-900 text-zinc-400'
                }`}
              >
                Lemon Squeezy
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3 text-[11px] text-zinc-400">
            <div className="flex items-center gap-1">
              <Shield className="h-3.5 w-3.5 text-emerald-400" />
              <span>256-Bit SSL</span>
            </div>
            <div className="flex items-center gap-1">
              <CreditCard className="h-3.5 w-3.5 text-emerald-400" />
              <span>Cancel Anytime</span>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
