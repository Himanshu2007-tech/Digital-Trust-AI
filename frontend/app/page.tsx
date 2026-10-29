"use client";

import React from "react";
import Link from "next/link";
import {
  FileText,
  Globe,
  Image as ImageIcon,
  Mic,
  Film,
  History,
  FileCheck,
  BarChart3,
  ArrowUpRight,
} from "lucide-react";

interface DashboardCardItem {
  title: string;
  description: string;
  href: string;
  icon: React.ElementType;
}

const DASHBOARD_CARDS: DashboardCardItem[] = [
  {
    title: "Verify Text",
    description: "Check claims and written information.",
    href: "/verify-text",
    icon: FileText,
  },
  {
    title: "Verify URL",
    description: "Check online articles and links.",
    href: "/verify-url",
    icon: Globe,
  },
  {
    title: "Verify Image",
    description: "Analyze images and extract visible text.",
    href: "/verify-image",
    icon: ImageIcon,
  },
  {
    title: "Verify Audio",
    description: "Check audio content.",
    href: "/verify-audio",
    icon: Mic,
  },
  {
    title: "Verify Video",
    description: "Analyze video content.",
    href: "/verify-video",
    icon: Film,
  },
  {
    title: "History",
    description: "View previous verification requests.",
    href: "/history",
    icon: History,
  },
  {
    title: "Reports",
    description: "View and download verification reports.",
    href: "/reports",
    icon: FileCheck,
  },
  {
    title: "Analytics",
    description: "View verification statistics.",
    href: "/analytics",
    icon: BarChart3,
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Clean Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
          Digital Trust AI
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Select a verification service or investigative tool below.
        </p>
      </div>

      {/* 8 Medium-Sized Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6">
        {DASHBOARD_CARDS.map((card) => {
          const Icon = card.icon;
          return (
            <Link
              key={card.title}
              href={card.href}
              className="group relative flex flex-col justify-between p-6 rounded-2xl border border-slate-200/90 dark:border-surface-borderDark bg-white dark:bg-[#0c1427] hover:border-cyan-500/50 dark:hover:border-cyan-500/50 shadow-xs hover:shadow-md dark:hover:shadow-cyan-950/20 transition-all duration-200 hover:-translate-y-0.5 select-none min-h-[160px]"
            >
              <div>
                <div className="flex items-center justify-between">
                  <div className="w-11 h-11 rounded-xl bg-cyan-500/10 dark:bg-cyan-500/15 text-cyan-600 dark:text-cyan-400 flex items-center justify-center group-hover:bg-cyan-500 group-hover:text-white transition-colors duration-200">
                    <Icon className="w-5 h-5" />
                  </div>
                  <ArrowUpRight className="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-cyan-600 dark:group-hover:text-cyan-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-all duration-200" />
                </div>

                <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100 group-hover:text-cyan-600 dark:group-hover:text-cyan-400 transition-colors mt-4">
                  {card.title}
                </h2>

                <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                  {card.description}
                </p>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
