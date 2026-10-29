"""
Part 14 — Security, Testing & Reliability Audit
Automated Regression and Vulnerability Test Suite for TruthLens AI.
Tests SSRF validation, DNS-rebinding mitigations, path traversal defenses,
report hash integrity checks, filename sanitization, CSV formula injection neutralization,
and HTTP security response headers.
"""

import io
import os
import hashlib
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.core.exceptions import SecurityRiskException, TruthLensException
from app.utils.security_helpers import (
    validate_url_for_ssrf,
    is_forbidden_ip,
    sanitize_filename,
    validate_file_upload,
)
from app.verification.article.fetcher import SafeArticleFetcher
from app.verification.image.security import save_image_file, validate_image_security
from app.verification.media.security import save_media_file, validate_media_security
from app.verification.reports.service import ReportService
from app.verification.analytics.service import sanitize_csv_cell
from app.models.report import Report


# ==============================================================================
# 1. SSRF & URL VALIDATION TESTS
# ==============================================================================

class TestSSRFDefenses:
    """Rigorous SSRF test cases covering loopback, private ranges, cloud metadata, hex/decimal IPs, credentials, and schemes."""

    @pytest.mark.parametrize("disallowed_url", [
        # Loopback IPv4
        "http://127.0.0.1/admin",
        "http://127.0.0.2:80/status",
        "http://127.1.1.1/secret",
        "http://localhost/api",
        "http://localhost:8080/dashboard",
        # Loopback IPv6
        "http://[::1]/",
        "http://[::1]:8080/internal",
        # Private Class A, B, C
        "http://10.0.0.1/conf",
        "http://10.255.255.254/login",
        "http://172.16.0.1/private",
        "http://172.31.255.255/",
        "http://192.168.1.1/router",
        "http://192.168.0.254:8080/",
        # Cloud Metadata (AWS, GCP, Azure, Alibaba)
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.253/",
        "http://100.100.100.200/",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://instance-data/latest/meta-data",
        "http://kubernetes.default.svc/api",
        # Shared & benchmark spaces
        "http://100.64.0.1/",
        "http://198.18.0.1/",
        # Non-standard forbidden schemes
        "file:///etc/passwd",
        "gopher://127.0.0.1:6379/_INFO",
        "ftp://example.com/test",
        "data:text/html,<html>alert(1)</html>",
        "javascript:alert(1)",
        # Embedded credentials (userinfo)
        "http://user:password@example.com/page",
        "http://admin:secret@127.0.0.1/",
        "http://victim.com@127.0.0.1/",
        # Forbidden internal TLDs & suffixes
        "http://service.internal/",
        "http://vault.local/",
        "http://corp.test/",
        "http://hidden.onion/",
        # Forbidden ports
        "http://example.com:22/ssh",
        "http://example.com:25/smtp",
        "http://example.com:3306/mysql",
        "http://example.com:6379/redis",
        "http://example.com:27017/mongo",
    ])
    def test_forbidden_urls_raise_security_risk(self, disallowed_url):
        with pytest.raises(SecurityRiskException):
            validate_url_for_ssrf(disallowed_url)

    def test_decimal_ip_rejected(self):
        # 2130706433 is integer decimal for 127.0.0.1
        with pytest.raises(SecurityRiskException):
            validate_url_for_ssrf("http://2130706433/")

    def test_hexadecimal_ip_rejected(self):
        # 0x7f000001 is hexadecimal for 127.0.0.1
        with pytest.raises(SecurityRiskException):
            validate_url_for_ssrf("http://0x7f000001/")

    def test_ipv4_mapped_ipv6_loopback_rejected(self):
        # ::ffff:127.0.0.1
        with pytest.raises(SecurityRiskException):
            validate_url_for_ssrf("http://[::ffff:127.0.0.1]/")

    def test_control_character_in_url_rejected(self):
        with pytest.raises(SecurityRiskException):
            validate_url_for_ssrf("http://example.com/\x00secret")

    def test_valid_public_urls_accepted(self):
        valid_urls = [
            "https://www.bbc.com/news/world",
            "https://en.wikipedia.org/wiki/Main_Page",
            "http://example.com:80/",
            "https://example.com:443/article",
        ]
        for url in valid_urls:
            assert validate_url_for_ssrf(url) == url

    def test_is_forbidden_ip_helper(self):
        # Forbidden IPs
        forbidden_samples = [
            "127.0.0.1", "10.0.0.1", "172.16.5.1", "192.168.1.1",
            "169.254.169.254", "100.64.1.1", "198.18.1.1",
            "::1", "fe80::1", "fc00::1", "::ffff:127.0.0.1", "100.100.100.200"
        ]
        for ip in forbidden_samples:
            is_forbidden, reason = is_forbidden_ip(ip)
            assert is_forbidden is True, f"Expected {ip} to be forbidden"
            assert len(reason) > 0

        # Public IPs
        public_samples = ["8.8.8.8", "1.1.1.1", "93.184.216.34", "2606:4700:4700::1111"]
        for ip in public_samples:
            is_forbidden, _ = is_forbidden_ip(ip)
            assert is_forbidden is False, f"Expected {ip} to be permitted"


# ==============================================================================
# 2. ARTICLE FETCHER DNS-REBINDING MITIGATION TESTS
# ==============================================================================

class TestArticleFetcherRebinding:
    """Tests the defense-in-depth socket peer IP verification in SafeArticleFetcher."""

    def test_peer_ip_forbidden_raises_security_risk(self):
        fetcher = SafeArticleFetcher(connect_timeout=2.0, total_timeout=2.0)
        
        # Mock httpx response stream where socket peer returns a private IP (simulated DNS rebinding)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        
        mock_sock = MagicMock()
        mock_sock.getpeername.return_value = ("127.0.0.1", 80)
        
        mock_stream = MagicMock()
        mock_stream._sock = mock_sock
        mock_response.extensions = {"network_stream": mock_stream}

        with patch("httpx.Client.stream") as mock_stream_call:
            mock_stream_call.return_value.__enter__.return_value = mock_response
            with pytest.raises(SecurityRiskException) as exc_info:
                fetcher.fetch("https://example.com")
            assert "forbidden destination" in str(exc_info.value).lower() or "security violation" in str(exc_info.value).lower()


# ==============================================================================
# 3. FILENAME SANITIZATION & UPLOAD SECURITY TESTS
# ==============================================================================

class TestUploadSecurity:
    """Tests filename traversal sanitization, null byte removal, and CSV formula neutralization."""

    def test_sanitize_filename_traversal_paths(self):
        # POSIX traversal
        assert sanitize_filename("../../../../etc/passwd") == "passwd"
        # Windows traversal
        assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
        # Nested slashes
        assert sanitize_filename("foo/bar/test.png") == "test.png"
        assert sanitize_filename("foo\\bar\\audio.mp3") == "audio.mp3"

    def test_sanitize_filename_null_bytes_and_control_chars(self):
        # Null bytes
        assert sanitize_filename("image\x00.jpg") == "image.jpg"
        # Newlines and tabs
        assert sanitize_filename("my\r\nfile\t.png") == "myfile.png"

    def test_sanitize_filename_formula_neutralization(self):
        # Leading formula symbols
        assert sanitize_filename("=1+1.jpg") == "'=1+1.jpg"
        assert sanitize_filename("+cmd|calc.png") == "'+cmd|calc.png"
        assert sanitize_filename("-test.wav") == "'-test.wav"
        assert sanitize_filename("@data.mp4") == "'@data.mp4"

    def test_save_image_file_applies_filename_sanitization(self, tmp_path):
        with patch("app.core.config.settings.STORAGE_PATH", str(tmp_path)):
            png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
            result = save_image_file(
                data=png_bytes,
                original_filename="../../../malicious_name.png",
                mime_type="image/png",
                ext="png"
            )
            assert result["original_filename"] == "malicious_name.png"
            assert os.path.exists(result["file_path"])

    def test_save_media_file_applies_filename_sanitization(self, tmp_path):
        with patch("app.core.config.settings.STORAGE_PATH", str(tmp_path)):
            audio_bytes = b"ID3" + b"\x00" * 30
            result = save_media_file(
                data=audio_bytes,
                original_filename="..\\..\\secret\\leak.mp3",
                mime_type="audio/mpeg",
                ext="mp3"
            )
            assert result["original_filename"] == "leak.mp3"
            assert os.path.exists(result["file_path"])


# ==============================================================================
# 4. REPORT FILE PATH TRAVERSAL & INTEGRITY TESTS
# ==============================================================================

class TestReportIntegrityAndSecurity:
    """Tests report file path traversal prevention and SHA-256 integrity validation."""

    def test_report_path_traversal_blocked(self, tmp_path):
        service = ReportService()
        storage_root = tmp_path / "reports"
        storage_root.mkdir()

        # Target file is outside storage_root
        outside_file = tmp_path / "sensitive.txt"
        outside_file.write_text("classified")

        with patch("app.core.config.settings.REPORTS_STORAGE_PATH", str(storage_root)):
            fake_report = Report(
                id=1,
                report_uuid="rep_test_traversal",
                request_id=1,
                file_path=str(outside_file),
                status="generated"
            )
            with pytest.raises(TruthLensException) as exc_info:
                service.get_report_file_path(fake_report)
            assert exc_info.value.status_code == 403

    def test_report_missing_file_returns_404(self, tmp_path):
        service = ReportService()
        storage_root = tmp_path / "reports"
        storage_root.mkdir()

        missing_file = storage_root / "nonexistent.pdf"

        with patch("app.core.config.settings.REPORTS_STORAGE_PATH", str(storage_root)):
            fake_report = Report(
                id=2,
                report_uuid="rep_test_missing",
                request_id=1,
                file_path=str(missing_file),
                status="generated"
            )
            with pytest.raises(TruthLensException) as exc_info:
                service.get_report_file_path(fake_report)
            assert exc_info.value.status_code == 404

    def test_report_tampered_hash_rejected_with_409(self, tmp_path):
        service = ReportService()
        storage_root = tmp_path / "reports"
        storage_root.mkdir()

        report_file = storage_root / "valid_dossier.pdf"
        report_file.write_bytes(b"%PDF-1.4 original content")

        recorded_sha256 = hashlib.sha256(b"%PDF-1.4 original content").hexdigest()

        # Modify file on disk to simulate tampering or corruption
        report_file.write_bytes(b"%PDF-1.4 TAMPERED content")

        with patch("app.core.config.settings.REPORTS_STORAGE_PATH", str(storage_root)):
            fake_report = Report(
                id=3,
                report_uuid="rep_test_tampered",
                request_id=1,
                file_path=str(report_file),
                sha256_hash=recorded_sha256,
                status="generated"
            )
            with pytest.raises(TruthLensException) as exc_info:
                service.get_report_file_path(fake_report)
            assert exc_info.value.status_code == 409
            assert "integrity" in exc_info.value.detail.lower()

    def test_authentic_report_file_passes_integrity_check(self, tmp_path):
        service = ReportService()
        storage_root = tmp_path / "reports"
        storage_root.mkdir()

        content = b"%PDF-1.4 authentic report stream"
        report_file = storage_root / "authentic.pdf"
        report_file.write_bytes(content)

        recorded_sha256 = hashlib.sha256(content).hexdigest()

        with patch("app.core.config.settings.REPORTS_STORAGE_PATH", str(storage_root)):
            fake_report = Report(
                id=4,
                report_uuid="rep_test_authentic",
                request_id=1,
                file_path=str(report_file),
                sha256_hash=recorded_sha256,
                status="generated"
            )
            resolved_path = service.get_report_file_path(fake_report)
            assert resolved_path == str(report_file.resolve())


# ==============================================================================
# 5. HTTP SECURITY HEADERS & ERROR DISCLOSURE TESTS
# ==============================================================================

class TestHTTPDefenses:
    """Tests security response headers and unhandled error containment."""

    def test_security_headers_present_on_api_responses(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        headers = response.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-XSS-Protection") == "1; mode=block"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "camera=()" in headers.get("Permissions-Policy", "")

    def test_unhandled_exception_returns_clean_500(self):
        from fastapi.testclient import TestClient
        from app.main import app
        with patch("app.api.v1.endpoints.health.check_db_connection", side_effect=RuntimeError("Secret database connection trace")):
            unhandled_client = TestClient(app, raise_server_exceptions=False)
            response = unhandled_client.get("/api/v1/health")
            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "error"
            assert "Secret database connection trace" not in str(data)
            assert "internal server error" in data["detail"].lower()


# ==============================================================================
# 6. SPREADSHEET FORMULA INJECTION DEFENSE TESTS
# ==============================================================================

class TestCSVFormulaInjection:
    """Tests CSV cell formula sanitization."""

    @pytest.mark.parametrize("payload,expected_prefix", [
        ("=1+1", "'=1+1"),
        ("=cmd|' /C calc'!A0", "'=cmd|' /C calc'!A0"),
        ("+SUM(A1:A10)", "'+SUM(A1:A10)"),
        ("-100*2", "'-100*2"),
        ("@evil.com", "'@evil.com"),
        ("\t=cmd", "'\t=cmd"),
        ("\r=evil", "'\r=evil"),
        ("   =spaced_formula", "'   =spaced_formula"),
    ])
    def test_dangerous_formula_characters_prefixed(self, payload, expected_prefix):
        assert sanitize_csv_cell(payload) == expected_prefix

    def test_benign_text_unaltered(self):
        assert sanitize_csv_cell("Verified True") == "Verified True"
        assert sanitize_csv_cell("REQ-000123") == "REQ-000123"
        assert sanitize_csv_cell(12345) == "12345"
        assert sanitize_csv_cell(None) == ""
