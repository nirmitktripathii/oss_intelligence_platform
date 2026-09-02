'use client';

import * as React from 'react';
import { Search, X, Loader2 } from 'lucide-react';
import { Input } from '@/components/ui/input';

interface SearchInputProps {
  value: string;
  onChange: (value: string) => void;
  isPending?: boolean;
  inputRef?: React.RefObject<HTMLInputElement>;
}

export function SearchInput({ value, onChange, isPending, inputRef }: SearchInputProps) {
  const [localValue, setLocalValue] = React.useState(value);

  // Sync external value changes
  React.useEffect(() => {
    setLocalValue(value);
  }, [value]);

  // 250ms Debounced search propagation
  React.useEffect(() => {
    const handler = setTimeout(() => {
      if (localValue !== value) {
        onChange(localValue);
      }
    }, 250);

    return () => clearTimeout(handler);
  }, [localValue, onChange, value]);

  const handleClear = () => {
    setLocalValue('');
    onChange('');
  };

  return (
    <div className="relative w-full">
      <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-muted-foreground">
        {isPending ? (
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
        ) : (
          <Search className="h-4 w-4 text-muted-foreground" />
        )}
      </div>

      <Input
        ref={inputRef}
        type="text"
        placeholder="Search 100% live issues, repos, error keywords, stack..."
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        className="pl-9 pr-14 h-10 border-border bg-background/80 text-xs font-mono placeholder:text-muted-foreground focus-visible:ring-primary"
      />

      <div className="absolute inset-y-0 right-0 flex items-center pr-2 gap-1">
        {localValue && (
          <button
            type="button"
            onClick={handleClear}
            className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
        <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-border bg-card px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
          /
        </kbd>
      </div>
    </div>
  );
}
