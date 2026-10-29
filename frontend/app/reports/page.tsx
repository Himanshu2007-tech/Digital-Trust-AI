"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  FileCheck,
  RefreshCw,
  Download,
  Eye,
  FileText,
  FileCode,
  CheckCircle2,
  Calendar,
  Trash2,
  ShieldCheck,
  Hash,
  ExternalLink,
  Plus,
  Search,
  AlertCircle,
  Clock,
  Sparkles,
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { fetchReports, generateReport, deleteReport, getReportDownloadUrl } from "@/lib/api";
import { ReportItem } from "@/types/api";
import { formatDate, sanitizeHref } from "@/lib/utils";

function formatBytes(bytes?: number | null): string {
  if (!bytes || bytes <= 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [requestIdFilter, setRequestIdFilter] = useState<string>("");

  // Quick generation modal / panel state
  const [isGenerateOpen, setIsGenerateOpen] = useState(false);
  const [inputRequestId, setInputRequestId] = useState("");
  const [inputTitle, setInputTitle] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);
  const [notification, setNotification] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadReports = useCallback(async () => {
    setLoading(true);
    try {
      const parsedReqId = requestIdFilter.trim() ? parseInt(requestIdFilter.trim(), 10) : undefined;
      const res = await fetchReports({
        request_id: isNaN(parsedReqId as number) ? undefined : parsedReqId,
        status: statusFilter || undefined,
        page,
        page_size: 15,
      });
      setReports(res.items);
      setTotalPages(res.total_pages);
      setTotalCount(res.total_count);
    } catch {
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, requestIdFilter]);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    const reqId = parseInt(inputRequestId.trim(), 10);
    if (isNaN(reqId) || reqId <= 0) {
      setGenError("Please enter a valid numeric Verification Request ID.");
      return;
    }

    setGenerating(true);
    setGenError(null);
    try {
      const newRep = await generateReport(reqId, inputTitle.trim() || undefined);
      setNotification({
        type: "success",
        text: `Report #${newRep.id} successfully generated (${formatBytes(newRep.file_size_bytes)})!`,
      });
      setIsGenerateOpen(false);
      setInputRequestId("");
      setInputTitle("");
      loadReports();
    } catch (err: any) {
      setGenError(err?.message || "Failed to generate report.");
    } finally {
      setGenerating(false);
    }
  };

  const handleDelete = async (reportId: number) => {
    if (!window.confirm(`Are you sure you want to permanently delete Report #${reportId}?`)) {
      return;
    }
    const ok = await deleteReport(reportId);
    if (ok) {
      setNotification({
        type: "success",
        text: `Report #${reportId} deleted successfully.`,
      });
      loadReports();
    } else {
      setNotification({
        type: "error",
        text: `Could not delete Report #${reportId}.`,
      });
    }
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      <PageHeader
        title="Investigation Dossier Reports"
        description="Tamper-evident, publication-grade multi-page PDF reports compiling multi-source evidence, claim forensics, and cryptographic integrity hashes."
        badgeText="Part 12 Certified"
        badgeVariant="cyan"
        icon={FileCheck}
        actions={
          <div className="flex items-center gap-2">
            <Button
              onClick={() => setIsGenerateOpen(true)}
              variant="primary"
              size="sm"

              className="gap-1.5 shadow-sm"
            >
              <Plus className="w-4 h-4" />
              <span>Generate PDF Dossier</span>
            </Button>
            <Button
              onClick={loadReports}
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

      {/* Notification Toast */}
      {notification && (
        <div
          className={`p-3.5 rounded-xl border text-xs font-medium flex items-center justify-between transition-all ${
            notification.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : "bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300"
          }`}
        >
          <span>{notification.text}</span>
          <button
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs ml-4"
          >
            x
          </button>
        </div>
      )}

      {/* Quick Generate Panel / Modal */}
      {isGenerateOpen && (
        <Card className="p-6 border-cyan-500/30 bg-cyan-500/5 dark:bg-cyan-950/20 shadow-md">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-500" />
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                Generate New PDF Verification Dossier
              </h3>
            </div>
            <button
              onClick={() => setIsGenerateOpen(false)}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs"
            >
              Cancel
            </button>
          </div>

          <form onSubmit={handleGenerate} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Verification Request ID *
                </label>
                <input
                  type="number"
                  placeholder="e.g. 1"
                  value={inputRequestId}
                  onChange={(e) => setInputRequestId(e.target.value)}
                  required
                  min="1"
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-surface-borderDark bg-white dark:bg-surface-cardDark text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                />
                <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 block">
                  The ID of an existing investigation saved in the history feed.
                </span>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Custom Report Title (Optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. Public Health Advisory Evaluation Dossier"
                  value={inputTitle}
                  onChange={(e) => setInputTitle(e.target.value)}
                  className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 dark:border-surface-borderDark bg-white dark:bg-surface-cardDark text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                />
                <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 block">
                  Defaults to &quot;TruthLens Verification Dossier — [Type] #[ID]&quot;.
                </span>
              </div>
            </div>

            {genError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{genError}</span>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setIsGenerateOpen(false)}
                disabled={generating}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"

                disabled={generating}
                className="gap-2"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>{generating ? "Compiling Multi-Page PDF..." : "Compile PDF Dossier"}</span>
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* Feature Architecture Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="p-4 bg-slate-50/50 dark:bg-surface-cardDark/40">
          <div className="flex items-center gap-2.5 font-bold text-xs text-slate-800 dark:text-slate-200 mb-1">
            <FileText className="w-4 h-4 text-rose-500" />
            <span>ISO 32000-1 Vector Engine</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Native server-side vector generator producing crisp, print-ready PDFs with two-pass dynamic pagination.
          </p>
        </Card>

        <Card className="p-4 bg-slate-50/50 dark:bg-surface-cardDark/40">
          <div className="flex items-center gap-2.5 font-bold text-xs text-slate-800 dark:text-slate-200 mb-1">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            <span>Cryptographic Fingerprint</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Every document is sealed with a unique SHA-256 digital digest, guaranteeing tamper-evident auditability.
          </p>
        </Card>

        <Card className="p-4 bg-slate-50/50 dark:bg-surface-cardDark/40">
          <div className="flex items-center gap-2.5 font-bold text-xs text-slate-800 dark:text-slate-200 mb-1">
            <ExternalLink className="w-4 h-4 text-cyan-500" />
            <span>Interactive URI Citations</span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400">
            Discovered news articles and corroborated source URLs embed directly as clickable annotations in the PDF.
          </p>
        </Card>
      </div>

      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-3 rounded-xl bg-slate-100/70 dark:bg-surface-cardDark/60 border border-slate-200 dark:border-surface-borderDark">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-48">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Filter by Request ID..."
              value={requestIdFilter}
              onChange={(e) => {
                setRequestIdFilter(e.target.value);
                setPage(1);
              }}
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-surface-borderDark bg-white dark:bg-surface-cardDark text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-1.5 text-xs rounded-lg border border-slate-200 dark:border-surface-borderDark bg-white dark:bg-surface-cardDark text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-1 focus:ring-cyan-500"
          >
            <option value="">All Statuses</option>
            <option value="generated">Generated</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </div>

        <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
          Total Reports: <span className="font-bold text-slate-800 dark:text-slate-200">{totalCount}</span>
        </div>
      </div>

      {/* Reports List */}
      {loading ? (
        <div className="p-16 text-center text-xs text-slate-400 font-mono flex flex-col items-center justify-center gap-3">
          <RefreshCw className="w-5 h-5 animate-spin text-cyan-500" />
          <span>Querying reports ledger in database...</span>
        </div>
      ) : reports.length > 0 ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-200 dark:border-surface-borderDark divide-y divide-slate-100 dark:divide-surface-borderDark overflow-hidden bg-white dark:bg-surface-cardDark shadow-sm">
            {reports.map((r) => {
              const downloadUrl = getReportDownloadUrl(r.id);
              const isGenerated = r.status === "generated";

              return (
                <div
                  key={r.id}
                  className="p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
                >
                  <div className="space-y-1.5 max-w-2xl">
                    <div className="flex flex-wrap items-center gap-2 font-mono">
                      <span className="font-bold text-slate-900 dark:text-slate-100">#{r.id}</span>
                      <Badge variant="indigo" size="sm">
                        {r.format.toUpperCase()}
                      </Badge>
                      <Badge
                        variant={isGenerated ? "emerald" : r.status === "failed" ? "rose" : "amber"}
                        size="sm"
                      >
                        {r.status.toUpperCase()}
                      </Badge>
                      {r.request_id && (
                        <Link
                          href={`/history/${r.request_id}`}
                          className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 text-[11px]"
                        >
                          <span>Request #{r.request_id}</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                      )}
                      <span className="text-slate-400">•</span>
                      <span className="text-slate-500 dark:text-slate-400 text-[11px] flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(r.created_at)}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      {r.title}
                    </h4>

                    {/* Technical File Metadata Bar */}
                    <div className="flex flex-wrap items-center gap-4 text-[11px] text-slate-500 dark:text-slate-400 font-mono pt-1">
                      <span>Size: {formatBytes(r.file_size_bytes)}</span>
                      {r.report_uuid && (
                        <span className="truncate max-w-xs" title={r.report_uuid}>
                          UUID: {r.report_uuid.slice(0, 14)}...
                        </span>
                      )}
                      {r.sha256_hash && (
                        <span
                          className="truncate max-w-xs flex items-center gap-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                          title={`SHA-256: ${r.sha256_hash}`}
                          onClick={() => {
                            navigator.clipboard.writeText(r.sha256_hash || "");
                            alert("Copied SHA-256 fingerprint to clipboard!");
                          }}
                        >
                          <Hash className="w-3 h-3 text-cyan-500" />
                          <span>{r.sha256_hash.slice(0, 12)}... (copy)</span>
                        </span>
                      )}
                    </div>

                    {r.error_message && (
                      <div className="text-[11px] text-rose-600 dark:text-rose-400 pt-1">
                        Error: {r.error_message}
                      </div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 shrink-0">
                    {r.request_id && (
                      <Link href={`/history/${r.request_id}`}>
                        <Button size="xs" variant="outline" className="gap-1.5">
                          <Eye className="w-3.5 h-3.5" />
                          <span>Dossier</span>
                        </Button>
                      </Link>
                    )}

                    {isGenerated && (
                      <a href={sanitizeHref(downloadUrl)} download>
                        <Button size="xs" variant="secondary" className="gap-1.5">
                          <Download className="w-3.5 h-3.5" />
                          <span>Download PDF</span>
                        </Button>
                      </a>
                    )}

                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={() => handleDelete(r.id)}
                      className="text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 p-1.5"
                      title="Delete Report"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between text-xs pt-2">
              <span className="text-slate-500 dark:text-slate-400">
                Page {page} of {totalPages}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  size="xs"
                  variant="outline"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  size="xs"
                  variant="outline"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </div>
      ) : (
        <EmptyState
          icon={FileCheck}
          badgeText="Report Generator Ready"
          badgeVariant="cyan"
          title="No investigation reports found."
          description="Reports are generated directly from completed investigations in the History feed or using the 'Generate PDF Dossier' button above."
          actionLabel="Open History Feed"
          onAction={() => window.location.assign("/history")}
        />
      )}
    </div>
  );
}
