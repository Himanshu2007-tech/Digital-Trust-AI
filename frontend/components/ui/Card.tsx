import React from "react";
import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
}

export function Card({ children, className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-200 dark:border-surface-borderDark bg-white dark:bg-surface-cardDark/80 shadow-sm dark:shadow-none p-5 transition-all",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className, ...props }: CardProps) {
  return (
    <div className={cn("flex flex-col space-y-1.5 mb-4", className)} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({ children, className, ...props }: CardProps) {
  return (
    <h3
      className={cn("text-base font-semibold text-slate-900 dark:text-slate-100 tracking-tight", className)}
      {...props}
    >
      {children}
    </h3>
  );
}

export function CardDescription({ children, className, ...props }: CardProps) {
  return (
    <p
      className={cn("text-xs text-slate-500 dark:text-slate-400 leading-relaxed", className)}
      {...props}
    >
      {children}
    </p>
  );
}

export function CardContent({ children, className, ...props }: CardProps) {
  return (
    <div className={cn("space-y-4", className)} {...props}>
      {children}
    </div>
  );
}

export function CardFooter({ children, className, ...props }: CardProps) {
  return (
    <div className={cn("mt-4 pt-3 border-t border-slate-100 dark:border-surface-borderDark flex items-center justify-between", className)} {...props}>
      {children}
    </div>
  );
}
