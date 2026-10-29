# TruthLens AI — System Architecture & Design Specification

TruthLens AI is an AI-Powered Fake News & Multimedia Verification System engineered for collegiate MDC demonstration.

---

## High-Level Architecture

```
                       ┌───────────────────────────────┐
                       │     Next.js 14 Frontend       │
                       │ (TypeScript, Tailwind, React) │
                       └──────────────┬────────────────┘
                                      │ HTTP / REST
                                      ▼
                       ┌───────────────────────────────┐
                       │       FastAPI Backend         │
                       │  (Pydantic, CORS, SSRF Guard) │
                       └──────────────┬────────────────┘
                                      │
               ┌──────────────────────┴──────────────────────┐
               ▼                                             ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│     Verification Router      │              │       System & Health        │
│  /api/verify/{text,url,...}  │              │       GET /api/health        │
└──────────────┬───────────────┘              └──────────────┬───────────────┘
               │                                             │
               ▼                                             ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│    Database Layer (ORM)      │              │    SQLAlchemy 2.0 Engine     │
│   (10 Relational Models)     │◄─────────────┤ (PostgreSQL / SQLite Dev)    │
└──────────────────────────────┘              └──────────────────────────────┘
```

---

## Future Modular Verification Pipeline (Planned for Subsequent Phases)

```
Text / URL / Multimedia Input
             │
             ▼
┌──────────────────────────────┐
│  Phase 3: Media Processing   │  [OpenCV / FFmpeg / Whisper / Tesseract]
│  - Frame Decomposition       │
│  - Speech-to-Text            │
│  - OCR Text Extraction       │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│  Phase 2: Claim Extraction   │  [NLP / LLM Claim Extractor]
│  - Atomic Claim Parsing      │
│  - Entity & Date Tagging     │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│  Phase 2: Evidence Engine    │  [Multi-Source Search API]
│  - SERP Query Generation     │
│  - Source Credibility Filter │
│  - Snippet Extraction        │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│  Phase 2: Stance & Synthesis │  [Contradiction & Consensus Engine]
│  - Supporting vs Refuting    │
│  - Source Weighting          │
│  - Truth & Confidence Score  │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│  Phase 4: Reporting Engine   │  [PDF / JSON / HTML Dossier]
│  - Explainable Verdict       │
│  - Audit Trail Preservation  │
└──────────────────────────────┘
```

---

## Relational Database Schema (10 Models)

| Model Name | Table Name | Key Fields | Purpose |
|---|---|---|---|
| `User` | `users` | `id`, `email`, `username`, `hashed_password`, `role`, `is_active` | Authentication, analyst management, audit trail |
| `VerificationRequest` | `verification_requests` | `id`, `user_id`, `request_type`, `content`, `media_file_id`, `status`, `priority` | Inbound verification tasks lifecycle |
| `Claim` | `claims` | `id`, `request_id`, `claim_text`, `speaker_or_source`, `claim_date`, `extraction_method`, `confidence_score`, `status` | Decomposed atomic assertions |
| `Source` | `sources` | `id`, `name`, `domain`, `url`, `credibility_score`, `source_type`, `reliability_tier`, `bias_rating` | External publisher credibility index |
| `Evidence` | `evidence` | `id`, `claim_id`, `source_id`, `evidence_type`, `snippet`, `url`, `relevance_score`, `stance_confidence` | Supporting / refuting source excerpts |
| `SourceComparison` | `source_comparisons` | `id`, `claim_id`, `supporting_sources_count`, `contradicting_sources_count`, `consensus_verdict`, `analysis_summary` | Consensus synthesis across multiple sources |
| `MediaFile` | `media_files` | `id`, `original_filename`, `stored_filename`, `file_path`, `file_size_bytes`, `mime_type`, `file_hash_sha256`, `storage_provider` | Upload tracking, SHA256 integrity checks |
| `VerificationResult` | `verification_results` | `id`, `request_id`, `overall_verdict`, `truth_score`, `confidence_score`, `summary`, `key_findings_json`, `verified_at` | Final explainable verdict record |
| `SearchQuery` | `search_queries` | `id`, `claim_id`, `query_text`, `search_engine`, `results_count`, `raw_response_json` | Audit record of search queries |
| `Report` | `reports` | `id`, `request_id`, `user_id`, `title`, `format`, `file_path`, `status` | Dossier export records (PDF/HTML/JSON) |

---

## Security Architecture

1. **SSRF Protection**:
   - URL verification targets are validated before network fetch via `validate_url_for_ssrf`.
   - Blocks private subnets: `127.0.0.0/8`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, AWS metadata `169.254.169.254`, IPv6 loopback.
2. **File Upload Security**:
   - File size ceiling enforced (`MAX_UPLOAD_SIZE_BYTES = 50MB`).
   - Allowed MIME types checked on upload.
   - Uploaded files are saved to designated isolated storage with generated unique filenames (no direct execution).
3. **Environment Security**:
   - Secret keys and credentials managed via `.env`.
   - `.env` excluded from version control via `.gitignore`.
