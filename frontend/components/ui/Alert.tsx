import React from "react";
import { Info, AlertTriangle, CheckCircle2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "info" | "warning" | "success" | "error";
  title?: string;
  children: React.ReactNode;
}

export function Alert({
  variant = "info",
  title,
  children,
  className,
  ...props
}: AlertProps) {
  const icons = {
    info: Info,
    warning: AlertTriangle,
    success: CheckCircle2,
    error: XCircle,
  };

  const Icon = icons[variant];

  const variantStyles = {
    info: "bg-cyan-50 dark:bg-cyan-950/20 border-cyan-200 dark:border-cyan-500/30 text-cyan-900 dark:text-cyan-200 [&_svg]:text-cyan-600 dark:[&_svg]:text-cyan-400",
    warning: "bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-500/30 text-amber-900 dark:text-amber-200 [&_svg]:text-amber-600 dark:[&_svg]:text-amber-400",
    success: "bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-500/30 text-emerald-900 dark:text-emerald-200 [&_svg]:text-emerald-600 dark:[&_svg]:text-emerald-400",
    error: "bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-500/30 text-rose-900 dark:text-rose-200 [&_svg]:text-rose-600 dark:[&_svg]:text-rose-400",
  };

  return (
    <div
      role="alert"
      className={cn(
        "rounded-xl border p-4 flex items-start gap-3 text-xs leading-relaxed transition-all",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      <Icon className="w-5 h-5 shrink-0 mt-0.5" />
      <div className="space-y-0.5 flex-1">
        {title && <h5 className="font-semibold text-sm tracking-tight">{title}</h5>}
        <div className="opacity-90">{children}</div>
      </div>
    </div>
  );
}
