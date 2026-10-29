"use client";

import React, { useState, useEffect, useCallback, useId } from "react";
import Link from "next/link";
import {
  BarChart3,
  Calendar,
  Clock,
  ShieldCheck,
  AlertTriangle,
  Scale,
  Database,
  Layers,
  HelpCircle,
  FileCheck2,
  FileX2,
  Download,
  RefreshCw,
  FileText,
  Globe,
  Image as ImageIcon,
  Mic,
  Film,
  CheckCircle2,
  XCircle,
  TrendingUp,
  Info,
  ArrowUpRight,
  ExternalLink,
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  fetchAnalyticsOverview,
  fetchAnalyticsTimeline,
  fetchAnalyticsVerificationTypes,
  fetchAnalyticsVerdictDistribution,
  fetchAnalyticsSourceCoverage,
  getAnalyticsExportCsvUrl,
} from "@/lib/api";
import {
  AnalyticsOverviewResponse,
  AnalyticsTimelineResponse,
  AnalyticsVerificationTypesResponse,
  AnalyticsVerdictDistributionResponse,
  AnalyticsSourceCoverageResponse,
  TimelinePoint,
} from "@/types/api";

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<string>("30d");
  const [fromDate, setFromDate] = useState<string>("");
  const [toDate, setToDate] = useState<string>("");
  const [interval, setInterval] = useState<string>("day");
  const [activeVerdictTab, setActiveVerdictTab] = useState<"requests" | "claims">("requests");

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<AnalyticsOverviewResponse | null>(null);
  const [timeline, setTimeline] = useState<AnalyticsTimelineResponse | null>(null);
  const [modality, setModality] = useState<AnalyticsVerificationTypesResponse | null>(null);
  const [verdicts, setVerdicts] = useState<AnalyticsVerdictDistributionResponse | null>(null);
  const [coverage, setCoverage] = useState<AnalyticsSourceCoverageResponse | null>(null);

  const [hoveredPoint, setHoveredPoint] = useState<TimelinePoint | null>(null);

  const loadAllAnalytics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        dateRange: timeRange,
        fromDate: timeRange === "custom" && fromDate ? fromDate : undefined,
        toDate: timeRange === "custom" && toDate ? toDate : undefined,
        interval,
      };

      const [ov, tl, mod, vd, cov] = await Promise.all([
        fetchAnalyticsOverview(params),
        fetchAnalyticsTimeline(params),
        fetchAnalyticsVerificationTypes(params),
        fetchAnalyticsVerdictDistribution(params),
        fetchAnalyticsSourceCoverage(params),
      ]);

      setOverview(ov);
      setTimeline(tl);
      setModality(mod);
      setVerdicts(vd);
      setCoverage(cov);
    } catch (err: any) {
      setError(err?.message || "Failed to load database analytics metrics.");
    } finally {
      setLoading(false);
    }
  }, [timeRange, fromDate, toDate, interval]);

  useEffect(() => {
    loadAllAnalytics();
  }, [loadAllAnalytics]);

  // Helpers for icons and styles
  const getModalityColor = (type: string) => {
    switch (type.toLowerCase()) {
      case "text":
        return { bg: "bg-sky-500", text: "text-sky-500", border: "border-sky-500", hex: "#0ea5e9" };
      case "url":
        return { bg: "bg-emerald-500", text: "text-emerald-500", border: "border-emerald-500", hex: "#10b981" };
      case "image":
        return { bg: "bg-purple-500", text: "text-purple-500", border: "border-purple-500", hex: "#a855f7" };
      case "audio":
        return { bg: "bg-amber-500", text: "text-amber-500", border: "border-amber-500", hex: "#f59e0b" };
      case "video":
        return { bg: "bg-rose-500", text: "text-rose-500", border: "border-rose-500", hex: "#f43f5e" };
      default:
        return { bg: "bg-slate-500", text: "text-slate-500", border: "border-slate-500", hex: "#64748b" };
    }
  };

  const getVerdictBadge = (verdictStr: string) => {
    const v = (verdictStr || "").toUpperCase();
    if (v.includes("TRUE") || v.includes("SUPPORTED")) {
      return <Badge variant="emerald" size="sm">{v}</Badge>;
    }
    if (v.includes("FALSE") || v.includes("CONTRADICTED")) {
      return <Badge variant="rose" size="sm">{v}</Badge>;
    }
    if (v.includes("MISLEADING")) {
      return <Badge variant="amber" size="sm">{v}</Badge>;
    }
    if (v.includes("MIXED")) {
      return <Badge variant="indigo" size="sm">{v}</Badge>;
    }
    return <Badge variant="slate" size="sm">{v || "UNVERIFIED"}</Badge>;
  };

  const getModalityIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "text":
        return <FileText className="w-3.5 h-3.5" />;
      case "url":
        return <Globe className="w-3.5 h-3.5" />;
      case "image":
        return <ImageIcon className="w-3.5 h-3.5" />;
      case "audio":
        return <Mic className="w-3.5 h-3.5" />;
      case "video":
        return <Film className="w-3.5 h-3.5" />;
      default:
        return <FileText className="w-3.5 h-3.5" />;
    }
  };

  const exportCsvUrl = getAnalyticsExportCsvUrl({
    date_range: timeRange,
    from_date: timeRange === "custom" && fromDate ? fromDate : undefined,
    to_date: timeRange === "custom" && toDate ? toDate : undefined,
  });

  // Calculate timeline max for responsive SVG scaling
  const maxTimelineTotal = Math.max(
    1,
    ...(timeline?.data_points.map((p) => p.total) || [1])
  );

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-2 sm:px-4 pb-12">
      {/* Page Header */}
      <PageHeader
        title="Verification Analytics & Intelligence"
        description="Authentic operational metrics, temporal volume distributions, multimodal breakdowns, categorical verdict consensus, and external source corroboration transparency."
        badgeText="100% Real Database Metrics"
        badgeVariant="emerald"
        icon={BarChart3}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <a
              href={exportCsvUrl}
              download
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors shadow-sm"
              title="Download sanitized CSV export of verified investigations"
            >
              <Download className="w-3.5 h-3.5 text-emerald-500" />
              <span>Export CSV</span>
            </a>
            <Button
              onClick={loadAllAnalytics}
              disabled={loading}
              variant="outline"
              size="sm"
              className="gap-2"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-500" : ""}`} />
              <span>Refresh</span>
            </Button>
          </div>
        }
      />

      {/* Date Range & Interval Filter Toolbar */}
      <Card className="p-3.5 bg-slate-50/70 dark:bg-surface-cardDark/50 border border-slate-200 dark:border-surface-borderDark">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          {/* Preset Buttons */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-medium text-slate-500 dark:text-slate-400 mr-1 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              <span>Timeframe:</span>
            </span>
            {[
              { id: "7d", label: "7 Days" },
              { id: "30d", label: "30 Days" },
              { id: "90d", label: "90 Days" },
              { id: "all", label: "All Time" },
              { id: "custom", label: "Custom" },
            ].map((preset) => (
              <button
                key={preset.id}
                onClick={() => setTimeRange(preset.id)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                  timeRange === preset.id
                    ? "bg-cyan-500 text-white shadow-sm"
                    : "bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-surface-borderDark hover:bg-slate-100 dark:hover:bg-slate-800"
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>

          {/* Custom Date Pickers (Shown if Custom) & Interval Selector */}
          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            {timeRange === "custom" && (
              <div className="flex items-center gap-1.5 text-xs">
                <input
                  type="date"
                  value={fromDate}
                  onChange={(e) => setFromDate(e.target.value)}
                  className="px-2 py-1 rounded-lg border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs"
                />
                <span className="text-slate-400">to</span>
                <input
                  type="date"
                  value={toDate}
                  onChange={(e) => setToDate(e.target.value)}
                  className="px-2 py-1 rounded-lg border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs"
                />
              </div>
            )}

            <div className="flex items-center gap-1 text-xs">
              <span className="text-slate-400 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                <span>Interval:</span>
              </span>
              <select
                value={interval}
                onChange={(e) => setInterval(e.target.value)}
                className="px-2 py-1 rounded-lg border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs"
              >
                <option value="day">Daily</option>
                <option value="week">Weekly</option>
                <option value="month">Monthly</option>
              </select>
            </div>
          </div>
        </div>
      </Card>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-500" />
          <span>{error}</span>
        </div>
      )}

      {/* Overview KPI Cards */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
        {/* Card 1: Total Verifications */}
        <Card className="p-4 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span>Investigations</span>
            <ShieldCheck className="w-4 h-4 text-cyan-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900 dark:text-slate-100">
            {overview ? overview.total_requests.toLocaleString() : "--"}
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
            <span className="text-emerald-500 font-semibold">{overview?.completed_count || 0} completed</span>
            <span>•</span>
            <span className="text-rose-500">{overview?.failed_count || 0} failed</span>
          </div>
        </Card>

        {/* Card 2: Completion Rate */}
        <Card className="p-4 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span>Pipeline Success</span>
            <TrendingUp className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
            {overview ? `${overview.completion_rate.toFixed(1)}%` : "--"}
          </div>
          {/* Progress bar */}
          <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className="bg-emerald-500 h-1.5 rounded-full transition-all duration-500"
              style={{ width: `${Math.min(100, overview?.completion_rate || 0)}%` }}
            />
          </div>
        </Card>

        {/* Card 3: Evidence Confidence */}
        <Card className="p-4 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span>Avg Evidence Conf.</span>
            <Scale className="w-4 h-4 text-indigo-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-indigo-600 dark:text-indigo-400">
            {overview?.average_confidence_percentage !== null && overview?.average_confidence_percentage !== undefined
              ? `${overview.average_confidence_percentage.toFixed(1)}%`
              : "--"}
          </div>
          <div className="text-[10px] text-slate-400 mt-1 truncate" title="Measures evidence certainty, not truth probability">
            Evidence certainty index
          </div>
        </Card>

        {/* Card 4: Atomic Claims */}
        <Card className="p-4 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span>Claims Decomposed</span>
            <Layers className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-purple-600 dark:text-purple-400">
            {overview ? overview.total_claims.toLocaleString() : "--"}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {overview && overview.total_requests > 0
              ? `${(overview.total_claims / overview.total_requests).toFixed(1)} claims/req`
              : "0 claims/req"}
          </div>
        </Card>

        {/* Card 5: Sources Discovered */}
        <Card className="p-4 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span>Corroboration Sources</span>
            <Database className="w-4 h-4 text-amber-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-600 dark:text-amber-400">
            {overview ? overview.total_sources.toLocaleString() : "--"}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {overview ? `${overview.total_evidence_items} passages` : "0 passages"}
          </div>
        </Card>

        {/* Card 6: PDF Reports */}
        <Card className="p-4 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark">
          <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 mb-1">
            <span>Reports Generated</span>
            <FileCheck2 className="w-4 h-4 text-teal-500" />
          </div>
          <div className="text-2xl font-bold font-mono text-teal-600 dark:text-teal-400">
            {overview ? overview.reports_generated.toLocaleString() : "--"}
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            <span className="text-teal-500 font-semibold">{overview?.reports_generated || 0} active</span>
            {overview && overview.reports_failed > 0 && (
              <span className="text-rose-500 ml-1">({overview.reports_failed} failed)</span>
            )}
          </div>
        </Card>
      </section>

      {/* Main Grid: Timeline & Modality Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Verification Volume Timeline (SVG Chart) */}
        <Card className="lg:col-span-2 p-5 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 mb-4">
            <div>
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <span>Verification Volume Trajectory</span>
                <Badge variant="cyan" size="sm">{interval.toUpperCase()}</Badge>
              </CardTitle>
              <CardDescription className="text-xs">
                Contiguous time-series of verification requests across input modalities.
              </CardDescription>
            </div>
            {hoveredPoint && (
              <div className="text-xs bg-slate-100 dark:bg-slate-800 px-2.5 py-1 rounded-lg border border-slate-200 dark:border-surface-borderDark text-slate-700 dark:text-slate-200">
                <span className="font-semibold">{hoveredPoint.date}: </span>
                <span className="text-cyan-500 font-bold">{hoveredPoint.total} total</span>
                {hoveredPoint.avg_confidence !== null && (
                  <span className="text-slate-400 ml-1.5">({(hoveredPoint.avg_confidence * 100).toFixed(0)}% conf)</span>
                )}
              </div>
            )}
          </div>

          {/* SVG Contiguous Bar Chart */}
          {timeline && timeline.data_points.length > 0 ? (
            <div className="space-y-4">
              <div className="h-56 w-full flex items-end gap-1 sm:gap-2 pt-6 px-2 border-b border-slate-200 dark:border-surface-borderDark/60 relative">
                {/* Horizontal reference lines */}
                <div className="absolute inset-x-0 top-6 border-b border-dashed border-slate-100 dark:border-slate-800 pointer-events-none" />
                <div className="absolute inset-x-0 top-1/2 border-b border-dashed border-slate-100 dark:border-slate-800 pointer-events-none" />

                {timeline.data_points.map((point, idx) => {
                  const heightPercent = Math.max(4, Math.round((point.total / maxTimelineTotal) * 100));

                  // Modality breakdown segments
                  const textPct = point.total > 0 ? (point.text / point.total) * 100 : 0;
                  const urlPct = point.total > 0 ? (point.url / point.total) * 100 : 0;
                  const imgPct = point.total > 0 ? (point.image / point.total) * 100 : 0;
                  const audPct = point.total > 0 ? (point.audio / point.total) * 100 : 0;
                  const vidPct = point.total > 0 ? (point.video / point.total) * 100 : 0;

                  return (
                    <div
                      key={point.date}
                      onMouseEnter={() => setHoveredPoint(point)}
                      onMouseLeave={() => setHoveredPoint(null)}
                      className="flex-1 flex flex-col items-center h-full justify-end group cursor-pointer"
                    >
                      {/* Bar Container */}
                      <div
                        className="w-full max-w-[28px] rounded-t-md overflow-hidden flex flex-col justify-end transition-all duration-200 group-hover:brightness-110 shadow-sm"
                        style={{ height: `${heightPercent}%` }}
                      >
                        {point.total === 0 ? (
                          <div className="w-full h-full bg-slate-200/50 dark:bg-slate-800/40 rounded-t-sm" />
                        ) : (
                          <>
                            {vidPct > 0 && <div style={{ height: `${vidPct}%` }} className="bg-rose-500 w-full" />}
                            {audPct > 0 && <div style={{ height: `${audPct}%` }} className="bg-amber-500 w-full" />}
                            {imgPct > 0 && <div style={{ height: `${imgPct}%` }} className="bg-purple-500 w-full" />}
                            {urlPct > 0 && <div style={{ height: `${urlPct}%` }} className="bg-emerald-500 w-full" />}
                            {textPct > 0 && <div style={{ height: `${textPct}%` }} className="bg-sky-500 w-full" />}
                          </>
                        )}
                      </div>

                      {/* Date label at bottom */}
                      <span className="text-[10px] text-slate-400 mt-2 rotate-45 sm:rotate-0 origin-left truncate w-full text-center">
                        {point.date.slice(5)}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Chart Legend */}
              <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-slate-500 dark:text-slate-400 pt-2">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
                  <span>Text</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                  <span>URL Article</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
                  <span>Image / OCR</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  <span>Audio</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                  <span>Video</span>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-56 flex items-center justify-center text-xs text-slate-400 font-mono border border-dashed border-slate-200 dark:border-surface-borderDark rounded-xl">
              No timeline data in active range.
            </div>
          )}
        </Card>

        {/* Modality Breakdown */}
        <Card className="p-5 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark flex flex-col justify-between">
          <div>
            <CardTitle className="text-base font-bold mb-1">Modality Distribution</CardTitle>
            <CardDescription className="text-xs mb-4">
              Breakdown of requests across text, articles, images, and audio/video media.
            </CardDescription>

            {/* Segmented Progress Bar */}
            <div className="w-full h-3 rounded-full overflow-hidden flex bg-slate-100 dark:bg-slate-800 mb-6">
              {modality?.breakdown.map((item) => {
                const color = getModalityColor(item.type);
                if (item.percentage <= 0) return null;
                return (
                  <div
                    key={item.type}
                    style={{ width: `${item.percentage}%` }}
                    className={`${color.bg} h-full transition-all`}
                    title={`${item.type.toUpperCase()}: ${item.count} (${item.percentage}%)`}
                  />
                );
              })}
            </div>

            {/* Modality Items Table */}
            <div className="space-y-3">
              {modality?.breakdown.map((item) => {
                const color = getModalityColor(item.type);
                return (
                  <div
                    key={item.type}
                    className="flex items-center justify-between text-xs p-2 rounded-lg bg-slate-50/70 dark:bg-surface-cardDark/50 border border-slate-100 dark:border-surface-borderDark"
                  >
                    <div className="flex items-center gap-2">
                      <span className={`p-1.5 rounded-md ${color.bg}/10 ${color.text}`}>
                        {getModalityIcon(item.type)}
                      </span>
                      <span className="font-semibold capitalize text-slate-800 dark:text-slate-200">
                        {item.type}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 font-mono">
                      <span className="font-bold text-slate-900 dark:text-slate-100">{item.count}</span>
                      <span className="text-slate-400 w-12 text-right">{item.percentage.toFixed(1)}%</span>
                      {item.avg_confidence !== null && (
                        <span className="text-[11px] text-cyan-500 w-12 text-right">
                          {(item.avg_confidence * 100).toFixed(0)}% cf
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-100 dark:border-surface-borderDark text-[11px] text-slate-400 flex items-center justify-between">
            <span>Total Investigated Modalities</span>
            <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
              {modality?.total_requests || 0}
            </span>
          </div>
        </Card>
      </div>

      {/* Categorical Verdict Distribution (Strictly Segregated Request vs Claim) */}
      <Card className="p-5 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark space-y-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <span>Categorical Verdict Distribution</span>
              <Badge variant="cyan" size="sm">Strict Separation</Badge>
            </CardTitle>
            <CardDescription className="text-xs">
              Decomposed verdicts for overall requests versus atomic decomposed claims.
            </CardDescription>
          </div>

          {/* Tab Selector */}
          <div className="inline-flex rounded-xl p-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-surface-borderDark text-xs">
            <button
              onClick={() => setActiveVerdictTab("requests")}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                activeVerdictTab === "requests"
                  ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm"
                  : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              }`}
            >
              Request-Level Verdicts ({verdicts?.total_evaluated_requests || 0})
            </button>
            <button
              onClick={() => setActiveVerdictTab("claims")}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                activeVerdictTab === "claims"
                  ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm"
                  : "text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
              }`}
            >
              Claim-Level Verdicts ({verdicts?.total_evaluated_claims || 0})
            </button>
          </div>
        </div>

        {/* Verdict Cards Matrix */}
        {verdicts && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {(activeVerdictTab === "requests" ? verdicts.request_verdicts : verdicts.claim_verdicts).map((item) => {
              return (
                <div
                  key={item.verdict}
                  className="p-3.5 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50/50 dark:bg-surface-cardDark/40 flex flex-col justify-between"
                >
                  <div className="mb-2">
                    {getVerdictBadge(item.verdict)}
                  </div>
                  <div>
                    <div className="text-xl font-bold font-mono text-slate-900 dark:text-slate-100">
                      {item.count}
                    </div>
                    <div className="text-xs text-slate-400 font-mono mt-0.5">
                      {item.percentage.toFixed(1)}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Methodological Disclaimer Alert Box */}
        <div className="p-3.5 rounded-xl border border-cyan-500/30 bg-cyan-500/5 text-slate-600 dark:text-slate-300 text-xs flex items-start gap-2.5">
          <Info className="w-4 h-4 text-cyan-500 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-slate-800 dark:text-slate-200">
              Methodological Corpus Notice:
            </span>
            <p className="text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
              {verdicts?.methodological_note ||
                "The proportion of supported or contradicted claims reflects the specific corpus of queries submitted by users to TruthLens AI and should not be interpreted as a general measure of misinformation prevalence in the broader information ecosystem."}
            </p>
          </div>
        </div>
      </Card>

      {/* Source Coverage & Corroboration Transparency */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Discovered Domains */}
        <Card className="p-5 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark">
          <div className="flex items-center justify-between mb-4">
            <div>
              <CardTitle className="text-base font-bold flex items-center gap-2">
                <span>Top Discovered Domains</span>
                <Badge variant="cyan" size="sm">{coverage?.unique_domains_count || 0} Domains</Badge>
              </CardTitle>
              <CardDescription className="text-xs">
                External publishers and news outlets discovered during multi-source web discovery.
              </CardDescription>
            </div>
            {coverage && (
              <Badge variant="emerald" size="sm" className="gap-1">
                <CheckCircle2 className="w-3 h-3" />
                <span>{coverage.primary_source_percentage.toFixed(1)}% Primary</span>
              </Badge>
            )}
          </div>

          {coverage && coverage.top_domains.length > 0 ? (
            <div className="space-y-2">
              {coverage.top_domains.slice(0, 7).map((d, i) => (
                <div
                  key={d.domain}
                  className="flex items-center justify-between p-2 rounded-lg bg-slate-50/70 dark:bg-surface-cardDark/50 border border-slate-100 dark:border-surface-borderDark text-xs"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-slate-400 w-4">#{i + 1}</span>
                    <Globe className="w-3.5 h-3.5 text-cyan-500" />
                    <span className="font-semibold text-slate-800 dark:text-slate-200">{d.domain}</span>
                    {d.source_type && (
                      <span className="text-[10px] text-slate-400 uppercase font-mono">({d.source_type})</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-900 dark:text-slate-100">
                      {d.sources_count} sources
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400 font-mono border border-dashed border-slate-200 dark:border-surface-borderDark rounded-xl">
              No discovered sources in active range.
            </div>
          )}
        </Card>

        {/* Evidence Direction & Corroboration Synthesis */}
        <Card className="p-5 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark flex flex-col justify-between">
          <div>
            <CardTitle className="text-base font-bold mb-1">Evidence Stance Consensus</CardTitle>
            <CardDescription className="text-xs mb-4">
              Distribution of factual evidence passages retrieved across all claims.
            </CardDescription>

            {coverage && (
              <div className="space-y-3">
                {/* Supporting */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" /> Supporting Evidence
                    </span>
                    <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                      {coverage.evidence_direction_distribution["SUPPORTING"] || 0} passages
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-emerald-500 h-2 rounded-full"
                      style={{
                        width: `${
                          coverage.total_evidence_passages > 0
                            ? ((coverage.evidence_direction_distribution["SUPPORTING"] || 0) /
                                coverage.total_evidence_passages) *
                              100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </div>

                {/* Contradicting */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-medium text-rose-600 dark:text-rose-400 flex items-center gap-1">
                      <XCircle className="w-3.5 h-3.5" /> Contradicting Evidence
                    </span>
                    <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                      {coverage.evidence_direction_distribution["CONTRADICTING"] || 0} passages
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-rose-500 h-2 rounded-full"
                      style={{
                        width: `${
                          coverage.total_evidence_passages > 0
                            ? ((coverage.evidence_direction_distribution["CONTRADICTING"] || 0) /
                                coverage.total_evidence_passages) *
                              100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </div>

                {/* Contextual */}
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="font-medium text-purple-600 dark:text-purple-400 flex items-center gap-1">
                      <Info className="w-3.5 h-3.5" /> Contextual Evidence
                    </span>
                    <span className="font-mono font-bold text-slate-700 dark:text-slate-300">
                      {coverage.evidence_direction_distribution["CONTEXTUAL"] || 0} passages
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-purple-500 h-2 rounded-full"
                      style={{
                        width: `${
                          coverage.total_evidence_passages > 0
                            ? ((coverage.evidence_direction_distribution["CONTEXTUAL"] || 0) /
                                coverage.total_evidence_passages) *
                              100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Metrics summary */}
          <div className="mt-5 pt-3 border-t border-slate-100 dark:border-surface-borderDark grid grid-cols-2 gap-2 text-center text-xs">
            <div className="p-2 rounded-lg bg-slate-50 dark:bg-surface-cardDark/50">
              <div className="text-slate-400 text-[10px]">Avg Sources/Claim</div>
              <div className="font-mono font-bold text-slate-800 dark:text-slate-200">
                {coverage?.avg_sources_per_claim || 0}
              </div>
            </div>
            <div className="p-2 rounded-lg bg-slate-50 dark:bg-surface-cardDark/50">
              <div className="text-slate-400 text-[10px]">Avg Passages/Claim</div>
              <div className="font-mono font-bold text-slate-800 dark:text-slate-200">
                {coverage?.avg_evidence_per_claim || 0}
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Recent Operational Activity Feed */}
      <Card className="p-5 bg-white dark:bg-surface-cardDark border border-slate-200 dark:border-surface-borderDark">
        <div className="flex items-center justify-between mb-4">
          <div>
            <CardTitle className="text-base font-bold">Recent Verification Pipeline Activity</CardTitle>
            <CardDescription className="text-xs">
              Latest investigations processed across the verification engine.
            </CardDescription>
          </div>
          <Link
            href="/history"
            className="text-xs text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 font-semibold"
          >
            <span>View Full History</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {overview && overview.recent_activity.length > 0 ? (
          <div className="space-y-2">
            {overview.recent_activity.map((act) => {
              const color = getModalityColor(act.request_type);
              return (
                <div
                  key={act.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl border border-slate-200 dark:border-surface-borderDark/60 bg-slate-50/50 dark:bg-surface-cardDark/30 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono font-semibold text-xs text-slate-700 dark:text-slate-300">
                      REQ-{act.id.toString().padStart(6, "0")}
                    </span>
                    <Badge variant="outline" size="sm" className="gap-1 capitalize">
                      {getModalityIcon(act.request_type)}
                      <span>{act.request_type}</span>
                    </Badge>
                    <Badge
                      variant={
                        act.status === "completed"
                          ? "emerald"
                          : act.status === "failed"
                          ? "rose"
                          : "amber"
                      }
                      size="sm"
                    >
                      {act.status}
                    </Badge>
                  </div>

                  <div className="flex items-center gap-3 text-xs">
                    {act.verdict && getVerdictBadge(act.verdict)}
                    {act.confidence_percentage !== null && act.confidence_percentage !== undefined && (
                      <span className="font-mono text-cyan-600 dark:text-cyan-400 font-semibold">
                        {act.confidence_percentage.toFixed(0)}% conf
                      </span>
                    )}
                    <span className="text-slate-400 text-[11px]">
                      {act.created_at ? new Date(act.created_at).toLocaleDateString() : ""}
                    </span>
                    <Link
                      href={`/history/${act.id}`}
                      className="p-1 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-slate-400 font-mono border border-dashed border-slate-200 dark:border-surface-borderDark rounded-xl">
            No recent verification activity in active range.
          </div>
        )}
      </Card>
    </div>
  );
}
