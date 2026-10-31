import type {
  Memory,
  MemoryListResponse,
  MemoryQueryParams,
  MemoryUpdate,
  Tag,
  Person,
  AIStatus,
  AIModelsResponse,
  SystemStatus,
  Transcript,
  TranscriptUpdate,
  TranscriptionJob,
  TranscriptionJobCreate,
  WhisperModelInfo,
  TranscriptionEngineStatus,
  SpeakerConsent,
  SpeakerProfile,
  AskMemoriesRequest,
  AskMemoriesResponse,
  SearchResponse,
  IndexStatus,
  EmbeddingModelInfo,
  StoryArtifact,
  StoryArtifactUpdate,
  BiographyGenerateRequest,
  StoryGenerateRequest,
  TimelineEvent,
  TimelineEventCreate,
  TimelineEventUpdate,
  RemembrancePage,
  RemembrancePageUpdate,
  MemoryCollection,
  CollectionCreate,
  CollectionUpdate,
  VaultStatus,
  VaultSetupRequest,
  VaultSetupResponse,
  VaultUnlockRequest,
  VaultPasswordChangeRequest,
  VaultRecoverRequest,
  MigrationStatus,
} from '../types';

const API_BASE = '/api';

export class ApiError extends Error {
  status: number;
  detail?: any;

  constructor(status: number, message: string, detail?: any) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail: any = null;
    try {
      errorDetail = await res.json();
    } catch {
      errorDetail = await res.text();
    }
    const message =
      typeof errorDetail?.detail === 'string'
        ? errorDetail.detail
        : errorDetail?.detail?.message || res.statusText || 'API request failed';
    throw new ApiError(res.status, message, errorDetail);
  }
  return res.json();
}

export const api = {
  // System & Health
  async getHealth(): Promise<{ status: string; app: string; version: string }> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse(res);
  },

  async getSystemStatus(): Promise<SystemStatus> {
    const res = await fetch(`${API_BASE}/system/status`);
    return handleResponse(res);
  },

  // Memories
  async getMemories(params: MemoryQueryParams = {}): Promise<MemoryListResponse> {
    const query = new URLSearchParams();
    if (params.page !== undefined) query.set('page', params.page.toString());
    if (params.size !== undefined) query.set('size', params.size.toString());
    if (params.search && params.search.trim()) query.set('search', params.search.trim());
    if (params.memory_type && params.memory_type !== 'all') query.set('memory_type', params.memory_type);
    if (params.person_id && params.person_id.trim()) query.set('person_id', params.person_id.trim());
    if (params.tag && params.tag.trim()) query.set('tag', params.tag.trim());
    if (params.date_from) query.set('date_from', params.date_from);
    if (params.date_to) query.set('date_to', params.date_to);
    if (params.sort_by) query.set('sort_by', params.sort_by);

    const res = await fetch(`${API_BASE}/memories?${query.toString()}`);
    return handleResponse(res);
  },

  async searchMemories(q: string, limit: number = 20): Promise<Memory[]> {
    const query = new URLSearchParams({ q, limit: limit.toString() });
    const res = await fetch(`${API_BASE}/memories/search?${query.toString()}`);
    return handleResponse(res);
  },

  async getMemory(id: string): Promise<Memory> {
    const res = await fetch(`${API_BASE}/memories/${id}`);
    return handleResponse(res);
  },

  async uploadMemory(formData: FormData): Promise<Memory> {
    const res = await fetch(`${API_BASE}/memories`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(res);
  },

  async updateMemory(id: string, data: MemoryUpdate): Promise<Memory> {
    const res = await fetch(`${API_BASE}/memories/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async deleteMemory(id: string): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/memories/${id}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  getMemoryFileUrl(id: string): string {
    return `${API_BASE}/memories/${id}/file`;
  },

  getMemoryThumbnailUrl(id: string): string {
    return `${API_BASE}/memories/${id}/thumbnail`;
  },

  // Tags
  async getTags(): Promise<Tag[]> {
    const res = await fetch(`${API_BASE}/tags`);
    return handleResponse(res);
  },

  async createTag(name: string): Promise<Tag> {
    const res = await fetch(`${API_BASE}/tags`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    return handleResponse(res);
  },

  async updateTag(id: string, name: string): Promise<Tag> {
    const res = await fetch(`${API_BASE}/tags/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    return handleResponse(res);
  },

  async deleteTag(id: string): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/tags/${id}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  // People
  async getPeople(): Promise<Person[]> {
    const res = await fetch(`${API_BASE}/people`);
    return handleResponse(res);
  },

  async createPerson(data: {
    full_name: string;
    relationship?: string;
    biography?: string;
  }): Promise<Person> {
    const res = await fetch(`${API_BASE}/people`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async getPersonMemories(personId: string): Promise<Memory[]> {
    const res = await fetch(`${API_BASE}/people/${personId}/memories`);
    return handleResponse(res);
  },

  // Phase 3: Speaker Consent & Voice Profiles
  async getSpeakerConsent(personId: string): Promise<SpeakerConsent | null> {
    const res = await fetch(`${API_BASE}/people/${personId}/consent`);
    return handleResponse(res);
  },

  async recordSpeakerConsent(
    personId: string,
    consentGiven: boolean,
    consentNotes?: string
  ): Promise<SpeakerConsent> {
    const res = await fetch(`${API_BASE}/people/${personId}/consent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        consent_given: consentGiven,
        consent_notes: consentNotes,
      }),
    });
    return handleResponse(res);
  },

  async getSpeakerProfile(personId: string): Promise<SpeakerProfile | null> {
    const res = await fetch(`${API_BASE}/people/${personId}/speaker-profile`);
    return handleResponse(res);
  },

  async enrollSpeakerProfile(
    personId: string,
    memoryId: string,
    startTime?: number,
    endTime?: number
  ): Promise<SpeakerProfile> {
    const res = await fetch(`${API_BASE}/people/${personId}/speaker-profile/enroll`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        memory_id: memoryId,
        start_time: startTime,
        end_time: endTime,
      }),
    });
    return handleResponse(res);
  },

  async deleteSpeakerProfile(personId: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/people/${personId}/speaker-profile`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  // Phase 3: Transcription Jobs & Speech Engine
  async startTranscription(
    memoryId: string,
    params: TranscriptionJobCreate = {}
  ): Promise<TranscriptionJob> {
    const res = await fetch(`${API_BASE}/memories/${memoryId}/transcription`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model_name: params.model_name || 'base',
        language: params.language || 'auto',
        enable_diarization: params.enable_diarization ?? true,
      }),
    });
    return handleResponse(res);
  },

  async getTranscriptionJobs(memoryId?: string): Promise<TranscriptionJob[]> {
    const query = new URLSearchParams();
    if (memoryId) query.set('memory_id', memoryId);
    const res = await fetch(`${API_BASE}/transcription/jobs?${query.toString()}`);
    return handleResponse(res);
  },

  async getTranscriptionJob(jobId: string): Promise<TranscriptionJob> {
    const res = await fetch(`${API_BASE}/transcription/jobs/${jobId}`);
    return handleResponse(res);
  },

  async cancelTranscriptionJob(jobId: string): Promise<TranscriptionJob> {
    const res = await fetch(`${API_BASE}/transcription/jobs/${jobId}/cancel`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async getTranscript(memoryId: string): Promise<Transcript> {
    const res = await fetch(`${API_BASE}/memories/${memoryId}/transcript`);
    return handleResponse(res);
  },

  async updateTranscript(transcriptId: string, data: TranscriptUpdate): Promise<Transcript> {
    const res = await fetch(`${API_BASE}/transcripts/${transcriptId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async deleteTranscript(transcriptId: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/transcripts/${transcriptId}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  async getWhisperModels(): Promise<WhisperModelInfo[]> {
    const res = await fetch(`${API_BASE}/transcription/models`);
    return handleResponse(res);
  },

  async downloadWhisperModel(
    modelName: string,
    force: boolean = false
  ): Promise<{ status: string; message: string; model_name: string }> {
    const res = await fetch(`${API_BASE}/transcription/models/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName, force }),
    });
    return handleResponse(res);
  },

  async deleteWhisperModel(modelName: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/transcription/models/${modelName}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  async getTranscriptionStatus(): Promise<TranscriptionEngineStatus> {
    const res = await fetch(`${API_BASE}/transcription/status`);
    return handleResponse(res);
  },

  // AI Studio
  async getAIStatus(): Promise<AIStatus> {
    const res = await fetch(`${API_BASE}/ai/status`);
    return handleResponse(res);
  },

  async getAIModels(): Promise<AIModelsResponse> {
    const res = await fetch(`${API_BASE}/ai/models`);
    return handleResponse(res);
  },

  // Phase 4: Semantic Search & RAG
  async askMemories(req: AskMemoriesRequest): Promise<AskMemoriesResponse> {
    const res = await fetch(`${API_BASE}/memories/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },

  async searchSemantic(req: AskMemoriesRequest): Promise<SearchResponse> {
    const res = await fetch(`${API_BASE}/search/semantic`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },

  async searchHybrid(req: AskMemoriesRequest): Promise<SearchResponse> {
    const res = await fetch(`${API_BASE}/search/hybrid`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },

  async getIndexStatus(): Promise<IndexStatus> {
    const res = await fetch(`${API_BASE}/search/index/status`);
    return handleResponse(res);
  },

  async rebuildIndex(): Promise<{
    status: string;
    total_memories: number;
    indexed_memories: number;
    total_chunks: number;
    errors: any[];
  }> {
    const res = await fetch(`${API_BASE}/search/index/rebuild`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async retryFailedIndexing(): Promise<{
    retried_count: number;
    succeeded_count: number;
    failed_count: number;
    errors: any[];
  }> {
    const res = await fetch(`${API_BASE}/search/index/retry`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async getEmbeddingModels(): Promise<EmbeddingModelInfo[]> {
    const res = await fetch(`${API_BASE}/search/models`);
    return handleResponse(res);
  },

  async downloadEmbeddingModel(modelName: string): Promise<{
    status: string;
    model_name: string;
    message: string;
  }> {
    const res = await fetch(`${API_BASE}/search/models/download`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName }),
    });
    return handleResponse(res);
  },

  // ---------------------------------------------------------------------------
  // Phase 5: Storytelling, Biographies, Timelines, Collections & Remembrance
  // ---------------------------------------------------------------------------

  async generateBiography(req: BiographyGenerateRequest): Promise<StoryArtifact> {
    const res = await fetch(`${API_BASE}/storytelling/biographies/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },

  async generateStory(req: StoryGenerateRequest): Promise<StoryArtifact> {
    const res = await fetch(`${API_BASE}/storytelling/stories/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },

  async generateTimeline(personId: string, sourceMemoryIds?: string[]): Promise<TimelineEvent[]> {
    const res = await fetch(`${API_BASE}/storytelling/timelines/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ person_id: personId, source_memory_ids: sourceMemoryIds }),
    });
    return handleResponse(res);
  },

  async getPersonTimeline(personId: string): Promise<TimelineEvent[]> {
    const res = await fetch(`${API_BASE}/storytelling/timelines/person/${personId}`);
    return handleResponse(res);
  },

  async createTimelineEvent(data: TimelineEventCreate): Promise<TimelineEvent> {
    const res = await fetch(`${API_BASE}/storytelling/timelines/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async updateTimelineEvent(id: string, data: TimelineEventUpdate): Promise<TimelineEvent> {
    const res = await fetch(`${API_BASE}/storytelling/timelines/events/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async deleteTimelineEvent(id: string): Promise<{ message: string; id: string }> {
    const res = await fetch(`${API_BASE}/storytelling/timelines/events/${id}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  async getArtifact(id: string): Promise<StoryArtifact> {
    const res = await fetch(`${API_BASE}/storytelling/artifacts/${id}`);
    return handleResponse(res);
  },

  async updateArtifact(id: string, data: StoryArtifactUpdate): Promise<StoryArtifact> {
    const res = await fetch(`${API_BASE}/storytelling/artifacts/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async deleteArtifact(id: string): Promise<{ message: string; id: string }> {
    const res = await fetch(`${API_BASE}/storytelling/artifacts/${id}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  async getPersonArtifacts(personId: string): Promise<StoryArtifact[]> {
    const res = await fetch(`${API_BASE}/storytelling/artifacts/person/${personId}`);
    return handleResponse(res);
  },

  async getRemembrancePage(personId: string): Promise<RemembrancePage> {
    const res = await fetch(`${API_BASE}/storytelling/remembrance/${personId}`);
    return handleResponse(res);
  },

  async updateRemembrancePage(personId: string, data: RemembrancePageUpdate): Promise<RemembrancePage> {
    const res = await fetch(`${API_BASE}/storytelling/remembrance/${personId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async getCollections(personId?: string): Promise<MemoryCollection[]> {
    const query = personId ? `?person_id=${encodeURIComponent(personId)}` : '';
    const res = await fetch(`${API_BASE}/storytelling/collections${query}`);
    return handleResponse(res);
  },

  async getCollection(id: string): Promise<MemoryCollection> {
    const res = await fetch(`${API_BASE}/storytelling/collections/${id}`);
    return handleResponse(res);
  },

  async createCollection(data: CollectionCreate): Promise<MemoryCollection> {
    const res = await fetch(`${API_BASE}/storytelling/collections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async updateCollection(id: string, data: CollectionUpdate): Promise<MemoryCollection> {
    const res = await fetch(`${API_BASE}/storytelling/collections/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse(res);
  },

  async deleteCollection(id: string): Promise<{ message: string; id: string }> {
    const res = await fetch(`${API_BASE}/storytelling/collections/${id}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  async addCollectionItem(collectionId: string, memoryId: string, orderIndex: number = 0): Promise<MemoryCollection> {
    const res = await fetch(`${API_BASE}/storytelling/collections/${collectionId}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ memory_id: memoryId, order_index: orderIndex }),
    });
    return handleResponse(res);
  },

  async removeCollectionItem(collectionId: string, memoryId: string): Promise<MemoryCollection> {
    const res = await fetch(`${API_BASE}/storytelling/collections/${collectionId}/items/${memoryId}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  // ==========================================
  // Phase 6: Security, Vault & Migration API
  // ==========================================

  async getVaultStatus(): Promise<VaultStatus> {
    const res = await fetch(`${API_BASE}/security/vault/status`);
    return handleResponse(res);
  },

  async setupVault(req: VaultSetupRequest): Promise<VaultSetupResponse> {
    const res = await fetch(`${API_BASE}/security/vault/setup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },

  async unlockVault(req: VaultUnlockRequest): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/security/vault/unlock`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },

  async lockVault(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/security/vault/lock`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async changeVaultPassword(req: VaultPasswordChangeRequest): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/security/vault/change-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },

  async recoverVault(req: VaultRecoverRequest): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/security/vault/recover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse(res);
  },

  async startMigration(): Promise<{ status: string; message: string; total_files: number }> {
    const res = await fetch(`${API_BASE}/security/migration/start`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async getMigrationStatus(): Promise<MigrationStatus> {
    const res = await fetch(`${API_BASE}/security/migration/status`);
    return handleResponse(res);
  },

  async cancelMigration(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/security/migration/cancel`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async rollbackMigration(): Promise<{ status: string; message: string; restored_files: number }> {
    const res = await fetch(`${API_BASE}/security/migration/rollback`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  async createBackup(): Promise<{ status: string; backup_file: string; size_bytes: number; message: string }> {
    const res = await fetch(`${API_BASE}/security/backup/create`, {
      method: 'POST',
    });
    return handleResponse(res);
  },
};
