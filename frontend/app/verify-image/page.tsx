"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Image as ImageIcon,
  Globe,
  Send,
  RotateCcw,
  ShieldCheck,
  AlertTriangle,
  Info,
  CheckCircle2,
  ExternalLink,
  Lock,
  Search,
  FileText,
  Clock,
  Layers,
  Calendar,
  Building,
  Scale,
  GitCompare,
  FileCheck2,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  AlertCircle,
  HelpCircle,
  Hash,
  ShieldAlert,
  ArrowRight,
  Eye,
  Scan,
  Maximize2,
  AtSign,
  Share2,
  SlidersHorizontal
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { FileDropzone } from "@/components/ui/FileDropzone";
import { sanitizeHref } from "@/lib/utils";
import { verifyImageFile } from "@/lib/api";
import {
  ImageVerificationResponse,
  ExtractedClaimItem,
  DiscoveredSourceItem,
  EvidenceItem,
  SourceComparisonItem,
  ClaimVerdictItem,
  RequestVerdictResult,
  VerdictType,
  OCRBlockItem
} from "@/types/api";

const PIPELINE_STAGES = [
  { id: 1, label: "Security & Magic Byte Validation", desc: "Validating real JPEG/PNG/WEBP headers & decompression bomb limits" },
  { id: 2, label: "EXIF Privacy Sanitization", desc: "Extracting camera info while stripping GPS & device serial numbers" },
  { id: 3, label: "Image Preprocessing", desc: "Orientation normalization, grayscale conversion & contrast enhancement" },
  { id: 4, label: "Multi-Engine OCR Extraction", desc: "Capturing spatial bounding blocks, word confidence & cleaning text" },
  { id: 5, label: "Context & URL Detection", desc: "Extracting visible URLs, social handles (@...), metrics & dates" },
  { id: 6, label: "Verifiable Claim Extraction", desc: "Decomposing OCR statements into atomic verifiable claims (Part 3)" },
  { id: 7, label: "Multi-Source Corroboration & Verdict", desc: "Web search, evidence stance analysis & verdict synthesis (Parts 4-6)" },
];

export default function VerifyImagePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [performSearch, setPerformSearch] = useState(true);
  const [extractEvidence, setExtractEvidence] = useState(true);
  const [finalizeVerdicts, setFinalizeVerdicts] = useState(true);
  const [maxClaims, setMaxClaims] = useState(5);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeStage, setActiveStage] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<ImageVerificationResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"verdict" | "ocr" | "claims" | "sources" | "evidence" | "comparisons" | "forensics">("verdict");
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedText, setCopiedText] = useState(false);
  const [selectedBlockIndex, setSelectedBlockIndex] = useState<number | null>(null);

  // Generate preview when file is selected
  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  // Animate pipeline stages during submission
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isSubmitting) {
      setActiveStage(1);
      timer = setInterval(() => {
        setActiveStage((prev) => {
          if (prev < 6) return prev + 1;
          return prev;
        });
      }, 1300);
    } else {
      setActiveStage(0);
    }
    return () => clearInterval(timer);
  }, [isSubmitting]);

  // Quick Sample Generator (creates client-side image files for instant one-click testing)
  const loadSampleImage = (type: "finance" | "social") => {
    const canvas = document.createElement("canvas");
    canvas.width = 800;
    canvas.height = 450;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    if (type === "finance") {
      // Create News Screenshot Card
      ctx.fillStyle = "#0f172a";
      ctx.fillRect(0, 0, 800, 450);

      // Header Bar
      ctx.fillStyle = "#1e293b";
      ctx.fillRect(0, 0, 800, 60);
      ctx.fillStyle = "#06b6d4";
      ctx.font = "bold 20px sans-serif";
      ctx.fillText("FINANCIAL CHRONICLE — BREAKING DESK", 30, 38);

      // Headline
      ctx.fillStyle = "#f8fafc";
      ctx.font = "bold 26px sans-serif";
      ctx.fillText("Central Bank Lowers Benchmark Interest Rate by 2%", 30, 130);

      // Body Text
      ctx.fillStyle = "#cbd5e1";
      ctx.font = "18px sans-serif";
      ctx.fillText("The monetary policy committee voted unanimously to reduce rates.", 30, 180);
      ctx.fillText("Inflation targets projected at 4.2% for the upcoming fiscal quarter.", 30, 215);
      ctx.fillText("Official communiqué published at https://reuters.com/markets/rate-cut", 30, 260);

      // Footer
      ctx.fillStyle = "#64748b";
      ctx.font = "14px sans-serif";
      ctx.fillText("Source: Reuters Wire Service · Sep 28, 2026 · Verified Bulletin", 30, 400);

      canvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], "financial_rate_cut_news.png", { type: "image/png" });
          setSelectedFile(file);
          setErrorMessage(null);
          setResult(null);
        }
      }, "image/png");
    } else {
      // Create Social Media Screenshot
      ctx.fillStyle = "#020617";
      ctx.fillRect(0, 0, 800, 450);

      // Tweet Card Background
      ctx.fillStyle = "#0f172a";
      ctx.roundRect(40, 30, 720, 390, 16);
      ctx.fill();

      // User Info
      ctx.fillStyle = "#38bdf8";
      ctx.font = "bold 22px sans-serif";
      ctx.fillText("Ministry of Health News", 70, 80);
      ctx.fillStyle = "#94a3b8";
      ctx.font = "16px sans-serif";
      ctx.fillText("@HealthMinistry · Sep 28, 2026", 70, 110);

      // Tweet Text
      ctx.fillStyle = "#f1f5f9";
      ctx.font = "20px sans-serif";
      ctx.fillText("New national wellness initiatives will grant universal coverage", 70, 165);
      ctx.fillText("for essential diagnostics starting October 2026 across all states.", 70, 200);
      ctx.fillText("Read policy draft at https://pib.gov.in/press-release-health-2026", 70, 245);

      // Engagement Metrics
      ctx.fillStyle = "#64748b";
      ctx.font = "bold 15px sans-serif";
      ctx.fillText("14.5K Reposts      82.1K Likes      1.4M Views", 70, 340);

      canvas.toBlob((blob) => {
        if (blob) {
          const file = new File([blob], "social_media_health_policy.png", { type: "image/png" });
          setSelectedFile(file);
          setErrorMessage(null);
          setResult(null);
        }
      }, "image/png");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage("Please select or drop an image file to verify.");
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const response = await verifyImageFile(
        selectedFile,
        performSearch,
        extractEvidence,
        finalizeVerdicts,
        maxClaims
      );
      setResult(response);
      setActiveTab("verdict");
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to process image verification.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setResult(null);
    setErrorMessage(null);
    setActiveTab("verdict");
    setSelectedBlockIndex(null);
  };

  const copyToClipboard = (text: string, type: "hash" | "text") => {
    navigator.clipboard.writeText(text);
    if (type === "hash") {
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    } else {
      setCopiedText(true);
      setTimeout(() => setCopiedText(false), 2000);
    }
  };

  const getVerdictBadge = (verdict?: string) => {
    switch (verdict) {
      case "SUPPORTED":
        return <Badge variant="emerald" size="md">SUPPORTED</Badge>;
      case "CONTRADICTED":
        return <Badge variant="rose" size="md">CONTRADICTED</Badge>;
      case "MISLEADING":
        return <Badge variant="amber" size="md">MISLEADING</Badge>;
      case "MIXED":
        return <Badge variant="indigo" size="md">MIXED VERDICT</Badge>;
      case "UNVERIFIED":
        return <Badge variant="outline" size="md">UNVERIFIED</Badge>;
      case "INSUFFICIENT_EVIDENCE":
      default:
        return <Badge variant="slate" size="md">INSUFFICIENT EVIDENCE</Badge>;
    }
  };

  return (
    <div className="space-y-8 max-w-6xl pb-16">
      <PageHeader
        title="Verify Image & Screenshot Claims"
        description="Inspect news card graphics, social media screenshots, quote cards, and infographics. Extracts recognized text, detects visible URLs, and verifies claims against independent sources."
        badgeText="Part 8 Operational"
        badgeVariant="cyan"
        icon={ImageIcon}
      />

      {/* Scope & Methodology Disclosure */}
      <Alert variant="info" title="Dual-Confidence Principle & Forensic Distinction">
        <div className="space-y-1 text-xs leading-relaxed">
          <p>
            <strong>1. OCR Recognition Clarity $\neq$ Factual Truth:</strong> Clear character extraction means the text is legible; it does not mean the assertion is factually truthful. TruthLens displays two distinct confidence meters: <em>OCR Clarity</em> and <em>Evidence Corroboration</em>.
          </p>
          <p>
            <strong>2. Image Authenticity Boundary:</strong> Corroborating a claim verifies the factual statements against independent journalism. It does not certify that the image pixels themselves are untampered or free from digital manipulation.
          </p>
        </div>
      </Alert>

      {/* Main Upload Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Scan className="w-4 h-4 text-cyan-500" />
                Upload Image or Screenshot
              </CardTitle>
              <CardDescription>
                Supports JPEG, PNG, WEBP, and GIF up to 15MB. Automatic decompression bomb protection enforced.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 dark:text-slate-400">Try Sample:</span>
              <button
                type="button"
                onClick={() => loadSampleImage("finance")}
                className="px-2.5 py-1 text-xs font-medium rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/20 transition-colors"
              >
                News Screenshot
              </button>
              <button
                type="button"
                onClick={() => loadSampleImage("social")}
                className="px-2.5 py-1 text-xs font-medium rounded-lg border border-indigo-500/30 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-500/20 transition-colors"
              >
                Social Media Post
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <FileDropzone
                accept="image/jpeg,image/png,image/webp,image/gif"
                mediaType="image"
                maxSizeMB={15}
                onFileSelect={(file) => {
                  setSelectedFile(file);
                  setErrorMessage(null);
                  setResult(null);
                }}
              />
            </div>

            {/* Selected File Preview Box */}
            {selectedFile && previewUrl && (
              <div className="p-4 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-slate-900/40 flex flex-col sm:flex-row items-center gap-4">
                <div className="relative w-36 h-24 rounded-lg overflow-hidden border border-slate-300 dark:border-slate-700 bg-black/40 shrink-0">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={previewUrl}
                    alt="Preview"
                    className="w-full h-full object-contain"
                  />
                </div>
                <div className="space-y-1 text-xs flex-1">
                  <div className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                    <span>{selectedFile.name}</span>
                    <Badge variant="cyan" size="sm">{selectedFile.type || "image"}</Badge>
                  </div>
                  <div className="text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                    Size: {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </div>
                  <div className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1 text-[11px]">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Integrity checked: Safe for OCR extraction</span>
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleReset}
                  className="shrink-0"
                >
                  <RotateCcw className="w-3.5 h-3.5 mr-1" />
                  Clear
                </Button>
              </div>
            )}

            {/* Verification Pipeline Options */}
            <div className="p-4 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50/50 dark:bg-surface-cardDark/30 space-y-3">
              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <SlidersHorizontal className="w-3.5 h-3.5 text-cyan-500" />
                Pipeline Execution Controls
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={performSearch}
                    onChange={(e) => setPerformSearch(e.target.checked)}
                    className="rounded border-slate-300 text-cyan-600 focus:ring-cyan-500"
                  />
                  <span>Independent Web Search (Part 4)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={extractEvidence}
                    onChange={(e) => setExtractEvidence(e.target.checked)}
                    className="rounded border-slate-300 text-cyan-600 focus:ring-cyan-500"
                  />
                  <span>Evidence Extraction (Part 5)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={finalizeVerdicts}
                    onChange={(e) => setFinalizeVerdicts(e.target.checked)}
                    className="rounded border-slate-300 text-cyan-600 focus:ring-cyan-500"
                  />
                  <span>Synthesize Verdicts (Part 6)</span>
                </label>
              </div>
            </div>

            {errorMessage && (
              <Alert variant="error" title="Verification Error">
                {errorMessage}
              </Alert>
            )}

            <div className="flex justify-end gap-3 pt-2">
              <Button
                type="submit"
                variant="primary"
                size="md"
                disabled={isSubmitting || !selectedFile}
                className="w-full sm:w-auto gap-2"
              >
                <Send className="w-4 h-4" />
                <span>{isSubmitting ? "Inspecting & Corroborating..." : "Verify Image Claims"}</span>
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Pipeline Progress Stages */}
      {isSubmitting && (
        <Card className="border-cyan-500/40 bg-cyan-950/10">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2 text-cyan-600 dark:text-cyan-400">
              <Sparkles className="w-4 h-4 animate-spin" />
              Forensic & Claim Verification Pipeline Active
            </CardTitle>
            <CardDescription>
              Processing image stages sequentially...
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {PIPELINE_STAGES.map((st) => {
                const isDone = activeStage > st.id;
                const isCurrent = activeStage === st.id;
                return (
                  <div
                    key={st.id}
                    className={`flex items-start gap-3 p-2.5 rounded-lg transition-all text-xs ${
                      isCurrent
                        ? "bg-cyan-500/10 border border-cyan-500/30 text-cyan-950 dark:text-cyan-200"
                        : isDone
                        ? "text-slate-700 dark:text-slate-300 opacity-80"
                        : "text-slate-400 opacity-40"
                    }`}
                  >
                    <div className="mt-0.5">
                      {isDone ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      ) : isCurrent ? (
                        <div className="w-4 h-4 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-slate-400 flex items-center justify-center text-[10px]">
                          {st.id}
                        </div>
                      )}
                    </div>
                    <div>
                      <div className="font-semibold">{st.label}</div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400">{st.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results Section */}
      {result && (
        <div className="space-y-6">
          {/* Dual Confidence Meters */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* 1. OCR Text Clarity */}
            <Card className="border-cyan-500/30 bg-gradient-to-br from-cyan-500/5 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Scan className="w-5 h-5 text-cyan-500" />
                    <div>
                      <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        Meter 1: Optical Text Clarity
                      </div>
                      <div className="text-sm font-bold text-slate-900 dark:text-white">
                        OCR Recognition Confidence
                      </div>
                    </div>
                  </div>
                  <div className="text-2xl font-black font-mono text-cyan-600 dark:text-cyan-400">
                    {result.ocr.ocr_confidence.toFixed(1)}%
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-slate-200 dark:bg-slate-800 h-2.5 rounded-full overflow-hidden mb-3">
                  <div
                    className="bg-cyan-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(100, Math.max(5, result.ocr.ocr_confidence))}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
                  <span>Engine: {result.forensics.ocr_engine}</span>
                  <span>{result.ocr.word_count} words recognized</span>
                </div>
                <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 leading-tight">
                  High score indicates clear typography and legible characters. Does not imply truth.
                </p>
              </CardContent>
            </Card>

            {/* 2. Factual Evidence Corroboration */}
            <Card className="border-indigo-500/30 bg-gradient-to-br from-indigo-500/5 to-transparent">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Scale className="w-5 h-5 text-indigo-500" />
                    <div>
                      <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        Meter 2: Factual Corroboration
                      </div>
                      <div className="text-sm font-bold text-slate-900 dark:text-white">
                        Evidence Credibility Score
                      </div>
                    </div>
                  </div>
                  <div className="text-2xl font-black font-mono text-indigo-600 dark:text-indigo-400">
                    {result.verdicts
                      ? `${(result.verdicts.overall_confidence * 100).toFixed(1)}%`
                      : "N/A"}
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-slate-200 dark:bg-slate-800 h-2.5 rounded-full overflow-hidden mb-3">
                  <div
                    className="bg-indigo-500 h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${
                        result.verdicts
                          ? Math.min(100, Math.max(5, result.verdicts.overall_confidence * 100))
                          : 10
                      }%`
                    }}
                  />
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
                  <span>Dossier Verdict:</span>
                  <div>{getVerdictBadge(result.verdicts?.overall_verdict)}</div>
                </div>
                <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 leading-tight">
                  Mathematical aggregation of corroborating vs contradicting reporting from independent news.
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Detected URLs Banner (One-click jump to Part 7 URL verification) */}
          {result.ocr.detected_urls && result.ocr.detected_urls.length > 0 && (
            <div className="p-4 rounded-xl border border-cyan-500/40 bg-cyan-500/5 space-y-3">
              <div className="flex items-center gap-2 text-cyan-600 dark:text-cyan-400 font-bold text-xs uppercase tracking-wider">
                <Globe className="w-4 h-4" />
                <span>Detected URLs in Image ({result.ocr.detected_urls.length})</span>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-300">
                The OCR engine detected visible web URLs inside this screenshot. You can cross-verify the underlying article directly:
              </p>
              <div className="space-y-2">
                {result.ocr.detected_urls.map((detUrl, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900/80"
                  >
                    <div className="font-mono text-xs text-slate-800 dark:text-slate-200 break-all">
                      {detUrl}
                    </div>
                    <Link
                      href={`/verify-url?url=${encodeURIComponent(detUrl)}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white shrink-0 shadow-xs transition-colors"
                    >
                      <Search className="w-3.5 h-3.5" />
                      <span>Verify Detected URL (Part 7)</span>
                      <ArrowRight className="w-3 h-3" />
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Contextual Social Handles & Engagement Metrics */}
          {(result.ocr.detected_handles.length > 0 || Object.keys(result.ocr.detected_metrics).length > 0) && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {result.ocr.detected_handles.length > 0 && (
                <div className="p-3 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-surface-cardDark/50 text-xs space-y-1">
                  <div className="font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1">
                    <AtSign className="w-3.5 h-3.5 text-cyan-500" />
                    <span>Detected Social Handles</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {result.ocr.detected_handles.map((h, i) => (
                      <Badge key={i} variant="cyan" size="sm">{h}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {Object.keys(result.ocr.detected_metrics).length > 0 && (
                <div className="p-3 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-surface-cardDark/50 text-xs space-y-1">
                  <div className="font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1">
                    <Share2 className="w-3.5 h-3.5 text-indigo-500" />
                    <span>Detected Engagement Statistics</span>
                  </div>
                  <div className="flex flex-wrap gap-2 pt-1 font-mono text-[11px]">
                    {Object.entries(result.ocr.detected_metrics).map(([k, v], i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                        {v} {k}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Navigation Tabs */}
          <div className="flex items-center gap-2 border-b border-slate-200 dark:border-surface-borderDark pb-2 overflow-x-auto text-xs font-medium">
            <button
              onClick={() => setActiveTab("verdict")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "verdict"
                  ? "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-bold border border-cyan-500/30"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              Overall Verdict & Synthesis
            </button>
            <button
              onClick={() => setActiveTab("ocr")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "ocr"
                  ? "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-bold border border-cyan-500/30"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              OCR Text & Blocks ({result.ocr.blocks.length})
            </button>
            <button
              onClick={() => setActiveTab("claims")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "claims"
                  ? "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-bold border border-cyan-500/30"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              Extracted Claims ({result.claims_count})
            </button>
            <button
              onClick={() => setActiveTab("sources")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "sources"
                  ? "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-bold border border-cyan-500/30"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              Discovered Sources ({result.sources_count})
            </button>
            <button
              onClick={() => setActiveTab("evidence")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "evidence"
                  ? "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-bold border border-cyan-500/30"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              Traceable Evidence ({result.evidence_count})
            </button>
            <button
              onClick={() => setActiveTab("comparisons")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "comparisons"
                  ? "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-bold border border-cyan-500/30"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              Source Comparisons ({result.comparisons.length})
            </button>
            <button
              onClick={() => setActiveTab("forensics")}
              className={`px-3 py-1.5 rounded-lg transition-all ${
                activeTab === "forensics"
                  ? "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-bold border border-cyan-500/30"
                  : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              Technical Forensics
            </button>
          </div>

          {/* TAB 1: OVERALL VERDICT */}
          {activeTab === "verdict" && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Scale className="w-5 h-5 text-indigo-500" />
                        Executive Verification Verdict
                      </CardTitle>
                      <CardDescription>
                        Synthesized dossier covering {result.claims_count} extracted assertions
                      </CardDescription>
                    </div>
                    {getVerdictBadge(result.verdicts?.overall_verdict)}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="p-4 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-surface-cardDark/50 text-sm leading-relaxed text-slate-800 dark:text-slate-200">
                    {result.verdicts?.summary || "No executive summary generated."}
                  </div>

                  {/* Verdict Stats Breakdown */}
                  {result.verdicts && (
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 text-center">
                      <div className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5">
                        <div className="text-xs text-slate-500 dark:text-slate-400">Supported</div>
                        <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                          {result.verdicts.supported_count}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg border border-rose-500/20 bg-rose-500/5">
                        <div className="text-xs text-slate-500 dark:text-slate-400">Contradicted</div>
                        <div className="text-lg font-bold text-rose-600 dark:text-rose-400">
                          {result.verdicts.contradicted_count}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg border border-amber-500/20 bg-amber-500/5">
                        <div className="text-xs text-slate-500 dark:text-slate-400">Misleading</div>
                        <div className="text-lg font-bold text-amber-600 dark:text-amber-400">
                          {result.verdicts.misleading_count}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg border border-purple-500/20 bg-purple-500/5">
                        <div className="text-xs text-slate-500 dark:text-slate-400">Unverified</div>
                        <div className="text-lg font-bold text-purple-600 dark:text-purple-400">
                          {result.verdicts.unverified_count}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg border border-slate-500/20 bg-slate-500/5 col-span-2 sm:col-span-1">
                        <div className="text-xs text-slate-500 dark:text-slate-400">Insufficient</div>
                        <div className="text-lg font-bold text-slate-600 dark:text-slate-400">
                          {result.verdicts.insufficient_count}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Limitations */}
                  {result.verdicts?.limitations && result.verdicts.limitations.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                        Investigation Limitations & Context
                      </div>
                      <ul className="space-y-1 text-xs text-slate-600 dark:text-slate-300">
                        {result.verdicts.limitations.map((lim, idx) => (
                          <li key={idx} className="flex items-start gap-2">
                            <span className="text-amber-500 font-bold">•</span>
                            <span>{lim}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Individual Claim Cards */}
              <div className="space-y-3">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                  Individual Claim Verifications ({result.claims.length})
                </div>
                {result.claims.map((claim, idx) => {
                  const claimVerdict = result.verdicts?.claims.find(
                    (cv) => cv.claim_id === claim.db_id || cv.claim_text === claim.text
                  );

                  return (
                    <Card key={idx} className="overflow-hidden">
                      <div className="p-4 space-y-3">
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="font-semibold text-sm text-slate-900 dark:text-white flex-1">
                            &ldquo;{claim.text}&rdquo;
                          </div>
                          {claimVerdict && getVerdictBadge(claimVerdict.verdict)}
                        </div>

                        {claimVerdict && (
                          <div className="p-3 rounded-lg border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-surface-cardDark/50 text-xs space-y-1 text-slate-700 dark:text-slate-300">
                            <div><strong>Reasoning:</strong> {claimVerdict.explanation}</div>
                            <div className="text-slate-500 text-[11px]">
                              Evidence Strength: {claimVerdict.evidence_strength} · Confidence: {(claimVerdict.confidence * 100).toFixed(1)}%
                            </div>
                          </div>
                        )}

                        <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500">
                          <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800">
                            Type: {claim.claim_type}
                          </span>
                          <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800">
                            Verifiability: {claim.verifiability}
                          </span>
                          {claim.dates.length > 0 && (
                            <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800">
                              Dates: {claim.dates.join(", ")}
                            </span>
                          )}
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </div>
          )}

          {/* TAB 2: OCR TEXT & BLOCKS */}
          {activeTab === "ocr" && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base flex items-center gap-2">
                        <FileText className="w-4 h-4 text-cyan-500" />
                        Normalized OCR Claim Text
                      </CardTitle>
                      <CardDescription>
                        Reconstructed typography used for claim decomposition
                      </CardDescription>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(result.ocr.normalized_text, "text")}
                    >
                      {copiedText ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-500 mr-1" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5 mr-1" />
                          Copy Text
                        </>
                      )}
                    </Button>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="p-4 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-slate-900/60 font-mono text-xs whitespace-pre-wrap leading-relaxed text-slate-800 dark:text-slate-200 max-h-72 overflow-y-auto">
                    {result.ocr.normalized_text || "No text extracted from image."}
                  </div>
                </CardContent>
              </Card>

              {/* Spatial Word Blocks Inspector */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Scan className="w-4 h-4 text-indigo-500" />
                    Spatial Recognized Blocks ({result.ocr.blocks.length})
                  </CardTitle>
                  <CardDescription>
                    Per-word bounding boxes `[x, y, w, h]` and clarity metrics
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="max-h-80 overflow-y-auto space-y-1.5">
                    {result.ocr.blocks.map((block, idx) => (
                      <div
                        key={idx}
                        onClick={() => setSelectedBlockIndex(idx)}
                        className={`flex items-center justify-between p-2 rounded-lg border text-xs cursor-pointer transition-all ${
                          selectedBlockIndex === idx
                            ? "border-cyan-500 bg-cyan-500/10 text-cyan-900 dark:text-cyan-100 font-semibold"
                            : "border-slate-200 dark:border-surface-borderDark hover:bg-slate-50 dark:hover:bg-slate-800/40"
                        }`}
                      >
                        <div className="font-mono">{block.text}</div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[11px] text-slate-400">
                            [{block.bbox.join(", ")}]
                          </span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                              block.confidence >= 80
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                : block.confidence >= 50
                                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                : "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                            }`}
                          >
                            {block.confidence.toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* TAB 3: EXTRACTED CLAIMS */}
          {activeTab === "claims" && (
            <div className="space-y-3">
              {result.claims.map((claim, idx) => (
                <Card key={idx}>
                  <CardContent className="pt-4 space-y-2 text-xs">
                    <div className="font-semibold text-sm text-slate-900 dark:text-white">
                      &ldquo;{claim.text}&rdquo;
                    </div>
                    <div className="text-slate-500 dark:text-slate-400">
                      <strong>Original Context:</strong> {claim.original_sentence}
                    </div>
                    <div className="flex flex-wrap items-center gap-2 pt-1 font-mono text-[11px]">
                      <Badge variant="cyan" size="sm">{claim.claim_type}</Badge>
                      <Badge variant="indigo" size="sm">{claim.verifiability}</Badge>
                      <Badge variant="slate" size="sm">Priority: {claim.importance}</Badge>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* TAB 4: DISCOVERED SOURCES */}
          {activeTab === "sources" && (
            <div className="space-y-3">
              {result.sources.length === 0 ? (
                <Card>
                  <CardContent className="pt-6 text-center text-xs text-slate-500">
                    No web sources retrieved. Search may have been disabled or yielded no matching pages.
                  </CardContent>
                </Card>
              ) : (
                result.sources.map((src, idx) => (
                  <Card key={idx}>
                    <CardContent className="pt-4 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="font-bold text-sm text-slate-900 dark:text-white">
                          {src.title}
                        </div>
                        <Badge variant="cyan" size="sm">{src.source_type}</Badge>
                      </div>
                      <div className="text-cyan-600 dark:text-cyan-400 font-mono text-[11px] truncate">
                        <a href={sanitizeHref(src.url)} target="_blank" rel="noopener noreferrer" className="hover:underline flex items-center gap-1">
                          {src.url}
                          <ExternalLink className="w-3 h-3 inline" />
                        </a>
                      </div>
                      <p className="text-slate-600 dark:text-slate-300">
                        {src.snippet}
                      </p>
                      <div className="flex items-center gap-4 text-[11px] text-slate-500 pt-1">
                        <span>Domain: {src.domain}</span>
                        {src.published_at && <span>Published: {src.published_at}</span>}
                        <span>Provider: {src.provider}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* TAB 5: TRACEABLE EVIDENCE */}
          {activeTab === "evidence" && (
            <div className="space-y-3">
              {result.evidence.length === 0 ? (
                <Card>
                  <CardContent className="pt-6 text-center text-xs text-slate-500">
                    No evidence items extracted.
                  </CardContent>
                </Card>
              ) : (
                result.evidence.map((ev, idx) => (
                  <Card key={idx}>
                    <CardContent className="pt-4 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-900 dark:text-white">
                          Source: {ev.domain || ev.article_title || "External Source"}
                        </div>
                        <Badge
                          variant={
                            ev.evidence_type === "SUPPORTING"
                              ? "emerald"
                              : ev.evidence_type === "CONTRADICTING"
                              ? "rose"
                              : "amber"
                          }
                          size="sm"
                        >
                          {ev.evidence_type}
                        </Badge>
                      </div>
                      <blockquote className="p-3 rounded-lg border-l-4 border-cyan-500 bg-slate-50 dark:bg-slate-900/40 text-slate-700 dark:text-slate-300 italic">
                        &ldquo;{ev.evidence_text || ev.snippet}&rdquo;
                      </blockquote>
                      {ev.explanation && (
                        <div className="text-slate-600 dark:text-slate-400">
                          <strong>Stance Rationale:</strong> {ev.explanation}
                        </div>
                      )}
                      <div className="text-[11px] text-slate-500 flex items-center gap-3">
                        <span>Stance Confidence: {(ev.stance_confidence * 100).toFixed(0)}%</span>
                        <span>Relevance: {(ev.relevance_score * 100).toFixed(0)}%</span>
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* TAB 6: SOURCE COMPARISONS */}
          {activeTab === "comparisons" && (
            <div className="space-y-3">
              {result.comparisons.length === 0 ? (
                <Card>
                  <CardContent className="pt-6 text-center text-xs text-slate-500">
                    No cross-source comparisons computed.
                  </CardContent>
                </Card>
              ) : (
                result.comparisons.map((cmp, idx) => (
                  <Card key={idx}>
                    <CardContent className="pt-4 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-slate-900 dark:text-white">
                          {cmp.source_a_domain || "Source A"} vs {cmp.source_b_domain || "Source B"}
                        </div>
                        <Badge variant="indigo" size="sm">{cmp.evidence_consistency}</Badge>
                      </div>
                      <p className="text-slate-600 dark:text-slate-300">
                        {cmp.details || cmp.analysis_summary || "Consistent reporting verified."}
                      </p>
                      <div className="text-[11px] text-slate-500">
                        Relationship: {cmp.source_relationship} · Type: {cmp.comparison_type}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* TAB 7: TECHNICAL FORENSICS */}
          {activeTab === "forensics" && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-cyan-500" />
                  Image Technical Forensics & Integrity
                </CardTitle>
                <CardDescription>
                  Cryptographic fingerprints, dimensions, and sanitized camera metadata
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-xs">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-surface-cardDark space-y-2">
                    <div className="font-bold text-slate-700 dark:text-slate-300">File Properties</div>
                    <div><strong>Dimensions:</strong> {result.forensics.image_width} x {result.forensics.image_height} px</div>
                    <div><strong>Format:</strong> {result.forensics.image_format}</div>
                    <div><strong>Size:</strong> {(result.forensics.file_size_bytes / (1024 * 1024)).toFixed(2)} MB</div>
                    <div><strong>Filename:</strong> {result.forensics.original_filename}</div>
                  </div>

                  <div className="p-3 rounded-lg border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-surface-cardDark space-y-2">
                    <div className="font-bold text-slate-700 dark:text-slate-300">Preprocessing Operations</div>
                    <div><strong>Orientation Corrected:</strong> {result.forensics.preprocessing_applied.orientation_corrected ? "Yes" : "No"}</div>
                    <div><strong>Grayscale Applied:</strong> {result.forensics.preprocessing_applied.grayscale_applied ? "Yes" : "No"}</div>
                    <div><strong>Contrast Enhanced:</strong> {result.forensics.preprocessing_applied.contrast_enhanced ? "Yes" : "No"}</div>
                    <div><strong>Rescaled:</strong> {result.forensics.preprocessing_applied.rescaled ? "Yes" : "No"}</div>
                  </div>
                </div>

                {/* SHA-256 Hash */}
                <div className="p-3 rounded-lg border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-surface-cardDark space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-700 dark:text-slate-300">SHA-256 Content Fingerprint</span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(result.forensics.file_hash_sha256, "hash")}
                      className="text-cyan-600 dark:text-cyan-400 hover:underline flex items-center gap-1 text-[11px]"
                    >
                      {copiedHash ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                      <span>{copiedHash ? "Copied" : "Copy Hash"}</span>
                    </button>
                  </div>
                  <div className="font-mono text-[11px] text-slate-500 break-all">
                    {result.forensics.file_hash_sha256}
                  </div>
                </div>

                {/* Sanitized EXIF Tags */}
                <div className="p-3 rounded-lg border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-surface-cardDark space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-700 dark:text-slate-300">Sanitized EXIF Metadata</span>
                    <Badge variant="emerald" size="sm">GPS Coordinates Stripped</Badge>
                  </div>
                  {result.forensics.sanitized_exif && Object.keys(result.forensics.sanitized_exif.technical_tags || {}).length > 0 ? (
                    <div className="space-y-1 font-mono text-[11px]">
                      {Object.entries(result.forensics.sanitized_exif.technical_tags).map(([k, v]) => (
                        <div key={k}>
                          <strong>{k}:</strong> {String(v)}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-slate-500 text-[11px]">
                      No camera EXIF metadata found or image was sanitized.
                    </div>
                  )}
                </div>

                {/* Disclaimer */}
                <Alert variant="info" title="Technical Boundaries Notice">
                  {result.authenticity_disclaimer}
                </Alert>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
