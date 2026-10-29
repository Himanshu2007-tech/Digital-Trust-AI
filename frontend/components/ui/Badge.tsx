import React from "react";
import { cn } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "cyan" | "emerald" | "amber" | "rose" | "indigo" | "purple" | "slate" | "outline";
  children: React.ReactNode;
  size?: "sm" | "md";
}

export function Badge({
  variant = "default",
  size = "md",
  className,
  children,
  ...props
}: BadgeProps) {
  const sizeStyles = {
    sm: "text-[10px] px-1.5 py-0.5",
    md: "text-xs px-2.5 py-0.5",
  };

  const variantStyles = {
    default:
      "bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700",
    cyan:
      "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30",
    emerald:
      "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30",
    amber:
      "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30",
    rose:
      "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30",
    indigo:
      "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30",
    purple:
      "bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/30",
    slate:
      "bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-surface-borderDark",
    outline:
      "border border-slate-300 dark:border-surface-borderDark text-slate-600 dark:text-slate-400",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-medium font-mono leading-none tracking-wide select-none",
        sizeStyles[size],
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
