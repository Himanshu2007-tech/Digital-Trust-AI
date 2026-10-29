import React from "react";
import {
  Shield,
  Layers,
  Database,
  Cpu,
  CheckCircle2,
  Clock,
  Sparkles,
  Search,
  Scan,
  AudioWaveform,
  Film,
  FileCheck
} from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export default function AboutPage() {
  const databaseModels = [
    { name: "users", description: "User credentials, access roles, and audit trail." },
    { name: "verification_requests", description: "Inbound verification tasks (text, URL, multimedia) with lifecycle status and timestamps." },
    { name: "claims", description: "Extracted atomic factual assertions with importance, verifiability, and confidence." },
    { name: "sources", description: "Catalog of external publishers with credibility tiers, reliability scores, and origin roles." },
    { name: "evidence", description: "Supporting, contradicting, and neutral quotes/snippets linked to claims." },
    { name: "source_comparisons", description: "Multi-source consensus matrix, independence evaluation, and stance synthesis." },
    { name: "media_files", description: "SHA-256 checksums, storage paths, dimensions, and MIME types for multimedia uploads." },
    { name: "verification_results", description: "Final explainable verdict, truth score, evidence confidence score, and rationale." },
    { name: "search_queries", description: "Audit trail of search queries and strategy tiers executed during evidence gathering." },
    { name: "reports", description: "Generated PDF verification dossiers with SHA-256 fingerprinting and audit events." },
    { name: "articles", description: "Parsed web articles with canonical URLs, readability scoring, and metadata." },
    { name: "image_verifications", description: "Image forensic records, spatial bounding blocks, and OCR legibility confidence." },
    { name: "media_verifications", description: "Audio/video metadata, track detection, and dual-confidence tracking." },
    { name: "transcript_segments", description: "Timestamped speech-to-text segments with word intervals and sequence order." },
    { name: "video_frames", description: "Extracted keyframes, scene-change timestamps, and visual context blocks." },
    { name: "claim_occurrences", description: "Cross-modal occurrences linking spoken and on-screen claims to exact video timestamps." },
    { name: "verification_events", description: "Lifecycle audit timeline events recording pipeline stage transitions and outcomes." },
  ];

  const roadmapPhases = [
    {
      phase: "Part 1",
      title: "Foundation & System Architecture",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "FastAPI backend, SQLAlchemy 2.0 ORM, 10 core relational models, SQLite/PostgreSQL support, SSRF security guards, and telemetry health monitor.",
    },
    {
      phase: "Part 2",
      title: "Professional Dashboard & Design System",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Investigative UI/UX, dual dark/light theme engine, mobile responsive drawer, specialized multimedia FileDropzones, and unified typography.",
    },
    {
      phase: "Part 3",
      title: "Atomic Claim Extraction & NLP Decomposition",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Decomposes complex text into verifiable factual claims, filters subjective opinions, and extracts temporal/numerical/quote entities.",
    },
    {
      phase: "Part 4",
      title: "Multi-Source Search & Discovery Engine",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Multi-tiered search query generation (quoted, relaxed, entity-only), parallel provider querying (DuckDuckGo, Yahoo, Mojeek), and search audit trails.",
    },
    {
      phase: "Part 5",
      title: "Evidence Extraction & Source Comparison",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Extracts supporting, contradicting, and neutral passages, evaluates source credibility tiers (Primary, High, Medium), and analyzes syndication.",
    },
    {
      phase: "Part 6",
      title: "Explainable Verdict Synthesis & Confidence",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Mathematical verdict calculation (SUPPORTED, CONTRADICTED, MISLEADING, UNVERIFIED, INSUFFICIENT_EVIDENCE) with separate evidence confidence index.",
    },
    {
      phase: "Part 7",
      title: "News URL Ingestion & Anti-Self-Corroboration",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Secure web scraping with SSRF prevention, per-hop redirect validation, readability parsing, and strict exclusion of submitted domain from self-corroboration.",
    },
    {
      phase: "Part 8",
      title: "Image Forensics, Spatial OCR & Verification",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Magic byte inspection, decompression bomb protection, EXIF privacy sanitization, multi-engine OCR, spatial bounding blocks, and OCR legibility vs evidence confidence.",
    },
    {
      phase: "Part 9",
      title: "Audio & Speech Transcription Verification",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Audio container verification, Whisper speech-to-text, timestamped transcript segmentation, spoken entity extraction, and dual confidence separation.",
    },
    {
      phase: "Part 10",
      title: "Advanced Video & Keyframe Multimedia Analysis",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Keyframe extraction, scene-change detection, on-screen text OCR, logo/brand detection, cross-modal speech vs visual claim timestamp correlation.",
    },
    {
      phase: "Part 11",
      title: "History Archive, Re-verification Lineage & DB Lifecycle",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Persistent database verification records, multi-parameter history filtering, interactive investigation dossiers, parent/child re-verification trees, and soft-archive.",
    },
    {
      phase: "Part 12",
      title: "Professional PDF Verification Dossiers",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Multi-page publication-grade PDF generation with ReportLab, executive summaries, evidence tables, cryptographic SHA-256 fingerprinting, and secure downloads.",
    },
    {
      phase: "Part 13",
      title: "Analytics Dashboard, Macro-Observatory & Safe CSV Export",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Database-backed analytics observatory, temporal verification timelines, modality distribution, verdict matrix, top domains, and formula-safe CSV downloads.",
    },
    {
      phase: "Part 14",
      title: "Security, Penetration Testing & Reliability Audit",
      status: "Complete",
      statusVariant: "emerald" as const,
      description: "Rigorous SSRF hardening, DNS-rebinding socket checks, upload filename sanitization, PDF SHA-256 tamper detection, security headers, DOM XSS defense, and 65 security regression tests.",
    },
    {
      phase: "Part 15",
      title: "Final Integration, Deployment Readiness & Polish",
      status: "Operational",
      statusVariant: "cyan" as const,
      description: "End-to-end multi-modal verification integration, clean Alembic migration suite, comprehensive documentation, and college MDC demonstration readiness.",
    },
  ];

  return (
    <div className="space-y-10 max-w-5xl">
      <PageHeader
        title="About Digital Trust AI"
        description="Comprehensive architecture documentation, mission statement, database entity catalog, and multi-phase engineering roadmap."
        badgeText="System Documentation"
        badgeVariant="cyan"
        icon={Shield}
      />

      {/* Purpose Banner */}
      <Card className="p-6 md:p-8 bg-gradient-to-r from-cyan-500/10 via-slate-50 dark:via-surface-cardDark to-blue-500/10 border-cyan-500/30">
        <div className="max-w-3xl space-y-3">
          <Badge variant="cyan" size="sm">Core Mission</Badge>
          <h2 className="text-lg md:text-xl font-bold text-slate-900 dark:text-white">
            &ldquo;Digital Trust AI is designed to help users investigate potentially misleading information by decomposing claims, comparing reliable sources, examining evidence, and generating explainable verification results.&rdquo;
          </h2>
          <p className="text-xs md:text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
            Built as a professional college MDC project, Digital Trust AI combines modern cyber-investigative principles with academic rigor, strict data integrity, and transparent reasoning.
          </p>
        </div>
      </Card>

      {/* Technology Stack Grid */}
      <section className="space-y-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Technology Stack Architecture
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-5 space-y-3">
            <div className="flex items-center gap-2.5 text-cyan-600 dark:text-cyan-400 font-bold text-sm">
              <Layers className="w-5 h-5" />
              <span>Frontend Stack</span>
            </div>
            <ul className="text-xs text-slate-600 dark:text-slate-300 space-y-2 list-disc list-inside">
              <li>Next.js 14 with App Router</li>
              <li>TypeScript with strict type checking</li>
              <li>Tailwind CSS dual dark/light system</li>
              <li>Lucide React iconography</li>
              <li>Real-time telemetry health monitor</li>
              <li>Accessible interactive components</li>
            </ul>
          </Card>

          <Card className="p-5 space-y-3">
            <div className="flex items-center gap-2.5 text-blue-600 dark:text-blue-400 font-bold text-sm">
              <Cpu className="w-5 h-5" />
              <span>Backend Stack</span>
            </div>
            <ul className="text-xs text-slate-600 dark:text-slate-300 space-y-2 list-disc list-inside">
              <li>Python 3.11 with FastAPI</li>
              <li>Pydantic v2 data validation</li>
              <li>Pydantic Settings (.env loader)</li>
              <li>Modular service architecture</li>
              <li>SSRF protection filters</li>
              <li>CORS middleware configuration</li>
            </ul>
          </Card>

          <Card className="p-5 space-y-3">
            <div className="flex items-center gap-2.5 text-indigo-600 dark:text-indigo-400 font-bold text-sm">
              <Database className="w-5 h-5" />
              <span>Database Architecture</span>
            </div>
            <ul className="text-xs text-slate-600 dark:text-slate-300 space-y-2 list-disc list-inside">
              <li>SQLAlchemy 2.0 ORM</li>
              <li>Alembic automated migrations</li>
              <li>PostgreSQL & SQLite compatibility</li>
              <li>10 claim-level verification tables</li>
              <li>Relational integrity & foreign keys</li>
              <li>Audit timestamps on all entities</li>
            </ul>
          </Card>
        </div>
      </section>

      {/* Multi-Phase Roadmap */}
      <section className="space-y-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Multi-Phase Engineering Roadmap
        </h3>

        <div className="space-y-3">
          {roadmapPhases.map((phase) => (
            <Card key={phase.phase} className="p-5 hover:border-cyan-500/40 transition-colors">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
                <div className="flex items-center gap-2.5">
                  <span className="font-mono font-bold text-sm text-cyan-600 dark:text-cyan-400">
                    {phase.phase}:
                  </span>
                  <h4 className="font-bold text-sm text-slate-900 dark:text-slate-100">
                    {phase.title}
                  </h4>
                </div>
                <Badge variant={phase.statusVariant} size="sm">
                  {phase.status}
                </Badge>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                {phase.description}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* 10 Core Database Models Catalog */}
      <section className="space-y-4">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
          <Database className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
          The 10 Core Database Schemas
        </h3>

        <div className="rounded-2xl border border-slate-200 dark:border-surface-borderDark overflow-hidden bg-white dark:bg-surface-cardDark shadow-sm">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-900/60 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-surface-borderDark">
              <tr>
                <th className="py-3 px-4 font-semibold">Table / Model</th>
                <th className="py-3 px-4 font-semibold">Purpose in Verification Lifecycle</th>
                <th className="py-3 px-4 font-semibold text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-surface-borderDark text-slate-700 dark:text-slate-300">
              {databaseModels.map((m) => (
                <tr key={m.name} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                  <td className="py-3 px-4 font-mono font-bold text-cyan-600 dark:text-cyan-400">
                    {m.name}
                  </td>
                  <td className="py-3 px-4 text-slate-600 dark:text-slate-400">
                    {m.description}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 dark:text-emerald-300 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                      <CheckCircle2 className="w-3 h-3" /> Ready
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
