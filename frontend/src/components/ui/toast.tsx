'use client';

import * as React from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ToastMessage {
  id: string;
  title: string;
  description?: string;
  type?: 'success' | 'error' | 'info';
}

interface ToastContextType {
  toast: (msg: Omit<ToastMessage, 'id'>) => void;
}

const ToastContext = React.createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastMessage[]>([]);

  const toast = React.useCallback((msg: Omit<ToastMessage, 'id'>) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { ...msg, id }]);

    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col space-y-2 max-w-sm pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              'pointer-events-auto flex items-start gap-3 rounded-lg border p-3.5 shadow-2xl backdrop-blur-md transition-all font-mono text-xs animate-in slide-in-from-bottom-5',
              t.type === 'error'
                ? 'border-destructive/50 bg-background/95 text-destructive'
                : t.type === 'info'
                ? 'border-accent/50 bg-background/95 text-accent'
                : 'border-primary/50 bg-background/95 text-primary'
            )}
          >
            {t.type === 'error' ? (
              <AlertCircle className="h-4 w-4 shrink-0 text-destructive mt-0.5" />
            ) : t.type === 'info' ? (
              <Info className="h-4 w-4 shrink-0 text-accent mt-0.5" />
            ) : (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-primary mt-0.5" />
            )}
            <div className="flex-1 space-y-0.5">
              <p className="font-semibold text-foreground">{t.title}</p>
              {t.description && <p className="text-[11px] text-muted-foreground">{t.description}</p>}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = React.useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
