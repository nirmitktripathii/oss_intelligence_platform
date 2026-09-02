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
      'inline-flex items-center justify-center whitespace-nowrap rounded-md text-xs font-mono font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary disabled:pointer-events-none disabled:opacity-50 select-none';

    const variants: Record<string, string> = {
      default: 'bg-primary text-primary-foreground shadow hover:bg-primary/90',
      primary: 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90 active:scale-[0.98]',
      terminal:
        'bg-card text-primary border border-primary/30 hover:border-primary hover:bg-primary/10 active:scale-[0.98] shadow-[0_0_10px_hsl(var(--primary)/0.1)]',
      outline:
        'border border-border/80 bg-transparent text-foreground hover:bg-secondary/80 hover:text-foreground dark:border-border dark:hover:bg-secondary',
      secondary: 'bg-secondary text-secondary-foreground shadow-sm hover:bg-muted',
      ghost: 'text-muted-foreground hover:bg-secondary/60 hover:text-foreground',
      destructive: 'bg-destructive text-white shadow-sm hover:bg-destructive/90',
      glow: 'bg-gradient-to-r from-primary to-accent text-primary-foreground shadow-[0_0_20px_hsl(var(--primary)/0.35)] hover:shadow-[0_0_25px_hsl(var(--primary)/0.5)] hover:brightness-110 active:scale-[0.98]',
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
