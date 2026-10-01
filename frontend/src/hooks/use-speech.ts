'use client';

import * as React from 'react';
import { pickBestAlternative } from '@/lib/tech-terms';

// The Web Speech API is not in lib.dom for every TS version; describe only what is used.
interface RecognitionResult {
  isFinal: boolean;
  length: number;
  [index: number]: { transcript: string };
}
interface RecognitionEvent {
  resultIndex: number;
  results: ArrayLike<RecognitionResult>;
}
interface Recognition {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((e: RecognitionEvent) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}
type RecognitionCtor = new () => Recognition;

function recognitionCtor(): RecognitionCtor | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as {
    SpeechRecognition?: RecognitionCtor;
    webkitSpeechRecognition?: RecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const MIC_ERRORS: Record<string, string> = {
  'not-allowed': 'Microphone access was blocked. Type your request instead.',
  'service-not-allowed': 'Microphone access was blocked. Type your request instead.',
  'no-speech': "I didn't catch anything. Try again.",
  'audio-capture': 'No microphone was found. Type your request instead.',
  network: 'Speech recognition needs a network connection.',
};

interface Options {
  /** Called with the transcript each time recording stops or is paused. It is not a request to send. */
  onTranscript: (text: string) => void;
}

/** Browser speech in and out, with feature detection so the page works without either. */
export function useSpeech({ onTranscript }: Options) {
  const [canListen, setCanListen] = React.useState(false);
  const [canSpeak, setCanSpeak] = React.useState(false);
  const [listening, setListening] = React.useState(false);
  const [speaking, setSpeaking] = React.useState(false);
  const [interim, setInterim] = React.useState('');
  const [micError, setMicError] = React.useState<string | null>(null);
  const [voiceReplies, setVoiceReplies] = React.useState(true);

  const rec = React.useRef<Recognition | null>(null);
  const callback = React.useRef(onTranscript);
  callback.current = onTranscript;

  React.useEffect(() => {
    setCanListen(recognitionCtor() !== null);
    setCanSpeak(typeof window !== 'undefined' && 'speechSynthesis' in window);
    return () => {
      rec.current?.abort();
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) window.speechSynthesis.cancel();
    };
  }, []);

  const stopSpeaking = React.useCallback(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) window.speechSynthesis.cancel();
    setSpeaking(false);
  }, []);

  const speak = React.useCallback(
    (text: string) => {
      if (!voiceReplies || typeof window === 'undefined' || !('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.onstart = () => setSpeaking(true);
      u.onend = () => setSpeaking(false);
      u.onerror = () => setSpeaking(false);
      window.speechSynthesis.speak(u);
    },
    [voiceReplies],
  );

  // Pausing and stopping are the same thing for the recognizer: end the session and hand back what
  // was heard. The page appends it to the draft, so recording again carries on from there.
  const stopListening = React.useCallback(() => rec.current?.stop(), []);

  const startListening = React.useCallback(() => {
    const Ctor = recognitionCtor();
    if (!Ctor || rec.current) return;
    stopSpeaking(); // never transcribe the assistant's own voice
    setMicError(null);
    setInterim('');
    const r = new Ctor();
    r.lang = navigator.language || 'en-US';
    r.interimResults = true;
    // Continuous mode keeps listening across pauses; the default ends the session at the first gap.
    r.continuous = true;
    // Ask for alternatives so a technical term can be picked from a lower-ranked guess.
    r.maxAlternatives = 5;
    let finalText = '';
    let partial = '';
    const heard = (res: RecognitionResult) => {
      const options: string[] = [];
      for (let k = 0; k < res.length; k++) options.push(res[k].transcript.trim());
      return pickBestAlternative(options);
    };
    r.onresult = (e) => {
      partial = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) finalText += (finalText ? ' ' : '') + heard(res);
        else partial += res[0].transcript;
      }
      setInterim([finalText, pickBestAlternative([partial.trim()])].filter(Boolean).join(' '));
    };
    r.onerror = (e) => setMicError(MIC_ERRORS[e.error] ?? 'Speech recognition failed. Type your request instead.');
    r.onend = () => {
      rec.current = null;
      setListening(false);
      setInterim('');
      // A phrase still being recognised when the session closed is better kept than lost.
      const text = [finalText, pickBestAlternative([partial.trim()])].filter(Boolean).join(' ').trim();
      if (text) callback.current(text);
    };
    rec.current = r;
    try {
      r.start();
      setListening(true);
    } catch {
      rec.current = null;
      setMicError('Could not start the microphone.');
    }
  }, [stopSpeaking]);

  const toggleVoiceReplies = React.useCallback(() => {
    setVoiceReplies((on) => {
      if (on) stopSpeaking();
      return !on;
    });
  }, [stopSpeaking]);

  return {
    canListen,
    canSpeak,
    listening,
    speaking,
    interim,
    micError,
    voiceReplies,
    toggleVoiceReplies,
    startListening,
    stopListening,
    stopSpeaking,
    speak,
  };
}
