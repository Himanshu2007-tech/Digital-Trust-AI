"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  FileText,
  ShieldCheck,
  Search,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  Calendar,
  Quote,
  ArrowRight,
  Info,
  ExternalLink,
  Globe,
  FileCheck2,
  HelpCircle,
  Check,
  X,
  AlertTriangle,
  RefreshCw,
  BarChart3,
  Image as ImageIcon,
  ArrowUpRight,
  Split
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { sanitizeHref } from "@/lib/utils";
import {
  extractTextClaims,
  verifyImageFile,
  searchSourcesForClaim,
  analyzeClaimEvidence,
  verifyClaim,
  finalizeRequest
} from "@/lib/api";
import {
  TextVerificationResponse,
  ExtractedClaimItem,
  DiscoveredSourceItem,
  EvidenceItem,
  SourceComparisonItem,
  ClaimVerdictItem,
  RequestVerdictResult,
  ImageOCRSummary
} from "@/types/api";

export default function VerifyInformationPage() {
  const [claimText, setClaimText] = useState("");
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [ocrResult, setOcrResult] = useState<ImageOCRSummary | null>(null);
  const [isImageUploaded, setIsImageUploaded] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [result, setResult] = useState<TextVerificationResponse | null>(null);
  const [activeViewTab, setActiveViewTab] = useState<"verdict" | "evidence" | "comparisons" | "sources" | "claims">("verdict");

  // Filters
  const [evidenceFilter, setEvidenceFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Interactive action states
  const [verifyingClaimId, setVerifyingClaimId] = useState<number | null>(null);
  const [isFinalizing, setIsFinalizing] = useState<boolean>(false);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const characterCount = claimText.length;
  const maxCharacters = 20000;

  // Manage image preview URL object
  useEffect(() => {
    if (!selectedImage) {
      setImagePreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(selectedImage);
    setImagePreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedImage]);

  // Handle image file selection & validation
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null);
    const file = e.target.files?.[0];
    if (!file) return;

    const validTypes = ["image/png", "image/jpeg", "image/jpg", "image/webp"];
    if (!validTypes.includes(file.type)) {
      setErrorMsg("Invalid file type. Please upload a PNG, JPG, JPEG, or WEBP image.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    const maxSize = 15 * 1024 * 1024; // 15MB
    if (file.size > maxSize) {
      setErrorMsg("Image size exceeds 15MB limit. Please upload a smaller image.");
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setSelectedImage(file);
  };

  const handleRemoveImage = () => {
    setSelectedImage(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleClear = () => {
    setClaimText("");
    setSelectedImage(null);
    setOcrResult(null);
    setIsImageUploaded(false);
    setResult(null);
    setErrorMsg(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // Main submission handler supporting text alone, image alone, or both
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = claimText.trim();
    if (!trimmed && !selectedImage) {
      setErrorMsg("Please enter text or upload an image to verify.");
      return;
    }
    if (isSubmitting) return;

    setIsSubmitting(true);
    setErrorMsg(null);

    try {
      if (selectedImage) {
        // 1. Process image via existing image verification service (performs real OCR + claim extraction + search + evidence + verdicts)
        const imageRes = await verifyImageFile(selectedImage, true, true, true, 5);
        setOcrResult(imageRes.ocr);
        setIsImageUploaded(true);

        let finalClaims = imageRes.claims || [];
        let finalSources = imageRes.sources || [];
        let finalEvidence = imageRes.evidence || [];
        let finalComparisons = imageRes.comparisons || [];
        let finalVerdict = imageRes.verdicts || null;

        // If user also provided explicit text, cross-verify it as well
        if (trimmed) {
          try {
            const textRes = await extractTextClaims(trimmed, "", true, true, true);
            const existingClaimTexts = new Set(finalClaims.map((c) => c.text.toLowerCase()));
            const extraClaims = (textRes.claims || []).filter((c) => !existingClaimTexts.has(c.text.toLowerCase()));
            finalClaims = [...extraClaims, ...finalClaims];

            const existingUrls = new Set(finalSources.map((s) => s.canonical_url));
            const extraSources = (textRes.sources || []).filter((s) => !existingUrls.has(s.canonical_url));
            finalSources = [...finalSources, ...extraSources];

            const existingEvIds = new Set(finalEvidence.map((ev) => ev.id));
            const extraEv = (textRes.evidence || []).filter((ev) => !existingEvIds.has(ev.id));
            finalEvidence = [...finalEvidence, ...extraEv];

            if (textRes.verdict) {
              finalVerdict = textRes.verdict;
            }
          } catch (textErr) {
            console.warn("Supplementary text verification error:", textErr);
          }
        }

        const unifiedResponse: TextVerificationResponse = {
          status: imageRes.status,
          request_id: imageRes.request_id,
          input_text: trimmed || imageRes.ocr.raw_text,
          sentence_count: imageRes.ocr.blocks?.length || 1,
          claims_count: finalClaims.length,
          claims: finalClaims,
          extraction_method: "hybrid_multimedia_ocr",
          sources_count: finalSources.length,
          sources: finalSources,
          queries: [],
          search_provider: "duckduckgo",
          evidence_count: finalEvidence.length,
          evidence: finalEvidence,
          comparisons_count: finalComparisons.length,
          source_comparisons: finalComparisons,
          verdict: finalVerdict,
          claim_verdicts: finalVerdict?.claims || [],
          message: imageRes.ocr.raw_text.trim()
            ? `Extracted ${finalClaims.length} claims and analyzed image OCR with ${finalSources.length} corroborating sources.`
            : "Image analyzed. No readable text was detected."
        };

        setResult(unifiedResponse);
        setActiveViewTab("verdict");
      } else {
        // 2. Text alone (no image uploaded)
        setIsImageUploaded(false);
        setOcrResult(null);
        const textRes = await extractTextClaims(trimmed, "", true, true, true);
        setResult(textRes);
        setActiveViewTab("verdict");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to execute complete verification pipeline.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleVerifySingleClaim = async (claim: ExtractedClaimItem) => {
    if (!claim.db_id || !result) return;
    setVerifyingClaimId(claim.db_id);
    try {
      const claimVerdict = await verifyClaim(claim.db_id);
      const existingVerdicts = result.claim_verdicts || [];
      const updatedVerdicts = existingVerdicts.filter((v) => v.claim_id !== claim.db_id);
      updatedVerdicts.push(claimVerdict);

      const updatedReq = await finalizeRequest(result.request_id, false);
      setResult({
        ...result,
        claim_verdicts: updatedReq.claims,
        verdict: updatedReq
      });
      setActiveViewTab("verdict");
    } catch (err: any) {
      setErrorMsg(`Claim verification failed: ${err.message}`);
    } finally {
      setVerifyingClaimId(null);
    }
  };

  const handleFinalizeAll = async () => {
    if (!result?.request_id) return;
    setIsFinalizing(true);
    try {
      const updatedReq = await finalizeRequest(result.request_id, true);
      setResult({
        ...result,
        claim_verdicts: updatedReq.claims,
        verdict: updatedReq
      });
      setActiveViewTab("verdict");
    } catch (err: any) {
      setErrorMsg(`Finalization re-evaluation failed: ${err.message}`);
    } finally {
      setIsFinalizing(false);
    }
  };

  // Helper to get verdict styling
  const getVerdictBadgeProps = (verdict: string) => {
    switch (verdict?.toUpperCase()) {
      case "SUPPORTED":
        return {
          variant: "emerald" as const,
          label: "SUPPORTED",
          border: "border-emerald-500/40",
          bg: "bg-emerald-500/10",
          text: "text-emerald-400",
          desc: "Corroborated by high-credibility reporting."
        };
      case "CONTRADICTED":
        return {
          variant: "rose" as const,
          label: "CONTRADICTED",
          border: "border-rose-500/40",
          bg: "bg-rose-500/10",
          text: "text-rose-400",
          desc: "Directly refuted by verifiable evidence."
        };
      case "MISLEADING":
        return {
          variant: "amber" as const,
          label: "MISLEADING",
          border: "border-amber-500/40",
          bg: "bg-amber-500/10",
          text: "text-amber-400",
          desc: "Contains factual elements but distorts context or policy status."
        };
      case "MIXED":
        return {
          variant: "indigo" as const,
          label: "MIXED FINDINGS",
          border: "border-indigo-500/40",
          bg: "bg-indigo-500/10",
          text: "text-indigo-400",
          desc: "Multiple claims with divergent supported and contradicted findings."
        };
      case "UNVERIFIED":
        return {
          variant: "cyan" as const,
          label: "UNVERIFIED",
          border: "border-cyan-500/40",
          bg: "bg-cyan-500/10",
          text: "text-cyan-400",
          desc: "Contextual reporting found, but insufficient direct proof."
        };
      case "INSUFFICIENT_EVIDENCE":
      default:
        return {
          variant: "slate" as const,
          label: "INSUFFICIENT EVIDENCE",
          border: "border-slate-500/40",
          bg: "bg-slate-500/10",
          text: "text-slate-400",
          desc: "No relevant sources or verifiable statements found."
        };
    }
  };

  // Filtered evidence items
  const filteredEvidence = (result?.evidence || []).filter((item) => {
    if (evidenceFilter !== "ALL" && item.evidence_type !== evidenceFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchPassage = item.evidence_text?.toLowerCase().includes(q);
      const matchDomain = (item.domain || "").toLowerCase().includes(q);
      const matchTitle = (item.article_title || "").toLowerCase().includes(q);
      if (!matchPassage && !matchDomain && !matchTitle) return false;
    }
    return true;
  });

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

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <PageHeader
        title="Verify Information"
        description="Verify news statements, factual claims, and image text against multi-source evidence."
        badgeText="Digital Trust AI"
        badgeVariant="cyan"
        icon={ShieldCheck}
      />

      {/* 1 & 2: Simplified Text Input & Image Upload Card */}
      <Card className="p-6 md:p-8">
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Spacious Textarea */}
          <div className="relative">
            <textarea
              rows={5}
              value={claimText}
              onChange={(e) => setClaimText(e.target.value)}
              placeholder="Paste news or claim to verify..."
              className="w-full rounded-2xl border border-slate-200 dark:border-surface-borderDark bg-slate-50/50 dark:bg-surface-cardDark px-4 py-3.5 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 transition-all resize-y min-h-[140px]"
            />
            {/* Subtle Character Counter Aligned Bottom-Right */}
            <div className="text-[11px] font-mono text-slate-400 dark:text-slate-500 text-right mt-1 px-1">
              {characterCount.toLocaleString()} / {maxCharacters.toLocaleString()} chars
            </div>
          </div>

          {/* Small Image Preview with Remove Button */}
          {selectedImage && imagePreviewUrl && (
            <div className="flex items-center justify-between p-3 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50/70 dark:bg-slate-900/40">
              <div className="flex items-center gap-3 min-w-0">
                <img
                  src={imagePreviewUrl}
                  alt="Upload preview"
                  className="w-12 h-12 rounded-lg object-cover border border-slate-200 dark:border-slate-700 shrink-0"
                />
                <div className="min-w-0">
                  <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 truncate">
                    {selectedImage.name}
                  </p>
                  <p className="text-[11px] text-slate-500 font-mono">
                    {(selectedImage.size / (1024 * 1024)).toFixed(2)} MB &bull;{" "}
                    {selectedImage.type.split("/")[1]?.toUpperCase() || "IMAGE"}
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleRemoveImage}
                className="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                title="Remove image"
                aria-label="Remove image"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Error Alert */}
          {errorMsg && (
            <Alert variant="error">
              {errorMsg}
            </Alert>
          )}

          {/* Action Row */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <div>
              <input
                type="file"
                ref={fileInputRef}
                accept="image/png,image/jpeg,image/webp"
                onChange={handleImageChange}
                className="hidden"
              />
              <Button
                type="button"
                variant="outline"
                size="md"
                onClick={() => fileInputRef.current?.click()}
                className="text-xs gap-2 border-slate-200 dark:border-surface-borderDark hover:border-cyan-500/50"
              >
                <ImageIcon className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                <span>Upload Image</span>
              </Button>
            </div>

            <div className="flex items-center gap-2">
              {(claimText || selectedImage) && (
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
                disabled={isSubmitting || (!claimText.trim() && !selectedImage)}
                className="text-xs gap-2 shadow-xs"
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Verifying...</span>
                  </>
                ) : (
                  <>
                    <ShieldCheck className="w-4 h-4" />
                    <span>Verify Information</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </form>
      </Card>

      {/* 4. Verification Results Layout */}
      {result && (
        <section className="space-y-6">
          {/* Verdict Card with Medium-Sized Circular Confidence Graph on Right */}
          <div className="rounded-2xl border border-slate-200/90 dark:border-surface-borderDark bg-white dark:bg-[#0c1427] p-6 shadow-xs space-y-5">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
              {/* Left: Overall Verdict & Concise Explanation */}
              <div className="space-y-3 flex-1 min-w-0">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                    Overall Verification Verdict
                  </span>
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge variant={getVerdictBadgeProps(result.verdict?.overall_verdict || "UNVERIFIED").variant} size="md">
                      {result.verdict?.overall_verdict || "UNVERIFIED"}
                    </Badge>
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                      {getVerdictBadgeProps(result.verdict?.overall_verdict || "UNVERIFIED").desc}
                    </span>
                  </div>
                </div>

                {/* Concise Explanation */}
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/50 border border-slate-200/70 dark:border-slate-800 text-xs sm:text-sm text-slate-700 dark:text-slate-300 leading-relaxed">
                  <p className="font-semibold text-slate-900 dark:text-slate-100 mb-1">Executive Summary:</p>
                  <p>{result.verdict?.summary || result.message}</p>
                </div>

                {/* Claim Breakdown Badges */}
                {result.verdict && (
                  <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                    <span className="text-[11px] text-slate-400 mr-1">Claim Findings:</span>
                    {result.verdict.supported_count > 0 && (
                      <Badge variant="emerald" size="sm">{result.verdict.supported_count} Supported</Badge>
                    )}
                    {result.verdict.contradicted_count > 0 && (
                      <Badge variant="rose" size="sm">{result.verdict.contradicted_count} Contradicted</Badge>
                    )}
                    {result.verdict.misleading_count > 0 && (
                      <Badge variant="amber" size="sm">{result.verdict.misleading_count} Misleading</Badge>
                    )}
                    {result.verdict.unverified_count > 0 && (
                      <Badge variant="cyan" size="sm">{result.verdict.unverified_count} Unverified</Badge>
                    )}
                    {result.verdict.insufficient_count > 0 && (
                      <Badge variant="slate" size="sm">{result.verdict.insufficient_count} Insufficient</Badge>
                    )}
                  </div>
                )}
              </div>

              {/* Right: Medium-Sized Circular Confidence Graph */}
              <div className="flex flex-col items-center justify-center p-4 rounded-2xl bg-slate-50/70 dark:bg-slate-900/60 border border-slate-200/80 dark:border-surface-borderDark shrink-0 self-center md:self-stretch">
                <div className="relative w-24 h-24 flex items-center justify-center">
                  <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 100 100">
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
                      strokeDashoffset={238.76 - (overallConfidence * 238.76)}
                      strokeLinecap="round"
                      fill="none"
                      style={{ transition: "stroke-dashoffset 0.8s ease-in-out" }}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                    <span className="text-xl font-bold font-mono text-slate-900 dark:text-white leading-none">
                      {confidencePercent}%
                    </span>
                    <span className="text-[10px] uppercase font-semibold text-slate-400 mt-1">
                      Confidence
                    </span>
                  </div>
                </div>
                <span className="text-xs font-semibold text-slate-600 dark:text-slate-300 mt-2">
                  {confidenceLevelText} Confidence
                </span>
              </div>
            </div>

            {/* Quick action bar */}
            <div className="flex items-center justify-between pt-3 border-t border-slate-200/70 dark:border-slate-800 text-xs">
              <span className="text-slate-400 font-mono">
                Request #{result.request_id} &bull; {result.claims_count} claims &bull; {result.sources_count || 0} sources
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleFinalizeAll}
                disabled={isFinalizing}
                className="text-xs gap-1.5"
              >
                <RefreshCw className={`w-3 h-3 ${isFinalizing ? "animate-spin" : ""}`} />
                <span>{isFinalizing ? "Re-Evaluating..." : "Re-Evaluate Dossier"}</span>
              </Button>
            </div>
          </div>

          {/* 3. Conditional Image Analysis: Displayed ONLY when an image was uploaded */}
          {isImageUploaded && (
            <Card className="p-6 border-cyan-500/30 bg-cyan-500/5 dark:bg-cyan-950/10 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-cyan-500/20">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 flex items-center justify-center border border-cyan-500/30">
                    <ImageIcon className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                      Image Analysis & OCR Extraction
                    </h4>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      Optical character recognition and visual claim extraction
                    </p>
                  </div>
                </div>

                {selectedImage && (
                  <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                    {selectedImage.name} &bull; {(selectedImage.size / (1024 * 1024)).toFixed(2)} MB
                  </span>
                )}
              </div>

              <div className="flex flex-col sm:flex-row gap-4 items-start">
                {imagePreviewUrl && (
                  <div className="w-28 h-28 rounded-xl overflow-hidden border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-900 shrink-0">
                    <img
                      src={imagePreviewUrl}
                      alt="Uploaded screenshot"
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}

                <div className="flex-1 min-w-0 space-y-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block">
                    Extracted Text:
                  </span>

                  {ocrResult?.raw_text && ocrResult.raw_text.trim().length > 0 ? (
                    <div className="p-3.5 rounded-xl bg-white dark:bg-slate-900/80 border border-slate-200 dark:border-slate-800 text-xs sm:text-sm font-mono text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
                      {ocrResult.raw_text}
                    </div>
                  ) : (
                    <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-700 dark:text-amber-300 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 shrink-0" />
                      <span>No readable text was detected in the uploaded image.</span>
                    </div>
                  )}

                  {ocrResult && (
                    <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-slate-500 font-mono">
                      <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        {ocrResult.word_count || 0} words extracted
                      </span>
                      <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                        {Math.round(ocrResult.ocr_confidence * 100)}% OCR Legibility
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          )}

          {/* List of Reliable Sources Checked */}
          <Card className="p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-surface-borderDark">
              <div className="flex items-center gap-2">
                <Globe className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Reliable Sources Checked ({result.sources?.length || 0})
                </h4>
              </div>
              <span className="text-[11px] text-slate-400">
                Multi-source corroboration
              </span>
            </div>

            {(!result.sources || result.sources.length === 0) ? (
              <div className="p-6 text-center text-xs text-slate-400">
                No external sources were retrieved for this submission.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {result.sources.map((source, sIdx) => (
                  <div
                    key={sIdx}
                    className="p-4 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50/50 dark:bg-slate-900/30 flex flex-col justify-between gap-2.5 hover:border-cyan-500/40 transition-colors"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <span className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">
                          {source.publisher || source.domain || "Web Source"}
                        </span>
                        <Badge variant={source.credibility_score && source.credibility_score >= 0.8 ? "emerald" : "cyan"} size="sm">
                          {source.credibility_rating || source.source_type || "Verified Source"}
                        </Badge>
                      </div>

                      <p className="text-xs text-slate-700 dark:text-slate-300 font-medium line-clamp-2">
                        {source.title || "Untitled Article"}
                      </p>

                      {source.snippet && (
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2 italic">
                          &ldquo;{source.snippet}&rdquo;
                        </p>
                      )}
                    </div>

                    <a
                      href={sanitizeHref(source.url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-cyan-600 dark:text-cyan-400 hover:underline pt-2 border-t border-slate-200/60 dark:border-slate-800"
                    >
                      <span>Visit Source Article</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Evidence Supporting or Contradicting the Submitted Claim */}
          <Card className="p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-surface-borderDark">
              <div className="flex items-center gap-2">
                <FileCheck2 className="w-4 h-4 text-emerald-500" />
                <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Evidence Stance Evaluation ({result.evidence?.length || 0} citations)
                </h4>
              </div>

              {/* Filter Pills */}
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setEvidenceFilter("ALL")}
                  className={`text-[11px] px-2.5 py-1 rounded-lg font-medium transition-colors ${
                    evidenceFilter === "ALL"
                      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400"
                  }`}
                >
                  All
                </button>
                <button
                  type="button"
                  onClick={() => setEvidenceFilter("SUPPORTING")}
                  className={`text-[11px] px-2.5 py-1 rounded-lg font-medium transition-colors ${
                    evidenceFilter === "SUPPORTING"
                      ? "bg-emerald-600 text-white"
                      : "bg-slate-100 dark:bg-slate-800 text-emerald-600 dark:text-emerald-400"
                  }`}
                >
                  Supporting
                </button>
                <button
                  type="button"
                  onClick={() => setEvidenceFilter("CONTRADICTING")}
                  className={`text-[11px] px-2.5 py-1 rounded-lg font-medium transition-colors ${
                    evidenceFilter === "CONTRADICTING"
                      ? "bg-rose-600 text-white"
                      : "bg-slate-100 dark:bg-slate-800 text-rose-600 dark:text-rose-400"
                  }`}
                >
                  Contradicting
                </button>
              </div>
            </div>

            {filteredEvidence.length === 0 ? (
              <div className="p-6 text-center text-xs text-slate-400">
                No evidence items match the selected filter.
              </div>
            ) : (
              <div className="space-y-3">
                {filteredEvidence.map((ev, eIdx) => {
                  const isSupporting = ev.evidence_type === "SUPPORTING";
                  const isContradicting = ev.evidence_type === "CONTRADICTING";
                  const borderClass = isSupporting
                    ? "border-l-4 border-l-emerald-500 bg-emerald-50/30 dark:bg-emerald-950/15"
                    : isContradicting
                    ? "border-l-4 border-l-rose-500 bg-rose-50/30 dark:bg-rose-950/15"
                    : "border-l-4 border-l-slate-400 bg-slate-50/50 dark:bg-slate-900/30";

                  return (
                    <div
                      key={eIdx}
                      className={`p-4 rounded-r-xl border border-slate-200 dark:border-surface-borderDark ${borderClass} space-y-2`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <Badge
                          variant={isSupporting ? "emerald" : isContradicting ? "rose" : "slate"}
                          size="sm"
                        >
                          {ev.evidence_type}
                        </Badge>

                        <span className="text-[11px] font-mono text-slate-500">
                          Stance Confidence: {Math.round((ev.stance_confidence || 0.8) * 100)}%
                        </span>
                      </div>

                      <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed italic">
                        &ldquo;{ev.evidence_text}&rdquo;
                      </p>

                      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500 pt-1 border-t border-slate-200/50 dark:border-slate-800">
                        <span>Source: <strong className="text-slate-700 dark:text-slate-300">{ev.publisher || ev.domain || "External Media"}</strong></span>
                        {ev.url && (
                          <a
                            href={sanitizeHref(ev.url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1"
                          >
                            <span>View Passage</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </Card>

          {/* Claim-by-Claim Breakdown (if multiple claims) */}
          {(result.claims && result.claims.length > 1) && (
            <Card className="p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-surface-borderDark">
                <div className="flex items-center gap-2">
                  <Layers className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
                  <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Extracted Claims Breakdown ({result.claims.length})
                  </h4>
                </div>
              </div>

              <div className="space-y-3">
                {result.claims.map((claim, idx) => {
                  const claimVerdict = (result.claim_verdicts || []).find((v) => v.claim_id === claim.db_id);
                  const verdictProps = claimVerdict ? getVerdictBadgeProps(claimVerdict.verdict) : null;

                  return (
                    <div
                      key={idx}
                      className="p-4 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50/40 dark:bg-slate-900/30 space-y-2"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-bold text-slate-500">
                          Claim #{idx + 1}
                        </span>
                        {claimVerdict && verdictProps && (
                          <Badge variant={verdictProps.variant} size="sm">
                            {claimVerdict.verdict} &bull; {Math.round(claimVerdict.confidence * 100)}%
                          </Badge>
                        )}
                      </div>

                      <p className="text-xs sm:text-sm font-medium text-slate-900 dark:text-slate-100">
                        &ldquo;{claim.text}&rdquo;
                      </p>

                      {claimVerdict?.explanation && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed pt-1 border-t border-slate-200/50 dark:border-slate-800">
                          {claimVerdict.explanation}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>
          )}
        </section>
      )}
    </div>
  );
}
