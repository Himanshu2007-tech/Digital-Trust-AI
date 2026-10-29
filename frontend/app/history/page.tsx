"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  History,
  RefreshCw,
  Search,
  Filter,
  FileText,
  Globe,
  Image as ImageIcon,
  Mic,
  Film,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Archive,
  ArchiveRestore,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  GitBranch,
  ArrowUpDown,
  Sparkles,
  Download,
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  fetchVerificationHistory,
  reverifyInvestigation,
  toggleArchiveInvestigation,
  getHistoryExportCsvUrl,
} from "@/lib/api";
import { HistoryItem } from "@/types/api";
import { formatDate } from "@/lib/utils";

export default function HistoryPage() {
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Sorting state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [selectedType, setSelectedType] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [selectedVerdict, setSelectedVerdict] = useState("all");
  const [sourceDomain, setSourceDomain] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState<"desc" | "asc">("desc");
  const [isArchived, setIsArchived] = useState(false);

  // Action states
  const [actionMessage, setActionMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [reverifyingId, setReverifyingId] = useState<number | null>(null);
  const [archivingId, setArchivingId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchVerificationHistory({
        page,
        pageSize,
        query: searchQuery || undefined,
        requestType: selectedType !== "all" ? selectedType : undefined,
        status: selectedStatus !== "all" ? selectedStatus : undefined,
        verdict: selectedVerdict !== "all" ? selectedVerdict : undefined,
        sourceDomain: sourceDomain.trim() || undefined,
        isArchived,
        sortBy,
        sortOrder,
      });

      setItems(res.items || []);
      setTotalCount(res.total_count || 0);
      setTotalPages(res.total_pages || 1);
      setHasNext(res.has_next || false);
      setHasPrevious(res.has_previous || false);
    } catch (err: any) {
      setError(err?.message || "Failed to load verification history records.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchQuery, selectedType, selectedStatus, selectedVerdict, sourceDomain, isArchived, sortBy, sortOrder]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Handle Search submit
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearchQuery(searchInput.trim());
  };

  const handleClearSearch = () => {
    setSearchInput("");
    setSearchQuery("");
    setPage(1);
  };

  // Re-verify handler
  const handleReverify = async (requestId: number) => {
    if (reverifyingId !== null) return;
    setReverifyingId(requestId);
    setActionMessage(null);
    try {
      const res = await reverifyInvestigation(requestId);
      setActionMessage({
        type: "success",
        text: `Re-verification initiated for #${requestId}! Linked child investigation #${res.new_request_id} created.`,
      });
      loadData();
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: `Re-verification failed for #${requestId}: ${err?.message || "Unknown error"}`,
      });
    } finally {
      setReverifyingId(null);
    }
  };

  // Archive toggle handler
  const handleToggleArchive = async (requestId: number, currentArchived: boolean) => {
    if (archivingId !== null) return;
    setArchivingId(requestId);
    setActionMessage(null);
    try {
      const nextArchive = !currentArchived;
      await toggleArchiveInvestigation(requestId, nextArchive);
      setActionMessage({
        type: "success",
        text: `Investigation #${requestId} ${nextArchive ? "archived" : "unarchived"} successfully.`,
      });
      loadData();
    } catch (err: any) {
      setActionMessage({
        type: "error",
        text: `Archive update failed for #${requestId}: ${err?.message || "Unknown error"}`,
      });
    } finally {
      setArchivingId(null);
    }
  };

  // Type Icon helper
  const getTypeIcon = (type: string) => {
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

  // Verdict Badge helper
  const getVerdictBadge = (verdict?: string | null) => {
    if (!verdict) {
      return (
        <Badge variant="slate" size="sm">
          PENDING
        </Badge>
      );
    }
    const norm = verdict.toUpperCase();
    if (norm === "SUPPORTED" || norm === "TRUE") {
      return (
        <Badge variant="emerald" size="sm" className="gap-1">
          <CheckCircle2 className="w-3 h-3" />
          <span>SUPPORTED</span>
        </Badge>
      );
    }
    if (norm === "CONTRADICTED" || norm === "FALSE") {
      return (
        <Badge variant="rose" size="sm" className="gap-1">
          <XCircle className="w-3 h-3" />
          <span>CONTRADICTED</span>
        </Badge>
      );
    }
    if (norm === "MISLEADING") {
      return (
        <Badge variant="amber" size="sm" className="gap-1">
          <AlertTriangle className="w-3 h-3" />
          <span>MISLEADING</span>
        </Badge>
      );
    }
    return (
      <Badge variant="slate" size="sm" className="gap-1">
        <HelpCircle className="w-3 h-3" />
        <span>{norm}</span>
      </Badge>
    );
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-2 sm:px-4">
      <PageHeader
        title="Verification Investigation History"
        description="Persistent repository of multimedia, text, and article investigations with cryptographic audit trails, claim evidence, and re-verification lifecycle management."
        badgeText={`${totalCount} Total Records`}
        badgeVariant="cyan"
        icon={History}
        actions={
          <div className="flex items-center gap-2">
            <a
              href={getHistoryExportCsvUrl({
                query: searchQuery || undefined,
                request_type: selectedType !== "all" ? selectedType : undefined,
                status: selectedStatus !== "all" ? selectedStatus : undefined,
                verdict: selectedVerdict !== "all" ? selectedVerdict : undefined,
                source_domain: sourceDomain.trim() || undefined,
              })}
              download
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs font-semibold hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors shadow-sm"
              title="Download filtered investigation records as sanitized CSV"
            >
              <Download className="w-3.5 h-3.5 text-emerald-500" />
              <span>Export CSV</span>
            </a>
            <Button
              onClick={() => {
                setPage(1);
                loadData();
              }}
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

      {/* Action Notification Toast/Banner */}
      {actionMessage && (
        <div
          className={`p-3.5 rounded-xl border text-xs font-medium flex items-center justify-between transition-all ${
            actionMessage.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : "bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {actionMessage.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
            )}
            <span>{actionMessage.text}</span>
          </div>
          <button
            onClick={() => setActionMessage(null)}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs px-2"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Toolbar: Search, Filters, and Archive Switch */}
      <Card className="p-4 space-y-4 bg-slate-50/60 dark:bg-surface-cardDark/50 border border-slate-200 dark:border-surface-borderDark">
        {/* Top bar: Archive Toggle & Search */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3">
          {/* Active vs Archived Toggle */}
          <div className="inline-flex rounded-xl p-1 bg-slate-200/70 dark:bg-slate-800 border border-slate-300/60 dark:border-surface-borderDark self-start">
            <button
              onClick={() => {
                setIsArchived(false);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                !isArchived
                  ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
              }`}
            >
              Active Investigations
            </button>
            <button
              onClick={() => {
                setIsArchived(true);
                setPage(1);
              }}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 ${
                isArchived
                  ? "bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 shadow-sm"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200"
              }`}
            >
              <Archive className="w-3.5 h-3.5" />
              <span>Archived</span>
            </button>
          </div>

          {/* Search Form */}
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 max-w-md">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Search by ID, keyword, claim, or URL..."
                className="w-full pl-9 pr-8 py-2 text-xs rounded-xl border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
              />
              {searchInput && (
                <button
                  type="button"
                  onClick={handleClearSearch}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
                >
                  ✕
                </button>
              )}
            </div>
            <Button type="submit" size="sm" variant="secondary" className="text-xs">
              Search
            </Button>
          </form>
        </div>

        {/* Filters row */}
        <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-200 dark:border-surface-borderDark/60 text-xs">
          <div className="flex items-center gap-1 text-slate-500 dark:text-slate-400 mr-2 font-medium">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          {/* Type filter */}
          <select
            value={selectedType}
            onChange={(e) => {
              setSelectedType(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs focus:ring-1 focus:ring-cyan-500"
          >
            <option value="all">All Formats</option>
            <option value="text">Text Claims</option>
            <option value="url">News Articles (URL)</option>
            <option value="image">Images / OCR</option>
            <option value="audio">Audio</option>
            <option value="video">Video & Multimedia</option>
          </select>

          {/* Status filter */}
          <select
            value={selectedStatus}
            onChange={(e) => {
              setSelectedStatus(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs focus:ring-1 focus:ring-cyan-500"
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="partial">Partial</option>
            <option value="failed">Failed</option>
          </select>

          {/* Verdict filter */}
          <select
            value={selectedVerdict}
            onChange={(e) => {
              setSelectedVerdict(e.target.value);
              setPage(1);
            }}
            className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs focus:ring-1 focus:ring-cyan-500"
          >
            <option value="all">All Verdicts</option>
            <option value="SUPPORTED">Supported</option>
            <option value="CONTRADICTED">Contradicted</option>
            <option value="MISLEADING">Misleading</option>
            <option value="UNVERIFIED">Unverified</option>
          </select>

          {/* Source Domain filter */}
          <input
            type="text"
            value={sourceDomain}
            onChange={(e) => {
              setSourceDomain(e.target.value);
              setPage(1);
            }}
            placeholder="Filter domain (e.g. reuters.com)..."
            className="px-2.5 py-1.5 w-48 rounded-lg border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs placeholder-slate-400 focus:ring-1 focus:ring-cyan-500"
          />

          {/* Sort selector */}
          <div className="ml-auto flex items-center gap-2">
            <span className="text-slate-400 flex items-center gap-1">
              <ArrowUpDown className="w-3 h-3" />
              <span>Sort:</span>
            </span>
            <select
              value={`${sortBy}_${sortOrder}`}
              onChange={(e) => {
                const [sb, so] = e.target.value.split("_");
                setSortBy(sb);
                setSortOrder(so as "asc" | "desc");
                setPage(1);
              }}
              className="px-2.5 py-1.5 rounded-lg border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 text-xs focus:ring-1 focus:ring-cyan-500"
            >
              <option value="created_at_desc">Date: Newest First</option>
              <option value="created_at_asc">Date: Oldest First</option>
              <option value="confidence_desc">Confidence: Highest</option>
              <option value="confidence_asc">Confidence: Lowest</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Main Content Area */}
      {loading ? (
        <div className="p-20 text-center text-xs text-slate-400 font-mono flex flex-col items-center justify-center gap-3">
          <RefreshCw className="w-6 h-6 animate-spin text-cyan-500" />
          <span>Loading verified investigations from database...</span>
        </div>
      ) : error ? (
        <Card className="p-8 text-center text-rose-500 space-y-3">
          <AlertTriangle className="w-8 h-8 mx-auto" />
          <p className="font-semibold">{error}</p>
          <Button onClick={loadData} variant="outline" size="sm">
            Retry Connection
          </Button>
        </Card>
      ) : items.length > 0 ? (
        <div className="space-y-4">
          {/* Table View */}
          <div className="rounded-2xl border border-slate-200 dark:border-surface-borderDark overflow-hidden bg-white dark:bg-surface-cardDark shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-100 dark:border-surface-borderDark bg-slate-50/70 dark:bg-slate-800/50 font-semibold text-slate-500 dark:text-slate-400">
                    <th className="py-3 px-4">Investigation</th>
                    <th className="py-3 px-3">Format</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3">Verdict & Confidence</th>
                    <th className="py-3 px-3">Claims</th>
                    <th className="py-3 px-3">Date</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-surface-borderDark/60">
                  {items.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors group"
                    >
                      {/* ID & Preview */}
                      <td className="py-3.5 px-4 max-w-xs sm:max-w-md">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <Link
                              href={`/history/${item.id}`}
                              className="font-mono font-bold text-cyan-600 dark:text-cyan-400 hover:underline"
                            >
                              #{item.id}
                            </Link>
                            {item.parent_request_id && (
                              <Badge variant="purple" size="sm" className="gap-1 font-mono text-[10px]">
                                <GitBranch className="w-2.5 h-2.5" />
                                <span>Re-verif of #{item.parent_request_id}</span>
                              </Badge>
                            )}
                            {item.is_archived && (
                              <Badge variant="slate" size="sm" className="font-mono text-[10px]">
                                Archived
                              </Badge>
                            )}
                          </div>
                          <p className="text-slate-800 dark:text-slate-200 line-clamp-2 leading-relaxed">
                            {item.content_preview || "No content summary recorded."}
                          </p>
                        </div>
                      </td>

                      {/* Format Type */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        <Badge variant="cyan" size="sm" className="gap-1 capitalize">
                          {getTypeIcon(item.request_type)}
                          <span>{item.request_type}</span>
                        </Badge>
                      </td>

                      {/* Status */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        <Badge
                          variant={
                            item.status === "completed"
                              ? "emerald"
                              : item.status === "processing"
                              ? "amber"
                              : item.status === "failed"
                              ? "rose"
                              : "slate"
                          }
                          size="sm"
                        >
                          {item.status.toUpperCase()}
                        </Badge>
                      </td>

                      {/* Verdict & Confidence */}
                      <td className="py-3.5 px-3 whitespace-nowrap">
                        <div className="space-y-1.5">
                          <div>{getVerdictBadge(item.verdict)}</div>
                          {item.confidence_percentage !== null && item.confidence_percentage !== undefined && (
                            <div className="flex items-center gap-2">
                              <div className="w-16 h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-cyan-500 rounded-full"
                                  style={{ width: `${item.confidence_percentage}%` }}
                                />
                              </div>
                              <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400">
                                {item.confidence_percentage}%
                              </span>
                            </div>
                          )}
                        </div>
                      </td>

                      {/* Claims count */}
                      <td className="py-3.5 px-3 whitespace-nowrap font-mono text-slate-600 dark:text-slate-300">
                        <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                          {item.claims_count} {item.claims_count === 1 ? "claim" : "claims"}
                        </span>
                      </td>

                      {/* Timestamp */}
                      <td className="py-3.5 px-3 whitespace-nowrap text-slate-500 dark:text-slate-400 text-[11px]">
                        <div>{formatDate(item.created_at)}</div>
                      </td>

                      {/* Action buttons */}
                      <td className="py-3.5 px-4 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <Link href={`/history/${item.id}`}>
                            <Button size="xs" variant="outline" className="gap-1">
                              <span>Dossier</span>
                              <ExternalLink className="w-3 h-3" />
                            </Button>
                          </Link>

                          {/* Re-verify action */}
                          <Button
                            size="xs"
                            variant="secondary"
                            onClick={() => handleReverify(item.id)}
                            disabled={reverifyingId === item.id}
                            title="Re-verify original input with fresh live search"
                            className="gap-1"
                          >
                            <RefreshCw
                              className={`w-3 h-3 ${reverifyingId === item.id ? "animate-spin text-cyan-500" : ""}`}
                            />
                            <span className="hidden sm:inline">Re-verify</span>
                          </Button>

                          {/* Archive/Unarchive action */}
                          <Button
                            size="xs"
                            variant="ghost"
                            onClick={() => handleToggleArchive(item.id, item.is_archived)}
                            disabled={archivingId === item.id}
                            title={item.is_archived ? "Restore to active" : "Move to archive"}
                          >
                            {item.is_archived ? (
                              <ArchiveRestore className="w-3.5 h-3.5 text-slate-500 hover:text-cyan-500" />
                            ) : (
                              <Archive className="w-3.5 h-3.5 text-slate-400 hover:text-rose-500" />
                            )}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Pagination Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-2 py-3 text-xs text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-2">
              <span>
                Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, totalCount)} of {totalCount} records
              </span>
              <span className="text-slate-300 dark:text-slate-700">|</span>
              <div className="flex items-center gap-1">
                <span>Per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value));
                    setPage(1);
                  }}
                  className="px-2 py-1 rounded border border-slate-300 dark:border-surface-borderDark bg-white dark:bg-slate-900 text-xs"
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                disabled={!hasPrevious || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="gap-1 text-xs"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Previous</span>
              </Button>
              <span className="font-mono px-2 font-medium text-slate-700 dark:text-slate-300">
                Page {page} of {totalPages}
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={!hasNext || loading}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="gap-1 text-xs"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>
      ) : (
        <EmptyState
          icon={isArchived ? Archive : History}
          badgeText={isArchived ? "Archived Investigations" : "Active Investigations"}
          badgeVariant="cyan"
          title={isArchived ? "No archived investigations" : "No investigations match your filters"}
          description={
            isArchived
              ? "You do not have any archived investigations. Investigations you archive in the history view will be stored here."
              : searchQuery || selectedType !== "all" || selectedStatus !== "all" || selectedVerdict !== "all"
              ? "No records found matching your active filter criteria. Try clearing search filters or resetting options."
              : "No verification investigations have been run yet. Submit a factual text claim, news URL, screenshot, audio recording, or video to start."
          }
          actionLabel={searchQuery || selectedType !== "all" ? "Reset Filters" : "Verify a Claim"}
          onAction={() => {
            if (searchQuery || selectedType !== "all" || selectedStatus !== "all" || selectedVerdict !== "all") {
              setSearchInput("");
              setSearchQuery("");
              setSelectedType("all");
              setSelectedStatus("all");
              setSelectedVerdict("all");
              setPage(1);
            } else {
              window.location.assign("/verify-text");
            }
          }}
        />
      )}
    </div>
  );
}
