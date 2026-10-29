"use client";

import React, { useState } from "react";
import {
  Globe,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Info,
  ExternalLink,
  RotateCcw,
  Building,
  Calendar,
  X,
  ClipboardCopy
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { sanitizeHref } from "@/lib/utils";
import { verifyNewsUrl } from "@/lib/api";
import {
  UrlVerificationResponse,
  DiscoveredSourceItem,
  VerdictType
} from "@/types/api";

export default function VerifyUrlPage() {
  const [url, setUrl] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [result, setResult] = useState<UrlVerificationResponse | null>(null);

  // Validate URL on client side before submission
  const validateUrlClient = (input: string): string | null => {
    const trimmed = input.trim();
    if (!trimmed) {
      return "Please enter a news article URL.";
    }

    try {
      const parsed = new URL(trimmed);
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
        return "Invalid scheme. Only HTTP and HTTPS URLs are allowed.";
      }

      const host = parsed.hostname.toLowerCase();
      if (
        host === "localhost" ||
        host === "127.0.0.1" ||
        host === "::1" ||
        host.startsWith("192.168.") ||
        host.startsWith("10.") ||
        host.startsWith("172.16.")
      ) {
        return "SSRF Protection: Access to localhost or internal network addresses is restricted.";
      }

      if (host === "169.254.169.254" || host.includes("metadata")) {
        return "SSRF Protection: Access to cloud metadata endpoints is strictly blocked.";
      }

      if (parsed.pathname.toLowerCase().endsWith(".pdf")) {
        return "PDF verification is not supported here. Please enter an HTML news article URL.";
      }
    } catch {
      return "Please enter a valid URL (e.g. https://www.reuters.com/world/...)";
    }

    return null;
  };

  // Paste from clipboard helper
  const handlePaste = async () => {
    try {
      if (navigator?.clipboard?.readText) {
        const text = await navigator.clipboard.readText();
        if (text) {
          setUrl(text.trim());
          if (urlError) setUrlError(null);
        }
      }
    } catch {
      // Browser permissions or clipboard read denied; fallback gracefully
    }
  };

  // Clear input and current result
  const handleClear = () => {
    setUrl("");
    setUrlError(null);
    setResult(null);
  };

  // Form submit handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setUrlError(null);

    const clientErr = validateUrlClient(url);
    if (clientErr) {
      setUrlError(clientErr);
      return;
    }

    setIsSubmitting(true);
    setResult(null);

    try {
      // Execute the real backend URL verification pipeline with full search, evidence extraction, and verdict synthesis
      const data = await verifyNewsUrl(url.trim(), true, true, true);
      setResult(data);
    } catch (err: any) {
      setUrlError(err.message || "Failed to verify article URL. Please check the URL or connectivity.");
    } finally {
      setIsSubmitting(false);
    }
  };

  // Verdict badge styling mapping
  const getVerdictBadgeProps = (verdict?: string) => {
    switch (verdict?.toUpperCase()) {
      case "SUPPORTED":
        return {
          variant: "emerald" as const,
          label: "Supported",
          desc: "Corroborated by independent, high-credibility external reporting."
        };
      case "CONTRADICTED":
        return {
          variant: "rose" as const,
          label: "Contradicted",
          desc: "Directly refuted by verifiable evidence from independent sources."
        };
      case "MISLEADING":
        return {
          variant: "amber" as const,
          label: "Misleading",
          desc: "Contains factual elements but distorts context or significance."
        };
      case "MIXED":
        return {
          variant: "indigo" as const,
          label: "Mixed",
          desc: "Contains a divergence of supported and contradicted claims."
        };
      case "UNVERIFIED":
        return {
          variant: "cyan" as const,
          label: "Unverified",
          desc: "Contextual reporting found, but insufficient direct confirmation."
        };
      case "INSUFFICIENT_EVIDENCE":
      default:
        return {
          variant: "slate" as const,
          label: "Insufficient Evidence",
          desc: "Insufficient independent evidence retrieved to substantiate or refute claims."
        };
    }
  };

  // Stance indicator badge styling
  const getStanceBadgeProps = (stance: string) => {
    switch (stance?.toUpperCase()) {
      case "SUPPORTING":
        return {
          variant: "emerald" as const,
          icon: CheckCircle2,
          text: "SUPPORTING"
        };
      case "CONTRADICTING":
        return {
          variant: "rose" as const,
          icon: AlertTriangle,
          text: "CONTRADICTING"
        };
      case "CONTEXTUAL":
      default:
        return {
          variant: "slate" as const,
          icon: Info,
          text: "CONTEXTUAL"
        };
    }
  };

  // Determine stance of an external source based on evidence extracted during verification
  const getSourceStance = (source: DiscoveredSourceItem): "SUPPORTING" | "CONTRADICTING" | "CONTEXTUAL" => {
    if (!result?.evidence || result.evidence.length === 0) return "CONTEXTUAL";

    const matchingEv = result.evidence.filter((ev) => {
      if (ev.source_id && source.id && ev.source_id === source.id) return true;
      if (ev.url && source.canonical_url && ev.url === source.canonical_url) return true;
      if (ev.domain && source.domain && ev.domain.toLowerCase() === source.domain.toLowerCase()) return true;
      return false;
    });

    if (matchingEv.length > 0) {
      const hasContradicting = matchingEv.some((ev) => ev.evidence_type === "CONTRADICTING");
      const hasSupporting = matchingEv.some((ev) => ev.evidence_type === "SUPPORTING");
      if (hasContradicting && !hasSupporting) return "CONTRADICTING";
      if (hasSupporting && !hasContradicting) return "SUPPORTING";
      return "CONTEXTUAL";
    }

    return "CONTEXTUAL";
  };

  // Calculate confidence meter metrics
  const overallConfidence = result?.verdict?.overall_confidence ?? 0;
  const confidencePercent = Math.round(overallConfidence * 100);
  const confidenceRingColor =
    overallConfidence >= 0.70
      ? "stroke-emerald-500"
      : overallConfidence >= 0.40
      ? "stroke-amber-500"
      : "stroke-rose-500";

  const confidenceLevelText =
    overallConfidence >= 0.75
      ? "High"
      : overallConfidence >= 0.45
      ? "Moderate"
      : "Low";

  const confidenceExplanation =
    overallConfidence >= 0.75
      ? "Strong independent evidence and high source corroboration consensus."
      : overallConfidence >= 0.45
      ? "Moderate evidence found across discovered reporting, with some variance or incomplete coverage."
      : "Low confidence due to sparse independent corroboration or conflicting accounts.";

  interface DisplayClaim {
    id: number;
    text: string;
    verdict: VerdictType;
    confidence: number;
    confidence_level: "HIGH" | "MODERATE" | "LOW";
    evidence_strength: string;
    explanation: string;
    supporting_evidence_ids: number[];
    contradicting_evidence_ids: number[];
  }

  // Extracted claims list (from synthesized claim verdicts or raw extracted claims)
  const claimItems: DisplayClaim[] =
    result?.claim_verdicts && result.claim_verdicts.length > 0
      ? result.claim_verdicts.map((cv) => {
          const rawClaim = result.claims?.find(
            (c) => c.db_id === cv.claim_id || c.id === String(cv.claim_id)
          );
          return {
            id: cv.claim_id,
            text: cv.claim_text || rawClaim?.text || "Extracted assertion",
            verdict: cv.verdict,
            confidence: cv.confidence,
            confidence_level: cv.confidence_level,
            evidence_strength: cv.evidence_strength,
            explanation: cv.explanation,
            supporting_evidence_ids: cv.supporting_evidence_ids || [],
            contradicting_evidence_ids: cv.contradicting_evidence_ids || []
          };
        })
      : (result?.claims || []).map((c, i) => ({
          id: c.db_id ?? (parseInt(c.id, 10) || i + 1),
          text: c.text,
          verdict: "UNVERIFIED" as VerdictType,
          confidence: 0.5,
          confidence_level: "LOW" as const,
          evidence_strength: "INSUFFICIENT",
          explanation: "Claim identified from article body.",
          supporting_evidence_ids: [] as number[],
          contradicting_evidence_ids: [] as number[]
        }));

  // Match evidence items for an individual claim
  const getClaimEvidence = (claim: DisplayClaim) => {
    const allEv = result?.evidence || [];
    const supporting = allEv.filter(
      (ev) =>
        (typeof ev.id === "number" && claim.supporting_evidence_ids.includes(ev.id)) ||
        (ev.claim_id === claim.id && ev.evidence_type === "SUPPORTING")
    );
    const contradicting = allEv.filter(
      (ev) =>
        (typeof ev.id === "number" && claim.contradicting_evidence_ids.includes(ev.id)) ||
        (ev.claim_id === claim.id && ev.evidence_type === "CONTRADICTING")
    );
    return { supporting, contradicting };
  };

  // External independent sources to display (deduplicating syndicated duplicates, max 15 reliable sources)
  const displaySources = (() => {
    const rawSources =
      result?.independent_sources && result.independent_sources.length > 0
        ? result.independent_sources
        : (result?.sources || []).filter((s) => s.source_role !== "USER_SUBMITTED_ARTICLE");

    const uniqueMap = new Map<string, DiscoveredSourceItem>();
    for (const src of rawSources) {
      const key = (src.canonical_url || src.url || src.title).trim().toLowerCase();
      if (!uniqueMap.has(key)) {
        uniqueMap.set(key, src);
      }
    }
    return Array.from(uniqueMap.values()).slice(0, 15);
  })();

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-16">
      {/* 1. Page Header */}
      <PageHeader
        title="Verify URL"
        description="Verify online articles and news links against independent corroborating sources."
        badgeText="Digital Trust AI"
        badgeVariant="cyan"
        icon={Globe}
      />

      {/* 2. Clean Input Interface */}
      <Card className="p-6 md:p-8">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
              <Globe className="w-4 h-4" />
            </div>
            <input
              type="url"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                if (urlError) setUrlError(null);
              }}
              placeholder="Paste news article URL here..."
              className="w-full rounded-2xl border border-slate-200 dark:border-surface-borderDark bg-slate-50/50 dark:bg-surface-cardDark pl-10 pr-24 py-3.5 text-xs sm:text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 transition-all font-mono"
              disabled={isSubmitting}
            />
            {/* Inline Paste / Clear controls */}
            <div className="absolute inset-y-0 right-2 flex items-center gap-1">
              {url ? (
                <button
                  type="button"
                  onClick={handleClear}
                  disabled={isSubmitting}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                  title="Clear input"
                >
                  <X className="w-4 h-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handlePaste}
                  disabled={isSubmitting}
                  className="px-2.5 py-1 text-xs text-slate-500 hover:text-cyan-600 dark:hover:text-cyan-400 font-sans flex items-center gap-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  title="Paste from clipboard"
                >
                  <ClipboardCopy className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Paste</span>
                </button>
              )}
            </div>
          </div>

          {/* Validation & Inaccessible URL Error Alert */}
          {urlError && (
            <Alert variant="error">
              {urlError}
            </Alert>
          )}

          {/* Action Row */}
          <div className="flex items-center justify-end gap-2 pt-1">
            {url && (
              <Button
                type="button"
                variant="ghost"
                size="md"
                onClick={handleClear}
                disabled={isSubmitting}
                className="text-xs text-slate-500 hover:text-slate-700 dark:hover:text-slate-200"
              >
                Clear
              </Button>
            )}

            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={isSubmitting || !url.trim()}
              className="text-xs gap-2 shadow-xs"
            >
              {isSubmitting ? (
                <>
                  <RotateCcw className="w-4 h-4 animate-spin" />
                  <span>Verifying URL...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  <span>Verify URL</span>
                </>
              )}
            </Button>
          </div>
        </form>
      </Card>

      {/* 3. Simple, Professional Loading State */}
      {isSubmitting && (
        <Card className="p-8 text-center border-cyan-500/30 bg-cyan-50/20 dark:bg-cyan-950/10">
          <div className="flex flex-col items-center justify-center space-y-3">
            <div className="relative w-12 h-12 flex items-center justify-center">
              <div className="w-12 h-12 rounded-full border-4 border-cyan-500/20 border-t-cyan-500 animate-spin" />
              <Globe className="w-5 h-5 text-cyan-600 dark:text-cyan-400 absolute inset-0 m-auto" />
            </div>
            <div className="space-y-1">
              <h4 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Verifying News Article URL...
              </h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto">
                Safely retrieving article text, extracting atomic claims, cross-referencing independent reliable sources, and compiling the evidence dossier.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* 4. Professional Two-Column Results Layout */}
      {result && (
        <div className="space-y-8">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
            {/* Left Column: Verification Result & Extracted Claims (2 columns wide on desktop) */}
            <div className="lg:col-span-2 space-y-6">
              {/* Overall Verdict & Article Summary Card */}
              <Card className="p-6 space-y-5">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Overall Verification Verdict
                  </span>
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge
                      variant={getVerdictBadgeProps(result.verdict?.overall_verdict).variant}
                      size="md"
                    >
                      {getVerdictBadgeProps(result.verdict?.overall_verdict).label}
                    </Badge>
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {getVerdictBadgeProps(result.verdict?.overall_verdict).desc}
                    </span>
                  </div>
                </div>

                {/* Concise Verdict Explanation */}
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200/70 dark:border-slate-800 text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  <p className="font-semibold text-slate-900 dark:text-slate-100 mb-1">
                    Executive Summary:
                  </p>
                  <p>{result.verdict?.summary || result.message}</p>
                </div>

                {/* Insufficient Evidence Clarification Note */}
                {result.verdict?.overall_verdict === "INSUFFICIENT_EVIDENCE" && (
                  <div className="p-3.5 rounded-xl bg-slate-100 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300 flex items-start gap-2.5">
                    <Info className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold block text-slate-900 dark:text-slate-100">
                        Insufficient Independent Corroboration
                      </span>
                      <span>
                        Independent reporting was insufficient to confirm or refute the claims. Digital Trust AI refrains from forcing a definitive verdict when independent verification cannot be established.
                      </span>
                    </div>
                  </div>
                )}

                {/* Extracted Article Details */}
                <div className="p-4 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50/50 dark:bg-slate-900/30 space-y-2.5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1 min-w-0">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                        Article Under Investigation
                      </span>
                      <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 leading-snug">
                        {result.article.title || result.article.domain || "News Article"}
                      </h3>
                    </div>
                    {result.article.original_url && (
                      <a
                        href={sanitizeHref(result.article.original_url)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-400 transition-colors shrink-0"
                        title="Open article in new tab"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600 dark:text-slate-400 pt-2 border-t border-slate-200/60 dark:border-slate-800">
                    <div className="flex items-center gap-1.5">
                      <Building className="w-3.5 h-3.5 text-slate-400" />
                      <span>Publisher: <strong>{result.article.publisher || result.article.domain}</strong></span>
                    </div>
                    <span>&bull;</span>
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5 text-slate-400" />
                      <span>Published: <strong>{result.article.published_at || "Date unavailable"}</strong></span>
                    </div>
                    <span>&bull;</span>
                    <span>Length: <strong>{result.article.word_count || 0} words</strong></span>
                  </div>
                </div>
              </Card>

              {/* Extracted Claims & Individual Status Badges */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                    Extracted Article Claims ({claimItems.length})
                  </h4>
                  <span className="text-[11px] text-slate-400">
                    Verified against independent sources
                  </span>
                </div>

                {claimItems.map((item, idx) => {
                  const { supporting, contradicting } = getClaimEvidence(item);
                  return (
                    <Card key={idx} className="p-4 sm:p-5 space-y-3 border-l-4 border-l-cyan-500">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <Badge variant={getVerdictBadgeProps(item.verdict).variant} size="sm">
                            {item.verdict}
                          </Badge>
                          <span className="text-xs text-slate-500 font-mono">
                            Confidence: {Math.round(item.confidence * 100)}%
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-400 font-mono">
                          Claim #{idx + 1}
                        </span>
                      </div>

                      <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 leading-snug">
                        &ldquo;{item.text}&rdquo;
                      </p>

                      {item.explanation && (
                        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed bg-slate-50/70 dark:bg-slate-900/40 p-3 rounded-lg border border-slate-200/70 dark:border-slate-800">
                          <strong className="text-slate-700 dark:text-slate-300">Analysis:</strong> {item.explanation}
                        </p>
                      )}

                      {/* Supporting & Contradicting Evidence Citations */}
                      {(supporting.length > 0 || contradicting.length > 0) && (
                        <div className="space-y-2 pt-2 border-t border-slate-200/70 dark:border-slate-800">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                            Evidence Citations:
                          </span>

                          {/* Supporting Evidence Excerpt */}
                          {supporting.map((ev, sIdx) => (
                            <div
                              key={`sup-${sIdx}`}
                              className="p-3 rounded-xl border border-emerald-500/30 bg-emerald-50/30 dark:bg-emerald-950/15 space-y-1.5 text-xs"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-1.5">
                                  <Badge variant="emerald" size="sm">
                                    <CheckCircle2 className="w-3 h-3 mr-0.5" />
                                    SUPPORTING
                                  </Badge>
                                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                                    {ev.publisher || ev.domain || "Independent Source"}
                                  </span>
                                </div>
                                {ev.url && (
                                  <a
                                    href={sanitizeHref(ev.url)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 text-[11px]"
                                  >
                                    <span>Source</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                )}
                              </div>
                              <blockquote className="text-slate-700 dark:text-slate-300 italic text-[11px] sm:text-xs leading-relaxed">
                                &ldquo;{ev.evidence_text || ev.snippet}&rdquo;
                              </blockquote>
                            </div>
                          ))}

                          {/* Contradicting Evidence Excerpt */}
                          {contradicting.map((ev, cIdx) => (
                            <div
                              key={`con-${cIdx}`}
                              className="p-3 rounded-xl border border-rose-500/30 bg-rose-50/30 dark:bg-rose-950/15 space-y-1.5 text-xs"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-1.5">
                                  <Badge variant="rose" size="sm">
                                    <AlertTriangle className="w-3 h-3 mr-0.5" />
                                    CONTRADICTING
                                  </Badge>
                                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                                    {ev.publisher || ev.domain || "Independent Source"}
                                  </span>
                                </div>
                                {ev.url && (
                                  <a
                                    href={sanitizeHref(ev.url)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 text-[11px]"
                                  >
                                    <span>Source</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                )}
                              </div>
                              <blockquote className="text-slate-700 dark:text-slate-300 italic text-[11px] sm:text-xs leading-relaxed">
                                &ldquo;{ev.evidence_text || ev.snippet}&rdquo;
                              </blockquote>
                            </div>
                          ))}
                        </div>
                      )}
                    </Card>
                  );
                })}
              </div>
            </div>

            {/* Right Column: Medium Circular Confidence Graph & Score Display */}
            <div className="lg:col-span-1 space-y-6">
              <Card className="p-6 space-y-5">
                <div className="text-center space-y-4">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block">
                    Confidence Score
                  </span>

                  {/* Circular SVG Confidence Meter */}
                  <div className="relative w-28 h-28 mx-auto flex items-center justify-center">
                    <svg className="w-28 h-28 transform -rotate-90" viewBox="0 0 100 100">
                      <circle
                        cx="50"
                        cy="50"
                        r="38"
                        className="stroke-slate-200 dark:stroke-slate-800"
                        strokeWidth="8"
                        fill="none"
                      />
                      <circle
                        cx="50"
                        cy="50"
                        r="38"
                        className={confidenceRingColor}
                        strokeWidth="8"
                        strokeDasharray={238.76}
                        strokeDashoffset={238.76 - overallConfidence * 238.76}
                        strokeLinecap="round"
                        fill="none"
                        style={{ transition: "stroke-dashoffset 0.8s ease-in-out" }}
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                      <span className="text-2xl font-bold font-mono text-slate-900 dark:text-white leading-none">
                        {confidencePercent}%
                      </span>
                      <span className="text-[10px] uppercase font-semibold text-slate-400 mt-1">
                        Confidence
                      </span>
                    </div>
                  </div>

                  {/* Brief Confidence Label */}
                  <div className="pt-1">
                    <span
                      className={`inline-block px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                        overallConfidence >= 0.70
                          ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30"
                          : overallConfidence >= 0.40
                          ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30"
                          : "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30"
                      }`}
                    >
                      {confidenceLevelText} Confidence
                    </span>
                  </div>

                  {/* Plain-Language Explanation of Evidence Strength */}
                  <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed px-2">
                    {confidenceExplanation}
                  </p>

                  <p className="text-[11px] text-slate-400 dark:text-slate-500 italic px-2">
                    Score reflects independent evidence quality, source agreement, and corroboration depth.
                  </p>
                </div>

                {/* Evidence Synthesis Breakdown */}
                {result.verdict && (
                  <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200/70 dark:border-slate-800 space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                      Claim Verdict Breakdown
                    </span>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div className="flex items-center justify-between p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        <span className="text-emerald-600 dark:text-emerald-400 font-medium">Supported</span>
                        <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                          {result.verdict.supported_count || 0}
                        </span>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        <span className="text-rose-600 dark:text-rose-400 font-medium">Contradicted</span>
                        <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                          {result.verdict.contradicted_count || 0}
                        </span>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        <span className="text-amber-600 dark:text-amber-400 font-medium">Misleading</span>
                        <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                          {result.verdict.misleading_count || 0}
                        </span>
                      </div>
                      <div className="flex items-center justify-between p-2 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        <span className="text-slate-500 dark:text-slate-400 font-medium">Unverified</span>
                        <span className="font-mono font-bold text-slate-800 dark:text-slate-200">
                          {(result.verdict.unverified_count || 0) +
                            (result.verdict.insufficient_count || 0)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Methodological Caveats & Limitations */}
                {result.verdict?.limitations && result.verdict.limitations.length > 0 && (
                  <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-900 dark:text-amber-200 space-y-2">
                    <div className="font-semibold flex items-center gap-1.5 text-amber-700 dark:text-amber-300">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>Caveats & Limitations</span>
                    </div>
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-amber-800 dark:text-amber-300">
                      {result.verdict.limitations.map((lim, lIdx) => (
                        <li key={lIdx}>{lim}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Request Metadata Footer */}
                <div className="pt-2 border-t border-slate-200/70 dark:border-slate-800 text-[11px] font-mono text-slate-400 flex items-center justify-between">
                  <span>Request #{result.request_id}</span>
                  <span>{displaySources.length} sources evaluated</span>
                </div>
              </Card>
            </div>
          </div>

          {/* 5. Evaluated External Sources Section (Approximately 10-15 reliable sources) */}
          <div className="space-y-4 pt-4 border-t border-slate-200/80 dark:border-surface-borderDark">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <div>
                <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                  <span>Evaluated Independent Sources</span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-mono bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30">
                    {displaySources.length} Sources
                  </span>
                </h4>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  External independent sources evaluated during verification (submitted article excluded from self-corroboration).
                </p>
              </div>
            </div>

            {displaySources.length === 0 ? (
              <Card className="p-6 text-center text-xs text-slate-500 italic">
                No external independent sources discovered for this article.
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {displaySources.map((src, idx) => {
                  const stance = getSourceStance(src);
                  const stanceProps = getStanceBadgeProps(stance);
                  const StanceIcon = stanceProps.icon;
                  return (
                    <Card key={idx} className="p-4 flex flex-col justify-between space-y-3">
                      <div className="space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
                            {src.publisher || src.domain || "Independent Source"}
                          </span>
                          <Badge variant={stanceProps.variant} size="sm">
                            <StanceIcon className="w-3 h-3 mr-0.5" />
                            {stanceProps.text}
                          </Badge>
                        </div>

                        <h5 className="text-xs font-semibold text-slate-800 dark:text-slate-200 line-clamp-2 leading-snug">
                          {src.title || src.domain}
                        </h5>

                        {src.snippet && (
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-3 leading-relaxed">
                            {src.snippet}
                          </p>
                        )}
                      </div>

                      <div className="pt-2 border-t border-slate-200/60 dark:border-surface-borderDark flex items-center justify-between text-[11px]">
                        <span className="text-slate-400">
                          {src.published_at || src.domain}
                        </span>
                        <a
                          href={sanitizeHref(src.canonical_url || src.url)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 font-medium"
                        >
                          <span>Visit Source</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      </div>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
