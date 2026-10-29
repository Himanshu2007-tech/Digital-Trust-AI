import React from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

interface VerificationModeCardProps {
  title: string;
  description: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  phaseText: string;
  phaseVariant?: "cyan" | "indigo" | "emerald" | "amber";
  colorClass?: string;
  badge?: string;
}

export function VerificationModeCard({
  title,
  description,
  href,
  icon: Icon,
  phaseText,
  phaseVariant = "cyan",
  colorClass = "text-cyan-500 dark:text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
  badge,
}: VerificationModeCardProps) {
  return (
    <Link
      href={href}
      className="group relative flex flex-col justify-between rounded-2xl border border-slate-200 dark:border-surface-borderDark bg-white dark:bg-surface-cardDark/70 hover:border-cyan-500/50 dark:hover:border-cyan-500/50 p-5 transition-all duration-200 hover:shadow-md dark:hover:shadow-cyan-950/20 hover:-translate-y-0.5"
    >
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className={cn("p-3 rounded-xl border", colorClass)}>
            <Icon className="w-5 h-5" />
          </div>
          <div className="flex items-center gap-1.5">
            {badge && (
              <Badge variant="emerald" size="sm">
                {badge}
              </Badge>
            )}
            <Badge variant={phaseVariant} size="sm">
              {phaseText}
            </Badge>
          </div>
        </div>

        <h3 className="text-base font-bold text-slate-900 dark:text-slate-100 group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors mb-2">
          {title}
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
          {description}
        </p>
      </div>

      <div className="mt-5 pt-3 border-t border-slate-100 dark:border-surface-borderDark flex items-center justify-between text-xs font-semibold text-cyan-600 dark:text-cyan-400 group-hover:translate-x-0.5 transition-transform">
        <span>Open Mode</span>
        <ArrowRight className="w-4 h-4" />
      </div>
    </Link>
  );
}
