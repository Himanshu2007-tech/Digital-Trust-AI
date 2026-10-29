"""
TruthLens AI — Professional Pure-Python Vector PDF Generator (Part 12)
Compliant with ISO 32000-1 / PDF 1.4 specification.
Zero external C-extension or internet dependencies required.
Produces clean, publication-grade multi-page verification reports.
"""

import zlib
import re
from typing import List, Tuple, Dict, Any, Optional

# Standard Adobe Type-1 Font 1000-unit Character Widths for Helvetica
HELVETICA_WIDTHS: Dict[str, int] = {
    ' ': 278, '!': 278, '"': 355, '#': 556, '$': 556, '%': 889, '&': 667, "'": 191,
    '(': 333, ')': 333, '*': 389, '+': 584, ',': 278, '-': 333, '.': 278, '/': 278,
    '0': 556, '1': 556, '2': 556, '3': 556, '4': 556, '5': 556, '6': 556, '7': 556,
    '8': 556, '9': 556, ':': 278, ';': 278, '<': 584, '=': 584, '>': 584, '?': 556,
    '@': 1015, 'A': 667, 'B': 667, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778,
    'H': 722, 'I': 278, 'J': 500, 'K': 667, 'L': 556, 'M': 833, 'N': 722, 'O': 778,
    'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722, 'V': 667, 'W': 944,
    'X': 667, 'Y': 667, 'Z': 611, '[': 278, '\\': 278, ']': 278, '^': 469, '_': 556,
    '`': 333, 'a': 556, 'b': 556, 'c': 500, 'd': 556, 'e': 556, 'f': 278, 'g': 556,
    'h': 556, 'i': 222, 'j': 222, 'k': 500, 'l': 222, 'm': 833, 'n': 556, 'o': 556,
    'p': 556, 'q': 556, 'r': 333, 's': 500, 't': 278, 'u': 556, 'v': 500, 'w': 722,
    'x': 500, 'y': 500, 'z': 500, '{': 334, '|': 260, '}': 334, '~': 584
}

HELVETICA_BOLD_WIDTHS: Dict[str, int] = {
    ' ': 278, '!': 333, '"': 474, '#': 556, '$': 556, '%': 889, '&': 722, "'": 238,
    '(': 333, ')': 333, '*': 389, '+': 584, ',': 278, '-': 333, '.': 278, '/': 278,
    '0': 556, '1': 556, '2': 556, '3': 556, '4': 556, '5': 556, '6': 556, '7': 556,
    '8': 556, '9': 556, ':': 333, ';': 333, '<': 584, '=': 584, '>': 584, '?': 611,
    '@': 975, 'A': 722, 'B': 722, 'C': 722, 'D': 722, 'E': 667, 'F': 611, 'G': 778,
    'H': 722, 'I': 278, 'J': 556, 'K': 722, 'L': 611, 'M': 833, 'N': 722, 'O': 778,
    'P': 667, 'Q': 778, 'R': 722, 'S': 667, 'T': 611, 'U': 722, 'V': 667, 'W': 944,
    'X': 667, 'Y': 667, 'Z': 611, '[': 333, '\\': 278, ']': 333, '^': 584, '_': 556,
    '`': 333, 'a': 556, 'b': 611, 'c': 556, 'd': 611, 'e': 556, 'f': 333, 'g': 611,
    'h': 611, 'i': 278, 'j': 278, 'k': 556, 'l': 278, 'm': 889, 'n': 611, 'o': 611,
    'p': 611, 'q': 611, 'r': 389, 's': 556, 't': 333, 'u': 611, 'v': 556, 'w': 778,
    'x': 556, 'y': 556, 'z': 500, '{': 389, '|': 280, '}': 389, '~': 584
}


def sanitize_text(text: Optional[str]) -> str:
    """Normalize unicode quotes, dashes, bullets, and non-ASCII characters to standard Latin/ASCII."""
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Unicode replacement map for common typographical marks
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
        "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
        "\u2013": "-", "\u2014": "--", "\u2015": "--", "\u2026": "...",
        "\u2022": "*", "\u2023": "*", "\u25aa": "*", "\u25ab": "*",
        "\u00a0": " ", "\u2009": " ", "\u202f": " ", "\u200b": "",
        "\u2713": "[v]", "\u2714": "[v]", "\u2717": "[x]", "\u2718": "[x]",
        "\u20ac": "EUR", "\u00a3": "GBP", "\u00a5": "JPY", "\u20b9": "INR",
        "\t": "    ", "\r": "",
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)

    # Strip or replace unprintable or unsupported codepoints
    cleaned = []
    for ch in text:
        code = ord(ch)
        if 32 <= code <= 126 or code in (10,):
            cleaned.append(ch)
        elif 160 <= code <= 255:
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    return "".join(cleaned)


def escape_pdf_string(text: str) -> str:
    """Escape special characters for PDF literal strings (...)."""
    text = sanitize_text(text)
    text = text.replace("\\", "\\\\")
    text = text.replace("(", "\\(")
    text = text.replace(")", "\\)")
    return text


def hex_to_rgb(hex_code: str) -> Tuple[float, float, float]:
    """Convert hex color (#1E293B) to PDF RGB float tuple (0.0 - 1.0)."""
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join(c * 2 for c in hex_code)
    if len(hex_code) != 6:
        return (0.1, 0.1, 0.1)
    r = int(hex_code[0:2], 16) / 255.0
    g = int(hex_code[2:4], 16) / 255.0
    b = int(hex_code[4:6], 16) / 255.0
    return (round(r, 4), round(g, 4), round(b, 4))


def measure_text_width(text: str, font_name: str, font_size: float) -> float:
    """Accurately compute width of a text string in points."""
    clean = sanitize_text(text)
    if font_name in ("Courier", "Courier-Bold"):
        return len(clean) * (font_size * 0.6)

    table = HELVETICA_BOLD_WIDTHS if "Bold" in font_name else HELVETICA_WIDTHS
    units = sum(table.get(ch, 550) for ch in clean)
    return (units * font_size) / 1000.0


def wrap_text(text: str, font_name: str, font_size: float, max_width: float) -> List[str]:
    """Wrap text cleanly into lines that strictly fit within max_width."""
    clean = sanitize_text(text).strip()
    if not clean:
        return []

    lines = []
    # Preserve explicit newlines if any
    raw_paragraphs = clean.split("\n")

    for raw_p in raw_paragraphs:
        words = raw_p.split()
        if not words:
            lines.append("")
            continue

        current_line = []
        current_width = 0.0
        space_width = measure_text_width(" ", font_name, font_size)

        for word in words:
            word_width = measure_text_width(word, font_name, font_size)
            
            # If word is wider than max_width, break the word itself
            if word_width > max_width:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = []
                    current_width = 0.0
                
                sub_chars = []
                sub_width = 0.0
                for ch in word:
                    ch_w = measure_text_width(ch, font_name, font_size)
                    if sub_width + ch_w > max_width and sub_chars:
                        lines.append("".join(sub_chars))
                        sub_chars = [ch]
                        sub_width = ch_w
                    else:
                        sub_chars.append(ch)
                        sub_width += ch_w
                if sub_chars:
                    current_line = ["".join(sub_chars)]
                    current_width = sub_width
                continue

            test_width = current_width + (space_width if current_line else 0.0) + word_width
            if test_width <= max_width:
                current_line.append(word)
                current_width = test_width
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_width = word_width

        if current_line:
            lines.append(" ".join(current_line))

    return lines


class PDFBuilder:
    """
    Standard-compliant, multi-page vector PDF Document Generator.
    Supports headings, paragraphs, styled callout cards, tables, badges,
    clickable URI hyperlinks, progress meters, and dynamic two-pass page numbers.
    """

    PAGE_WIDTH: float = 612.0    # 8.5 in * 72 pt
    PAGE_HEIGHT: float = 792.0   # 11 in * 72 pt
    MARGIN_LEFT: float = 42.0
    MARGIN_RIGHT: float = 42.0
    MARGIN_TOP: float = 46.0
    MARGIN_BOTTOM: float = 46.0
    CONTENT_WIDTH: float = 528.0 # 612 - 84
    HEADER_OFFSET: float = 24.0
    FOOTER_OFFSET: float = 26.0

    FONT_MAP = {
        "Helvetica": "/F1",
        "Helvetica-Bold": "/F2",
        "Helvetica-Oblique": "/F3",
        "Courier": "/F4",
        "Courier-Bold": "/F5",
    }

    def __init__(self, doc_title: str = "TruthLens AI Verification Report", subtitle: str = ""):
        self.doc_title = sanitize_text(doc_title)
        self.doc_subtitle = sanitize_text(subtitle)
        
        # Pages storage: each page stores commands and link annotations
        self.pages_ops: List[List[str]] = []
        self.pages_annots: List[List[str]] = []
        
        self.current_ops: List[str] = []
        self.current_annots: List[str] = []
        
        self.cursor_y: float = self.PAGE_HEIGHT - self.MARGIN_TOP - self.HEADER_OFFSET
        self.min_y: float = self.MARGIN_BOTTOM + self.FOOTER_OFFSET
        
        # Start initial page
        self._new_page()

    def _new_page(self):
        """Finalize current page if any and start a new page."""
        if self.current_ops:
            self.pages_ops.append(self.current_ops)
            self.pages_annots.append(self.current_annots)
        
        self.current_ops = []
        self.current_annots = []
        self.cursor_y = self.PAGE_HEIGHT - self.MARGIN_TOP - self.HEADER_OFFSET

    def check_page_break(self, required_height: float):
        """Ensure there is at least required_height available, otherwise create a new page."""
        if (self.cursor_y - required_height) < self.min_y:
            self._new_page()

    # Low-level PDF Graphics Operators
    def draw_rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill_color: Optional[str] = None,
        stroke_color: Optional[str] = None,
        stroke_width: float = 1.0,
        rx: float = 0.0
    ):
        """Draw an optionally filled/stroked rectangle with optional rounded corners."""
        ops = ["q"]
        if fill_color:
            r, g, b = hex_to_rgb(fill_color)
            ops.append(f"{r:.4f} {g:.4f} {b:.4f} rg")
        if stroke_color:
            r, g, b = hex_to_rgb(stroke_color)
            ops.append(f"{r:.4f} {g:.4f} {b:.4f} RG")
            ops.append(f"{stroke_width:.2f} w")

        if rx <= 0.0:
            ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re")
        else:
            # Rounded rectangle bezier path
            k = 0.5522847498 * rx
            x0, x1, x2, x3 = x, x + rx, x + w - rx, x + w
            y0, y1, y2, y3 = y, y + rx, y + h - rx, y + h
            ops.append(f"{x1:.2f} {y0:.2f} m")
            ops.append(f"{x2:.2f} {y0:.2f} l")
            ops.append(f"{x2 + k:.2f} {y0:.2f} {x3:.2f} {y0 + rx - k:.2f} {x3:.2f} {y1:.2f} c")
            ops.append(f"{x3:.2f} {y2:.2f} l")
            ops.append(f"{x3:.2f} {y2 + k:.2f} {x2 + k:.2f} {y3:.2f} {x2:.2f} {y3:.2f} c")
            ops.append(f"{x1:.2f} {y3:.2f} l")
            ops.append(f"{x1 - k:.2f} {y3:.2f} {x0:.2f} {y2 + k:.2f} {x0:.2f} {y2:.2f} c")
            ops.append(f"{x0:.2f} {y1:.2f} l")
            ops.append(f"{x0:.2f} {y0 + rx - k:.2f} {x1 - k:.2f} {y0:.2f} {x1:.2f} {y0:.2f} c")

        if fill_color and stroke_color:
            ops.append("B")
        elif fill_color:
            ops.append("f")
        elif stroke_color:
            ops.append("S")
        ops.append("Q")
        self.current_ops.append(" ".join(ops))

    def draw_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        stroke_color: str = "#CBD5E1",
        stroke_width: float = 0.75,
        dash: Optional[List[int]] = None
    ):
        """Draw a vector stroke line."""
        r, g, b = hex_to_rgb(stroke_color)
        ops = ["q", f"{r:.4f} {g:.4f} {b:.4f} RG", f"{stroke_width:.2f} w"]
        if dash:
            dash_str = " ".join(str(d) for d in dash)
            ops.append(f"[{dash_str}] 0 d")
        ops.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S Q")
        self.current_ops.append(" ".join(ops))

    def draw_text(
        self,
        x: float,
        y: float,
        text: str,
        font_name: str = "Helvetica",
        font_size: float = 9.0,
        color: str = "#1E293B",
        align: str = "left"
    ):
        """Render a single text line at (x, y) baseline."""
        clean = sanitize_text(text)
        if not clean:
            return

        font_tag = self.FONT_MAP.get(font_name, "/F1")
        r, g, b = hex_to_rgb(color)

        if align == "center":
            w = measure_text_width(clean, font_name, font_size)
            x = x - (w / 2.0)
        elif align == "right":
            w = measure_text_width(clean, font_name, font_size)
            x = x - w

        escaped = escape_pdf_string(clean)
        op = f"q {r:.4f} {g:.4f} {b:.4f} rg BT {font_tag} {font_size:.2f} Tf {x:.2f} {y:.2f} Td ({escaped}) Tj ET Q"
        self.current_ops.append(op)

    def add_link_annotation(self, x: float, y: float, w: float, h: float, url: str):
        """Add clickable URI hyperlink annotation to current page."""
        clean_url = sanitize_text(url).replace("(", "%28").replace(")", "%29")
        annot = (
            f"<< /Type /Annot /Subtype /Link "
            f"/Rect [{x:.2f} {y:.2f} {x + w:.2f} {y + h:.2f}] "
            f"/Border [0 0 0] "
            f"/A << /S /URI /URI ({clean_url}) >> >>"
        )
        self.current_annots.append(annot)

    # High-Level Layout Components
    def add_spacer(self, points: float = 10.0):
        """Advance cursor downward."""
        self.cursor_y -= points
        if self.cursor_y < self.min_y:
            self._new_page()

    def add_separator(self, space_before: float = 6.0, space_after: float = 8.0, color: str = "#E2E8F0"):
        """Draw horizontal dividing line."""
        self.check_page_break(space_before + space_after + 1.0)
        self.cursor_y -= space_before
        self.draw_line(self.MARGIN_LEFT, self.cursor_y, self.PAGE_WIDTH - self.MARGIN_RIGHT, self.cursor_y, stroke_color=color, stroke_width=0.75)
        self.cursor_y -= space_after

    def add_cover_banner(
        self,
        report_title: str,
        report_uuid: str,
        request_id: int,
        request_type: str,
        status: str,
        generated_at: str,
    ):
        """Render publication-grade report header block."""
        banner_height = 84.0
        self.check_page_break(banner_height + 15.0)

        top_y = self.cursor_y
        w = self.CONTENT_WIDTH
        x = self.MARGIN_LEFT
        y = top_y - banner_height

        # Main dark brand background (#0F172A slate-900)
        self.draw_rect(x, y, w, banner_height, fill_color="#0F172A", rx=4.0)

        # Brand accent stripe on left edge (primary cyan/blue #2563EB)
        self.draw_rect(x, y, 6.0, banner_height, fill_color="#2563EB", rx=2.0)

        # TruthLens branding tag
        self.draw_text(x + 16.0, top_y - 20.0, "TRUTHLENS AI  *  OFFICIAL VERIFICATION DOSSIER", font_name="Helvetica-Bold", font_size=8.0, color="#94A3B8")

        # Main document title
        self.draw_text(x + 16.0, top_y - 40.0, report_title.upper(), font_name="Helvetica-Bold", font_size=15.0, color="#FFFFFF")

        # Subtitle / metadata tags
        meta_str = f"REPORT ID: {report_uuid}   |   REQUEST #{request_id}   |   TYPE: {request_type.upper()}   |   STATUS: {status.upper()}"
        self.draw_text(x + 16.0, top_y - 58.0, meta_str, font_name="Helvetica", font_size=8.5, color="#CBD5E1")

        # Timestamp right-aligned
        date_str = f"GENERATED: {generated_at}"
        self.draw_text(x + 16.0, top_y - 72.0, date_str, font_name="Courier", font_size=7.5, color="#94A3B8")

        self.cursor_y = y - 14.0

    def add_section_heading(self, title: str, section_number: Optional[str] = None):
        """Render major section title with numbering and accent line."""
        self.check_page_break(34.0)
        self.cursor_y -= 6.0

        label = f"{section_number}. {title.upper()}" if section_number else title.upper()
        self.draw_text(self.MARGIN_LEFT, self.cursor_y, label, font_name="Helvetica-Bold", font_size=11.5, color="#0F172A")
        
        # Underline bar
        bar_y = self.cursor_y - 4.0
        self.draw_line(self.MARGIN_LEFT, bar_y, self.PAGE_WIDTH - self.MARGIN_RIGHT, bar_y, stroke_color="#E2E8F0", stroke_width=1.0)
        self.draw_line(self.MARGIN_LEFT, bar_y, self.MARGIN_LEFT + 40.0, bar_y, stroke_color="#2563EB", stroke_width=2.0)

        self.cursor_y = bar_y - 10.0

    def add_paragraph(
        self,
        text: str,
        font_name: str = "Helvetica",
        font_size: float = 9.0,
        color: str = "#334155",
        line_height: float = 13.0,
        space_after: float = 6.0,
        indent: float = 0.0,
        max_width: Optional[float] = None,
    ):
        """Add word-wrapped paragraph."""
        w = (max_width or self.CONTENT_WIDTH) - indent
        lines = wrap_text(text, font_name, font_size, w)
        if not lines:
            return

        for line in lines:
            self.check_page_break(line_height + 2.0)
            self.draw_text(self.MARGIN_LEFT + indent, self.cursor_y, line, font_name=font_name, font_size=font_size, color=color)
            self.cursor_y -= line_height

        self.cursor_y -= space_after

    def add_verdict_card(
        self,
        verdict: Optional[str],
        confidence_pct: Optional[float],
        summary: Optional[str],
        claims_counts: Dict[str, int],
    ):
        """Render prominent Executive Summary card with verdict badge and confidence bar."""
        card_w = self.CONTENT_WIDTH
        v_upper = (verdict or "UNVERIFIED").upper()

        # Verdict theme mapping
        theme = {
            "SUPPORTED": {"bg": "#ECFDF5", "border": "#10B981", "badge_bg": "#059669", "text": "#065F46", "label": "SUPPORTED BY EVIDENCE"},
            "CONTRADICTED": {"bg": "#FEF2F2", "border": "#EF4444", "badge_bg": "#DC2626", "text": "#991B1B", "label": "CONTRADICTED BY EVIDENCE"},
            "MISLEADING": {"bg": "#FFFBEB", "border": "#F59E0B", "badge_bg": "#D97706", "text": "#92400E", "label": "MISLEADING / LACKS CONTEXT"},
            "UNVERIFIED": {"bg": "#F8FAFC", "border": "#94A3B8", "badge_bg": "#64748B", "text": "#334155", "label": "UNVERIFIED CLAIMS"},
            "INSUFFICIENT_INFORMATION": {"bg": "#F8FAFC", "border": "#94A3B8", "badge_bg": "#64748B", "text": "#334155", "label": "INSUFFICIENT INFORMATION"},
        }.get(v_upper, {"bg": "#F8FAFC", "border": "#94A3B8", "badge_bg": "#64748B", "text": "#334155", "label": v_upper})

        # Calculate summary wrapped lines
        summary_text = summary or "No analytical explanation was stored for this verification."
        wrapped_summary = wrap_text(summary_text, "Helvetica", 8.5, card_w - 28.0)
        
        # Estimate card height
        base_h = 96.0 + (len(wrapped_summary) * 12.0)
        self.check_page_break(base_h + 12.0)

        card_top = self.cursor_y
        card_bottom = card_top - base_h
        card_x = self.MARGIN_LEFT

        # Outer card background and border
        self.draw_rect(card_x, card_bottom, card_w, base_h, fill_color=theme["bg"], stroke_color=theme["border"], stroke_width=1.0, rx=4.0)

        # Verdict pill badge
        badge_w = measure_text_width(theme["label"], "Helvetica-Bold", 9.0) + 20.0
        badge_h = 20.0
        badge_y = card_top - 28.0
        self.draw_rect(card_x + 14.0, badge_y, badge_w, badge_h, fill_color=theme["badge_bg"], rx=3.0)
        self.draw_text(card_x + 24.0, badge_y + 6.0, theme["label"], font_name="Helvetica-Bold", font_size=9.0, color="#FFFFFF")

        # Confidence percentage
        conf_val = confidence_pct if confidence_pct is not None else 0.0
        conf_str = f"EVIDENCE CONFIDENCE: {conf_val:.1f}%"
        self.draw_text(card_x + badge_w + 30.0, badge_y + 6.0, conf_str, font_name="Helvetica-Bold", font_size=9.0, color=theme["text"])

        # Confidence progress bar
        bar_x = card_x + card_w - 170.0
        bar_y = badge_y + 4.0
        bar_w = 150.0
        bar_h = 10.0
        self.draw_rect(bar_x, bar_y, bar_w, bar_h, fill_color="#E2E8F0", rx=2.0)
        fill_w = max(2.0, min(bar_w, (conf_val / 100.0) * bar_w))
        self.draw_rect(bar_x, bar_y, fill_w, bar_h, fill_color=theme["border"], rx=2.0)

        # Claims breakdown stats line
        stats_y = card_top - 46.0
        stats_str = (
            f"Claims Analyzed: {sum(claims_counts.values())}   |   "
            f"Supported: {claims_counts.get('supported', 0)}   |   "
            f"Contradicted: {claims_counts.get('contradicted', 0)}   |   "
            f"Misleading: {claims_counts.get('misleading', 0)}   |   "
            f"Unverified: {claims_counts.get('unverified', 0)}"
        )
        self.draw_text(card_x + 14.0, stats_y, stats_str, font_name="Helvetica-Bold", font_size=8.0, color="#475569")
        self.draw_line(card_x + 14.0, stats_y - 6.0, card_x + card_w - 14.0, stats_y - 6.0, stroke_color="#CBD5E1", stroke_width=0.5)

        # Summary text lines
        cur_text_y = stats_y - 18.0
        for s_line in wrapped_summary:
            self.draw_text(card_x + 14.0, cur_text_y, s_line, font_name="Helvetica", font_size=8.5, color="#1E293B")
            cur_text_y -= 12.0

        self.cursor_y = card_bottom - 12.0

    def add_table(
        self,
        headers: List[str],
        rows: List[List[str]],
        col_widths: Optional[List[float]] = None,
        alignments: Optional[List[str]] = None,
        row_urls: Optional[List[Dict[int, str]]] = None,
        font_size: float = 8.0,
    ):
        """Render a clean grid table with multi-line cell wrapping and clickable link cells."""
        if not headers:
            return

        num_cols = len(headers)
        if not col_widths:
            equal_w = self.CONTENT_WIDTH / num_cols
            col_widths = [equal_w] * num_cols

        if not alignments:
            alignments = ["left"] * num_cols

        # Header height
        header_h = 18.0
        self.check_page_break(header_h + 20.0)

        table_x = self.MARGIN_LEFT
        top_y = self.cursor_y

        # Draw Header Row (#0F172A dark navy fill)
        self.draw_rect(table_x, top_y - header_h, self.CONTENT_WIDTH, header_h, fill_color="#0F172A")
        
        cur_x = table_x
        for i, h_text in enumerate(headers):
            w = col_widths[i]
            align = alignments[i]
            tx = cur_x + (w / 2.0 if align == "center" else (w - 6.0 if align == "right" else 6.0))
            self.draw_text(tx, top_y - 12.0, h_text.upper(), font_name="Helvetica-Bold", font_size=7.5, color="#F8FAFC", align=align)
            cur_x += w

        self.cursor_y = top_y - header_h

        # Rows
        for row_idx, row in enumerate(rows):
            # Compute row height based on cell with highest wrap count
            cell_lines_per_col = []
            for i, val in enumerate(row):
                w = col_widths[i] - 10.0
                cell_lines = wrap_text(str(val), "Helvetica", font_size, w)
                cell_lines_per_col.append(cell_lines or [""])

            max_lines = max((len(c) for c in cell_lines_per_col), default=1)
            row_h = max(16.0, (max_lines * 11.0) + 6.0)

            self.check_page_break(row_h + 4.0)
            row_top = self.cursor_y
            row_bottom = row_top - row_h

            # Alternating zebra striping
            bg_color = "#FFFFFF" if row_idx % 2 == 0 else "#F8FAFC"
            self.draw_rect(table_x, row_bottom, self.CONTENT_WIDTH, row_h, fill_color=bg_color, stroke_color="#E2E8F0", stroke_width=0.5)

            # Render cells
            cur_x = table_x
            for col_idx, lines in enumerate(cell_lines_per_col):
                w = col_widths[col_idx]
                align = alignments[col_idx]
                url = row_urls[row_idx].get(col_idx) if row_urls and row_idx < len(row_urls) else None

                cell_y = row_top - 10.0
                for l_idx, line in enumerate(lines):
                    tx = cur_x + (w / 2.0 if align == "center" else (w - 6.0 if align == "right" else 6.0))
                    text_color = "#2563EB" if url else "#334155"
                    font = "Helvetica-Bold" if url else "Helvetica"
                    self.draw_text(tx, cell_y, line, font_name=font, font_size=font_size, color=text_color, align=align)
                    
                    if url and l_idx == 0:
                        # Add clickable link annotation over cell area
                        self.add_link_annotation(cur_x + 4.0, row_bottom + 2.0, w - 8.0, row_h - 4.0, url)
                    cell_y -= 11.0

                cur_x += w

            self.cursor_y = row_bottom

        self.cursor_y -= 8.0

    def add_card(
        self,
        title: str,
        subtitle: Optional[str] = None,
        lines: Optional[List[str]] = None,
        key_values: Optional[List[Tuple[str, str]]] = None,
        border_color: str = "#CBD5E1",
        bg_color: str = "#F8FAFC",
        accent_color: Optional[str] = None,
    ):
        """Render a boxed metadata card."""
        w = self.CONTENT_WIDTH
        x = self.MARGIN_LEFT

        # Estimate card height
        h_est = 24.0
        if subtitle:
            h_est += 12.0
        if key_values:
            h_est += len(key_values) * 13.0
        if lines:
            h_est += sum(len(wrap_text(l, "Helvetica", 8.5, w - 24.0)) * 12.0 for l in lines) + 6.0

        self.check_page_break(h_est + 8.0)
        card_top = self.cursor_y
        card_bottom = card_top - h_est

        # Background box
        self.draw_rect(x, card_bottom, w, h_est, fill_color=bg_color, stroke_color=border_color, stroke_width=0.75, rx=3.0)

        # Optional left accent bar
        if accent_color:
            self.draw_rect(x, card_bottom, 4.0, h_est, fill_color=accent_color, rx=2.0)

        cur_y = card_top - 14.0
        self.draw_text(x + 12.0, cur_y, title, font_name="Helvetica-Bold", font_size=9.5, color="#0F172A")
        cur_y -= 13.0

        if subtitle:
            self.draw_text(x + 12.0, cur_y, subtitle, font_name="Helvetica", font_size=8.0, color="#64748B")
            cur_y -= 13.0

        if key_values:
            for k, v in key_values:
                k_clean = f"{k}:"
                self.draw_text(x + 12.0, cur_y, k_clean, font_name="Helvetica-Bold", font_size=8.0, color="#475569")
                self.draw_text(x + 110.0, cur_y, v, font_name="Helvetica", font_size=8.0, color="#1E293B")
                cur_y -= 12.0

        if lines:
            for l in lines:
                wrapped = wrap_text(l, "Helvetica", 8.5, w - 24.0)
                for wl in wrapped:
                    self.draw_text(x + 12.0, cur_y, wl, font_name="Helvetica", font_size=8.5, color="#334155")
                    cur_y -= 12.0

        self.cursor_y = card_bottom - 8.0

    def add_callout(
        self,
        text: str,
        title: Optional[str] = None,
        style: str = "info"
    ):
        """Render a full-width callout notice box."""
        styles = {
            "info": {"bg": "#F0F9FF", "border": "#38BDF8", "accent": "#0284C7", "title_color": "#0369A1"},
            "warning": {"bg": "#FFFBEB", "border": "#FCD34D", "accent": "#D97706", "title_color": "#92400E"},
            "danger": {"bg": "#FEF2F2", "border": "#FCA5A5", "accent": "#EF4444", "title_color": "#991B1B"},
            "success": {"bg": "#ECFDF5", "border": "#6EE7B7", "accent": "#10B981", "title_color": "#065F46"},
        }
        cfg = styles.get(style, styles["info"])

        w = self.CONTENT_WIDTH
        x = self.MARGIN_LEFT
        wrapped_lines = wrap_text(text, "Helvetica", 8.5, w - 28.0)
        
        box_h = (len(wrapped_lines) * 12.0) + (26.0 if title else 16.0)
        self.check_page_break(box_h + 8.0)

        card_top = self.cursor_y
        card_bottom = card_top - box_h

        self.draw_rect(x, card_bottom, w, box_h, fill_color=cfg["bg"], stroke_color=cfg["border"], stroke_width=0.75, rx=3.0)
        self.draw_rect(x, card_bottom, 4.0, box_h, fill_color=cfg["accent"], rx=2.0)

        cur_y = card_top - 13.0
        if title:
            self.draw_text(x + 14.0, cur_y, title.upper(), font_name="Helvetica-Bold", font_size=8.5, color=cfg["title_color"])
            cur_y -= 13.0

        for line in wrapped_lines:
            self.draw_text(x + 14.0, cur_y, line, font_name="Helvetica", font_size=8.5, color="#1E293B")
            cur_y -= 12.0

        self.cursor_y = card_bottom - 8.0

    # Page Header / Footer Renderer & PDF Serializer
    def _render_page_headers_and_footers(self, total_pages: int):
        """Append running headers and dynamic 'Page X of Y' footers to all pages."""
        header_y = self.PAGE_HEIGHT - self.MARGIN_TOP + 8.0
        footer_y = self.MARGIN_BOTTOM - 14.0

        for p_idx, ops in enumerate(self.pages_ops):
            p_num = p_idx + 1

            # --- Running Header ---
            r_head = (
                f"q 0.5804 0.6392 0.7216 RG 0.50 w "
                f"{self.MARGIN_LEFT:.2f} {header_y - 6.0:.2f} m {self.PAGE_WIDTH - self.MARGIN_RIGHT:.2f} {header_y - 6.0:.2f} l S Q"
            )
            ops.append(r_head)
            
            # Left title & right timestamp
            escaped_title = escape_pdf_string("TRUTHLENS AI -- VERIFICATION DOSSIER")
            escaped_sub = escape_pdf_string(self.doc_subtitle)
            h_text_op = (
                f"q 0.4000 0.4500 0.5200 rg "
                f"BT /F2 7.00 Tf {self.MARGIN_LEFT:.2f} {header_y:.2f} Td ({escaped_title}) Tj ET "
                f"BT /F1 7.00 Tf {self.PAGE_WIDTH - self.MARGIN_RIGHT - 140.0:.2f} {header_y:.2f} Td ({escaped_sub}) Tj ET "
                f"Q"
            )
            ops.append(h_text_op)

            # --- Running Footer ---
            r_foot = (
                f"q 0.8863 0.9098 0.9412 RG 0.50 w "
                f"{self.MARGIN_LEFT:.2f} {footer_y + 12.0:.2f} m {self.PAGE_WIDTH - self.MARGIN_RIGHT:.2f} {footer_y + 12.0:.2f} l S Q"
            )
            ops.append(r_foot)

            page_str = escape_pdf_string(f"PAGE {p_num} OF {total_pages}")
            confidential_str = escape_pdf_string("CONFIDENTIAL & AUDITED VERIFICATION DOSSIER * SECURE DIGITAL ARCHIVE")
            f_text_op = (
                f"q 0.4000 0.4500 0.5200 rg "
                f"BT /F1 6.50 Tf {self.MARGIN_LEFT:.2f} {footer_y:.2f} Td ({confidential_str}) Tj ET "
                f"BT /F2 7.00 Tf {self.PAGE_WIDTH - self.MARGIN_RIGHT - 65.0:.2f} {footer_y:.2f} Td ({page_str}) Tj ET "
                f"Q"
            )
            ops.append(f_text_op)

    def build_pdf_bytes(self) -> bytes:
        """
        Compile complete PDF 1.4 document into byte string.
        Flate-compresses page streams using zlib and generates valid cross-reference table.
        """
        # Ensure last active page is saved
        if self.current_ops and self.current_ops not in self.pages_ops:
            self.pages_ops.append(self.current_ops)
            self.pages_annots.append(self.current_annots)

        total_pages = len(self.pages_ops)
        if total_pages == 0:
            self._new_page()
            self.pages_ops.append(self.current_ops)
            self.pages_annots.append(self.current_annots)
            total_pages = 1

        # Second pass: inject header and dynamic Page X of Y footers
        self._render_page_headers_and_footers(total_pages)

        # Object registry for xref table
        objects: Dict[int, bytes] = {}
        next_obj_id = 1

        # 1. Catalog
        catalog_id = next_obj_id
        next_obj_id += 1

        # 2. Pages Root
        pages_id = next_obj_id
        next_obj_id += 1

        # 3. Fonts: Helvetica, Helvetica-Bold, Helvetica-Oblique, Courier, Courier-Bold
        font_helvetica_id = next_obj_id
        next_obj_id += 1
        objects[font_helvetica_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"

        font_bold_id = next_obj_id
        next_obj_id += 1
        objects[font_bold_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"

        font_oblique_id = next_obj_id
        next_obj_id += 1
        objects[font_oblique_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique /Encoding /WinAnsiEncoding >>"

        font_courier_id = next_obj_id
        next_obj_id += 1
        objects[font_courier_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>"

        font_courier_bold_id = next_obj_id
        next_obj_id += 1
        objects[font_courier_bold_id] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold /Encoding /WinAnsiEncoding >>"

        # Resources dictionary string
        resources_str = (
            f"<< /Font << "
            f"/F1 {font_helvetica_id} 0 R "
            f"/F2 {font_bold_id} 0 R "
            f"/F3 {font_oblique_id} 0 R "
            f"/F4 {font_courier_id} 0 R "
            f"/F5 {font_courier_bold_id} 0 R "
            f">> /ProcSet [/PDF /Text /ImageB /ImageC /ImageI] >>"
        )

        page_ids = []
        # Create Page Objects and Content Streams
        for p_idx in range(total_pages):
            page_obj_id = next_obj_id
            next_obj_id += 1
            page_ids.append(page_obj_id)

            content_obj_id = next_obj_id
            next_obj_id += 1

            # Compress stream content
            stream_raw = "\n".join(self.pages_ops[p_idx]).encode("latin-1", errors="replace")
            compressed = zlib.compress(stream_raw)
            stream_dict = f"<< /Length {len(compressed)} /Filter /FlateDecode >>\nstream\n".encode("latin-1")
            stream_body = stream_dict + compressed + b"\nendstream"
            objects[content_obj_id] = stream_body

            # Annotations
            annots_list = self.pages_annots[p_idx]
            annots_clause = ""
            if annots_list:
                annots_joined = " ".join(annots_list)
                annots_clause = f"/Annots [ {annots_joined} ] "

            page_dict = (
                f"<< /Type /Page "
                f"/Parent {pages_id} 0 R "
                f"/MediaBox [0 0 {self.PAGE_WIDTH:.1f} {self.PAGE_HEIGHT:.1f}] "
                f"/Contents {content_obj_id} 0 R "
                f"/Resources {resources_str} "
                f"{annots_clause}>>"
            ).encode("latin-1")
            objects[page_obj_id] = page_dict

        # Catalog dictionary
        objects[catalog_id] = f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("latin-1")

        # Pages Root dictionary
        kids_str = " ".join(f"{pid} 0 R" for pid in page_ids)
        objects[pages_id] = f"<< /Type /Pages /Kids [ {kids_str} ] /Count {len(page_ids)} >>".encode("latin-1")

        # Info dictionary
        info_id = next_obj_id
        next_obj_id += 1
        title_esc = escape_pdf_string(self.doc_title)
        objects[info_id] = (
            f"<< /Title ({title_esc}) "
            f"/Author (TruthLens AI Enterprise Verification Subsystem) "
            f"/Producer (TruthLens AI Pure-Python PDF Generator v1.0) "
            f"/Subject (Automated Fact-Checking & Multimedia Forensic Dossier) >>"
        ).encode("latin-1")

        # Serialize PDF with exact byte offsets in cross reference table
        buf = bytearray()
        buf.extend(b"%PDF-1.4\n")
        # Binary comment to ensure 8-bit binary transport integrity
        buf.extend(b"%\xe2\xe3\xcf\xd3\n")

        offsets = {}
        sorted_ids = sorted(objects.keys())
        for oid in sorted_ids:
            offsets[oid] = len(buf)
            buf.extend(f"{oid} 0 obj\n".encode("latin-1"))
            buf.extend(objects[oid])
            buf.extend(b"\nendobj\n")

        # Cross reference table
        xref_offset = len(buf)
        buf.extend(f"xref\n0 {next_obj_id}\n".encode("latin-1"))
        buf.extend(b"0000000000 65535 f \n")
        for oid in range(1, next_obj_id):
            if oid in offsets:
                buf.extend(f"{offsets[oid]:010d} 00000 n \n".encode("latin-1"))
            else:
                buf.extend(b"0000000000 65535 f \n")

        # Trailer
        trailer = (
            f"trailer\n<< /Size {next_obj_id} /Root {catalog_id} 0 R /Info {info_id} 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("latin-1")
        buf.extend(trailer)

        return bytes(buf)
