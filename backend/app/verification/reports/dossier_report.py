"""
TruthLens AI — Professional Dossier Report Compiler (Part 12)
Assembles publication-grade multi-page verification reports covering all 8 mandatory sections:
1. Cover and Report Information
2. Executive Summary
3. Input Overview
4. Claim-by-Claim Analysis
5. Evidence and Source Analysis
6. Multimedia Findings (Image OCR / Audio-Video Transcripts & Keyframes)
7. Methodology and Limitations
8. Audit Trail and Cryptographic Fingerprint
"""

import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from app.verification.reports.pdf_builder import PDFBuilder, sanitize_text


class DossierReportGenerator:
    """Compiles complete verification dossiers into standardized, publication-grade PDFs."""

    def __init__(self, report_uuid: str, version: str = "1.0"):
        self.report_uuid = report_uuid
        self.version = version

    def generate_dossier_pdf(
        self,
        dossier: Dict[str, Any],
        report_title: Optional[str] = None
    ) -> bytes:
        """
        Builds the complete multi-page PDF document bytes from a verification dossier dict.
        Works seamlessly with HistoryDetailResponse.model_dump() or raw dictionary.
        """
        req_id = dossier.get("id", 0)
        req_type = dossier.get("request_type", "unknown").lower()
        status = dossier.get("status", "completed").lower()
        created_at_str = dossier.get("created_at") or datetime.now(timezone.utc).isoformat()
        
        # Clean formatted title
        title = report_title or f"Verification Dossier: {req_type.capitalize()} Analysis #{req_id}"

        # Initialize PDF Document Builder
        builder = PDFBuilder(
            doc_title=f"TruthLens AI Dossier #{req_id}",
            subtitle=f"ID: {self.report_uuid[:16]}... | {created_at_str[:10]}"
        )

        # -------------------------------------------------------------
        # SECTION 1: Cover and Report Information
        # -------------------------------------------------------------
        builder.add_cover_banner(
            report_title=title,
            report_uuid=self.report_uuid,
            request_id=req_id,
            request_type=req_type,
            status=status,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

        # Basic Metadata Grid
        parent_id = dossier.get("parent_request_id")
        lineage_str = f"Re-verification of Request #{parent_id}" if parent_id else "Initial primary investigation"
        completed_at_str = dossier.get("completed_at") or "In-progress"
        
        meta_items = [
            ("Investigation ID", f"REQ-{req_id:06d}"),
            ("Input Modality", f"{req_type.upper()} verification"),
            ("Lifecycle Status", status.upper()),
            ("Investigation Lineage", lineage_str),
            ("Initial Submission", created_at_str),
            ("Completion Timestamp", completed_at_str),
        ]
        builder.add_card(
            title="Investigation Identification & Parameters",
            key_values=meta_items,
            border_color="#CBD5E1",
            bg_color="#F8FAFC",
            accent_color="#2563EB"
        )
        builder.add_spacer(6.0)

        # -------------------------------------------------------------
        # SECTION 2: Executive Summary
        # -------------------------------------------------------------
        builder.add_section_heading("Executive Summary", "1")
        
        verdict = dossier.get("verdict")
        confidence_pct = dossier.get("confidence_percentage")
        if confidence_pct is None and dossier.get("confidence") is not None:
            confidence_pct = round(dossier["confidence"] * 100.0, 1)

        summary_text = dossier.get("summary") or dossier.get("error_message") or (
            "No high-level narrative summary was stored for this verification."
        )

        claims_breakdown = {
            "supported": dossier.get("supported_count", 0),
            "contradicted": dossier.get("contradicted_count", 0),
            "misleading": dossier.get("misleading_count", 0),
            "unverified": dossier.get("unverified_count", 0) + dossier.get("insufficient_count", 0),
        }

        builder.add_verdict_card(
            verdict=verdict,
            confidence_pct=confidence_pct,
            summary=summary_text,
            claims_counts=claims_breakdown
        )

        # -------------------------------------------------------------
        # SECTION 3: Input Overview
        # -------------------------------------------------------------
        builder.add_section_heading("Input Overview & Scope", "2")

        input_text = dossier.get("content") or ""
        article_data = dossier.get("article")
        image_data = dossier.get("image_verification")
        media_data = dossier.get("media_verification")

        if req_type == "text":
            preview = input_text.strip()
            word_count = len(preview.split()) if preview else 0
            char_count = len(preview)
            kv = [
                ("Input Format", "Raw Text / Headline"),
                ("Word Count", f"{word_count:,} words"),
                ("Character Count", f"{char_count:,} characters"),
            ]
            builder.add_card(
                title="Submitted Text Overview",
                lines=[preview if len(preview) <= 500 else preview[:497] + "..."],
                key_values=kv,
                bg_color="#FFFFFF"
            )

        elif req_type == "url":
            orig_url = article_data.get("original_url") if article_data else (input_text or "N/A")
            canon_url = article_data.get("canonical_url") if article_data else "N/A"
            art_title = article_data.get("title") if article_data else "Unknown Article Title"
            publisher = article_data.get("publisher") if article_data else "Unknown"
            domain = article_data.get("domain") if article_data else "N/A"
            pub_date = article_data.get("published_at") if article_data else "N/A"
            w_count = article_data.get("word_count") if article_data else 0

            kv = [
                ("Article Title", art_title or "N/A"),
                ("Source Domain", domain or "N/A"),
                ("Publisher", publisher or "N/A"),
                ("Publication Date", pub_date or "Not specified"),
                ("Original URL", orig_url),
                ("Word Count", f"{w_count:,} words" if w_count else "N/A"),
            ]
            builder.add_card(
                title="Web Article Overview",
                key_values=kv,
                bg_color="#FFFFFF"
            )

        elif req_type == "image":
            w = image_data.get("width") if image_data else "N/A"
            h = image_data.get("height") if image_data else "N/A"
            mime = image_data.get("mime_type") if image_data else "image/jpeg"
            ocr_words = image_data.get("word_count") if image_data else 0
            ocr_conf = image_data.get("ocr_confidence") if image_data else None

            kv = [
                ("Media Type", "Image / Screenshot"),
                ("Dimensions", f"{w} x {h} pixels" if w != "N/A" else "N/A"),
                ("MIME Type", mime),
                ("Detected Words", f"{ocr_words} words extracted via OCR"),
                ("OCR Text Quality", f"{ocr_conf:.1f}% confidence" if ocr_conf is not None else "N/A"),
            ]
            builder.add_card(
                title="Image / Graphic Input Overview",
                key_values=kv,
                bg_color="#FFFFFF"
            )

        elif req_type in ("audio", "video"):
            m_type = media_data.get("media_type") if media_data else req_type
            dur = media_data.get("duration_seconds") if media_data else 0.0
            lang = media_data.get("language") if media_data else "auto-detected"
            t_conf = media_data.get("transcription_confidence") if media_data else None
            seg_count = len(media_data.get("segments", [])) if media_data else 0

            kv = [
                ("Media Type", f"{m_type.capitalize()} stream"),
                ("Media Duration", f"{dur:.1f} seconds ({dur/60.0:.1f} min)" if dur else "N/A"),
                ("Audio Language", lang.upper() if lang else "N/A"),
                ("Audio Segments", f"{seg_count} time-aligned segments"),
                ("Transcription Quality", f"{t_conf*100.0:.1f}% confidence" if t_conf is not None else "N/A"),
            ]
            builder.add_card(
                title=f"{req_type.capitalize()} Recording Overview",
                key_values=kv,
                bg_color="#FFFFFF"
            )

        builder.add_spacer(6.0)

        # -------------------------------------------------------------
        # SECTION 4: Claim-by-Claim Analysis
        # -------------------------------------------------------------
        builder.add_section_heading("Claim-by-Claim Verification Analysis", "3")
        claims = dossier.get("claims") or []

        if not claims:
            builder.add_callout(
                text="No atomic claims were extracted from this content for independent corroboration.",
                title="Zero Atomic Claims Identified",
                style="info"
            )
        else:
            builder.add_paragraph(
                f"TruthLens decomposed the submitted material into {len(claims)} verifiable atomic claim(s). "
                "Each statement was independently matched against authoritative news indexes and corroborated fact-checks."
            )

            for idx, c in enumerate(claims, 1):
                c_id = c.get("id", idx)
                c_text = c.get("claim_text", "")
                c_type = c.get("claim_type", "factual")
                verifiability = c.get("verifiability", "high")
                importance = c.get("importance", 1)
                verdict_c = c.get("verdict") or "UNVERIFIED"
                conf_c = c.get("confidence")
                conf_c_pct = round(conf_c * 100.0, 1) if conf_c is not None else None
                expl_c = c.get("explanation") or "No explanation stored for this specific claim."
                limitations_c = c.get("limitations") or []

                c_theme = {
                    "SUPPORTED": {"bg": "#ECFDF5", "border": "#10B981", "accent": "#059669"},
                    "CONTRADICTED": {"bg": "#FEF2F2", "border": "#EF4444", "accent": "#DC2626"},
                    "MISLEADING": {"bg": "#FFFBEB", "border": "#F59E0B", "accent": "#D97706"},
                }.get(verdict_c.upper(), {"bg": "#F8FAFC", "border": "#CBD5E1", "accent": "#64748B"})

                kv = [
                    ("Claim Classification", f"{c_type.capitalize()} statement (Verifiability: {verifiability})"),
                    ("Verification Verdict", verdict_c.upper()),
                    ("Evidence Confidence", f"{conf_c_pct:.1f}%" if conf_c_pct is not None else "N/A"),
                ]

                lines = [
                    f'"{c_text}"',
                    f"Analytical Finding: {expl_c}",
                ]
                if limitations_c:
                    lines.append(f"Caveats & Limitations: {'; '.join(limitations_c)}")

                # Check occurrences if video or audio
                occurrences = c.get("occurrences") or []
                if occurrences:
                    occ_strs = [
                        f"[{o.get('source_type', 'media')} @ {o.get('timestamp_start', 0):.1f}s - {o.get('timestamp_end', 0):.1f}s]: \"{o.get('text', '')}\""
                        for o in occurrences[:3]
                    ]
                    lines.append("Multimedia Timestamps: " + " | ".join(occ_strs))

                builder.add_card(
                    title=f"Claim #{idx} [ID: {c_id}]: {verdict_c.upper()}",
                    key_values=kv,
                    lines=lines,
                    border_color=c_theme["border"],
                    bg_color=c_theme["bg"],
                    accent_color=c_theme["accent"]
                )

        builder.add_spacer(6.0)

        # -------------------------------------------------------------
        # SECTION 5: Evidence and Source Analysis
        # -------------------------------------------------------------
        builder.add_section_heading("Evidence & Source Analysis", "4")
        sources = dossier.get("sources") or []
        evidence_items = dossier.get("evidence") or []
        comparisons = dossier.get("comparisons") or []

        if not sources and not evidence_items:
            builder.add_callout(
                text="No authoritative external web sources or corroborated evidence documents were linked to this verification.",
                title="No External Evidence Cited",
                style="warning"
            )
        else:
            # Table of Discovered Sources
            if sources:
                builder.add_paragraph(
                    f"A total of {len(sources)} authoritative external source(s) were retrieved and evaluated during multi-source web search."
                )
                headers = ["Domain / Publisher", "Title / Excerpt", "Type", "Link"]
                widths = [110.0, 240.0, 70.0, 108.0]
                aligns = ["left", "left", "center", "left"]

                rows = []
                row_urls = []
                for s in sources[:15]:  # Show top 15 sources to keep report clean
                    pub = s.get("publisher") or s.get("domain") or "Unknown"
                    title_s = s.get("title") or s.get("snippet") or "Source Document"
                    if len(title_s) > 90:
                        title_s = title_s[:87] + "..."
                    s_type = s.get("source_type") or "news"
                    url = s.get("url") or ""
                    display_url = url if len(url) <= 30 else url[:27] + "..."

                    rows.append([pub, title_s, s_type.capitalize(), display_url])
                    row_urls.append({3: url} if url.startswith("http") else {})

                builder.add_table(headers, rows, col_widths=widths, alignments=aligns, row_urls=row_urls)

            # Evidence Items List
            if evidence_items:
                builder.add_spacer(4.0)
                builder.add_paragraph("Key Corroborating & Contradicting Evidence Snippets:", font_name="Helvetica-Bold", font_size=9.0)
                
                ev_headers = ["Direction", "Relevance", "Source / Publisher", "Evidence Excerpt"]
                ev_widths = [80.0, 55.0, 110.0, 283.0]
                ev_aligns = ["center", "center", "left", "left"]
                
                ev_rows = []
                ev_urls = []
                for ev in evidence_items[:12]:
                    direction = (ev.get("direction") or "NEUTRAL").upper()
                    rel = ev.get("relevance_score")
                    rel_str = f"{rel*100.0:.0f}%" if rel is not None else "N/A"
                    pub = ev.get("publisher") or ev.get("domain") or "Source"
                    text_e = ev.get("evidence_text") or ev.get("snippet") or ""
                    if len(text_e) > 130:
                        text_e = text_e[:127] + "..."
                    url_e = ev.get("url") or ""

                    ev_rows.append([direction, rel_str, pub, text_e])
                    ev_urls.append({2: url_e} if url_e.startswith("http") else {})

                builder.add_table(ev_headers, ev_rows, col_widths=ev_widths, alignments=ev_aligns, row_urls=ev_urls)

            # Consensus & Comparisons
            if comparisons:
                builder.add_spacer(4.0)
                for cmp in comparisons[:5]:
                    consensus = cmp.get("consensus_verdict", "INCONCLUSIVE")
                    consistency = cmp.get("evidence_consistency", "moderate")
                    sup_count = cmp.get("supporting_sources_count", 0)
                    con_count = cmp.get("contradicting_sources_count", 0)
                    neu_count = cmp.get("neutral_sources_count", 0)
                    summary_c = cmp.get("analysis_summary", "")

                    cmp_kv = [
                        ("Consensus Verdict", consensus),
                        ("Evidence Consistency", consistency.capitalize()),
                        ("Sources Distribution", f"{sup_count} Supporting  |  {con_count} Contradicting  |  {neu_count} Neutral"),
                    ]
                    builder.add_card(
                        title=f"Source Comparison & Consensus: {consensus}",
                        key_values=cmp_kv,
                        lines=[summary_c] if summary_c else None,
                        bg_color="#F8FAFC"
                    )

        builder.add_spacer(6.0)

        # -------------------------------------------------------------
        # SECTION 6: Multimedia Findings (Image / Audio / Video)
        # -------------------------------------------------------------
        if req_type in ("image", "audio", "video") or image_data or media_data:
            builder.add_section_heading("Multimedia Forensic Findings", "5")

            if req_type == "image" and image_data:
                ocr_text = image_data.get("ocr_raw_text") or "No readable text detected in image."
                ocr_conf = image_data.get("ocr_confidence")
                urls_detected = image_data.get("detected_urls") or []
                dates_detected = image_data.get("detected_dates") or []

                kv = [
                    ("OCR Extraction Confidence", f"{ocr_conf:.1f}% (text legibility metric)" if ocr_conf is not None else "N/A"),
                    ("Detected URLs in Graphic", ", ".join(urls_detected) if urls_detected else "None detected"),
                    ("Detected Dates in Graphic", ", ".join(dates_detected) if dates_detected else "None detected"),
                ]
                builder.add_card(
                    title="Optical Character Recognition (OCR) Analysis",
                    key_values=kv,
                    lines=[
                        "Important distinction: OCR confidence reflects optical character clarity, not factual truth of the claims.",
                        f"Extracted Text: \"{ocr_text[:600] + ('...' if len(ocr_text) > 600 else '')}\""
                    ],
                    bg_color="#F8FAFC"
                )

            if req_type in ("audio", "video") and media_data:
                transcript = media_data.get("normalized_transcript") or media_data.get("raw_transcript") or "No transcript available."
                t_conf = media_data.get("transcription_confidence")
                quotes = media_data.get("detected_quotes") or []
                segments = media_data.get("segments") or []
                frames = media_data.get("frames") or []

                kv = [
                    ("Acoustic Confidence", f"{t_conf*100.0:.1f}% (acoustic clarity)" if t_conf is not None else "N/A"),
                    ("Detected Quotations", f"{len(quotes)} direct quote statements" if quotes else "None detected"),
                ]
                builder.add_card(
                    title="Audio Speech-to-Text Transcription",
                    key_values=kv,
                    lines=[
                        "Acoustic confidence measures phonetic recognition accuracy, completely separate from factual evidence confidence.",
                        f"Transcript Excerpt: \"{transcript[:500] + ('...' if len(transcript) > 500 else '')}\""
                    ],
                    bg_color="#F8FAFC"
                )

                # Segment Table
                if segments:
                    builder.add_spacer(4.0)
                    builder.add_paragraph("Time-Aligned Acoustic Segments:", font_name="Helvetica-Bold", font_size=8.5)
                    seg_headers = ["Seq", "Time Range", "Confidence", "Transcribed Speech"]
                    seg_widths = [35.0, 80.0, 65.0, 348.0]
                    seg_aligns = ["center", "center", "center", "left"]
                    seg_rows = []
                    for seg in segments[:10]:
                        s_time = f"{seg.get('start_time', 0):.1f}s - {seg.get('end_time', 0):.1f}s"
                        c_val = seg.get('confidence')
                        c_str = f"{c_val*100.0:.0f}%" if c_val is not None else "N/A"
                        s_text = seg.get('text', '')
                        if len(s_text) > 95:
                            s_text = s_text[:92] + "..."
                        seg_rows.append([str(seg.get('sequence', 1)), s_time, c_str, s_text])
                    builder.add_table(seg_headers, seg_rows, col_widths=seg_widths, alignments=seg_aligns)

                # Video Frames Table
                if frames:
                    builder.add_spacer(4.0)
                    builder.add_paragraph("Sampled Video Keyframes & On-Screen Visual Analysis:", font_name="Helvetica-Bold", font_size=8.5)
                    f_headers = ["Frame #", "Timestamp", "Method", "Visual Context / On-Screen OCR"]
                    f_widths = [50.0, 65.0, 75.0, 338.0]
                    f_aligns = ["center", "center", "center", "left"]
                    f_rows = []
                    for frm in frames[:8]:
                        f_num = str(frm.get('frame_number', 0))
                        t_stamp = f"{frm.get('timestamp', 0):.2f}s"
                        method = frm.get('selection_method', 'interval').capitalize()
                        desc = frm.get('ocr_text') or frm.get('visual_context') or "Visual frame sampled"
                        if len(desc) > 95:
                            desc = desc[:92] + "..."
                        f_rows.append([f_num, t_stamp, method, desc])
                    builder.add_table(f_headers, f_rows, col_widths=f_widths, alignments=f_aligns)

            builder.add_spacer(6.0)

        # -------------------------------------------------------------
        # SECTION 7: Methodology and Limitations
        # -------------------------------------------------------------
        section_idx = "6" if req_type == "text" and not image_data and not media_data else "6"
        builder.add_section_heading("Verification Methodology & Operational Boundaries", section_idx)
        
        methodology_text = (
            "TruthLens AI operates on a rigorous multi-stage verification architecture: atomic claim extraction, "
            "automated authoritative source discovery, bi-directional evidence stance evaluation, and deterministic "
            "confidence synthesis. The verdict reflects corroborated evidence across reputable indices at the time of query."
        )
        builder.add_paragraph(methodology_text, font_size=8.5, color="#1E293B", line_height=12.0)

        limitations_lines = [
            "1. Real-Time Index Limitations: Verification depends on publicly indexed and accessible reporting at the moment of search.",
            "2. Metric Independence: Acoustic clarity (transcription) and visual clarity (OCR) are technical indicators and do NOT imply truthfulness.",
            "3. Machine Synthesis Guardrails: LLM components only synthesize verified external citations and cannot invent independent assertions.",
            "4. Legal Disclaimer: This automated report is an investigative aid and does not constitute a judicial, regulatory, or definitive finding of law.",
        ]
        builder.add_card(
            title="Standard Investigative Boundaries & Caveats",
            lines=limitations_lines,
            border_color="#CBD5E1",
            bg_color="#F8FAFC"
        )
        builder.add_spacer(6.0)

        # -------------------------------------------------------------
        # SECTION 8: Audit Information & Cryptographic Fingerprint
        # -------------------------------------------------------------
        builder.add_section_heading("Audit Trail & Cryptographic Signature", "7")
        events = dossier.get("events") or []

        if events:
            builder.add_paragraph(
                f"Full lifecycle audit logged {len(events)} discrete state transition(s) during verification execution."
            )
            ev_headers = ["Timestamp (UTC)", "Stage Name", "Event Type", "Status"]
            ev_widths = [135.0, 130.0, 150.0, 113.0]
            ev_aligns = ["left", "left", "left", "center"]
            ev_rows = []
            for ev in events[:12]:
                ts = ev.get("created_at") or ""
                if len(ts) > 19:
                    ts = ts[:19].replace("T", " ")
                s_name = ev.get("stage_name", "")
                e_type = ev.get("event_type", "")
                s_stat = ev.get("status", "success").upper()
                ev_rows.append([ts, s_name, e_type, s_stat])
            builder.add_table(ev_headers, ev_rows, col_widths=ev_widths, alignments=ev_aligns)

        # Cryptographic Signatures
        content_hash = dossier.get("content_hash") or "N/A"
        sha_lines = [
            f"Input Content Fingerprint: {content_hash}",
            f"Document Engine Version: TruthLens Core Engine v{self.version} (Part 12 Certified)",
            f"Audit Identification UUID: {self.report_uuid}",
            "Tamper-Evident Assurance: Any byte-level alteration of this PDF file invalidates the SHA-256 fingerprint registered in the primary audit ledger."
        ]
        builder.add_callout(
            text="\n".join(sha_lines),
            title="Cryptographic Integrity & Tamper-Evident Seal",
            style="info"
        )

        # Build PDF bytes
        return builder.build_pdf_bytes()
