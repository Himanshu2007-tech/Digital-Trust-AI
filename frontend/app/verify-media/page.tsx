"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  Mic,
  Film,
  Play,
  Pause,
  RotateCcw,
  Volume2,
  Clock,
  Sparkles,
  ExternalLink,
  Shield,
  ShieldCheck,
  AlertTriangle,
  Info,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Search,
  Scale,
  GitCompare,
  FileCheck2,
  Copy,
  Check,
  Layers,
  FileText,
  SlidersHorizontal,
  Hash,
  Globe,
  Quote,
  Eye,
  ArrowRight,
  Maximize2,
  Video,
  Image as ImageIcon,
  Calendar,
  X,
  FastForward,
  Rewind,
  AlertOctagon,
  FileSearch,
  Activity,
  Layers2
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { FileDropzone } from "@/components/ui/FileDropzone";
import { sanitizeHref } from "@/lib/utils";
import { verifyMediaFile } from "@/lib/api";
import {
  MediaVerificationResponse,
  TranscriptSegmentItem,
  MediaExtractedClaimItem,
  DiscoveredSourceItem,
  EvidenceItem,
  SourceComparisonItem,
  ClaimVerdictItem,
  RequestVerdictResult,
  VideoFrameItem,
  ClaimOccurrenceItem,
  TimelineEventItem,
  AudioVisualAlignmentReport,
  ReusedFootageReport,
  SearchQueryAuditItem
} from "@/types/api";

const PIPELINE_STAGES = [
  { id: 1, label: "Security & Magic Byte Validation", desc: "Validating container signatures (MP3/WAV/MP4/MOV/WEBM) & size limits" },
  { id: 2, label: "Container & Stream Inspection", desc: "Extracting audio/video codecs, channels, bitrate, and silent video checks" },
  { id: 3, label: "Keyframe Sampling & OCR", desc: "Sampling video keyframes, extracting on-screen text, tickers & graphics (Part 10)" },
  { id: 4, label: "Speech-to-Text Transcription", desc: "High-precision acoustic transcription with atomic timestamped segments" },
  { id: 5, label: "Multimodal Claim Extraction & Fusion", desc: "Fusing speech & on-screen claims with occurrence tracking (Parts 3 & 10)" },
  { id: 6, label: "Audio-Visual Alignment & Reused Footage", desc: "Building unified timeline, thematic alignment & database footage check" },
  { id: 7, label: "Multi-Source Corroboration & Verdict", desc: "Web search, evidence stance analysis & Bayesian verdict synthesis (Parts 4-6)" },
];

type TabType =
  | "verdict"
  | "media"
  | "timeline"
  | "transcript"
  | "keyframes"
  | "visual_text"
  | "claims"
  | "evidence"
  | "sources"
  | "technical"
  | "search_audit";

export default function VerifyMediaPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [mediaType, setMediaType] = useState<"audio" | "video">("audio");
  const [performSearch, setPerformSearch] = useState(true);
  const [extractEvidence, setExtractEvidence] = useState(true);
  const [finalizeVerdicts, setFinalizeVerdicts] = useState(true);
  const [maxClaims, setMaxClaims] = useState(5);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeStage, setActiveStage] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<MediaVerificationResponse | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>("verdict");
  const [copiedHash, setCopiedHash] = useState(false);
  const [copiedTranscript, setCopiedTranscript] = useState(false);
  const [selectedFrameModal, setSelectedFrameModal] = useState<VideoFrameItem | null>(null);

  // Playback state
  const mediaRef = useRef<HTMLVideoElement | HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [activeSegmentIndex, setActiveSegmentIndex] = useState<number | null>(null);

  // Generate preview when file is selected
  useEffect(() => {
    if (!selectedFile) {
      setPreviewUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(selectedFile);
    setPreviewUrl(objectUrl);
    setMediaType(selectedFile.type.startsWith("video") ? "video" : "audio");
    return () => URL.revokeObjectURL(objectUrl);
  }, [selectedFile]);

  // Track playback time to highlight current transcript segment
  const handleTimeUpdate = () => {
    if (mediaRef.current) {
      const time = mediaRef.current.currentTime;
      setCurrentTime(time);

      if (result?.transcription?.segments) {
        const segIdx = result.transcription.segments.findIndex(
          (s) => time >= s.start_time && time <= s.end_time
        );
        setActiveSegmentIndex(segIdx !== -1 ? segIdx : null);
      }
    }
  };

  const handleLoadedMetadata = () => {
    if (mediaRef.current) {
      setDuration(mediaRef.current.duration);
    }
  };

  const seekToTime = (seconds: number) => {
    if (mediaRef.current) {
      mediaRef.current.currentTime = Math.max(0, seconds);
      mediaRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const jumpSeconds = (delta: number) => {
    if (mediaRef.current) {
      const target = Math.max(0, Math.min(duration || 9999, (mediaRef.current.currentTime || 0) + delta));
      seekToTime(target);
    }
  };

  // Pipeline animation
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isSubmitting) {
      setActiveStage(1);
      timer = setInterval(() => {
        setActiveStage((prev) => (prev < 7 ? prev + 1 : prev));
      }, 1200);
    } else {
      setActiveStage(0);
    }
    return () => clearInterval(timer);
  }, [isSubmitting]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage("Please select or drop an audio or video file to verify.");
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const response = await verifyMediaFile(
        selectedFile,
        performSearch,
        extractEvidence,
        finalizeVerdicts,
        maxClaims
      );
      setResult(response);
      setActiveTab("verdict");
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to process media verification.");
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
    setIsPlaying(false);
    setCurrentTime(0);
    setActiveSegmentIndex(null);
    setSelectedFrameModal(null);
  };

  const copyToClipboard = (text: string, type: "hash" | "transcript") => {
    navigator.clipboard.writeText(text);
    if (type === "hash") {
      setCopiedHash(true);
      setTimeout(() => setCopiedHash(false), 2000);
    } else {
      setCopiedTranscript(true);
      setTimeout(() => setCopiedTranscript(false), 2000);
    }
  };

  // Synthetic sample generator for quick zero-asset demonstration
  const loadSampleMedia = (type: "audio" | "video") => {
    const sampleRate = 44100;
    const durationSec = 3.0;
    const numSamples = sampleRate * durationSec;
    const buffer = new ArrayBuffer(44 + numSamples * 2);
    const view = new DataView(buffer);

    // RIFF WAV Header
    const writeString = (offset: number, str: string) => {
      for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
      }
    };

    writeString(0, "RIFF");
    view.setUint32(4, 36 + numSamples * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, numSamples * 2, true);

    // Simple 440Hz sine wave tone
    for (let i = 0; i < numSamples; i++) {
      const sample = Math.sin((i / sampleRate) * 440 * 2 * Math.PI) * 0.25 * 32767;
      view.setInt16(44 + i * 2, sample, true);
    }

    const blob = new Blob([buffer], { type: "audio/wav" });
    const file = new File([blob], "sample_press_briefing.wav", { type: "audio/wav" });
    setSelectedFile(file);
    setMediaType("audio");
    setErrorMessage(null);
    setResult(null);
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

  const getOriginBadge = (origin?: string) => {
    switch (origin) {
      case "MULTIMODAL":
        return <Badge variant="indigo" size="sm">SPEECH + VISUAL MATCH</Badge>;
      case "VISUAL_OCR":
        return <Badge variant="purple" size="sm">ON-SCREEN GRAPHIC</Badge>;
      case "AUDIO_TRANSCRIPT":
      default:
        return <Badge variant="cyan" size="sm">SPOKEN IN AUDIO</Badge>;
    }
  };

  const formatSeconds = (sec: number) => {
    const mins = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${mins.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  // Collect aggregated visual text metrics across keyframes
  const aggregatedVisualStats = (() => {
    if (!result?.frames || result.frames.length === 0) return null;
    let totalOcrWords = 0;
    const tickerFrames: VideoFrameItem[] = [];
    const documentFrames: VideoFrameItem[] = [];
    const chartFrames: VideoFrameItem[] = [];
    const detectedLogos: string[] = [];

    result.frames.forEach((f) => {
      if (f.ocr_text) {
        totalOcrWords += f.ocr_text.split(/\s+/).filter(Boolean).length;
      }
      if (f.visual_context?.contains_ticker_or_headline) {
        tickerFrames.push(f);
      }
      if (f.visual_context?.contains_document_or_screenshot) {
        documentFrames.push(f);
      }
      if (f.visual_context?.contains_chart_or_table) {
        chartFrames.push(f);
      }
      if (f.visual_context?.detected_logos_or_badges) {
        f.visual_context.detected_logos_or_badges.forEach((l) => {
          if (!detectedLogos.includes(l)) detectedLogos.push(l);
        });
      }
    });

    return {
      framesCount: result.frames.length,
      totalOcrWords,
      tickerCount: tickerFrames.length,
      documentCount: documentFrames.length,
      chartCount: chartFrames.length,
      detectedLogos,
    };
  })();

  return (
    <div className="space-y-8 max-w-6xl pb-16">
      <PageHeader
        title="Verify Audio & Video Claims"
        description="Advanced multimedia verification engine. Samples key video frames, extracts on-screen text and graphics, transcribes spoken speech, aligns audio-visual claims chronologically, and corroborates against authoritative web sources."
        badgeText="Part 10 Multimedia Operational"
        badgeVariant="cyan"
        icon={Film}
      />

      {/* Scope & Methodology Disclosure */}
      <Alert variant="info" title="Dual-Confidence Principle & Forensic Distinction">
        <div className="space-y-1 text-xs leading-relaxed">
          <p>
            <strong>1. Speech Recognition Clarity &ne; Factual Truth:</strong> Clear acoustic transcription means the speaker is intelligible; it does not indicate whether what was spoken is factually truthful. TruthLens strictly isolates two distinct confidence meters: <em>Acoustic Transcription Clarity</em> and <em>Evidence Corroboration</em>.
          </p>
          <p>
            <strong>2. Multimedia Visual Extraction:</strong> On-screen text, tickers, graphics, and documents visible in video keyframes are recognized via OCR and analyzed as observable context. Personal identities and digital authenticity are never fabricated.
          </p>
          <p>
            <strong>3. Media Authenticity Boundary:</strong> Corroborating a spoken or visual statement against news sources verifies factual truth. It does not certify that the audio or video recording itself is unedited, free from synthetic voice cloning, or untampered. Container properties are labeled strictly as &ldquo;Technical Indicators&rdquo;.
          </p>
        </div>
      </Alert>

      {/* Main Upload Card */}
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Film className="w-4 h-4 text-cyan-500" />
                Upload Audio or Video File
              </CardTitle>
              <CardDescription>
                Supports MP3, WAV, M4A, AAC, OGG (audio up to 50MB) and MP4, MOV, WEBM, MKV (video up to 200MB). Video frames sampled at 5s intervals and scene boundaries.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 dark:text-slate-400">Try Sample:</span>
              <button
                type="button"
                onClick={() => loadSampleMedia("audio")}
                className="px-2.5 py-1 text-xs font-medium rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/20 transition-colors"
              >
                Press Briefing (Audio)
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <FileDropzone
                accept="audio/mpeg,audio/wav,audio/ogg,audio/x-m4a,audio/aac,video/mp4,video/quicktime,video/webm,video/x-matroska"
                mediaType="any"
                maxSizeMB={200}
                onFileSelect={(file) => {
                  setSelectedFile(file);
                  setErrorMessage(null);
                  setResult(null);
                }}
              />
            </div>

            {/* Selected File & Media Player Preview Box */}
            {selectedFile && previewUrl && (
              <div className="p-4 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50 dark:bg-slate-900/40 space-y-4">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div className="space-y-0.5 text-xs">
                    <div className="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
                      <span>{selectedFile.name}</span>
                      <Badge variant="cyan" size="sm">
                        {selectedFile.type || (mediaType === "video" ? "video/mp4" : "audio/wav")}
                      </Badge>
                      <Badge variant="slate" size="sm">
                        {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                      </Badge>
                    </div>
                    <div className="text-slate-500 dark:text-slate-400 font-mono text-[11px]">
                      Playback position: {formatSeconds(currentTime)} / {formatSeconds(duration || 0)}
                    </div>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleReset}
                    className="text-xs"
                  >
                    <RotateCcw className="w-3.5 h-3.5 mr-1" />
                    Replace File
                  </Button>
                </div>

                {/* Built-in HTML5 Media Player */}
                <div className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800 bg-black/90 p-2 flex flex-col items-center">
                  {mediaType === "video" ? (
                    <video
                      ref={mediaRef as React.RefObject<HTMLVideoElement>}
                      src={previewUrl}
                      controls
                      onTimeUpdate={handleTimeUpdate}
                      onLoadedMetadata={handleLoadedMetadata}
                      onPlay={() => setIsPlaying(true)}
                      onPause={() => setIsPlaying(false)}
                      className="w-full max-h-[320px] rounded object-contain"
                    />
                  ) : (
                    <div className="w-full py-2 px-2 flex flex-col items-center gap-2">
                      <div className="flex items-center gap-2 text-cyan-400 text-xs font-mono">
                        <Volume2 className="w-4 h-4 animate-pulse" />
                        <span>Interactive Audio Inspector</span>
                      </div>
                      <audio
                        ref={mediaRef as React.RefObject<HTMLAudioElement>}
                        src={previewUrl}
                        controls
                        onTimeUpdate={handleTimeUpdate}
                        onLoadedMetadata={handleLoadedMetadata}
                        onPlay={() => setIsPlaying(true)}
                        onPause={() => setIsPlaying(false)}
                        className="w-full"
                      />
                    </div>
                  )}

                  {/* Player Quick Seek Controls */}
                  <div className="flex items-center gap-2 mt-2 pt-2 border-t border-slate-800 w-full justify-center">
                    <button
                      type="button"
                      onClick={() => jumpSeconds(-5)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
                    >
                      <Rewind className="w-3 h-3" />
                      -5s
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        if (mediaRef.current) {
                          if (isPlaying) {
                            mediaRef.current.pause();
                            setIsPlaying(false);
                          } else {
                            mediaRef.current.play();
                            setIsPlaying(true);
                          }
                        }
                      }}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white transition-colors"
                    >
                      {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3 fill-current" />}
                      {isPlaying ? "Pause" : "Play"}
                    </button>
                    <button
                      type="button"
                      onClick={() => jumpSeconds(5)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
                    >
                      +5s
                      <FastForward className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Pipeline Configuration Options */}
            <div className="p-4 rounded-xl border border-slate-200 dark:border-surface-borderDark bg-slate-50/50 dark:bg-slate-900/20 space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-900 dark:text-white">
                <SlidersHorizontal className="w-3.5 h-3.5 text-cyan-500" />
                <span>Verification Pipeline Options</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={performSearch}
                    onChange={(e) => setPerformSearch(e.target.checked)}
                    className="rounded border-slate-300 dark:border-slate-700 text-cyan-500 focus:ring-cyan-500"
                  />
                  <span>Web Search (Part 4)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={extractEvidence}
                    onChange={(e) => setExtractEvidence(e.target.checked)}
                    className="rounded border-slate-300 dark:border-slate-700 text-cyan-500 focus:ring-cyan-500"
                  />
                  <span>Evidence Extraction (Part 5)</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-slate-700 dark:text-slate-300">
                  <input
                    type="checkbox"
                    checked={finalizeVerdicts}
                    onChange={(e) => setFinalizeVerdicts(e.target.checked)}
                    className="rounded border-slate-300 dark:border-slate-700 text-cyan-500 focus:ring-cyan-500"
                  />
                  <span>Verdict Engine (Part 6)</span>
                </label>
                <div className="flex items-center gap-2 text-slate-700 dark:text-slate-300">
                  <span>Max Claims:</span>
                  <select
                    value={maxClaims}
                    onChange={(e) => setMaxClaims(Number(e.target.value))}
                    className="rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2 py-1 text-xs"
                  >
                    <option value={1}>1 Claim</option>
                    <option value={3}>3 Claims</option>
                    <option value={5}>5 Claims</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Error Message Alert */}
            {errorMessage && (
              <Alert variant="error" title="Verification Error">
                {errorMessage}
              </Alert>
            )}

            {/* Submit Actions */}
            <div className="flex items-center justify-between pt-2">
              <div className="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-cyan-500" />
                <span>Audited cryptographic SHA-256 fingerprinting applied.</span>
              </div>
              <Button
                type="submit"
                variant="primary"
                disabled={!selectedFile || isSubmitting}
                className="px-6"
              >
                {isSubmitting ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin mr-2" />
                    Analyzing Multimedia & Verifying...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4 mr-2" />
                    Analyze & Verify Media
                  </>
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Real-Time Processing Pipeline Stage Card */}
      {isSubmitting && (
        <Card className="border-cyan-500/30 bg-cyan-500/5">
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2 text-cyan-600 dark:text-cyan-400">
              <span className="w-2 h-2 rounded-full bg-cyan-500 animate-ping" />
              Automated Forensic, Multimedia & Corroboration Pipeline in Progress
            </CardTitle>
            <CardDescription className="text-xs">
              Executing container security check, keyframe sampling & OCR, speech transcription, multimodal claim fusion, and multi-source web search.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {PIPELINE_STAGES.map((stg) => {
                const isDone = activeStage > stg.id;
                const isCurrent = activeStage === stg.id;
                return (
                  <div
                    key={stg.id}
                    className={`flex items-start gap-3 p-2.5 rounded-lg border text-xs transition-colors ${
                      isDone
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
                        : isCurrent
                        ? "border-cyan-500/50 bg-cyan-500/15 text-cyan-800 dark:text-cyan-200 shadow-sm"
                        : "border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20 text-slate-400"
                    }`}
                  >
                    <div className="mt-0.5 shrink-0">
                      {isDone ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                      ) : isCurrent ? (
                        <div className="w-4 h-4 rounded-full border-2 border-cyan-500 border-t-transparent animate-spin" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-slate-400 dark:border-slate-600 flex items-center justify-center text-[10px]">
                          {stg.id}
                        </div>
                      )}
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold">{stg.label}</div>
                      <div className="text-[11px] opacity-80">{stg.desc}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Verification Result Dossier */}
      {result && !isSubmitting && (
        <div className="space-y-6 animate-fadeIn">
          {/* Executive Header Banner */}
          <div className="p-6 rounded-2xl border border-slate-200 dark:border-surface-borderDark bg-white dark:bg-surface-cardDark shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <Badge variant="cyan" size="sm">Request #{result.request_id}</Badge>
                  <Badge variant="outline" size="sm">{result.forensics.media_type.toUpperCase()}</Badge>
                  {result.frames_count ? (
                    <Badge variant="purple" size="sm">{result.frames_count} Keyframes Analyzed</Badge>
                  ) : null}
                  {result.transcription.is_code_switched && (
                    <Badge variant="indigo" size="sm">Code-Switching (Hinglish)</Badge>
                  )}
                  <Badge variant="slate" size="sm">Lang: {result.transcription.language.toUpperCase()}</Badge>
                </div>
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                  Multimedia Claim Verification Dossier
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {result.forensics.original_filename} &bull; {result.forensics.duration_seconds.toFixed(1)}s duration &bull; {result.transcription.word_count} spoken words &bull; {result.frames_count || 0} sampled frames
                </p>
              </div>

              {/* Overall Verdict Badge */}
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-[11px] uppercase tracking-wider text-slate-400 font-mono">
                    Synthesized Verdict
                  </div>
                  <div className="mt-0.5">
                    {getVerdictBadge(result.verdicts?.overall_verdict)}
                  </div>
                </div>
              </div>
            </div>

            {/* DUAL CONFIDENCE METERS DISPLAY */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Meter 1: Acoustic Transcription Clarity */}
              <div className="p-4 rounded-xl border border-cyan-500/20 bg-cyan-500/5 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-cyan-700 dark:text-cyan-300">
                    <Volume2 className="w-4 h-4 text-cyan-500" />
                    <span>Acoustic Transcription Clarity</span>
                  </div>
                  <Badge variant="cyan" size="sm">
                    {result.transcription.confidence_category}
                  </Badge>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
                    {result.transcription.transcription_confidence.toFixed(1)}%
                  </span>
                  <span className="text-xs text-slate-500">Acoustic clarity score</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-cyan-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(100, result.transcription.transcription_confidence)}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-snug">
                  Measures acoustic signal clarity and word-level decoding confidence. Does <strong>not</strong> indicate factual truth.
                </p>
              </div>

              {/* Meter 2: Journalistic Evidence Corroboration */}
              <div className="p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-700 dark:text-emerald-300">
                    <Scale className="w-4 h-4 text-emerald-500" />
                    <span>Evidence Corroboration Confidence</span>
                  </div>
                  <Badge variant="emerald" size="sm">
                    Part 6 Bayesian Engine
                  </Badge>
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
                    {result.verdicts ? `${(result.verdicts.overall_confidence * 100).toFixed(1)}%` : "N/A"}
                  </span>
                  <span className="text-xs text-slate-500">Fact-checking credibility</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, (result.verdicts?.overall_confidence || 0) * 100)}%`,
                    }}
                  />
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-snug">
                  Mathematical confidence derived from multi-source cross-referencing against independent journalistic reporting.
                </p>
              </div>
            </div>

            {/* Journalistic Boundary Notice */}
            <div className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/30 text-xs text-slate-600 dark:text-slate-400 flex items-start gap-2">
              <Info className="w-4 h-4 text-cyan-500 shrink-0 mt-0.5" />
              <span>{result.authenticity_disclaimer}</span>
            </div>
          </div>

          {/* ALL 11 SPECIFIED DOSSIER TABS */}
          <div className="flex items-center gap-1.5 border-b border-slate-200 dark:border-surface-borderDark overflow-x-auto pb-2 scrollbar-none">
            {[
              { id: "verdict", label: "Verdict", count: result.verdicts?.claims_count },
              { id: "media", label: "Media Player", count: null },
              { id: "timeline", label: "Timeline", count: result.timeline?.length || 0 },
              { id: "transcript", label: "Transcript", count: result.transcription.segments.length },
              { id: "keyframes", label: "Key Frames", count: result.frames?.length || result.frames_count || 0 },
              { id: "visual_text", label: "Visual Text", count: aggregatedVisualStats ? aggregatedVisualStats.tickerCount + aggregatedVisualStats.documentCount : null },
              { id: "claims", label: "Claims", count: result.claims_count },
              { id: "evidence", label: "Evidence", count: result.evidence_count },
              { id: "sources", label: "Sources", count: result.sources_count },
              { id: "technical", label: "Technical Analysis", count: null },
              { id: "search_audit", label: "Search Audit", count: result.queries?.length || 0 },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as TabType)}
                className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                  activeTab === tab.id
                    ? "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30 shadow-sm"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/60"
                }`}
              >
                <span>{tab.label}</span>
                {tab.count !== null && tab.count !== undefined && (
                  <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 font-mono">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* TAB 1: VERDICT */}
          {activeTab === "verdict" && (
            <div className="space-y-6">
              {result.verdicts && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Scale className="w-4 h-4 text-emerald-500" />
                      Executive Verdict Summary
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-serif">
                      {result.verdicts.summary}
                    </p>

                    {/* Breakdown pill counters */}
                    <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-2">
                      <div className="p-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 text-center">
                        <div className="text-xs text-emerald-600 font-bold font-mono">
                          {result.verdicts.supported_count}
                        </div>
                        <div className="text-[10px] text-slate-500 uppercase">Supported</div>
                      </div>
                      <div className="p-2.5 rounded-lg border border-rose-500/20 bg-rose-500/5 text-center">
                        <div className="text-xs text-rose-600 font-bold font-mono">
                          {result.verdicts.contradicted_count}
                        </div>
                        <div className="text-[10px] text-slate-500 uppercase">Contradicted</div>
                      </div>
                      <div className="p-2.5 rounded-lg border border-amber-500/20 bg-amber-500/5 text-center">
                        <div className="text-xs text-amber-600 font-bold font-mono">
                          {result.verdicts.misleading_count}
                        </div>
                        <div className="text-[10px] text-slate-500 uppercase">Misleading</div>
                      </div>
                      <div className="p-2.5 rounded-lg border border-slate-500/20 bg-slate-500/5 text-center">
                        <div className="text-xs text-slate-600 font-bold font-mono">
                          {result.verdicts.unverified_count}
                        </div>
                        <div className="text-[10px] text-slate-500 uppercase">Unverified</div>
                      </div>
                      <div className="p-2.5 rounded-lg border border-indigo-500/20 bg-indigo-500/5 text-center">
                        <div className="text-xs text-indigo-600 font-bold font-mono">
                          {result.verdicts.insufficient_count}
                        </div>
                        <div className="text-[10px] text-slate-500 uppercase">Insufficient</div>
                      </div>
                    </div>

                    {/* Limitations & Methodology Notes */}
                    {result.verdicts.limitations && result.verdicts.limitations.length > 0 && (
                      <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40 text-xs space-y-1">
                        <div className="font-semibold text-slate-700 dark:text-slate-300">Dossier Limitations:</div>
                        <ul className="list-disc list-inside space-y-0.5 text-slate-500 dark:text-slate-400">
                          {result.verdicts.limitations.map((lim, i) => (
                            <li key={i}>{lim}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {/* Extracted Fused Claims Preview */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <Quote className="w-4 h-4 text-cyan-500" />
                      Multimodal Claims ({result.claims.length})
                    </span>
                    <span className="text-xs text-slate-500 font-normal">
                      Click timestamp to seek playback
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {result.claims.map((clm, idx) => (
                    <div
                      key={clm.id || idx}
                      className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-2 hover:border-cyan-500/40 transition-colors"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge variant="cyan" size="sm">Claim #{idx + 1}</Badge>
                          {getOriginBadge(clm.primary_origin)}
                          {clm.formatted_timestamp && (
                            <button
                              type="button"
                              onClick={() => seekToTime(clm.start_time || 0)}
                              className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30 transition-colors"
                            >
                              <Play className="w-2.5 h-2.5 fill-current" />
                              {clm.formatted_timestamp}
                            </button>
                          )}
                          <Badge variant="outline" size="sm">{clm.claim_type}</Badge>
                        </div>
                      </div>
                      <p className="text-sm font-medium text-slate-900 dark:text-white">
                        &ldquo;{clm.text}&rdquo;
                      </p>
                      {clm.occurrences && clm.occurrences.length > 1 && (
                        <div className="flex items-center gap-2 flex-wrap pt-1 text-[11px] text-slate-500">
                          <span className="font-semibold">Multiple Occurrences ({clm.occurrences.length}):</span>
                          {clm.occurrences.map((occ, oIdx) => (
                            <button
                              key={oIdx}
                              type="button"
                              onClick={() => seekToTime(occ.timestamp_start)}
                              className="px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-800 hover:bg-cyan-500/20 text-slate-700 dark:text-slate-300 font-mono transition-colors"
                            >
                              {occ.source_type === "VISUAL_OCR" ? "Visual @ " : "Audio @ "}
                              {occ.formatted_timestamp || `${occ.timestamp_start.toFixed(0)}s`}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>

              {/* Spoken URLs Detected */}
              {result.transcription.detected_urls && result.transcription.detected_urls.length > 0 && (
                <Card className="border-cyan-500/30">
                  <CardHeader>
                    <CardTitle className="text-sm flex items-center gap-2 text-cyan-600 dark:text-cyan-400">
                      <Globe className="w-4 h-4" />
                      Spoken URLs Detected in Transcript ({result.transcription.detected_urls.length})
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Web addresses mentioned aloud in the media. Click to cross-verify directly in the Part 7 URL Engine.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {result.transcription.detected_urls.map((url, i) => (
                      <div
                        key={i}
                        className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex items-center justify-between gap-3 text-xs"
                      >
                        <div className="font-mono text-cyan-600 dark:text-cyan-400 truncate">
                          {url}
                        </div>
                        <Link
                          href={`/verify-url?url=${encodeURIComponent(url)}`}
                          className="shrink-0 inline-flex items-center gap-1 px-3 py-1 rounded-md text-xs font-medium bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30 transition-colors"
                        >
                          Verify Detected URL
                          <ArrowRight className="w-3 h-3" />
                        </Link>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* TAB 2: MEDIA PLAYER */}
          {activeTab === "media" && (
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <CardTitle className="text-sm flex items-center gap-2">
                        <Video className="w-4 h-4 text-cyan-500" />
                        Interactive Media Playback Engine
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Precise atomic time tracking synchronized with claims, transcript segments, and video keyframes.
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2 text-xs font-mono text-cyan-600 dark:text-cyan-400">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{formatSeconds(currentTime)} / {formatSeconds(duration || result.forensics.duration_seconds)}</span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Player Canvas */}
                  <div className="rounded-xl overflow-hidden border border-slate-800 bg-black p-3 flex flex-col items-center">
                    {mediaType === "video" ? (
                      <video
                        ref={mediaRef as React.RefObject<HTMLVideoElement>}
                        src={previewUrl || undefined}
                        controls
                        onTimeUpdate={handleTimeUpdate}
                        onLoadedMetadata={handleLoadedMetadata}
                        onPlay={() => setIsPlaying(true)}
                        onPause={() => setIsPlaying(false)}
                        className="w-full max-h-[460px] rounded object-contain"
                      />
                    ) : (
                      <div className="w-full py-8 flex flex-col items-center gap-3">
                        <Volume2 className="w-8 h-8 text-cyan-400 animate-pulse" />
                        <span className="text-xs font-mono text-cyan-300">Synchronized Audio Channel</span>
                        <audio
                          ref={mediaRef as React.RefObject<HTMLAudioElement>}
                          src={previewUrl || undefined}
                          controls
                          onTimeUpdate={handleTimeUpdate}
                          onLoadedMetadata={handleLoadedMetadata}
                          onPlay={() => setIsPlaying(true)}
                          onPause={() => setIsPlaying(false)}
                          className="w-full max-w-lg mt-2"
                        />
                      </div>
                    )}

                    {/* Extended Player Quick Controls */}
                    <div className="flex items-center gap-3 mt-3 pt-3 border-t border-slate-800 w-full justify-center text-xs">
                      <button
                        type="button"
                        onClick={() => seekToTime(0)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                      >
                        Reset (00:00)
                      </button>
                      <button
                        type="button"
                        onClick={() => jumpSeconds(-10)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                      >
                        -10s
                      </button>
                      <button
                        type="button"
                        onClick={() => jumpSeconds(-5)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                      >
                        -5s
                      </button>
                      <button
                        type="button"
                        onClick={() => jumpSeconds(5)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                      >
                        +5s
                      </button>
                      <button
                        type="button"
                        onClick={() => jumpSeconds(10)}
                        className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                      >
                        +10s
                      </button>
                    </div>
                  </div>

                  {/* Media Technical Metadata Pill */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                    <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                      <span className="text-[10px] text-slate-400 font-mono uppercase">Dimensions / Resolution</span>
                      <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                        {result.forensics.width && result.forensics.height
                          ? `${result.forensics.width} &times; ${result.forensics.height}`
                          : "Audio-only Container"}
                      </div>
                    </div>
                    <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                      <span className="text-[10px] text-slate-400 font-mono uppercase">Codec</span>
                      <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                        {result.forensics.video_codec || result.forensics.audio_codec || result.forensics.mime_type}
                      </div>
                    </div>
                    <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                      <span className="text-[10px] text-slate-400 font-mono uppercase">Sample Rate / Channels</span>
                      <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                        {result.forensics.sample_rate || 44100} Hz &bull; {result.forensics.channels || 1} ch
                      </div>
                    </div>
                    <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                      <span className="text-[10px] text-slate-400 font-mono uppercase">File Size</span>
                      <div className="font-semibold text-slate-800 dark:text-slate-200 mt-0.5">
                        {(result.forensics.file_size_bytes / (1024 * 1024)).toFixed(2)} MB
                      </div>
                    </div>
                  </div>

                  {/* Quick Timeline Markers Jump Bar */}
                  {result.timeline && result.timeline.length > 0 && (
                    <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20 space-y-2">
                      <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                        Quick Seek Markers ({result.timeline.length}):
                      </span>
                      <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto pr-1">
                        {result.timeline.map((evt, eIdx) => (
                          <button
                            key={eIdx}
                            type="button"
                            onClick={() => seekToTime(evt.timestamp)}
                            className="px-2 py-1 rounded text-[11px] font-mono bg-white dark:bg-slate-800 hover:bg-cyan-500/20 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:text-cyan-500 transition-colors flex items-center gap-1"
                          >
                            <Play className="w-2.5 h-2.5 fill-current" />
                            <span>{evt.formatted_timestamp}</span>
                            <span className="text-slate-400">({evt.label.substring(0, 15)}...)</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* TAB 3: TIMELINE */}
          {activeTab === "timeline" && (
            <Card>
              <CardHeader>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Activity className="w-4 h-4 text-cyan-500" />
                      Unified Chronological Media Timeline ({result.timeline?.length || 0} events)
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Chronologically sorted events combining spoken audio, keyframe scene transitions, recognized on-screen graphics, and extracted claims.
                    </CardDescription>
                  </div>
                  <Badge variant="cyan" size="sm">
                    {result.forensics.duration_seconds.toFixed(1)}s Total Duration
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {(!result.timeline || result.timeline.length === 0) ? (
                  <div className="p-8 text-center text-slate-500 text-xs">
                    No chronological timeline events constructed for this media item.
                  </div>
                ) : (
                  <div className="relative pl-6 border-l-2 border-slate-200 dark:border-slate-800 space-y-4">
                    {result.timeline.map((evt, idx) => {
                      const isClaim = evt.event_type === "VERIFIABLE_CLAIM";
                      const isKeyframe = evt.event_type === "KEYFRAME_SCENE";
                      const isVisualText = evt.event_type === "VISUAL_TEXT";

                      return (
                        <div
                          key={idx}
                          className="relative group p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/40 hover:border-cyan-500/40 transition-all space-y-1.5"
                        >
                          {/* Timeline node dot */}
                          <div className="absolute -left-[31px] top-4 w-3.5 h-3.5 rounded-full bg-cyan-500 border-2 border-white dark:border-slate-950 group-hover:scale-125 transition-transform" />

                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div className="flex items-center gap-2 flex-wrap">
                              <button
                                type="button"
                                onClick={() => seekToTime(evt.timestamp)}
                                className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30 transition-colors"
                              >
                                <Play className="w-2.5 h-2.5 fill-current" />
                                {evt.formatted_timestamp}
                              </button>

                              <Badge
                                variant={
                                  isClaim
                                    ? "emerald"
                                    : isKeyframe
                                    ? "amber"
                                    : isVisualText
                                    ? "purple"
                                    : "cyan"
                                }
                                size="sm"
                              >
                                {evt.event_type.replace(/_/g, " ")}
                              </Badge>

                              <span className="text-xs font-semibold text-slate-900 dark:text-white">
                                {evt.label}
                              </span>
                            </div>

                            {evt.confidence !== null && evt.confidence !== undefined && (
                              <span className="text-[10px] text-slate-400 font-mono">
                                Conf: {(evt.confidence * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>

                          <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed pl-1">
                            {evt.description}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* TAB 4: TRANSCRIPT */}
          {activeTab === "transcript" && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-sm flex items-center gap-2">
                      <FileText className="w-4 h-4 text-cyan-500" />
                      Timestamped Transcript Segments ({result.transcription.segments.length})
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Click any timestamp segment to synchronize the player to that exact playback moment.
                    </CardDescription>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => copyToClipboard(result.transcription.normalized_transcript, "transcript")}
                    className="text-xs"
                  >
                    {copiedTranscript ? (
                      <>
                        <Check className="w-3.5 h-3.5 mr-1 text-emerald-500" />
                        Copied Transcript
                      </>
                    ) : (
                      <>
                        <Copy className="w-3.5 h-3.5 mr-1" />
                        Copy Full Text
                      </>
                    )}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {result.transcription.segments.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 text-xs">
                    No speech segments detected (or silent media stream).
                  </div>
                ) : (
                  result.transcription.segments.map((seg, idx) => {
                    const isSegmentActive = activeSegmentIndex === idx;
                    return (
                      <div
                        key={idx}
                        onClick={() => seekToTime(seg.start_time)}
                        className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                          isSegmentActive
                            ? "border-cyan-500 bg-cyan-500/15 shadow-sm"
                            : "border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 hover:border-cyan-500/40"
                        }`}
                      >
                        <button
                          type="button"
                          className={`shrink-0 px-2 py-1 rounded text-xs font-mono font-bold flex items-center gap-1.5 transition-colors ${
                            isSegmentActive
                              ? "bg-cyan-500 text-white"
                              : "bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/20"
                          }`}
                        >
                          <Play className="w-2.5 h-2.5 fill-current" />
                          <span>{seg.formatted_timestamp}</span>
                        </button>

                        <div className="flex-1 space-y-1">
                          <p className="text-xs text-slate-900 dark:text-white leading-relaxed">
                            {seg.text}
                          </p>
                          {seg.confidence !== null && (
                            <div className="text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                              Acoustic Confidence: {((seg.confidence || 0) * 100).toFixed(0)}%
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </CardContent>
            </Card>
          )}

          {/* TAB 5: KEY FRAMES */}
          {activeTab === "keyframes" && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <CardTitle className="text-sm flex items-center gap-2">
                        <ImageIcon className="w-4 h-4 text-cyan-500" />
                        Sampled Video Keyframes ({result.frames?.length || result.frames_count || 0})
                      </CardTitle>
                      <CardDescription className="text-xs">
                        Extracted at fixed 5s intervals and scene change transitions. Click any keyframe to inspect full OCR text, word bounding blocks, and visual context.
                      </CardDescription>
                    </div>
                    {result.frames && result.frames.length > 0 && (
                      <Badge variant="cyan" size="sm">
                        Max {result.frames.length} Frames Evaluated
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {(!result.frames || result.frames.length === 0) ? (
                    <div className="p-8 text-center text-slate-500 text-xs">
                      No video keyframes sampled (Audio file uploaded or video stream contains zero decodable frames).
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {result.frames.map((frame, fIdx) => (
                        <div
                          key={frame.id || fIdx}
                          className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/40 hover:border-cyan-500/50 transition-all flex flex-col justify-between space-y-3"
                        >
                          <div className="space-y-2">
                            {/* Frame Header Bar */}
                            <div className="flex items-center justify-between gap-2">
                              <span className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200">
                                Frame #{frame.frame_number}
                              </span>
                              <Badge
                                variant={
                                  frame.selection_method === "SCENE_CHANGE"
                                    ? "amber"
                                    : frame.selection_method === "HIGH_TEXT_DENSITY"
                                    ? "purple"
                                    : "slate"
                                }
                                size="sm"
                              >
                                {frame.selection_method.replace(/_/g, " ")}
                              </Badge>
                            </div>

                            {/* Keyframe Visual Preview Box */}
                            <div className="relative rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-950 aspect-video flex items-center justify-center group">
                              <div className="flex flex-col items-center gap-1.5 text-slate-500 group-hover:text-cyan-400 transition-colors">
                                <Film className="w-8 h-8 opacity-75" />
                                <span className="text-[11px] font-mono">{frame.formatted_timestamp}</span>
                              </div>

                              <button
                                type="button"
                                onClick={() => seekToTime(frame.timestamp)}
                                className="absolute bottom-2 right-2 px-2 py-1 rounded bg-black/70 hover:bg-cyan-600 text-white text-[11px] font-mono flex items-center gap-1 transition-colors"
                              >
                                <Play className="w-2.5 h-2.5 fill-current" />
                                Seek {frame.formatted_timestamp}
                              </button>
                            </div>

                            {/* Visual Context Badges */}
                            {frame.visual_context && (
                              <div className="flex flex-wrap gap-1">
                                {frame.visual_context.contains_ticker_or_headline && (
                                  <Badge variant="cyan" size="sm">News Ticker</Badge>
                                )}
                                {frame.visual_context.contains_document_or_screenshot && (
                                  <Badge variant="purple" size="sm">Document / Screenshot</Badge>
                                )}
                                {frame.visual_context.contains_chart_or_table && (
                                  <Badge variant="emerald" size="sm">Chart / Metric</Badge>
                                )}
                              </div>
                            )}

                            {/* Recognized OCR Snippet */}
                            <div className="text-xs text-slate-700 dark:text-slate-300 line-clamp-3 bg-slate-50 dark:bg-slate-950/60 p-2.5 rounded-lg border border-slate-100 dark:border-slate-800/80 font-mono text-[11px]">
                              {frame.ocr_text ? (
                                frame.ocr_text
                              ) : (
                                <span className="text-slate-400 italic">No text recognized in this keyframe</span>
                              )}
                            </div>
                          </div>

                          {/* Footer Action */}
                          <div className="pt-2 border-t border-slate-100 dark:border-slate-800/60 flex items-center justify-between text-xs">
                            <span className="text-[10px] text-slate-400 font-mono truncate max-w-[120px]">
                              SHA: {frame.image_hash.substring(0, 10)}...
                            </span>
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => setSelectedFrameModal(frame)}
                              className="text-xs h-7"
                            >
                              <Maximize2 className="w-3 h-3 mr-1" />
                              Inspect
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Keyframe Detail Modal */}
              {selectedFrameModal && (
                <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
                  <div className="bg-white dark:bg-surface-cardDark rounded-2xl border border-slate-200 dark:border-surface-borderDark max-w-2xl w-full max-h-[85vh] overflow-y-auto p-6 space-y-4 shadow-2xl animate-scaleIn">
                    <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                      <div className="flex items-center gap-2">
                        <Badge variant="cyan" size="sm">Frame #{selectedFrameModal.frame_number}</Badge>
                        <span className="font-bold text-slate-900 dark:text-white text-sm">
                          Timestamp: {selectedFrameModal.formatted_timestamp}
                        </span>
                        <Badge variant="outline" size="sm">
                          {selectedFrameModal.selection_method}
                        </Badge>
                      </div>
                      <button
                        type="button"
                        onClick={() => setSelectedFrameModal(null)}
                        className="text-slate-400 hover:text-slate-700 dark:hover:text-white"
                      >
                        <X className="w-5 h-5" />
                      </button>
                    </div>

                    {/* Modal Content */}
                    <div className="space-y-3 text-xs">
                      <div>
                        <div className="font-semibold text-slate-700 dark:text-slate-300 mb-1">
                          Full Recognized On-Screen OCR Text:
                        </div>
                        <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 font-mono text-[11px] whitespace-pre-wrap leading-relaxed">
                          {selectedFrameModal.ocr_text || "No text detected in this frame."}
                        </div>
                      </div>

                      {/* Word Bounding Boxes Count */}
                      <div className="flex items-center gap-3 text-slate-500 font-mono text-[11px]">
                        <span>OCR Confidence: {selectedFrameModal.ocr_confidence ? `${selectedFrameModal.ocr_confidence.toFixed(1)}%` : "N/A"}</span>
                        <span>Word Blocks: {selectedFrameModal.ocr_blocks?.length || 0}</span>
                        <span>Dimensions: {selectedFrameModal.width} &times; {selectedFrameModal.height}</span>
                      </div>

                      {/* Visual Context Observations */}
                      {selectedFrameModal.visual_context?.observations && (
                        <div className="space-y-1">
                          <div className="font-semibold text-slate-700 dark:text-slate-300">
                            Visual Structure Observations:
                          </div>
                          <ul className="list-disc list-inside space-y-0.5 text-slate-500 dark:text-slate-400">
                            {selectedFrameModal.visual_context.observations.map((obs, i) => (
                              <li key={i}>{obs}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Cryptographic SHA-256 Hash */}
                      <div className="p-2.5 rounded bg-slate-100 dark:bg-slate-900 font-mono text-[11px] text-slate-600 dark:text-slate-400 truncate">
                        SHA-256: {selectedFrameModal.image_hash}
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
                      <Button
                        type="button"
                        variant="primary"
                        size="sm"
                        onClick={() => {
                          seekToTime(selectedFrameModal.timestamp);
                          setSelectedFrameModal(null);
                        }}
                        className="text-xs"
                      >
                        <Play className="w-3.5 h-3.5 mr-1 fill-current" />
                        Seek Player to Frame ({selectedFrameModal.formatted_timestamp})
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setSelectedFrameModal(null)}
                        className="text-xs"
                      >
                        Close
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 6: VISUAL TEXT */}
          {activeTab === "visual_text" && (
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2">
                    <FileSearch className="w-4 h-4 text-cyan-500" />
                    On-Screen Recognized Headlines, Tickers & Graphics
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Aggregated text extracted from video frames via optical character recognition (Part 8 OCR integration).
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Aggregated Highlights */}
                  {aggregatedVisualStats && (
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                        <span className="text-[10px] text-slate-400 uppercase font-mono">Frames with Text</span>
                        <div className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                          {result.frames?.filter(f => f.ocr_text && f.ocr_text.trim().length > 0).length || 0} / {result.frames_count || 0}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                        <span className="text-[10px] text-slate-400 uppercase font-mono">Total Visual Words</span>
                        <div className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                          {aggregatedVisualStats.totalOcrWords}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                        <span className="text-[10px] text-slate-400 uppercase font-mono">Ticker / Headline Banners</span>
                        <div className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                          {aggregatedVisualStats.tickerCount}
                        </div>
                      </div>
                      <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                        <span className="text-[10px] text-slate-400 uppercase font-mono">Document Graphics</span>
                        <div className="text-lg font-bold text-slate-900 dark:text-white mt-1">
                          {aggregatedVisualStats.documentCount}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Frame-by-Frame Recognized Visual Text Stream */}
                  {(!result.frames || result.frames.length === 0) ? (
                    <div className="p-8 text-center text-slate-500 text-xs">
                      No on-screen graphics or text frames detected.
                    </div>
                  ) : (
                    <div className="space-y-3 pt-2">
                      {result.frames.map((f, i) => {
                        if (!f.ocr_text || !f.ocr_text.trim()) return null;
                        return (
                          <div
                            key={i}
                            className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-2 hover:border-cyan-500/40 transition-colors"
                          >
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <button
                                  type="button"
                                  onClick={() => seekToTime(f.timestamp)}
                                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30"
                                >
                                  <Play className="w-2.5 h-2.5 fill-current" />
                                  {f.formatted_timestamp}
                                </button>
                                <span className="text-xs font-mono font-semibold text-slate-700 dark:text-slate-300">
                                  Frame #{f.frame_number}
                                </span>
                              </div>

                              <div className="flex items-center gap-2">
                                {f.visual_context?.contains_ticker_or_headline && (
                                  <Badge variant="cyan" size="sm">News Ticker</Badge>
                                )}
                                {f.visual_context?.contains_document_or_screenshot && (
                                  <Badge variant="purple" size="sm">Document / Screenshot</Badge>
                                )}
                              </div>
                            </div>

                            <p className="text-xs font-mono text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed bg-white dark:bg-slate-950 p-2.5 rounded-lg border border-slate-200/60 dark:border-slate-800">
                              {f.ocr_text}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* TAB 7: CLAIMS */}
          {activeTab === "claims" && (
            <div className="space-y-4">
              {result.claims.map((clm, idx) => (
                <Card key={clm.id || idx}>
                  <CardHeader>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="cyan" size="sm">Claim #{idx + 1}</Badge>
                        {getOriginBadge(clm.primary_origin)}
                        {clm.formatted_timestamp && (
                          <button
                            type="button"
                            onClick={() => seekToTime(clm.start_time || 0)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-semibold bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 border border-cyan-500/30"
                          >
                            <Play className="w-2.5 h-2.5 fill-current" />
                            {clm.formatted_timestamp}
                          </button>
                        )}
                        <Badge variant="outline" size="sm">{clm.claim_type}</Badge>
                        <Badge variant="slate" size="sm">{clm.verifiability}</Badge>
                      </div>
                      <span className="text-xs text-slate-400 font-mono">
                        Method: {clm.extraction_method}
                      </span>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm font-semibold text-slate-900 dark:text-white">
                      &ldquo;{clm.text}&rdquo;
                    </p>

                    {/* Occurrences List */}
                    {clm.occurrences && clm.occurrences.length > 0 && (
                      <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/30 space-y-1.5 text-xs">
                        <div className="font-semibold text-slate-700 dark:text-slate-300">
                          Detected Multimodal Occurrences ({clm.occurrences.length}):
                        </div>
                        <div className="space-y-1">
                          {clm.occurrences.map((occ, oIdx) => (
                            <div
                              key={oIdx}
                              className="flex items-center justify-between gap-2 p-1.5 rounded bg-white dark:bg-slate-800/80 border border-slate-200/50 dark:border-slate-700/50 text-[11px]"
                            >
                              <div className="flex items-center gap-2">
                                <Badge
                                  variant={occ.source_type === "VISUAL_OCR" ? "purple" : "cyan"}
                                  size="sm"
                                >
                                  {occ.source_type === "VISUAL_OCR" ? "ON-SCREEN GRAPHIC" : "AUDIO SPEECH"}
                                </Badge>
                                <span className="font-mono text-slate-600 dark:text-slate-300">
                                  {occ.formatted_timestamp || `${occ.timestamp_start.toFixed(1)}s`}
                                </span>
                              </div>
                              <button
                                type="button"
                                onClick={() => seekToTime(occ.timestamp_start)}
                                className="px-2 py-0.5 rounded bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 font-semibold transition-colors flex items-center gap-1"
                              >
                                <Play className="w-2.5 h-2.5 fill-current" />
                                Seek
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs pt-1">
                      <div className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20">
                        <div className="text-[10px] text-slate-400 uppercase font-mono">Named Entities</div>
                        <div className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                          {clm.entities && clm.entities.length > 0 ? clm.entities.join(", ") : "None detected"}
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20">
                        <div className="text-[10px] text-slate-400 uppercase font-mono">Temporal Expressions</div>
                        <div className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                          {clm.dates && clm.dates.length > 0 ? clm.dates.join(", ") : "None detected"}
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20">
                        <div className="text-[10px] text-slate-400 uppercase font-mono">Statistics / Numbers</div>
                        <div className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                          {clm.numbers && clm.numbers.length > 0 ? clm.numbers.join(", ") : "None detected"}
                        </div>
                      </div>
                      <div className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/20">
                        <div className="text-[10px] text-slate-400 uppercase font-mono">Attribution</div>
                        <div className="font-medium text-slate-700 dark:text-slate-300 mt-0.5">
                          {clm.source_attributions && clm.source_attributions.length > 0
                            ? clm.source_attributions.join(", ")
                            : "Direct speech / graphic"}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* TAB 8: EVIDENCE */}
          {activeTab === "evidence" && (
            <div className="space-y-4">
              {result.evidence.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs">
                  No evidence stances extracted from discovered sources.
                </div>
              ) : (
                result.evidence.map((ev, idx) => {
                  const badgeVariant =
                    ev.direction === "SUPPORTS"
                      ? "emerald"
                      : ev.direction === "CONTRADICTS"
                      ? "rose"
                      : "slate";
                  return (
                    <Card key={ev.id || idx}>
                      <CardContent className="p-4 space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <Badge variant={badgeVariant as any} size="sm">
                            {ev.direction}
                          </Badge>
                          <span className="text-[11px] text-slate-400 font-mono">
                            Relevance: {ev.relevance_score ? (ev.relevance_score * 100).toFixed(0) : "N/A"}%
                          </span>
                        </div>
                        <p className="text-xs text-slate-800 dark:text-slate-200 font-serif italic border-l-2 border-cyan-500 pl-3">
                          &ldquo;{ev.evidence_text}&rdquo;
                        </p>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center justify-between pt-1">
                          <span>Source: {ev.publisher || ev.domain || "Authoritative Source"}</span>
                          {ev.explanation && <span>{ev.explanation}</span>}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })
              )}
            </div>
          )}

          {/* TAB 9: SOURCES */}
          {activeTab === "sources" && (
            <div className="space-y-4">
              {result.sources.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-xs">
                  No web sources discovered. Check search settings or query status.
                </div>
              ) : (
                result.sources.map((src, idx) => (
                  <Card key={idx}>
                    <CardContent className="p-4 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <Badge variant="cyan" size="sm">{src.domain}</Badge>
                        <span className="text-[11px] text-slate-400 font-mono">
                          Provider: {src.provider || "Yahoo Search"}
                        </span>
                      </div>
                      <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
                        <a
                          href={sanitizeHref(src.url)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:text-cyan-500 transition-colors inline-flex items-center gap-1.5"
                        >
                          {src.title}
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </h4>
                      <p className="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">
                        {src.snippet}
                      </p>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          )}

          {/* TAB 10: TECHNICAL ANALYSIS */}
          {activeTab === "technical" && (
            <div className="space-y-6">
              {/* Audio-Visual Thematic Alignment Report */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <GitCompare className="w-4 h-4 text-cyan-500" />
                      Audio-Visual Thematic Alignment & Divergence
                    </CardTitle>
                    {result.alignment && (
                      <Badge
                        variant={
                          result.alignment.summary_status === "CONSISTENT_ALIGNMENT"
                            ? "emerald"
                            : result.alignment.summary_status === "CONTEXT_DIVERGENCE_OBSERVED"
                            ? "amber"
                            : "slate"
                        }
                        size="sm"
                      >
                        {result.alignment.summary_status.replace(/_/g, " ")}
                      </Badge>
                    )}
                  </div>
                  <CardDescription className="text-xs">
                    Compares spoken topics against on-screen visual text at identical time offsets.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 text-xs">
                  {result.alignment ? (
                    <>
                      <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                        <div className="font-semibold text-slate-800 dark:text-slate-200">
                          {result.alignment.summary_note}
                        </div>
                        <div className="flex items-center gap-4 text-[11px] text-slate-500 font-mono mt-1">
                          <span>Consistent Alignments: {result.alignment.alignments_count}</span>
                          <span>Context Divergences: {result.alignment.mismatches_count}</span>
                        </div>
                      </div>

                      {/* Alignments List */}
                      {result.alignment.alignments && result.alignment.alignments.length > 0 && (
                        <div className="space-y-2">
                          <div className="font-semibold text-emerald-600 dark:text-emerald-400">
                            Thematically Corroborated Offsets:
                          </div>
                          {result.alignment.alignments.map((al, idx) => (
                            <div
                              key={idx}
                              className="p-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 space-y-1"
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-mono text-emerald-700 dark:text-emerald-300 font-bold">
                                  Offset {al.formatted_timestamp}
                                </span>
                                <span className="font-mono text-[10px] text-slate-500">
                                  Sim: {(al.similarity * 100).toFixed(0)}%
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-700 dark:text-slate-300">
                                <strong>Spoken:</strong> &ldquo;{al.audio_phrase}&rdquo;
                              </div>
                              <div className="text-[11px] text-slate-700 dark:text-slate-300">
                                <strong>On-Screen:</strong> &ldquo;{al.visual_text}&rdquo;
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Divergences List */}
                      {result.alignment.mismatches && result.alignment.mismatches.length > 0 && (
                        <div className="space-y-2">
                          <div className="font-semibold text-amber-600 dark:text-amber-400">
                            Context Divergences Observed:
                          </div>
                          {result.alignment.mismatches.map((ms, idx) => (
                            <div
                              key={idx}
                              className="p-2.5 rounded-lg border border-amber-500/20 bg-amber-500/5 space-y-1"
                            >
                              <div className="font-mono text-amber-700 dark:text-amber-300 font-bold">
                                Offset {ms.formatted_timestamp}
                              </div>
                              <div className="text-[11px] text-slate-700 dark:text-slate-300">
                                <strong>Audio topic:</strong> &ldquo;{ms.audio_topic}&rdquo; &bull; <strong>Visual topic:</strong> &ldquo;{ms.visual_topic}&rdquo;
                              </div>
                              <div className="text-[10px] text-slate-500 italic">
                                Note: {ms.note}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/30 text-slate-500 text-[11px]">
                        <strong>Methodology Note:</strong> {result.alignment.disclaimer}
                      </div>
                    </>
                  ) : (
                    <div className="text-slate-400">Audio-visual alignment not evaluated.</div>
                  )}
                </CardContent>
              </Card>

              {/* Reused Footage Check Report */}
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Layers2 className="w-4 h-4 text-cyan-500" />
                      Internal Database Reused Footage Check
                    </CardTitle>
                    {result.reused_footage && (
                      <Badge
                        variant={result.reused_footage.reused_footage_detected ? "amber" : "slate"}
                        size="sm"
                      >
                        {result.reused_footage.reused_footage_detected ? "Reused Footage Detected" : "No Reused Match in DB"}
                      </Badge>
                    )}
                  </div>
                  <CardDescription className="text-xs">
                    Cross-references cryptographic keyframe SHA-256 hashes against prior requests in the TruthLens database.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  {result.reused_footage ? (
                    <>
                      <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-1">
                        <div className="font-semibold text-slate-800 dark:text-slate-200">
                          {result.reused_footage.reused_footage_detected
                            ? `Detected ${result.reused_footage.matching_frames_count} matching frame(s) from prior analyses.`
                            : "No matching frames found in internal verification database."}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          {result.reused_footage.source_origin_note}
                        </div>
                      </div>

                      {/* Disclosures on external reverse search */}
                      <div className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/40 space-y-1 text-slate-600 dark:text-slate-400 text-[11px]">
                        <div>
                          <strong>External Search:</strong> {result.reused_footage.reverse_image_search_status}
                        </div>
                        <div>
                          <strong>Journalistic Notice:</strong> {result.reused_footage.disclaimer}
                        </div>
                      </div>
                    </>
                  ) : (
                    <div className="text-slate-400">Reused footage check not available.</div>
                  )}
                </CardContent>
              </Card>

              {/* Forensic Boundaries & Disclaimers */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-cyan-500" />
                    Forensic Boundaries & Non-Hallucination Disclosures
                  </CardTitle>
                  <CardDescription className="text-xs">
                    Strict scientific and journalistic limitations enforced by TruthLens AI.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                      <div className="text-[10px] text-slate-400 uppercase font-mono">AI Generation Detection</div>
                      <div className="font-semibold text-slate-800 dark:text-slate-200 mt-1">
                        NOT ASSESSED
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        No dedicated AI generation detector integrated.
                      </div>
                    </div>
                    <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                      <div className="text-[10px] text-slate-400 uppercase font-mono">Deepfake Detection</div>
                      <div className="font-semibold text-slate-800 dark:text-slate-200 mt-1">
                        NOT ASSESSED
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        No dedicated deepfake detector integrated.
                      </div>
                    </div>
                    <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30">
                      <div className="text-[10px] text-slate-400 uppercase font-mono">Reverse Image Search</div>
                      <div className="font-semibold text-slate-800 dark:text-slate-200 mt-1">
                        NOT AVAILABLE
                      </div>
                      <div className="text-[10px] text-slate-500 mt-0.5">
                        External search API not configured.
                      </div>
                    </div>
                  </div>

                  {/* Container & Stream Inspection */}
                  <div className="space-y-2 pt-2">
                    <div className="font-semibold text-slate-800 dark:text-slate-200">
                      Container & Stream Inspection:
                    </div>
                    <div className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/30 flex items-center justify-between gap-3 font-mono text-[11px]">
                      <div className="truncate">
                        <span className="text-slate-400">File SHA-256: </span>
                        <span className="text-slate-700 dark:text-slate-300">{result.forensics.file_hash_sha256}</span>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => copyToClipboard(result.forensics.file_hash_sha256, "hash")}
                        className="text-xs h-7 shrink-0"
                      >
                        {copiedHash ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-500 mr-1" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3 mr-1" />
                            Copy Hash
                          </>
                        )}
                      </Button>
                    </div>

                    {result.forensics.technical_indicators?.observations && (
                      <ul className="list-disc list-inside space-y-1 text-slate-600 dark:text-slate-400 pl-1 pt-1">
                        {result.forensics.technical_indicators.observations.map((obs: string, idx: number) => (
                          <li key={idx}>{obs}</li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/5 text-amber-800 dark:text-amber-300 text-xs flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                    <span>
                      {result.forensics.technical_indicators?.disclaimer ||
                        "These technical indicators reflect basic container and stream properties. They do not by themselves establish whether the media is authentic or manipulated."}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}

          {/* TAB 11: SEARCH AUDIT */}
          {activeTab === "search_audit" && (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between gap-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Search className="w-4 h-4 text-cyan-500" />
                    Part 4 Search Query Audit Trail ({result.queries?.length || 0} queries)
                  </CardTitle>
                  <Badge variant="cyan" size="sm">
                    Multi-Strategy Execution
                  </Badge>
                </div>
                <CardDescription className="text-xs">
                  Full transparent audit of exact search queries, strategy tiers, search providers used, and result yields.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {(!result.queries || result.queries.length === 0) ? (
                  <div className="p-8 text-center text-slate-500 text-xs">
                    No web search queries executed for this request (or search was skipped).
                  </div>
                ) : (
                  result.queries.map((q, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 space-y-2 text-xs"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <Badge variant="cyan" size="sm">{q.strategy_level}</Badge>
                          <Badge variant="outline" size="sm">{q.search_engine}</Badge>
                          <Badge
                            variant={q.status === "success" ? "emerald" : q.status === "empty" ? "amber" : "rose"}
                            size="sm"
                          >
                            {q.status}
                          </Badge>
                        </div>
                        <span className="font-mono text-[11px] text-slate-500">
                          {q.results_count} results retrieved
                        </span>
                      </div>

                      <div className="font-mono text-xs text-slate-900 dark:text-white bg-white dark:bg-slate-950 p-2.5 rounded-lg border border-slate-200/60 dark:border-slate-800">
                        {q.query_text}
                      </div>

                      {q.error_message && (
                        <div className="text-[11px] text-rose-500">
                          Error: {q.error_message}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
