"use client";

import React from "react";
import { usePathname } from "next/navigation";
import { BackendStatusBadge } from "@/components/ui/BackendStatusBadge";
import { ThemeToggle } from "@/components/ui/ThemeToggle";
import { Menu, PanelLeftClose, PanelLeftOpen, User } from "lucide-react";

interface HeaderProps {
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  onOpenMobile?: () => void;
}

const pageTitles: Record<string, { title: string; subtitle: string }> = {
  "/": {
    title: "Dashboard",
    subtitle: "Digital Trust Verification & Investigative Platform",
  },
  "/verify-text": {
    title: "Verify Information",
    subtitle: "Verify news claims, statements, or uploaded images against evidence",
  },
  "/verify-url": {
    title: "Verify URL",
    subtitle: "Analyze web publication context with SSRF protection",
  },
  "/verify-image": {
    title: "Verify Image",
    subtitle: "Image forensics, EXIF analysis, and OCR claim extraction",
  },
  "/verify-audio": {
    title: "Verify Audio",
    subtitle: "Speech-to-text transcription and spoken claim verification",
  },
  "/verify-video": {
    title: "Verify Video",
    subtitle: "Keyframe extraction, scene OCR, and cross-modal reconciliation",
  },
  "/verify-media": {
    title: "Verify Media",
    subtitle: "Multi-modal audio and video forensic verification",
  },
  "/history": {
    title: "Verification History",
    subtitle: "Archived investigation dossiers and audit records",
  },
  "/reports": {
    title: "Verification Reports",
    subtitle: "Downloadable verification dossiers and analytical summaries",
  },
  "/analytics": {
    title: "Analytics",
    subtitle: "Verification statistics, trend analytics, and accuracy index",
  },
  "/about": {
    title: "About Digital Trust AI",
    subtitle: "System architecture, methodology, and verification pipeline",
  },
};

export function Header({ isCollapsed = false, onToggleCollapse, onOpenMobile }: HeaderProps) {
  const pathname = usePathname();
  const pageInfo = pageTitles[pathname] || {
    title: "Digital Trust AI",
    subtitle: "Verification & Forensic Suite",
  };

  return (
    <header className="h-16 border-b border-slate-200 dark:border-surface-borderDark bg-white/90 dark:bg-[#090e1c]/90 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30 transition-colors">
      {/* Left: Sidebar Toggle & Contextual Title */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Mobile Toggle Button */}
        <button
          onClick={onOpenMobile}
          className="lg:hidden p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
          aria-label="Open navigation menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Desktop Collapse/Expand Toggle Button */}
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex p-2 rounded-xl text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors focus:outline-none focus:ring-2 focus:ring-cyan-500/40"
            title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {isCollapsed ? (
              <PanelLeftOpen className="w-5 h-5" />
            ) : (
              <PanelLeftClose className="w-5 h-5" />
            )}
          </button>
        )}

        {/* Title and Subtitle */}
        <div className="min-w-0">
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate tracking-tight">
            {pageInfo.title}
          </h2>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate hidden sm:block">
            {pageInfo.subtitle}
          </p>
        </div>
      </div>

      {/* Right: Telemetry Status, Theme Toggle, Profile */}
      <div className="flex items-center gap-2.5 sm:gap-4 shrink-0">
        {/* Live Backend Telemetry Badge */}
        <BackendStatusBadge />

        {/* Dark/Light Theme Switcher */}
        <ThemeToggle />

        {/* Investigator Session Indicator */}
        <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-slate-200 dark:border-surface-borderDark text-xs text-slate-600 dark:text-slate-300">
          <div className="w-7 h-7 rounded-full bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20 flex items-center justify-center font-bold font-mono text-[10px]">
            <User className="w-3.5 h-3.5" />
          </div>
          <span className="font-medium text-[11px] hidden md:inline">Investigator</span>
        </div>
      </div>
    </header>
  );
}
