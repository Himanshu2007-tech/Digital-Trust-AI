"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  Shield,
  ArrowLeft,
  RefreshCw,
  Archive,
  ArchiveRestore,
  ExternalLink,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Clock,
  Fingerprint,
  GitBranch,
  FileText,
  Globe,
  Image as ImageIcon,
  Mic,
  Film,
  Layers,
  Search,
  Scale,
  Award,
  Calendar,
  Eye,
  Activity,
  Download,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { fetchHistoryDetail, reverifyInvestigation, toggleArchiveInvestigation, generateReport, getReportDownloadUrl } from "@/lib/api";
import { HistoryDetailResponse } from "@/types/api";
import { formatDate } from "@/lib/utils";


export default function HistoryDetailPage() {
  const params = useParams();
  const router = useRouter();
  const requestId = Number(params?.requestId);

  const [dossier, setDossier] = useState<HistoryDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Action states
  const [reverifying, setReverifying] = useState(false);
  const [archiving, setArchiving] = useState(false);
  const [generatingReport, setGeneratingReport] = useState(false);
  const [notification, setNotification] = useState<{ type: "success" | "error"; text: string } | null>(null);


  // Tab state
  const [activeTab, setActiveTab] = useState<"overview" | "claims" | "evidence" | "multimedia" | "audit">("overview");

  const loadDossier = useCallback(async () => {
    if (!requestId || isNaN(requestId)) {
      setError("Invalid investigation ID requested.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = await fetchHistoryDetail(requestId);
      setDossier(data);
    } catch (err: any) {
      setError(err?.message || `Failed to retrieve dossier for investigation #${requestId}.`);
    } finally {
      setLoading(false);
    }
  }, [requestId]);

  useEffect(() => {
    loadDossier();
  }, [loadDossier]);

  // Re-verify action
  const handleReverify = async () => {
    if (reverifying || !dossier) return;
    setReverifying(true);
    setNotification(null);
    try {
      const res = await reverifyInvestigation(dossier.id);
      setNotification({
        type: "success",
        text: `Re-verification initiated! New investigation #${res.new_request_id} created with latest evidence.`,
      });
      // Navigate to the newly created investigation dossier after a short pause
      setTimeout(() => {
        router.push(`/history/${res.new_request_id}`);
      }, 1500);
    } catch (err: any) {
      setNotification({
        type: "error",
        text: `Re-verification failed: ${err?.message || "Unknown error"}`,
      });
      setReverifying(false);
    }
  };

  // Archive toggle action
  const handleToggleArchive = async () => {
    if (archiving || !dossier) return;
    setArchiving(true);
    setNotification(null);
    try {
      const nextState = !dossier.is_archived;
      await toggleArchiveInvestigation(dossier.id, nextState);
      setDossier((prev) => (prev ? { ...prev, is_archived: nextState } : null));
      setNotification({
        type: "success",
        text: `Investigation #${dossier.id} ${nextState ? "archived" : "restored to active"} successfully.`,
      });
    } catch (err: any) {
      setNotification({
        type: "error",
        text: `Archive toggle failed: ${err?.message || "Unknown error"}`,
      });
    } finally {
      setArchiving(false);
    }
  };

  // Generate PDF Dossier action (Part 12)
  const handleGeneratePdf = async () => {
    if (generatingReport || !dossier) return;
    setGeneratingReport(true);
    setNotification(null);
    try {
      const rep = await generateReport(dossier.id);
      setNotification({
        type: "success",
        text: `PDF Dossier successfully generated! Starting download...`,
      });
      const dlUrl = getReportDownloadUrl(rep.id);
      const link = document.createElement("a");
      link.href = dlUrl;
      link.setAttribute("download", `TruthLens_Dossier_${dossier.id}.pdf`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: any) {
      setNotification({
        type: "error",
        text: `PDF generation failed: ${err?.message || "Unknown error"}`,
      });
    } finally {
      setGeneratingReport(false);
    }
  };


  // Format icon helper
  const getTypeIcon = (type?: string) => {
    switch (type?.toLowerCase()) {
      case "text":
        return <FileText className="w-4 h-4" />;
      case "url":
        return <Globe className="w-4 h-4" />;
      case "image":
        return <ImageIcon className="w-4 h-4" />;
      case "audio":
        return <Mic className="w-4 h-4" />;
      case "video":
        return <Film className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  // Verdict badge helper
  const getVerdictBadge = (verdict?: string | null) => {
    if (!verdict) {
      return <Badge variant="slate">PENDING EVALUATION</Badge>;
    }
    const norm = verdict.toUpperCase();
    if (norm === "SUPPORTED" || norm === "TRUE") {
      return (
        <Badge variant="emerald" className="gap-1.5 px-3 py-1 text-xs">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>VERIFIED SUPPORTED</span>
        </Badge>
      );
    }
    if (norm === "CONTRADICTED" || norm === "FALSE") {
      return (
        <Badge variant="rose" className="gap-1.5 px-3 py-1 text-xs">
          <XCircle className="w-3.5 h-3.5" />
          <span>VERIFIED CONTRADICTED</span>
        </Badge>
      );
    }
    if (norm === "MISLEADING") {
      return (
        <Badge variant="amber" className="gap-1.5 px-3 py-1 text-xs">
          <AlertTriangle className="w-3.5 h-3.5" />
          <span>MISLEADING CLAIMS</span>
        </Badge>
      );
    }
    return (
      <Badge variant="slate" className="gap-1.5 px-3 py-1 text-xs">
        <HelpCircle className="w-3.5 h-3.5" />
        <span>{norm}</span>
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto py-20 text-center space-y-4">
        <RefreshCw className="w-8 h-8 animate-spin text-cyan-500 mx-auto" />
        <p className="text-xs font-mono text-slate-400">Loading authentic verification dossier #{requestId}...</p>
      </div>
    );
  }

  if (error || !dossier) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        <Link href="/history">
          <Button variant="ghost" size="sm" className="gap-1.5 text-xs">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to History</span>
          </Button>
        </Link>
        <Card className="p-8 text-center space-y-4 border-rose-500/30">
          <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto" />
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">Dossier Retrieval Error</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">{error || "Investigation not found."}</p>
          <div className="flex justify-center gap-3 pt-2">
            <Button onClick={loadDossier} variant="outline" size="sm">
              Retry
            </Button>
            <Link href="/history">
              <Button variant="secondary" size="sm">
                Return to History Feed
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  const hasMultimedia = Boolean(dossier.image_verification || dossier.media_verification);

  return (
    <div className="space-y-6 max-w-6xl mx-auto px-2 sm:px-4 pb-12">
      {/* Navigation Breadcrumb & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
        <Link href="/history">
          <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-slate-600 dark:text-slate-400">
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Investigation History Feed</span>
          </Button>
        </Link>

        <div className="flex items-center gap-2">
          {/* Export PDF Dossier Button */}
          <Button
            variant="primary"
            size="sm"
            onClick={handleGeneratePdf}

            disabled={generatingReport}
            className="gap-1.5 text-xs shadow-sm"
            title="Compile and download a publication-grade multi-page PDF verification report"
          >
            <Download className={`w-3.5 h-3.5 ${generatingReport ? "animate-bounce text-cyan-200" : ""}`} />
            <span>{generatingReport ? "Compiling PDF..." : "Export PDF Dossier"}</span>
          </Button>

          {/* Re-verify Button */}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleReverify}
            disabled={reverifying}
            className="gap-1.5 text-xs"
            title="Creates a child investigation re-running live search and evidence discovery"
          >

            <RefreshCw className={`w-3.5 h-3.5 ${reverifying ? "animate-spin text-cyan-500" : ""}`} />
            <span>{reverifying ? "Re-verifying..." : "Re-Verify Investigation"}</span>
          </Button>

          {/* Archive Toggle Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleToggleArchive}
            disabled={archiving}
            className="gap-1.5 text-xs"
          >
            {dossier.is_archived ? (
              <>
                <ArchiveRestore className="w-3.5 h-3.5 text-cyan-500" />
                <span>Restore to Active</span>
              </>
            ) : (
              <>
                <Archive className="w-3.5 h-3.5 text-slate-400" />
                <span>Archive Dossier</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Notification Toast */}
      {notification && (
        <div
          className={`p-3.5 rounded-xl border text-xs font-medium flex items-center justify-between transition-all ${
            notification.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-300"
              : "bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {notification.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
            )}
            <span>{notification.text}</span>
          </div>
          <button
            onClick={() => setNotification(null)}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs px-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* Dossier Header Card */}
      <Card className="p-6 bg-gradient-to-br from-slate-900 to-slate-950 text-white border-slate-800 shadow-md">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-xl font-bold tracking-tight text-white">
                Investigation #{dossier.id}
              </span>
              <Badge variant="cyan" size="md" className="gap-1 capitalize">
                {getTypeIcon(dossier.request_type)}
                <span>{dossier.request_type} Verification</span>
              </Badge>
              <Badge
                variant={
                  dossier.status === "completed"
                    ? "emerald"
                    : dossier.status === "failed"
                    ? "rose"
                    : "amber"
                }
                size="md"
              >
                {dossier.status.toUpperCase()}
              </Badge>
              {dossier.parent_request_id && (
                <Link href={`/history/${dossier.parent_request_id}`}>
                  <Badge variant="purple" size="md" className="gap-1 cursor-pointer hover:opacity-80">
                    <GitBranch className="w-3 h-3" />
                    <span>Child of #{dossier.parent_request_id}</span>
                  </Badge>
                </Link>
              )}
              {dossier.is_archived && (
                <Badge variant="slate" size="md">
                  Archived
                </Badge>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 font-mono">
              <span className="flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-cyan-400" />
                <span>Created: {formatDate(dossier.created_at)}</span>
              </span>
              {dossier.completed_at && (
                <span className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Completed: {formatDate(dossier.completed_at)}</span>
                </span>
              )}
              {dossier.content_hash && (
                <span className="flex items-center gap-1.5" title={`SHA-256: ${dossier.content_hash}`}>
                  <Fingerprint className="w-3.5 h-3.5 text-purple-400" />
                  <span>Hash: {dossier.content_hash.slice(0, 12)}...</span>
                </span>
              )}
            </div>
          </div>

          {/* Verdict and Confidence Callout */}
          <div className="bg-slate-800/80 rounded-xl p-4 border border-slate-700/80 min-w-[220px] text-center space-y-2">
            <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider block">
              Overall Verification Verdict
            </span>
            <div className="flex justify-center">{getVerdictBadge(dossier.verdict)}</div>
            {dossier.confidence_percentage !== null && dossier.confidence_percentage !== undefined && (
              <div className="pt-1 space-y-1">
                <div className="flex justify-between text-[11px] font-mono text-slate-300">
                  <span>Evidence Confidence:</span>
                  <span className="font-bold text-cyan-400">{dossier.confidence_percentage}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-cyan-400 rounded-full"
                    style={{ width: `${dossier.confidence_percentage}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-200 dark:border-surface-borderDark overflow-x-auto pb-px">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap ${
            activeTab === "overview"
              ? "border-cyan-500 text-cyan-600 dark:text-cyan-400"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Executive Overview</span>
        </button>
        <button
          onClick={() => setActiveTab("claims")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap ${
            activeTab === "claims"
              ? "border-cyan-500 text-cyan-600 dark:text-cyan-400"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Scale className="w-3.5 h-3.5" />
          <span>Extracted Claims ({dossier.claims.length})</span>
        </button>
        <button
          onClick={() => setActiveTab("evidence")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap ${
            activeTab === "evidence"
              ? "border-cyan-500 text-cyan-600 dark:text-cyan-400"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Search className="w-3.5 h-3.5" />
          <span>Sources & Evidence ({dossier.evidence.length})</span>
        </button>
        {hasMultimedia && (
          <button
            onClick={() => setActiveTab("multimedia")}
            className={`px-4 py-2 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap ${
              activeTab === "multimedia"
                ? "border-cyan-500 text-cyan-600 dark:text-cyan-400"
                : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
            }`}
          >
            <Film className="w-3.5 h-3.5" />
            <span>Forensics & Multimedia</span>
          </button>
        )}
        <button
          onClick={() => setActiveTab("audit")}
          className={`px-4 py-2 text-xs font-semibold border-b-2 transition-all flex items-center gap-1.5 whitespace-nowrap ${
            activeTab === "audit"
              ? "border-cyan-500 text-cyan-600 dark:text-cyan-400"
              : "border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Audit Trail ({dossier.events.length})</span>
        </button>
      </div>

      {/* Tab: Executive Overview */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Input Content Card */}
          <Card className="p-5 space-y-2">
            <span className="text-[11px] font-mono font-semibold uppercase text-slate-400 tracking-wider">
              Submitted Input Payload
            </span>
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark text-xs leading-relaxed text-slate-800 dark:text-slate-200 max-h-60 overflow-y-auto whitespace-pre-wrap font-sans">
              {dossier.content || "No text content recorded for this investigation."}
            </div>
          </Card>

          {/* Executive Verdict Summary */}
          <Card className="p-5 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-mono font-semibold uppercase text-slate-400 tracking-wider">
                Verification Synthesis & Justification
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-slate-500">
                  {dossier.supported_count} Supported · {dossier.contradicted_count} Contradicted · {dossier.misleading_count} Misleading
                </span>
              </div>
            </div>

            <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300">
              {dossier.summary || "No executive summary available for this investigation."}
            </p>

            {/* Factual Limitations */}
            {dossier.limitations && dossier.limitations.length > 0 && (
              <div className="space-y-1.5 pt-2">
                <span className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>Investigative Boundaries & Limitations:</span>
                </span>
                <ul className="list-disc list-inside space-y-1 text-xs text-slate-600 dark:text-slate-400 pl-1">
                  {dossier.limitations.map((lim, idx) => (
                    <li key={idx}>{lim}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Methodology Notes */}
            {dossier.methodology_notes && (
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-surface-borderDark text-[11px] font-mono text-slate-500 dark:text-slate-400">
                <span className="font-bold text-slate-700 dark:text-slate-300">Methodology: </span>
                {dossier.methodology_notes}
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Tab: Extracted Claims */}
      {activeTab === "claims" && (
        <div className="space-y-4">
          {dossier.claims.length > 0 ? (
            dossier.claims.map((claim, idx) => (
              <Card key={claim.id || idx} className="p-5 space-y-3 hover:border-cyan-500/40 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-400">#{idx + 1}</span>
                    <Badge variant="cyan" size="sm">
                      {claim.claim_type || "FACTUAL"}
                    </Badge>
                    <Badge variant="slate" size="sm">
                      {claim.verifiability || "VERIFIABLE"}
                    </Badge>
                    {claim.primary_origin && (
                      <Badge variant="purple" size="sm" className="font-mono text-[10px]">
                        Origin: {claim.primary_origin}
                      </Badge>
                    )}
                    {claim.formatted_timestamp && (
                      <span className="text-[11px] font-mono text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded">
                        ⏱ {claim.formatted_timestamp}
                      </span>
                    )}
                  </div>
                  {claim.verdict && getVerdictBadge(claim.verdict)}
                </div>

                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                  "{claim.claim_text || claim.text}"
                </p>

                {claim.explanation && (
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed bg-slate-50 dark:bg-slate-900/60 p-3 rounded-lg border border-slate-100 dark:border-surface-borderDark">
                    {claim.explanation}
                  </p>
                )}

                {/* Entities & Citations */}
                {claim.entities && claim.entities.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1.5 pt-1 text-[11px]">
                    <span className="text-slate-400 font-mono">Entities:</span>
                    {claim.entities.map((e: string, i: number) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono"
                      >
                        {e}
                      </span>
                    ))}
                  </div>
                )}
              </Card>
            ))
          ) : (
            <Card className="p-8 text-center text-xs text-slate-400">
              No atomic factual claims were extracted for this investigation.
            </Card>
          )}
        </div>
      )}

      {/* Tab: Sources & Evidence */}
      {activeTab === "evidence" && (
        <div className="space-y-6">
          {/* Sources section */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono font-semibold uppercase text-slate-400 tracking-wider">
              Discovered Web Sources ({dossier.sources.length})
            </h4>
            {dossier.sources.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {dossier.sources.map((src, i) => (
                  <Card key={src.id || i} className="p-4 space-y-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-slate-900 dark:text-slate-100 truncate">
                        {src.publisher || src.domain}
                      </span>
                      {src.credibility_score != null && (
                        <Badge variant="cyan" size="sm">
                          Credibility: {Math.round(src.credibility_score * 100)}%
                        </Badge>
                      )}
                    </div>
                    <p className="text-slate-500 dark:text-slate-400 truncate">{src.title || src.url}</p>
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 font-mono text-[11px] pt-1"
                    >
                      <span>Visit Source URL</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="p-6 text-center text-xs text-slate-400">
                No external web sources were discovered during this investigation.
              </Card>
            )}
          </div>

          {/* Evidence section */}
          <div className="space-y-3">
            <h4 className="text-xs font-mono font-semibold uppercase text-slate-400 tracking-wider">
              Corroborating Evidence Snippets ({dossier.evidence.length})
            </h4>
            {dossier.evidence.length > 0 ? (
              <div className="space-y-3">
                {dossier.evidence.map((ev, i) => (
                  <Card key={ev.id || i} className="p-4 space-y-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <Badge
                        variant={
                          (ev.stance || ev.evidence_type) === "SUPPORTING"
                            ? "emerald"
                            : (ev.stance || ev.evidence_type) === "CONTRADICTING"
                            ? "rose"
                            : "amber"
                        }
                        size="sm"
                      >
                        {ev.stance || ev.evidence_type || "CONTEXTUAL"}
                      </Badge>
                      {ev.relevance_score !== undefined && (
                        <span className="font-mono text-[11px] text-slate-400">
                          Relevance: {Math.round(ev.relevance_score * 100)}%
                        </span>
                      )}
                    </div>
                    <p className="text-slate-800 dark:text-slate-200 leading-relaxed font-sans italic">
                      "{ev.evidence_text || ev.quote}"
                    </p>
                  </Card>
                ))}
              </div>
            ) : (
              <Card className="p-6 text-center text-xs text-slate-400">
                No factual evidence statements recorded.
              </Card>
            )}
          </div>
        </div>
      )}

      {/* Tab: Forensics & Multimedia */}
      {activeTab === "multimedia" && hasMultimedia && (
        <div className="space-y-6">
          {/* Image Forensics if available */}
          {dossier.image_verification && (
            <Card className="p-5 space-y-3">
              <CardTitle className="text-sm">Image & OCR Forensics</CardTitle>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark">
                  <span className="text-slate-400 block text-[10px]">Format</span>
                  <span className="font-bold">{dossier.image_verification.image_format || "N/A"}</span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark">
                  <span className="text-slate-400 block text-[10px]">Dimensions</span>
                  <span className="font-bold">
                    {dossier.image_verification.image_width}x{dossier.image_verification.image_height}
                  </span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark">
                  <span className="text-slate-400 block text-[10px]">OCR Confidence</span>
                  <span className="font-bold text-cyan-500">
                    {dossier.image_verification.ocr_confidence
                      ? `${Math.round(dossier.image_verification.ocr_confidence)}%`
                      : "N/A"}
                  </span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark">
                  <span className="text-slate-400 block text-[10px]">OCR Engine</span>
                  <span className="font-bold">{dossier.image_verification.ocr_engine || "Tesseract"}</span>
                </div>
              </div>

              {dossier.image_verification.normalized_ocr_text && (
                <div className="space-y-1.5 pt-2">
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Extracted On-Screen Text (OCR):
                  </span>
                  <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark text-xs font-mono leading-relaxed max-h-40 overflow-y-auto">
                    {dossier.image_verification.normalized_ocr_text}
                  </div>
                </div>
              )}
            </Card>
          )}

          {/* Media/Video Forensics if available */}
          {dossier.media_verification && (
            <Card className="p-5 space-y-4">
              <CardTitle className="text-sm">Audio & Video Multimedia Forensics</CardTitle>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark">
                  <span className="text-slate-400 block text-[10px]">Type</span>
                  <span className="font-bold capitalize">{dossier.media_verification.media_type || "Video"}</span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark">
                  <span className="text-slate-400 block text-[10px]">Duration</span>
                  <span className="font-bold">
                    {dossier.media_verification.duration_seconds
                      ? `${Math.round(dossier.media_verification.duration_seconds)}s`
                      : "N/A"}
                  </span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark">
                  <span className="text-slate-400 block text-[10px]">Language</span>
                  <span className="font-bold uppercase">{dossier.media_verification.language || "EN"}</span>
                </div>
                <div className="p-2.5 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark">
                  <span className="text-slate-400 block text-[10px]">Transcription Score</span>
                  <span className="font-bold text-cyan-500">
                    {dossier.media_verification.transcription_confidence
                      ? `${Math.round(dossier.media_verification.transcription_confidence)}%`
                      : "N/A"}
                  </span>
                </div>
              </div>

              {/* Speech Transcript Segments */}
              {dossier.media_verification.segments && dossier.media_verification.segments.length > 0 && (
                <div className="space-y-2 pt-2">
                  <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Timestamped Speech Segments:
                  </span>
                  <div className="space-y-1.5 max-h-60 overflow-y-auto">
                    {dossier.media_verification.segments.map((seg: any, idx: number) => (
                      <div
                        key={idx}
                        className="p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-surface-borderDark flex items-start gap-3 text-xs"
                      >
                        <span className="font-mono text-[11px] text-cyan-500 shrink-0">
                          {seg.start_time !== undefined ? `${seg.start_time.toFixed(1)}s` : `00:${idx * 3}`}
                        </span>
                        <p className="text-slate-800 dark:text-slate-200">{seg.text}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          )}
        </div>
      )}

      {/* Tab: Audit Trail & Lifecycle Events */}
      {activeTab === "audit" && (
        <Card className="p-6 space-y-6">
          <div>
            <CardTitle className="text-sm">Cryptographic Verification Lifecycle Events</CardTitle>
            <p className="text-xs text-slate-400 mt-1">
              Immutable sequence of milestones logged to the verification_events table during pipeline orchestration.
            </p>
          </div>

          {dossier.events && dossier.events.length > 0 ? (
            <div className="relative pl-6 border-l-2 border-slate-200 dark:border-surface-borderDark space-y-6">
              {dossier.events.map((evt, idx) => (
                <div key={evt.id || idx} className="relative group">
                  {/* Timeline dot */}
                  <div
                    className={`absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full border-2 border-white dark:border-slate-900 ${
                      evt.status === "success"
                        ? "bg-emerald-500 ring-2 ring-emerald-500/20"
                        : evt.status === "failed"
                        ? "bg-rose-500 ring-2 ring-rose-500/20"
                        : "bg-cyan-500 ring-2 ring-cyan-500/20"
                    }`}
                  />

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-900 dark:text-slate-100">
                        {evt.event_type}
                      </span>
                      <Badge variant="cyan" size="sm" className="font-mono text-[10px]">
                        {evt.stage_name}
                      </Badge>
                      <Badge
                        variant={evt.status === "success" ? "emerald" : "rose"}
                        size="sm"
                        className="text-[10px]"
                      >
                        {evt.status.toUpperCase()}
                      </Badge>
                      <span className="text-[11px] font-mono text-slate-400 ml-auto">
                        {formatDate(evt.created_at)}
                      </span>
                    </div>

                    {evt.details && Object.keys(evt.details).length > 0 && (
                      <pre className="mt-1.5 p-2 rounded bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-surface-borderDark text-[11px] font-mono text-slate-600 dark:text-slate-300 overflow-x-auto">
                        {JSON.stringify(evt.details, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center text-xs text-slate-400 font-mono">
              No audit milestones recorded for this investigation.
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
