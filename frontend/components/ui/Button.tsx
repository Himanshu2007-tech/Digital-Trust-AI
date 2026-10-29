import React from "react";
import { cn } from "@/lib/utils";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger" | "subtle";
  size?: "xs" | "sm" | "md" | "lg";
  children: React.ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...props
}: ButtonProps) {
  const baseStyles =
    "inline-flex items-center justify-center font-medium rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-cyan-500/50 disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]";

  const sizeStyles = {
    xs: "text-[11px] px-2.5 py-1 gap-1",
    sm: "text-xs px-3 py-1.5 gap-1.5",
    md: "text-xs px-4 py-2 gap-2",
    lg: "text-sm px-5 py-2.5 gap-2.5",
  };

  const variantStyles = {
    primary:
      "bg-cyan-500 text-slate-950 hover:bg-cyan-400 font-semibold shadow-sm hover:shadow",
    secondary:
      "bg-slate-100 dark:bg-slate-800/80 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 border border-slate-200 dark:border-surface-borderDark",
    outline:
      "border border-slate-300 dark:border-surface-borderDark text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60 hover:text-cyan-600 dark:hover:text-cyan-400",
    ghost:
      "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/50",
    danger:
      "bg-rose-600 hover:bg-rose-500 text-white shadow-sm",
    subtle:
      "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/20 border border-cyan-500/20",
  };

  return (
    <button
      className={cn(baseStyles, sizeStyles[size], variantStyles[variant], className)}
      {...props}
    >
      {children}
    </button>
  );
}
