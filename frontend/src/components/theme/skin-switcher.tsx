'use client';

import * as React from 'react';
import { Check, Palette } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

type Skin = {
  id: string;
  name: string;
  tag: string;
  swatch: string;
};

// Order and swatch hues mirror the design canvas themeMeta.
const SKINS: Skin[] = [
  { id: 'tokyo', name: 'Tokyo Night', tag: 'neon dusk', swatch: '#7aa2f7' },
  { id: 'phosphor', name: 'Phosphor', tag: 'green CRT', swatch: '#10b981' },
  { id: 'amber', name: 'Amber CRT', tag: 'retro terminal', swatch: '#ffb000' },
  { id: 'brutalist', name: 'Brutalist', tag: 'ink & orange', swatch: '#ff5c35' },
  { id: 'rosepine', name: 'Rosé Pine', tag: 'soft serif', swatch: '#9ccfd8' },
];

const STORAGE_KEY = 'gitscout-skin';
const DEFAULT_SKIN = 'tokyo';

export function SkinSwitcher() {
  const [mounted, setMounted] = React.useState(false);
  const [skin, setSkinState] = React.useState<string>(DEFAULT_SKIN);

  React.useEffect(() => {
    setMounted(true);
    const current =
      document.documentElement.getAttribute('data-skin') || DEFAULT_SKIN;
    setSkinState(current);
  }, []);

  const setSkin = React.useCallback((id: string) => {
    document.documentElement.setAttribute('data-skin', id);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* storage unavailable — session-only skin */
    }
    setSkinState(id);
  }, []);

  const active = SKINS.find((s) => s.id === skin) ?? SKINS[0];

  if (!mounted) {
    return (
      <Button
        variant="outline"
        size="icon"
        className="h-8 w-8 border-border bg-card/50"
      >
        <Palette className="h-4 w-4 text-muted-foreground" />
        <span className="sr-only">Change theme skin</span>
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 border-border bg-card/80 hover:border-primary/60 text-foreground"
          aria-label={`Theme skin: ${active.name}`}
        >
          <span
            className="h-3.5 w-3.5 rounded-full ring-2 ring-background"
            style={{ backgroundColor: active.swatch }}
          />
          <span className="sr-only">Change theme skin</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-52 border-border bg-popover/95 font-mono text-xs backdrop-blur"
      >
        <DropdownMenuLabel className="text-[10px] uppercase tracking-widest text-muted-foreground">
          Terminal Skin
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="bg-border" />
        {SKINS.map((s) => (
          <DropdownMenuItem
            key={s.id}
            onClick={() => setSkin(s.id)}
            className="flex items-center gap-2.5 cursor-pointer"
          >
            <span
              className="h-3.5 w-3.5 shrink-0 rounded-full ring-1 ring-border"
              style={{ backgroundColor: s.swatch }}
            />
            <span className="flex flex-col leading-tight">
              <span className="text-foreground">{s.name}</span>
              <span className="text-[10px] text-muted-foreground">{s.tag}</span>
            </span>
            {s.id === skin && (
              <Check className="ml-auto h-3.5 w-3.5 text-primary" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
