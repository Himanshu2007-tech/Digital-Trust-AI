import React from "react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

interface ArchitectureStepProps {
  stepNumber: number;
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  phaseTag: string;
  isLast?: boolean;
}

export function ArchitectureStep({
  stepNumber,
  title,
  description,
  icon: Icon,
  phaseTag,
  isLast = false,
}: ArchitectureStepProps) {
  return (
    <div className="relative flex flex-col items-center text-center group">
      {/* Step Icon Capsule */}
      <div className="relative mb-3 flex items-center justify-center">
        <div className="w-12 h-12 rounded-2xl border border-slate-200 dark:border-surface-borderDark bg-white dark:bg-surface-cardDark flex items-center justify-center text-cyan-600 dark:text-cyan-400 group-hover:border-cyan-500/50 group-hover:scale-105 transition-all shadow-sm">
          <Icon className="w-5 h-5" />
        </div>
        <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-cyan-500 text-slate-950 font-mono text-[10px] font-bold flex items-center justify-center shadow">
          {stepNumber}
        </span>
      </div>

      <div className="space-y-1 max-w-[160px]">
        <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100">
          {title}
        </h4>
        <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight">
          {description}
        </p>
        <div className="pt-1">
          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
            {phaseTag}
          </span>
        </div>
      </div>
    </div>
  );
}
