export interface PersonSimple {
  id: string;
  full_name: string;
  relationship?: string;
}

export interface Person {
  id: string;
  full_name: string;
  relationship?: string;
  biography?: string;
  created_at: string;
  memories_count?: number;
}

export interface Tag {
  id: string;
  name: string;
  created_at?: string;
  memories_count?: number;
}

export interface TagCreate {
  name: string;
}

export interface TagUpdate {
  name: string;
}

export interface TranscriptSegment {
  id: string;
  transcript_id: string;
  start_time: number;
  end_time: number;
  text: string;
  speaker_label: string;
  speaker_id?: string | null;
  confidence?: number | null;
  segment_order: number;
}

export interface TranscriptSegmentUpdate {
  id?: string;
  text?: string;
  speaker_label?: string;
  speaker_id?: string | null;
  start_time?: number;
  end_time?: number;
}

export interface TranscriptUpdate {
  transcript_text?: string;
  language?: string;
  segments?: TranscriptSegmentUpdate[];
}

export interface Transcript {
  id: string;
  memory_id: string;
  language: string;
  detected_language?: string | null;
  model_name?: string | null;
  processing_duration?: number | null;
  transcript_text: string;
  processing_status: string;
  created_at: string;
  updated_at?: string | null;
  segments: TranscriptSegment[];
}

export interface TranscriptionJob {
  id: string;
  memory_id: string;
  status: 'queued' | 'preprocessing' | 'transcribing' | 'diarizing' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_stage: string;
  error_message?: string | null;
  model_name: string;
  language: string;
  enable_diarization: boolean;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface TranscriptionJobCreate {
  model_name?: string;
  language?: string;
  enable_diarization?: boolean;
}

export interface WhisperModelInfo {
  name: string;
  description: string;
  disk_size_mb: number;
  actual_size_mb: number;
  is_installed: boolean;
  is_downloading: boolean;
  download_progress: number;
  recommended: boolean;
  local_path?: string | null;
}

export interface TranscriptionEngineStatus {
  device: string;
  compute_type: string;
  cpu_threads: number;
  queue_concurrency: number;
  ffmpeg_available: boolean;
  pyav_available: boolean;
  models_installed_count: number;
  models_directory: string;
  active_jobs_count: number;
}

export interface SpeakerConsent {
  id: string;
  person_id: string;
  consent_given: boolean;
  consent_notes?: string | null;
  consent_date: string;
  revoked_at?: string | null;
}

export interface SpeakerProfile {
  id: string;
  person_id: string;
  sample_count: number;
  created_at: string;
  updated_at: string;
}

export interface Memory {
  id: string;
  title: string;
  description?: string;
  memory_type: 'photograph' | 'audio' | 'document' | 'story' | 'video';
  original_filename: string;
  stored_filename: string;
  mime_type: string;
  file_size: number;
  sha256_hash?: string;
  file_hash?: string;
  width?: number | null;
  height?: number | null;
  duration_seconds?: number | null;
  extracted_text?: string | null;
  thumbnail_path?: string | null;
  has_thumbnail?: boolean;
  location?: string | null;
  original_created_at?: string | null;
  processing_status: string;
  processing_error?: string | null;
  created_at: string;
  updated_at: string;
  event_date?: string | null;
  privacy_level: string;
  people: PersonSimple[];
  tags: Tag[];
  transcripts: Transcript[];
}

export interface MemoryUpdate {
  title?: string;
  description?: string | null;
  location?: string | null;
  privacy_level?: string;
  event_date?: string | null;
  person_ids?: string[];
  tags?: string[];
}

export interface MemoryListResponse {
  items: Memory[];
  total: number;
  page: number;
  size: number;
  total_pages: number;
}

export interface MemoryQueryParams {
  page?: number;
  size?: number;
  search?: string;
  memory_type?: string;
  person_id?: string;
  tag?: string;
  date_from?: string;
  date_to?: string;
  sort_by?: 'created_at_desc' | 'created_at_asc' | 'event_date_desc' | 'event_date_asc' | 'title_asc' | 'size_desc';
}

export interface AIStatus {
  status: 'online' | 'offline';
  ollama_running: boolean;
  configured_model: string;
  model_available: boolean;
  base_url: string;
  installed_models: string[];
  message: string;
  setup_instructions?: string;
}

export interface ModelInfo {
  name: string;
  model: string;
  size?: number;
  modified_at?: string;
  is_configured: boolean;
}

export interface AIModelsResponse {
  models: ModelInfo[];
  count: number;
  configured_model: string;
}

export interface StorageStatus {
  storage_directory: string;
  total_files: number;
  total_bytes: number;
  formatted_size: string;
}

export interface MemoryStats {
  total_memories: number;
  photographs: number;
  audio_recordings: number;
  documents: number;
  stories: number;
  videos: number;
  total_people: number;
}

export interface SystemStatus {
  application_name: string;
  version: string;
  environment: string;
  privacy_mode: string;
  database_connected: boolean;
  ai_status: string;
  storage: StorageStatus;
  statistics: MemoryStats;
}

// Phase 4: Semantic Search & RAG Types
export interface CitationItem {
  index: number;
  memory_id: string;
  title: string;
  source_type: string;
  memory_type: string;
  original_filename: string;
  excerpt: string;
  start_time?: number | null;
  end_time?: number | null;
  speaker_label?: string | null;
  event_date?: string | null;
  similarity: number;
}

export interface AskMemoriesResponse {
  answer: string;
  evidence_status: 'grounded' | 'insufficient_evidence' | 'offline_ai' | 'no_sources' | 'uninstalled_model';
  citations: CitationItem[];
  query: string;
  retrieval_mode: 'hybrid' | 'semantic';
  sources_retrieved_count: number;
  model_name: string;
  processing_time_seconds: number;
  semantic_available?: boolean;
  fallback_mode?: 'real_semantic' | 'keyword_only';
  warning?: string | null;
}

export interface AskMemoriesRequest {
  query: string;
  retrieval_mode?: 'hybrid' | 'semantic';
  top_k?: number;
  date_from?: string;
  date_to?: string;
  person_id?: string;
  memory_type?: string;
  tags?: string[];
  transcript_language?: string;
}

export interface SearchResultItem {
  chunk_id: string;
  memory_id: string;
  memory_title: string;
  memory_type: string;
  memory_date?: string | null;
  source_type: string;
  original_filename: string;
  text: string;
  similarity: number;
  start_time?: number | null;
  end_time?: number | null;
  speaker_label?: string | null;
  tags: string[];
  person_ids: string[];
}

export interface SearchResponse {
  query: string;
  mode: string;
  total_results: number;
  results: SearchResultItem[];
  semantic_available?: boolean;
  fallback_mode?: 'real_semantic' | 'keyword_only';
  warning?: string | null;
}

export interface IndexStatus {
  total_memories: number;
  indexed_memories: number;
  failed_jobs: number;
  pending_jobs: number;
  semantic_available?: boolean;
  keyword_available?: boolean;
  vector_store_available?: boolean;
  embedding_model_name?: string;
  embedding_model_loaded?: boolean;
  fallback_mode?: 'real_semantic' | 'keyword_only';
  vector_store: {
    status: string;
    healthy: boolean;
    vector_count: number;
    persist_directory: string;
    collection_name: string;
    error?: string;
  };
  embedding_model: {
    name: string;
    installed: boolean;
    available: boolean;
    size_mb?: number;
    path?: string;
    description?: string;
  };
  is_synchronized: boolean;
}

export interface EmbeddingModelInfo {
  name: string;
  repo_id: string;
  dimension: number;
  max_sequence_length: number;
  description: string;
  installed: boolean;
  available: boolean;
  path?: string | null;
  size_mb: number;
  is_default: boolean;
}

// Phase 5: Storytelling, Biographies, Timelines, Collections, and Remembrance Pages
export interface SourceMemoryInfo {
  memory_id: string;
  title: string;
  memory_type: string;
  original_filename: string;
  event_date?: string | null;
  location?: string | null;
  excerpt?: string | null;
  evidence_classification: 'documented_fact' | 'generated_narrative' | 'unverified_detail' | 'unknown';
}

export interface BiographySection {
  section_id: string;
  section_title: string;
  narrative: string;
  evidence_classification: 'documented_fact' | 'generated_narrative' | 'unverified_detail' | 'unknown';
  source_memory_ids: string[];
  is_unknown: boolean;
}

export interface StoryArtifact {
  id: string;
  person_id: string;
  person_name?: string | null;
  artifact_type: 'biography' | 'story' | 'timeline' | 'remembrance_page';
  title: string;
  content: string;
  sections_json?: string | null;
  sections: BiographySection[];
  language: string;
  tone: string;
  model_name?: string | null;
  generation_status: 'completed' | 'failed' | 'draft';
  approval_status: 'pending' | 'approved' | 'rejected';
  evidence_coverage: number;
  warning?: string | null;
  source_memories: SourceMemoryInfo[];
  created_at: string;
  updated_at: string;
}

export interface StoryArtifactUpdate {
  title?: string;
  content?: string;
  approval_status?: 'pending' | 'approved' | 'rejected';
  sections_json?: string;
}

export interface BiographyGenerateRequest {
  person_id: string;
  source_memory_ids?: string[];
  length?: 'short' | 'medium' | 'detailed';
  tone?: 'respectful' | 'warm' | 'factual' | 'reflective';
  language?: 'en' | 'hi' | 'source_preserved';
  sections_to_include?: string[];
}

export interface StoryGenerateRequest {
  person_id: string;
  source_memory_ids: string[];
  title?: string;
  tone?: 'respectful' | 'warm' | 'factual' | 'reflective';
  language?: 'en' | 'hi' | 'source_preserved';
}

export interface TimelineEvent {
  id: string;
  person_id: string;
  artifact_id?: string | null;
  title: string;
  event_date?: string | null;
  approximate_date?: string | null;
  date_confidence: 'exact' | 'approximate' | 'unknown';
  description: string;
  verification_status: 'ai_suggested' | 'user_confirmed';
  order_index: number;
  source_memory_ids: string[];
  source_memories: SourceMemoryInfo[];
  created_at: string;
  updated_at: string;
}

export interface TimelineEventCreate {
  person_id: string;
  artifact_id?: string | null;
  title: string;
  event_date?: string | null;
  approximate_date?: string | null;
  date_confidence?: 'exact' | 'approximate' | 'unknown';
  description: string;
  verification_status?: 'ai_suggested' | 'user_confirmed';
  source_memory_ids?: string[];
  order_index?: number;
}

export interface TimelineEventUpdate {
  title?: string;
  event_date?: string | null;
  approximate_date?: string | null;
  date_confidence?: 'exact' | 'approximate' | 'unknown';
  description?: string;
  verification_status?: 'ai_suggested' | 'user_confirmed';
  source_memory_ids?: string[];
  order_index?: number;
}

export interface RemembrancePage {
  id: string;
  person_id: string;
  person_name: string;
  person_relationship?: string | null;
  biography_artifact_id?: string | null;
  biography?: StoryArtifact | null;
  featured_photograph_id?: string | null;
  featured_photograph?: {
    id: string;
    title: string;
    thumbnail_path?: string | null;
    file_path: string;
    original_filename: string;
    event_date?: string | null;
  } | null;
  user_personal_notes?: string | null;
  privacy_level: string;
  stories: StoryArtifact[];
  timeline_events: TimelineEvent[];
  created_at: string;
  updated_at: string;
}

export interface RemembrancePageUpdate {
  biography_artifact_id?: string | null;
  featured_photograph_id?: string | null;
  user_personal_notes?: string | null;
}

export interface MemoryCollection {
  id: string;
  title: string;
  description?: string | null;
  collection_type: 'childhood' | 'family' | 'education' | 'career' | 'celebrations' | 'travel' | 'milestones' | 'custom';
  person_id?: string | null;
  cover_memory_id?: string | null;
  memories_count: number;
  memories: Array<{
    id: string;
    title: string;
    memory_type: string;
    original_filename: string;
    thumbnail_path?: string | null;
    event_date?: string | null;
    order_index: number;
    added_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface CollectionCreate {
  title: string;
  description?: string;
  collection_type?: 'childhood' | 'family' | 'education' | 'career' | 'celebrations' | 'travel' | 'milestones' | 'custom';
  person_id?: string;
  cover_memory_id?: string;
  memory_ids?: string[];
}

export interface CollectionUpdate {
  title?: string;
  description?: string;
  collection_type?: string;
  person_id?: string;
  cover_memory_id?: string;
}

// ==========================================
// Phase 6: Encryption, Vault & Data Protection
// ==========================================

export interface VaultStatus {
  is_initialized: boolean;
  is_unlocked: boolean;
  algorithm: string;
  kdf: string;
  auto_lock_minutes: number;
  total_files: number;
  encrypted_files: number;
  plaintext_files: number;
  is_fully_encrypted: boolean;
}

export interface VaultSetupRequest {
  password: string;
  auto_lock_minutes?: number;
}

export interface VaultSetupResponse {
  status: string;
  recovery_key: string;
  message: string;
}

export interface VaultUnlockRequest {
  password?: string;
  recovery_key?: string;
}

export interface VaultPasswordChangeRequest {
  current_password: string;
  new_password: string;
}

export interface VaultRecoverRequest {
  recovery_key: string;
  new_password: string;
}

export interface MigrationStatus {
  is_running: boolean;
  total_files: number;
  processed_files: number;
  successful_files: number;
  failed_files: number;
  progress_percent: number;
  errors: string[];
  cancelled: boolean;
  completed_at?: string | null;
  backup_path?: string | null;
}


