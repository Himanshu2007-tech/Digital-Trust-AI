import React from "react";
import { LucideIcon, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
  badgeText?: string;
  badgeVariant?: "default" | "cyan" | "emerald" | "amber" | "rose" | "indigo";
}

export function EmptyState({
  icon: Icon = ShieldAlert,
  title,
  description,
  actionLabel,
  onAction,
  className,
  badgeText,
  badgeVariant = "cyan",
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 md:p-12 text-center rounded-2xl border-2 border-dashed border-slate-200 dark:border-surface-borderDark bg-slate-50/40 dark:bg-surface-cardDark/30 transition-colors",
        className
      )}
    >
      {badgeText && (
        <div className="mb-3">
          <Badge variant={badgeVariant} size="sm">
            {badgeText}
          </Badge>
        </div>
      )}
      <div className="p-3.5 mb-3 rounded-2xl bg-slate-100 dark:bg-slate-800/80 text-cyan-600 dark:text-cyan-400 border border-slate-200 dark:border-slate-700/50 shadow-sm">
        <Icon className="w-8 h-8" />
      </div>
      <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 mb-1 tracking-tight">
        {title}
      </h4>
      <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mb-4 leading-relaxed">
        {description}
      </p>
      {actionLabel && onAction && (
        <Button onClick={onAction} size="sm" variant="primary">
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
