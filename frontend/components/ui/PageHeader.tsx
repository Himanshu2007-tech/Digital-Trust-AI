import React from "react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description: string;
  badgeText?: string;
  badgeVariant?: "default" | "cyan" | "emerald" | "amber" | "rose" | "indigo";
  icon?: React.ComponentType<{ className?: string }>;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  badgeText,
  badgeVariant = "cyan",
  icon: Icon,
  actions,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("flex flex-col md:flex-row md:items-center md:justify-between gap-4 pb-6 border-b border-slate-200 dark:border-surface-borderDark", className)}>
      <div className="space-y-1.5 max-w-3xl">
        {badgeText && (
          <div className="flex items-center gap-2">
            <Badge variant={badgeVariant} size="sm">
              {badgeText}
            </Badge>
          </div>
        )}
        <div className="flex items-center gap-2.5">
          {Icon && <Icon className="w-6 h-6 text-cyan-600 dark:text-cyan-400 shrink-0" />}
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            {title}
          </h1>
        </div>
        <p className="text-xs md:text-sm text-slate-500 dark:text-slate-400 leading-relaxed">
          {description}
        </p>
      </div>

      {actions && <div className="flex items-center gap-2.5 shrink-0">{actions}</div>}
    </div>
  );
}
