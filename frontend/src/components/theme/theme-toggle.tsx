'use client';

import * as React from 'react';
import { Moon, Sun, Laptop } from 'lucide-react';
import { useTheme } from 'next-themes';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <Button variant="outline" size="icon" className="h-8 w-8 border-border bg-card/50">
        <Sun className="h-4 w-4 text-muted-foreground" />
        <span className="sr-only">Toggle theme</span>
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="h-8 w-8 border-border bg-card/80 hover:border-border text-foreground hover:text-foreground"
        >
          {theme === 'dark' ? (
            <Moon className="h-4 w-4 text-primary" />
          ) : theme === 'light' ? (
            <Sun className="h-4 w-4 text-bounty-gold" />
          ) : (
            <Laptop className="h-4 w-4 text-accent" />
          )}
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="border-border bg-background/95 font-mono text-xs">
        <DropdownMenuItem
          onClick={() => setTheme('light')}
          className="flex items-center gap-2 cursor-pointer"
        >
          <Sun className="h-3.5 w-3.5 text-bounty-gold" />
          <span>Light Mode</span>
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => setTheme('dark')}
          className="flex items-center gap-2 cursor-pointer"
        >
          <Moon className="h-3.5 w-3.5 text-primary" />
          <span>Dark Obsidian</span>
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => setTheme('system')}
          className="flex items-center gap-2 cursor-pointer"
        >
          <Laptop className="h-3.5 w-3.5 text-accent" />
          <span>System Sync</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
