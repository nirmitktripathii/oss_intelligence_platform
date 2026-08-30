import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cn } from '@/lib/utils';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
  variant?: 'default' | 'primary' | 'terminal' | 'outline' | 'secondary' | 'ghost' | 'destructive' | 'glow';
  size?: 'default' | 'sm' | 'lg' | 'icon' | 'xs';
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';

    const baseStyles =
      'inline-flex items-center justify-center whitespace-nowrap rounded-md text-xs font-mono font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-emerald-500 disabled:pointer-events-none disabled:opacity-50 select-none';

    const variants: Record<string, string> = {
      default: 'bg-primary text-primary-foreground shadow hover:bg-primary/90',
      primary: 'bg-emerald-600 text-white shadow-sm hover:bg-emerald-500 active:scale-[0.98]',
      terminal:
        'bg-zinc-900 text-emerald-400 border border-emerald-500/30 hover:border-emerald-400 hover:bg-emerald-950/30 active:scale-[0.98] shadow-[0_0_10px_rgba(16,185,129,0.1)]',
      outline:
        'border border-zinc-700/80 bg-transparent text-zinc-300 hover:bg-zinc-800/80 hover:text-white dark:border-zinc-800 dark:hover:bg-zinc-800',
      secondary: 'bg-zinc-800 text-zinc-200 shadow-sm hover:bg-zinc-700',
      ghost: 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200',
      destructive: 'bg-rose-600 text-white shadow-sm hover:bg-rose-500',
      glow: 'bg-gradient-to-r from-emerald-600 to-teal-500 text-white shadow-[0_0_20px_rgba(16,185,129,0.35)] hover:shadow-[0_0_25px_rgba(16,185,129,0.5)] hover:brightness-110 active:scale-[0.98]',
    };

    const sizes: Record<string, string> = {
      xs: 'h-6 px-2 text-[11px] rounded',
      sm: 'h-8 rounded-md px-3 text-xs',
      default: 'h-9 px-4 py-2 text-xs',
      lg: 'h-10 rounded-md px-6 text-sm',
      icon: 'h-8 w-8',
    };

    return (
      <Comp
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';

export { Button };
