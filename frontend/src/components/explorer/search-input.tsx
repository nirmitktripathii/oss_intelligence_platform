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
      <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-zinc-500">
        {isPending ? (
          <Loader2 className="h-4 w-4 animate-spin text-emerald-400" />
        ) : (
          <Search className="h-4 w-4 text-zinc-500" />
        )}
      </div>

      <Input
        ref={inputRef}
        type="text"
        placeholder="Search 100% live issues, repos, error keywords, stack..."
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        className="pl-9 pr-14 h-10 border-zinc-800 bg-zinc-950/80 text-xs font-mono placeholder:text-zinc-500 focus-visible:ring-emerald-500"
      />

      <div className="absolute inset-y-0 right-0 flex items-center pr-2 gap-1">
        {localValue && (
          <button
            type="button"
            onClick={handleClear}
            className="p-1 rounded text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
        <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 text-[10px] font-mono text-zinc-400">
          /
        </kbd>
      </div>
    </div>
  );
}
