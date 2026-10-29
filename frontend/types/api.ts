export interface DatabaseHealth {
  connected: boolean;
  type: string;
  error?: string | null;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  timestamp: string;
  environment: string;
  database: DatabaseHealth;
  features?: Record<string, string>;
}

export type ConnectionStatus = "connected" | "disconnected" | "loading" | "error";

export interface BackendConnectionState {
  status: ConnectionStatus;
  latencyMs: number | null;
  data: HealthResponse | null;
  errorMessage: string | null;
  lastChecked: Date | null;
}

export interface NotImplementedResponse {
  status: "not_implemented";
  message: string;
  module?: string;
}

export interface VerificationHistoryItem {
  id: number;
  request_type: string;
  status: string;
  created_at: string | null;
  content_preview: string | null;
}

export interface ReportItem {
  id: number;
  report_uuid?: string;
  request_id?: number;
  user_id?: number | null;
  title: string;
  format: string;
  download_url?: string;
  file_size_bytes?: number | null;
  mime_type?: string;
  sha256_hash?: string | null;
  status: string;
  version?: string;
  generated_at?: string | null;
  created_at: string | null;
  updated_at?: string | null;
  error_message?: string | null;
}

export interface ReportListResponse {
  items: ReportItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}


export interface ExtractedClaimItem {
  id: string;
  db_id?: number;
  text: string;
  normalized_text: string;
  claim_type: string;
  verifiability: string;
  importance: string;
  entities: string[];
  dates: string[];
  locations: string[];
  numbers: string[];
  source_attributions: string[];
  original_sentence: string;
  extraction_method: string;
}

export interface DiscoveredSourceItem {
  id?: number;
  title: string;
  url: string;
  canonical_url: string;
  domain: string;
  snippet: string;
  published_at?: string | null;
  publisher?: string | null;
  author?: string | null;
  country?: string | null;
  source_type: string;
  source_role?: string;
  credibility_score?: number | null;
  credibility_rating?: string | null;
  query: string;
  retrieved_at: string;
  provider: string;
  syndication_source?: string | null;
}

export interface SearchQueryAuditItem {
  query_text: string;
  strategy_level: string;
  search_engine: string;
  results_count: number;
  status: string;
  error_message?: string | null;
}

export interface ClaimSearchResponse {
  status: string;
  claim_id?: number | null;
  claim_text?: string | null;
  queries_count: number;
  sources_count: number;
  queries: SearchQueryAuditItem[];
  sources: DiscoveredSourceItem[];
  provider: string;
  message: string;
}

export interface TextVerificationResponse {
  status: string;
  request_id: number;
  input_text: string;
  sentence_count: number;
  claims_count: number;
  claims: ExtractedClaimItem[];
  extraction_method: string;
  sources_count?: number;
  sources?: DiscoveredSourceItem[];
  queries?: SearchQueryAuditItem[];
  search_provider?: string | null;
  evidence_count?: number;
  evidence?: EvidenceItem[];
  comparisons_count?: number;
  source_comparisons?: SourceComparisonItem[];
  verdict?: RequestVerdictResult | null;
  claim_verdicts?: ClaimVerdictItem[];
  message: string;
}

export interface EvidenceItem {
  id?: number;
  claim_id: number;
  source_id?: number | null;
  evidence_text: string;
  snippet: string;
  evidence_type: "SUPPORTING" | "CONTRADICTING" | "CONTEXTUAL" | "INSUFFICIENT";
  stance?: string | null;
  quote?: string | null;
  direction: string;
  relevance: "HIGH" | "MEDIUM" | "LOW";
  relevance_score: number;
  confidence_in_extraction: number;
  stance_confidence: number;
  source_location?: string | null;
  extraction_method: string;
  extracted_at?: string | null;
  url: string;
  article_title?: string | null;
  publisher?: string | null;
  domain?: string | null;
  publish_date?: string | null;
  explanation?: string | null;
}

export interface SourceComparisonItem {
  id?: number;
  claim_id: number;
  source_a_id?: number | null;
  source_b_id?: number | null;
  source_a_title?: string | null;
  source_b_title?: string | null;
  source_a_domain?: string | null;
  source_b_domain?: string | null;
  comparison_type: string;
  source_relationship: "INDEPENDENT" | "POSSIBLY_SYNDICATED" | "DUPLICATE" | "UNKNOWN";
  evidence_consistency: "CONSISTENT_EVIDENCE" | "CONFLICTING_INFORMATION" | "COMPLEMENTARY" | "INSUFFICIENT";
  details?: string | null;
  supporting_sources_count: number;
  contradicting_sources_count: number;
  neutral_sources_count: number;
  consensus_verdict: string;
  analysis_summary?: string | null;
}

export interface ClaimEvidenceResponse {
  status: string;
  claim_id: number;
  claim_text: string;
  evidence_count: number;
  evidence: EvidenceItem[];
  comparisons_count: number;
  source_comparisons: SourceComparisonItem[];
  message: string;
}

export type VerdictType = 
  | "SUPPORTED"
  | "CONTRADICTED"
  | "MISLEADING"
  | "UNVERIFIED"
  | "INSUFFICIENT_EVIDENCE"
  | "MIXED";

export interface ClaimVerdictItem {
  id?: number;
  claim_id: number;
  claim_text: string;
  verdict: VerdictType;
  confidence: number;
  confidence_level: "HIGH" | "MODERATE" | "LOW";
  evidence_strength: "STRONG" | "MODERATE" | "WEAK" | "INSUFFICIENT";
  explanation: string;
  supporting_evidence_ids: number[];
  contradicting_evidence_ids: number[];
  contextual_evidence_ids: number[];
  limitations: string[];
  methodology_version: string;
  generated_at?: string | null;
}

export interface RequestVerdictResult {
  id?: number;
  request_id: number;
  overall_verdict: VerdictType;
  overall_confidence: number;
  summary: string;
  claims: ClaimVerdictItem[];
  claims_count: number;
  supported_count: number;
  contradicted_count: number;
  misleading_count: number;
  unverified_count: number;
  insufficient_count: number;
  limitations: string[];
  methodology_notes?: string | null;
  generated_at?: string | null;
}

export interface ArticleItem {
  id?: number;
  request_id?: number;
  original_url: string;
  canonical_url?: string | null;
  domain: string;
  title?: string | null;
  publisher?: string | null;
  author?: string | null;
  published_at?: string | null;
  description?: string | null;
  language?: string | null;
  featured_image_url?: string | null;
  article_text: string;
  content_hash: string;
  content_length: number;
  word_count: number;
  extraction_method: string;
  retrieval_status: string;
  retrieved_at?: string | null;
}

export interface UrlVerificationRequest {
  url: string;
  perform_search?: boolean;
  extract_evidence?: boolean;
  finalize_verdicts?: boolean;
}

export interface UrlVerificationResponse {
  status: string;
  request_id: number;
  article: ArticleItem;
  claims_count: number;
  claims: ExtractedClaimItem[];
  sources_count: number;
  sources: DiscoveredSourceItem[];
  submitted_source?: DiscoveredSourceItem | null;
  independent_sources: DiscoveredSourceItem[];
  queries: SearchQueryAuditItem[];
  search_provider?: string | null;
  evidence_count: number;
  evidence: EvidenceItem[];
  comparisons_count: number;
  source_comparisons: SourceComparisonItem[];
  verdict?: RequestVerdictResult | null;
  claim_verdicts: ClaimVerdictItem[];
  message: string;
}

export interface OCRBlockItem {
  text: string;
  confidence: number;
  bbox: [number, number, number, number];
  block_num?: number;
  par_num?: number;
  line_num?: number;
  word_num?: number;
}

export interface ImageForensicDetails {
  image_width: number;
  image_height: number;
  image_format: string;
  file_size_bytes: number;
  file_hash_sha256: string;
  original_filename: string;
  sanitized_exif: Record<string, any>;
  ocr_engine: string;
  preprocessing_applied: Record<string, any>;
}

export interface ImageOCRSummary {
  raw_text: string;
  normalized_text: string;
  ocr_confidence: number;
  word_count: number;
  low_confidence_warning: boolean;
  detected_urls: string[];
  detected_handles: string[];
  detected_metrics: Record<string, string>;
  detected_dates: string[];
  blocks: OCRBlockItem[];
}

export interface ImageVerificationResponse {
  request_id: number;
  media_file_id?: number | null;
  image_verification_id?: number | null;
  status: string;
  forensics: ImageForensicDetails;
  ocr: ImageOCRSummary;
  claims: ExtractedClaimItem[];
  sources: DiscoveredSourceItem[];
  evidence: EvidenceItem[];
  comparisons: SourceComparisonItem[];
  verdicts?: RequestVerdictResult | null;
  claims_count: number;
  sources_count: number;
  evidence_count: number;
  authenticity_disclaimer: string;
}

export interface TranscriptSegmentItem {
  id?: number | null;
  sequence: number;
  start_time: number;
  end_time: number;
  formatted_timestamp: string;
  text: string;
  confidence?: number | null;
}

export interface MediaForensicDetails {
  media_type: "audio" | "video";
  duration_seconds: number;
  file_size_bytes: number;
  file_hash_sha256: string;
  original_filename: string;
  stored_filename: string;
  mime_type: string;
  width?: number | null;
  height?: number | null;
  video_codec?: string | null;
  audio_codec?: string | null;
  sample_rate?: number | null;
  channels?: number | null;
  bitrate?: number | null;
  has_audio_track: boolean;
  technical_indicators: Record<string, any>;
}

export interface TranscriptionSummary {
  raw_transcript: string;
  normalized_transcript: string;
  language: string;
  is_code_switched: boolean;
  transcription_confidence: number;
  confidence_category: string;
  low_confidence_warning: boolean;
  word_count: number;
  duration_seconds: number;
  segments: TranscriptSegmentItem[];
  detected_urls: string[];
  detected_quotes: Array<{ speaker: string; quote: string; raw_match: string }>;
}

export interface VideoFrameItem {
  id?: number | null;
  frame_number: number;
  timestamp: number;
  formatted_timestamp: string;
  selection_method: string;
  image_hash: string;
  stored_path?: string | null;
  width: number;
  height: number;
  ocr_text?: string | null;
  ocr_confidence?: number | null;
  ocr_blocks?: OCRBlockItem[];
  visual_context?: {
    contains_document_or_screenshot?: boolean;
    contains_ticker_or_headline?: boolean;
    contains_chart_or_table?: boolean;
    detected_logos_or_badges?: string[];
    observations?: string[];
  };
}

export interface ClaimOccurrenceItem {
  id?: number | null;
  claim_id?: number | null;
  source_type: "AUDIO_TRANSCRIPT" | "VISUAL_OCR" | string;
  timestamp_start: number;
  timestamp_end: number;
  formatted_timestamp?: string | null;
  frame_id?: number | null;
  frame_number?: number | null;
  transcript_segment_id?: number | null;
  text: string;
  confidence?: number | null;
}

export interface TimelineEventItem {
  timestamp: number;
  timestamp_end?: number | null;
  formatted_timestamp: string;
  event_type: "AUDIO_SPEECH" | "KEYFRAME_SCENE" | "VISUAL_TEXT" | "VERIFIABLE_CLAIM" | string;
  label: string;
  description: string;
  confidence?: number | null;
  frame_id?: number | null;
  claim_id?: number | null;
  badge_color?: string;
}

export interface AudioVisualAlignmentReport {
  summary_status: string;
  summary_note: string;
  alignments_count: number;
  mismatches_count: number;
  alignments: Array<{
    audio_phrase: string;
    visual_text: string;
    timestamp: number;
    formatted_timestamp: string;
    similarity: number;
  }>;
  mismatches: Array<{
    audio_topic: string;
    visual_topic: string;
    timestamp: number;
    formatted_timestamp: string;
    note: string;
  }>;
  disclaimer: string;
}

export interface ReusedFootageReport {
  reused_footage_detected: boolean;
  matching_frames_count: number;
  matched_prior_requests: Array<{
    prior_request_id: number;
    frame_number: number;
    matched_timestamp: number;
  }>;
  source_origin_note: string;
  reverse_image_search_status: string;
  disclaimer: string;
}

export interface MediaExtractedClaimItem extends ExtractedClaimItem {
  start_time?: number | null;
  end_time?: number | null;
  formatted_timestamp?: string | null;
  segment_sequence?: number | null;
  primary_origin?: string;
  occurrences?: ClaimOccurrenceItem[];
}

export interface MediaVerificationResponse {
  request_id: number;
  media_file_id?: number | null;
  media_verification_id?: number | null;
  status: string;
  forensics: MediaForensicDetails;
  transcription: TranscriptionSummary;
  frames?: VideoFrameItem[];
  timeline?: TimelineEventItem[];
  alignment?: AudioVisualAlignmentReport | null;
  reused_footage?: ReusedFootageReport | null;
  forensic_observations?: Record<string, any> | null;
  frames_count?: number;
  claims: MediaExtractedClaimItem[];
  queries?: SearchQueryAuditItem[];
  sources: DiscoveredSourceItem[];
  evidence: EvidenceItem[];
  comparisons: SourceComparisonItem[];
  verdicts?: RequestVerdictResult | null;
  claims_count: number;
  sources_count: number;
  evidence_count: number;
  authenticity_disclaimer: string;
}

export interface VerificationEventItem {
  id?: number;
  request_id: number;
  stage_name: string;
  event_type: string;
  status: string;
  details?: Record<string, any>;
  created_at: string;
}

export interface HistoryItem {
  id: number;
  request_type: string;
  content_preview: string;
  status: string;
  created_at: string;
  completed_at?: string | null;
  content_hash?: string | null;
  parent_request_id?: number | null;
  is_archived: boolean;
  claims_count: number;
  verdict?: VerdictType | string | null;
  confidence?: number | null;
  confidence_percentage?: number | null;
  error_message?: string | null;
}

export interface HistoryListResponse {
  items: HistoryItem[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface HistoryFiltersResponse {
  request_types: string[];
  statuses: string[];
  verdicts: string[];
  sort_options: string[];
}

export interface DuplicateCheckResponse {
  has_duplicate: boolean;
  match_type?: string | null;
  matched_request?: HistoryItem | null;
  matches_count: number;
  message: string;
}

export interface ReverifyResponse {
  status: string;
  message: string;
  original_request_id: number;
  new_request_id: number;
  new_status: string;
  verdict?: string | null;
  confidence?: number | null;
}

export interface HistoryDetailResponse {
  id: number;
  request_type: string;
  status: string;
  content?: string | null;
  content_hash?: string | null;
  media_file_id?: number | null;
  parent_request_id?: number | null;
  is_archived: boolean;
  created_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  verdict?: VerdictType | string | null;
  confidence?: number | null;
  confidence_percentage?: number | null;
  summary?: string | null;
  limitations: string[];
  methodology_notes?: string | null;
  supported_count: number;
  contradicted_count: number;
  misleading_count: number;
  unverified_count: number;
  insufficient_count: number;
  claims: any[];
  sources: DiscoveredSourceItem[];
  evidence: EvidenceItem[];
  comparisons: SourceComparisonItem[];
  queries: SearchQueryAuditItem[];
  events: VerificationEventItem[];
  article?: ArticleItem | null;
  image_verification?: Record<string, any> | null;
  media_verification?: Record<string, any> | null;
}

export interface AnalyticsActivityItem {
  id: number;
  request_type: string;
  status: string;
  verdict?: string | null;
  confidence?: number | null;
  confidence_percentage?: number | null;
  created_at?: string | null;
  claims_count: number;
}

export interface AnalyticsOverviewResponse {
  total_requests: number;
  completed_count: number;
  failed_count: number;
  processing_count: number;
  partial_count: number;
  completion_rate: number;
  total_claims: number;
  average_confidence: number | null;
  average_confidence_percentage: number | null;
  total_sources: number;
  total_evidence_items: number;
  reports_generated: number;
  reports_failed: number;
  time_range: string;
  from_date?: string | null;
  to_date?: string | null;
  recent_activity: AnalyticsActivityItem[];
}

export interface TimelinePoint {
  date: string;
  total: number;
  completed: number;
  failed: number;
  text: number;
  url: number;
  image: number;
  audio: number;
  video: number;
  avg_confidence: number | null;
}

export interface AnalyticsTimelineResponse {
  interval: string;
  total_requests: number;
  data_points: TimelinePoint[];
  from_date?: string | null;
  to_date?: string | null;
}

export interface TypeBreakdownItem {
  type: string;
  count: number;
  percentage: number;
  completed_count: number;
  avg_confidence: number | null;
}

export interface AnalyticsVerificationTypesResponse {
  total_requests: number;
  breakdown: TypeBreakdownItem[];
  from_date?: string | null;
  to_date?: string | null;
}

export interface VerdictCountItem {
  verdict: string;
  count: number;
  percentage: number;
}

export interface AnalyticsVerdictDistributionResponse {
  total_evaluated_requests: number;
  pending_evaluation_requests: number;
  request_verdicts: VerdictCountItem[];
  total_evaluated_claims: number;
  claim_verdicts: VerdictCountItem[];
  methodological_note: string;
  from_date?: string | null;
  to_date?: string | null;
}

export interface DomainCoverageItem {
  domain: string;
  sources_count: number;
  publisher?: string | null;
  source_type?: string | null;
}

export interface AnalyticsSourceCoverageResponse {
  unique_sources_count: number;
  unique_domains_count: number;
  total_evidence_passages: number;
  avg_sources_per_claim: number;
  avg_evidence_per_claim: number;
  primary_source_count: number;
  primary_source_percentage: number;
  top_domains: DomainCoverageItem[];
  evidence_direction_distribution: Record<string, number>;
  source_independence: Record<string, number>;
  evidence_consistency: Record<string, number>;
  notes: string;
  from_date?: string | null;
  to_date?: string | null;
}


