'use client';

import * as React from 'react';
import {
  AlertTriangle,
  Mic,
  Pause,
  RotateCcw,
  Send,
  ShieldCheck,
  Square,
  Volume2,
  VolumeX,
  Radio,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { MiniMarkdown } from '@/components/alexa/mini-markdown';
import { StepTimeline } from '@/components/alexa/step-timeline';
import { useAgentSession, type Turn } from '@/hooks/use-agent-session';
import { useSpeech } from '@/hooks/use-speech';
import { cn } from '@/lib/utils';

const SUGGESTIONS = [
  'Find me a beginner-friendly Python issue and explain what is wrong in it',
  'Are there any funded bounties for Rust right now?',
  'Is the GitScout backend healthy?',
];

const YES = /^\s*(yes|yeah|yep|approve|approved|go ahead|do it|ok|okay|sure|confirm)\b/i;
const NO = /^\s*(no|nope|cancel|reject|decline|don't|do not|stop)\b/i;

function pendingStep(turn: Turn) {
  return turn.mission?.status === 'awaiting_approval'
    ? turn.steps.find((s) => s.state === 'awaiting')
    : undefined;
}

export default function AlexaPage() {
  const [draft, setDraft] = React.useState('');
  const speechRef = React.useRef<(text: string) => void>(() => {});
  const agent = useAgentSession({ onSpeech: (t) => speechRef.current(t) });
  const { turns, busy, send, decide, stop, reset } = agent;

  const latest = turns[turns.length - 1];
  const awaiting = latest && pendingStep(latest) ? latest : undefined;

  const submit = React.useCallback(
    (text: string) => {
      const t = text.trim();
      if (!t || busy) return;
      setDraft('');
      // While the assistant is waiting for a go-ahead, "yes" / "no" answers it.
      if (awaiting) {
        if (YES.test(t)) return void decide(awaiting.id, true);
        if (NO.test(t)) return void decide(awaiting.id, false);
      }
      send(t);
    },
    [awaiting, busy, decide, send],
  );

  // Spoken text goes into the box for the user to review, edit and send; recording never sends.
  const onTranscript = React.useCallback((text: string) => {
    setDraft((d) => (d.trim() ? `${d.trim()} ${text}` : text));
  }, []);

  const speech = useSpeech({ onTranscript });
  speechRef.current = speech.speak;

  // Keep the newest activity in view.
  // Scroll the conversation pane only; scrollIntoView would also scroll the whole page.
  const listRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [turns]);

  // Every "on screen" answer is kept, newest first, so nothing is lost when the conversation moves on.
  const screens = React.useMemo(() => turns.filter((t) => t.mission?.display).reverse(), [turns]);
  const [focusId, setFocusId] = React.useState<string | null>(null);
  const showOnScreen = React.useCallback((id: string) => {
    setFocusId(id);
    document.getElementById(`screen-${id}`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }, []);

  return (
    <div className="container flex h-[calc(100vh-3.5rem)] flex-col gap-4 py-4 font-mono">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-primary" />
          <h1 className="text-sm font-bold tracking-tight">Alexa+ simulator</h1>
          <Badge variant="outline">Developer Mission Control</Badge>
        </div>
        <div className="flex items-center gap-1.5">
          {speech.canSpeak && (
            <Button
              variant="ghost"
              size="sm"
              className="gap-1.5 text-xs text-muted-foreground"
              onClick={speech.toggleVoiceReplies}
              aria-pressed={speech.voiceReplies}
            >
              {speech.voiceReplies ? <Volume2 className="h-3.5 w-3.5" /> : <VolumeX className="h-3.5 w-3.5" />}
              Voice replies {speech.voiceReplies ? 'on' : 'off'}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 text-xs text-muted-foreground"
            onClick={() => {
              speech.stopSpeaking();
              reset();
            }}
            disabled={turns.length === 0}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            New conversation
          </Button>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        {/* Conversation */}
        <section className="flex min-h-0 flex-col rounded-lg border border-border bg-card/60">
          <div ref={listRef} className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
            {turns.length === 0 && (
              <div className="space-y-3 text-sm text-muted-foreground">
                <p>
                  Ask for open-source work by voice or text. The assistant plans its own steps, calls
                  the GitScout tools over MCP, and pauses before anything that needs your go-ahead.
                </p>
                <div className="flex flex-col items-start gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => submit(s)}
                      className="rounded-md border border-border bg-background/60 px-3 py-1.5 text-left text-xs hover:border-primary/50 hover:text-foreground"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {turns.map((turn) => (
              <TurnView
                key={turn.id}
                turn={turn}
                busy={busy}
                onDecide={(ok) => decide(turn.id, ok)}
                onShowScreen={() => showOnScreen(turn.id)}
              />
            ))}
          </div>

          {/* Input */}
          <form
            className="flex items-center gap-2 border-t border-border p-3"
            onSubmit={(e) => {
              e.preventDefault();
              // Enter while recording only pauses it, so the text can be checked before it is sent.
              if (speech.listening) return speech.stopListening();
              submit(draft);
            }}
          >
            {speech.canListen && (
              <Button
                type="button"
                variant={speech.listening ? 'glow' : 'outline'}
                size={speech.listening ? 'sm' : 'icon'}
                className={cn('h-9 shrink-0', speech.listening ? 'gap-1.5' : 'w-9')}
                onClick={speech.listening ? speech.stopListening : speech.startListening}
                disabled={busy && !speech.listening}
                title={speech.listening ? 'Pause recording' : draft.trim() ? 'Resume recording' : 'Talk to the assistant'}
                aria-pressed={speech.listening}
              >
                {speech.listening ? (
                  <>
                    <Pause className="h-4 w-4" />
                    <span className="text-xs">Pause</span>
                  </>
                ) : (
                  <>
                    <Mic className="h-4 w-4" />
                    <span className="sr-only">{draft.trim() ? 'Resume recording' : 'Start recording'}</span>
                  </>
                )}
              </Button>
            )}
            <input
              value={speech.listening ? [draft.trim(), speech.interim].filter(Boolean).join(' ') : draft}
              onChange={(e) => setDraft(e.target.value)}
              readOnly={speech.listening}
              maxLength={2000}
              placeholder={
                speech.listening
                  ? 'Listening... pause to think, then press Send'
                  : awaiting
                    ? 'Say or type yes / no, or ask something else'
                    : 'Ask for open-source work'
              }
              aria-label="Your request"
              className="h-9 min-w-0 flex-1 rounded-md border border-border bg-background px-3 text-sm outline-none placeholder:text-muted-foreground focus:border-primary/60"
            />
            {busy ? (
              <Button type="button" variant="outline" size="sm" className="h-9 gap-1.5" onClick={stop}>
                <Square className="h-3.5 w-3.5" />
                Stop
              </Button>
            ) : (
              <Button type="submit" size="sm" className="h-9 gap-1.5" disabled={!draft.trim() || speech.listening}>
                <Send className="h-3.5 w-3.5" />
                Send
              </Button>
            )}
          </form>
          {(speech.micError || !speech.canListen) && (
            <p className="px-4 pb-3 text-[11px] text-muted-foreground">
              {speech.micError ??
                'Voice input is not supported in this browser (try Chrome or Edge). Typing works everywhere.'}
            </p>
          )}
        </section>

        {/* The "screen" on an Alexa+ device: the longer answer that is not spoken. */}
        <section className="flex min-h-0 flex-col rounded-lg border border-border bg-card/60">
          <div className="border-b border-border px-4 py-2.5 text-xs font-semibold text-muted-foreground">
            On screen
          </div>
          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
            {screens.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Details, links and code the assistant would not read aloud appear here, and stay here for
                the rest of the conversation.
              </p>
            )}
            {screens.map((t, i) => (
              <article
                key={t.id}
                id={`screen-${t.id}`}
                className={cn(
                  'rounded-md border bg-background/50 p-3',
                  t.id === focusId || (focusId === null && i === 0) ? 'border-primary/50' : 'border-border',
                )}
              >
                <button
                  type="button"
                  className="mb-2 block w-full truncate text-left text-[11px] text-muted-foreground hover:text-foreground"
                  onClick={() => setFocusId(t.id)}
                  title={t.utterance}
                >
                  {i === 0 ? 'Latest: ' : ''}You asked: {t.utterance}
                </button>
                <MiniMarkdown source={t.mission!.display!} />
              </article>
            ))}
          </div>
          {latest?.mission && latest.mission.providers.length > 0 && (
            <div className="border-t border-border px-4 py-2 text-[11px] text-muted-foreground">
              Reasoned by {latest.mission.providers.join(', ')}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function TurnView({
  turn,
  busy,
  onDecide,
  onShowScreen,
}: {
  turn: Turn;
  busy: boolean;
  onDecide: (approved: boolean) => void;
  onShowScreen: () => void;
}) {
  const pending = pendingStep(turn);
  const mission = turn.mission;

  return (
    <div className="space-y-2.5">
      <div className="ml-auto w-fit max-w-[85%] rounded-lg bg-primary/10 px-3 py-2 text-sm text-foreground">
        {turn.utterance}
      </div>

      <StepTimeline steps={turn.steps} thinking={turn.working} />

      {pending && (
        <div className="space-y-2 rounded-md border border-bounty-gold/40 bg-bounty-gold/5 p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-bounty-gold">
            <ShieldCheck className="h-4 w-4" />
            Approval needed
          </div>
          <p className="text-xs text-muted-foreground">
            It wants to run <span className="font-semibold text-foreground">{pending.tool}</span> with exactly
            these arguments:
          </p>
          <pre className="overflow-x-auto rounded border border-border bg-background/70 p-2 text-[11px]">
            {JSON.stringify(pending.arguments, null, 2)}
          </pre>
          <div className="flex gap-2">
            <Button size="sm" className="h-8 text-xs" onClick={() => onDecide(true)} disabled={busy}>
              Approve
            </Button>
            <Button variant="outline" size="sm" className="h-8 text-xs" onClick={() => onDecide(false)} disabled={busy}>
              Decline
            </Button>
          </div>
        </div>
      )}

      {mission?.speech && (
        <div className={cn('max-w-[90%] rounded-lg border border-border bg-background/60 px-3 py-2 text-sm')}>
          {mission.speech}
          {mission.display && (
            <button
              type="button"
              onClick={onShowScreen}
              className="mt-2 block text-[11px] text-primary hover:underline"
            >
              Show on screen
            </button>
          )}
        </div>
      )}

      {(turn.error || mission?.status === 'failed') && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-2.5 text-xs text-destructive">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <div>
            <p>{turn.error ?? mission?.error ?? 'The mission failed.'}</p>
            {turn.unavailable && (
              <p className="mt-1 text-destructive/80">
                The operator needs to set AGENT_MCP_SERVERS on the backend before the assistant can run.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
