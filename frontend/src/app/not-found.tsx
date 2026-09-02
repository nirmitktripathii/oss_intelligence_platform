import Link from 'next/link';
import { Terminal, ArrowLeft, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="container flex min-h-[70vh] flex-col items-center justify-center text-center font-mono text-foreground">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-card border border-border text-destructive mb-6 shadow-xl">
        <AlertTriangle className="h-8 w-8" />
      </div>

      <div className="inline-flex items-center gap-1.5 rounded-full border border-destructive/40 bg-destructive/10 px-3 py-1 text-xs text-destructive font-bold mb-3">
        <span>ERROR 404: RESOURCE_NOT_FOUND</span>
      </div>

      <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
        Target AST Symbol or Issue Not Found
      </h1>

      <p className="text-xs sm:text-sm text-muted-foreground max-w-md mt-2 mb-8 leading-relaxed">
        The requested repository issue or triage report does not exist in the index or has been migrated.
      </p>

      <Link href="/">
        <Button variant="terminal" size="default" className="gap-2 text-xs">
          <ArrowLeft className="h-4 w-4" />
          <span>Return to Master Issue Terminal</span>
        </Button>
      </Link>
    </div>
  );
}
