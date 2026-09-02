'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { DOMAINS } from '@/lib/constants';
import { apiClient } from '@/lib/api-client';
import { useToast } from '@/components/ui/toast';
import { Send, CheckCircle2, Bell, ExternalLink, Bot, MessageSquare, Mail } from 'lucide-react';

interface NotificationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NotificationModal({ isOpen, onClose }: NotificationModalProps) {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = React.useState<'telegram' | 'discord' | 'email'>('telegram');

  // Telegram state
  const [telegramCode, setTelegramCode] = React.useState('GTS-' + Math.floor(1000 + Math.random() * 9000));
  const [telegramConnected, setTelegramConnected] = React.useState(false);

  // Discord state
  const [discordWebhookUrl, setDiscordWebhookUrl] = React.useState('');
  const [discordTesting, setDiscordTesting] = React.useState(false);
  const [discordVerified, setDiscordVerified] = React.useState(false);

  // Email state
  const [emailAddress, setEmailAddress] = React.useState('');
  const [emailFrequency, setEmailFrequency] = React.useState<'instant' | 'daily' | 'weekly'>('daily');
  const [emailSaved, setEmailSaved] = React.useState(false);

  // Filter preferences
  const [selectedDomains, setSelectedDomains] = React.useState<string[]>(['ai_ml', 'data', 'web']);
  const [minBounty, setMinBounty] = React.useState<number>(50);

  const toggleDomain = (domainId: string) => {
    setSelectedDomains((prev) =>
      prev.includes(domainId) ? prev.filter((d) => d !== domainId) : [...prev, domainId]
    );
  };

  const handleTestDiscord = async () => {
    if (!discordWebhookUrl.includes('discord.com/api/webhooks')) {
      toast({
        title: 'Invalid Webhook URL',
        description: 'Please paste a valid Discord incoming webhook URL.',
        type: 'error',
      });
      return;
    }

    setDiscordTesting(true);
    try {
      const res = await apiClient.testNotification({
        channel: 'discord',
        destination: discordWebhookUrl,
      });

      if (res.success) {
        setDiscordVerified(true);
        toast({
          title: 'Discord Ping Successful!',
          description: 'A test embed payload was dispatched to your Discord server.',
          type: 'success',
        });
      } else {
        setDiscordVerified(false);
        toast({
          title: 'Test Not Delivered',
          description: res.message || 'Could not reach the notification service. No message was sent.',
          type: 'error',
        });
      }
    } catch {
      setDiscordVerified(false);
      toast({
        title: 'Test Failed',
        description: 'Could not reach the notification service. No test message was sent.',
        type: 'error',
      });
    } finally {
      setDiscordTesting(false);
    }
  };

  const handleSaveSubscription = async () => {
    try {
      const destination =
        activeTab === 'telegram'
          ? telegramCode
          : activeTab === 'discord'
          ? discordWebhookUrl
          : emailAddress;

      if (!destination) {
        toast({
          title: 'Missing destination',
          description: 'Please provide a valid channel target or code.',
          type: 'error',
        });
        return;
      }

      await apiClient.subscribeNotifications({
        channel: activeTab,
        destination,
        domains: selectedDomains,
        minBountyUsd: minBounty,
        digestFrequency: emailFrequency,
      });

      toast({
        title: 'Alerts Configured Successfully!',
        description: `Subscribed to ${activeTab.toUpperCase()} notifications with $${minBounty}+ min bounty threshold.`,
        type: 'success',
      });
      onClose();
    } catch (err: any) {
      // Keep the modal open so the user can retry; never report a false success.
      toast({
        title: 'Could Not Save Alerts',
        description:
          err?.message ||
          'The notification service is unreachable. Your subscription was not saved — please try again.',
        type: 'error',
      });
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl border-border bg-background/95 font-mono">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/20 text-primary border border-primary/40">
              <Bell className="h-4 w-4" />
            </div>
            <div>
              <DialogTitle className="text-sm font-semibold text-foreground">
                Multi-Channel Real-Time Alert Dispatcher
              </DialogTitle>
              <DialogDescription className="text-xs text-muted-foreground">
                Receive sub-60s push notifications for newly indexed live issues and funded bounties.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 pt-2">
          {/* Channel selector tabs */}
          <Tabs value={activeTab} onValueChange={(val: any) => setActiveTab(val)}>
            <TabsList className="grid w-full grid-cols-3 bg-card border-border">
              <TabsTrigger value="telegram" className="flex items-center gap-1.5 text-xs">
                <Bot className="h-3.5 w-3.5" />
                Telegram Bot
              </TabsTrigger>
              <TabsTrigger value="discord" className="flex items-center gap-1.5 text-xs">
                <MessageSquare className="h-3.5 w-3.5" />
                Discord Webhook
              </TabsTrigger>
              <TabsTrigger value="email" className="flex items-center gap-1.5 text-xs">
                <Mail className="h-3.5 w-3.5" />
                Resend Email
              </TabsTrigger>
            </TabsList>

            {/* Telegram Channel */}
            <TabsContent value="telegram" className="space-y-3 pt-2">
              <div className="rounded-md border border-border bg-card/40 p-3 space-y-2.5">
                <p className="text-xs text-foreground leading-relaxed">
                  Pair with <span className="text-primary font-semibold">@GitScoutAlertsBot</span> on Telegram for instant alerts with inline PR action buttons.
                </p>
                <div className="flex items-center justify-between gap-3 bg-background p-2.5 rounded border border-border">
                  <div>
                    <span className="text-[10px] text-muted-foreground uppercase tracking-wider block">Pairing Token</span>
                    <span className="text-sm font-bold text-primary">{telegramCode}</span>
                  </div>
                  <a
                    href={`https://t.me/GitScoutAlertsBot?start=pair_${telegramCode}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Button variant="terminal" size="sm" className="gap-1.5 text-xs">
                      Open in Telegram
                      <ExternalLink className="h-3 w-3" />
                    </Button>
                  </a>
                </div>
                <div className="flex items-center justify-between text-xs text-muted-foreground pt-1">
                  <span>Status:</span>
                  <Badge variant={telegramConnected ? 'emerald' : 'secondary'} className="text-[11px]">
                    {telegramConnected ? '🟢 Connected' : '⚪ Waiting for /start command'}
                  </Badge>
                </div>
              </div>
            </TabsContent>

            {/* Discord Channel */}
            <TabsContent value="discord" className="space-y-3 pt-2">
              <div className="rounded-md border border-border bg-card/40 p-3 space-y-3">
                <p className="text-xs text-foreground">
                  Paste your Discord incoming Webhook URL to stream formatted rich embeds with domain color tags directly into your server channel.
                </p>
                <div className="space-y-1.5">
                  <label className="text-[11px] text-muted-foreground">Discord Webhook URL</label>
                  <div className="flex gap-2">
                    <Input
                      placeholder="https://discord.com/api/webhooks/123456789/abcdef..."
                      value={discordWebhookUrl}
                      onChange={(e) => {
                        setDiscordWebhookUrl(e.target.value);
                        setDiscordVerified(false);
                      }}
                      className="text-xs font-mono"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleTestDiscord}
                      disabled={discordTesting || !discordWebhookUrl}
                      className="shrink-0 text-xs gap-1"
                    >
                      {discordTesting ? 'Testing...' : 'Test Ping'}
                    </Button>
                  </div>
                </div>
                {discordVerified && (
                  <div className="flex items-center gap-1.5 text-primary text-xs">
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>Webhook verified & ready for live notifications</span>
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Email Channel */}
            <TabsContent value="email" className="space-y-3 pt-2">
              <div className="rounded-md border border-border bg-card/40 p-3 space-y-3">
                <p className="text-xs text-foreground">
                  Transactional digests powered by Resend API with 1-click unsubscribe and curated issue links.
                </p>
                <div className="space-y-1.5">
                  <label className="text-[11px] text-muted-foreground">Developer Email</label>
                  <Input
                    type="email"
                    placeholder="hacker@company.com"
                    value={emailAddress}
                    onChange={(e) => setEmailAddress(e.target.value)}
                    className="text-xs font-mono"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[11px] text-muted-foreground">Digest Cadence</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(['instant', 'daily', 'weekly'] as const).map((freq) => (
                      <button
                        key={freq}
                        type="button"
                        onClick={() => setEmailFrequency(freq)}
                        className={`text-xs py-1.5 px-2 rounded border font-mono capitalize transition-colors ${
                          emailFrequency === freq
                            ? 'border-primary bg-primary/15 text-primary'
                            : 'border-border bg-card text-muted-foreground hover:border-border'
                        }`}
                      >
                        {freq} {freq === 'instant' ? '⚡' : ''}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>

          {/* Filtering Criteria */}
          <div className="rounded-md border border-border/80 bg-card/30 p-3 space-y-3">
            <h4 className="text-xs font-semibold text-foreground">Alert Triggers & Filter Rules</h4>

            {/* Domain toggles */}
            <div className="space-y-1.5">
              <span className="text-[11px] text-muted-foreground">Active Domains</span>
              <div className="flex flex-wrap gap-1.5">
                {DOMAINS.map((dom) => {
                  const isSelected = selectedDomains.includes(dom.id);
                  return (
                    <button
                      key={dom.id}
                      type="button"
                      onClick={() => toggleDomain(dom.id)}
                      className={`text-[11px] px-2 py-0.5 rounded border transition-all ${
                        isSelected
                          ? 'border-primary/60 bg-primary/15 text-primary font-medium'
                          : 'border-border bg-card/60 text-muted-foreground hover:border-border'
                      }`}
                    >
                      {dom.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Min bounty threshold */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] text-muted-foreground">
                <span>Minimum Bounty Threshold</span>
                <span className="text-bounty-gold font-semibold">${minBounty} USD</span>
              </div>
              <div className="flex gap-1.5">
                {[0, 50, 100, 250, 500].map((amt) => (
                  <button
                    key={amt}
                    type="button"
                    onClick={() => setMinBounty(amt)}
                    className={`text-xs flex-1 py-1 rounded border transition-colors ${
                      minBounty === amt
                        ? 'border-bounty-gold/60 bg-bounty-gold/15 text-bounty-gold font-semibold'
                        : 'border-border bg-card/60 text-muted-foreground hover:border-border'
                    }`}
                  >
                    {amt === 0 ? 'All' : `$${amt}`}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="glow" size="sm" onClick={handleSaveSubscription} className="gap-1.5">
              <Send className="h-3.5 w-3.5" />
              Save Alert Preferences
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
