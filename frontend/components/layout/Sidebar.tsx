"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  ShieldCheck,
  History,
  FileCheck,
  BarChart3,
  Info,
  ChevronLeft,
  ChevronRight,
  X,
  PanelLeftClose,
  PanelLeftOpen
} from "lucide-react";
import { cn } from "@/lib/utils";

interface SidebarProps {
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

const navigationItems = [
  { name: "Home", href: "/", icon: LayoutDashboard },
  { name: "Verify", href: "/verify-text", icon: ShieldCheck, matchPrefix: "/verify" },
  { name: "History", href: "/history", icon: History, matchPrefix: "/history" },
  { name: "Reports", href: "/reports", icon: FileCheck, matchPrefix: "/reports" },
  { name: "Analytics", href: "/analytics", icon: BarChart3, matchPrefix: "/analytics" },
  { name: "About", href: "/about", icon: Info, matchPrefix: "/about" },
];

export function Sidebar({
  isCollapsed = false,
  onToggleCollapse,
  isMobileOpen = false,
  onCloseMobile,
}: SidebarProps) {
  const pathname = usePathname();

  const isItemActive = (item: typeof navigationItems[0]) => {
    if (item.href === "/") {
      return pathname === "/";
    }
    if (item.matchPrefix) {
      return pathname.startsWith(item.matchPrefix);
    }
    return pathname === item.href;
  };

  return (
    <>
      {/* Mobile Drawer Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-slate-950/60 backdrop-blur-sm lg:hidden transition-opacity duration-300"
          aria-hidden="true"
        />
      )}

      {/* Mobile Drawer (Always full width w-64 when open) */}
      <aside
        className={cn(
          "fixed top-0 bottom-0 left-0 z-50 w-64 border-r border-slate-200 dark:border-surface-borderDark bg-white dark:bg-[#090e1c] flex flex-col min-h-screen lg:hidden transition-transform duration-300 ease-in-out shadow-2xl",
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Mobile Header with Brand & Close Button */}
        <div className="h-16 flex items-center justify-between px-5 border-b border-slate-200 dark:border-surface-borderDark">
          <Link
            href="/"
            onClick={onCloseMobile}
            className="flex items-center gap-3 focus:outline-none"
          >
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 dark:bg-cyan-500/20 border border-cyan-500/30 text-cyan-600 dark:text-cyan-400 flex items-center justify-center shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="font-bold text-sm tracking-wide text-slate-900 dark:text-white flex items-center gap-1.5 uppercase">
                <span>Digital Trust</span>
                <span className="text-cyan-600 dark:text-cyan-400 text-[10px] font-mono px-1 py-0.2 rounded bg-cyan-500/10 border border-cyan-500/30">
                  AI
                </span>
              </div>
              <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono tracking-wider">
                Verification Suite
              </div>
            </div>
          </Link>

          <button
            onClick={onCloseMobile}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 focus:outline-none"
            aria-label="Close sidebar"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mobile Navigation List */}
        <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
          {navigationItems.map((item) => {
            const active = isItemActive(item);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onCloseMobile}
                className={cn(
                  "flex items-center gap-3.5 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all group select-none",
                  active
                    ? "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border border-cyan-500/30 font-semibold shadow-xs"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60"
                )}
              >
                <Icon
                  className={cn(
                    "w-5 h-5 shrink-0 transition-colors",
                    active
                      ? "text-cyan-600 dark:text-cyan-400"
                      : "text-slate-400 dark:text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300"
                  )}
                />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Desktop Collapsible Sidebar */}
      <aside
        className={cn(
          "hidden lg:flex flex-col border-r border-slate-200 dark:border-surface-borderDark bg-white dark:bg-[#090e1c] shrink-0 min-h-screen transition-all duration-300 ease-in-out sticky top-0 h-screen",
          isCollapsed ? "w-20" : "w-64"
        )}
      >
        {/* Brand Header */}
        <div
          className={cn(
            "h-16 flex items-center border-b border-slate-200 dark:border-surface-borderDark transition-all duration-300",
            isCollapsed ? "justify-center px-2" : "justify-between px-5"
          )}
        >
          <Link
            href="/"
            className={cn(
              "flex items-center gap-3 focus:outline-none group",
              isCollapsed && "justify-center"
            )}
            title="Digital Trust AI"
          >
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 dark:bg-cyan-500/20 border border-cyan-500/30 text-cyan-600 dark:text-cyan-400 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
              <ShieldCheck className="w-5 h-5" />
            </div>

            {!isCollapsed && (
              <div className="min-w-0 transition-opacity duration-300">
                <div className="font-bold text-sm tracking-wide text-slate-900 dark:text-white flex items-center gap-1.5 uppercase whitespace-nowrap">
                  <span>Digital Trust</span>
                  <span className="text-cyan-600 dark:text-cyan-400 text-[10px] font-mono px-1 py-0.2 rounded bg-cyan-500/10 border border-cyan-500/30">
                    AI
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono tracking-wider truncate">
                  Verification Suite
                </div>
              </div>
            )}
          </Link>

          {!isCollapsed && onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus:outline-none"
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Navigation Section */}
        <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
          {navigationItems.map((item) => {
            const active = isItemActive(item);
            const Icon = item.icon;

            return (
              <Link
                key={item.href}
                href={item.href}
                title={isCollapsed ? item.name : undefined}
                className={cn(
                  "flex items-center rounded-xl text-sm font-medium transition-all group select-none",
                  isCollapsed
                    ? "justify-center w-11 h-11 mx-auto"
                    : "gap-3.5 px-3.5 py-2.5",
                  active
                    ? "bg-cyan-500/10 text-cyan-700 dark:text-cyan-300 border border-cyan-500/30 font-semibold shadow-xs"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/60"
                )}
              >
                <Icon
                  className={cn(
                    "w-5 h-5 shrink-0 transition-colors",
                    active
                      ? "text-cyan-600 dark:text-cyan-400"
                      : "text-slate-400 dark:text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-300"
                  )}
                />
                {!isCollapsed && <span className="truncate">{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Bottom Expand Toggle (When Collapsed) */}
        {isCollapsed && onToggleCollapse && (
          <div className="p-3 border-t border-slate-200 dark:border-surface-borderDark flex justify-center">
            <button
              onClick={onToggleCollapse}
              className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus:outline-none"
              title="Expand sidebar"
              aria-label="Expand sidebar"
            >
              <PanelLeftOpen className="w-5 h-5" />
            </button>
          </div>
        )}
      </aside>
    </>
  );
}
