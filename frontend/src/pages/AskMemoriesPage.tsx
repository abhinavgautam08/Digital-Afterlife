import { useState, useEffect } from 'react';
import {
  Sparkles,
  BookOpen,
  Filter,
  Calendar,
  Clock,
  Play,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
  Cpu,
  Database,
  History,
  RotateCcw,
  Languages,
  ChevronDown,
  ChevronUp,
  FileText,
  Music,
  Camera,
  Film
} from 'lucide-react';
import type {
  Person,
  Memory,
  CitationItem,
  AskMemoriesResponse,
  IndexStatus,
  AIStatus
} from '../types';
import { api } from '../services/api';

interface AskMemoriesPageProps {
  people: Person[];
  onSelectMemory: (memory: Memory, initialSeekTime?: number | null) => void;
  aiStatus: AIStatus | null;
}

export const AskMemoriesPage = ({
  people,
  onSelectMemory,
  aiStatus,
}: AskMemoriesPageProps) => {
  const [query, setQuery] = useState('');
  const [retrievalMode, setRetrievalMode] = useState<'hybrid' | 'semantic'>('hybrid');
  const [topK, setTopK] = useState(5);
  const [selectedPersonId, setSelectedPersonId] = useState('');
  const [selectedMemoryType, setSelectedMemoryType] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<AskMemoriesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Index and Vector Store Status
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null);

  // Local History
  const [history, setHistory] = useState<string[]>(() => {
    try {
      const saved = localStorage.getItem('digital_afterlife_rag_history');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    loadIndexStatus();
  }, []);

  const loadIndexStatus = async () => {
    try {
      const status = await api.getIndexStatus();
      setIndexStatus(status);
    } catch (err) {
      console.error('Failed to load vector store status', err);
    }
  };

  const handleAsk = async (queryToAsk?: string) => {
    const q = (queryToAsk || query).trim();
    if (!q) return;

    setIsLoading(true);
    setError(null);
    setResult(null);

    // Save to local history
    setHistory((prev) => {
      const filtered = prev.filter((item) => item.toLowerCase() !== q.toLowerCase());
      const updated = [q, ...filtered].slice(0, 8);
      try {
        localStorage.setItem('digital_afterlife_rag_history', JSON.stringify(updated));
      } catch {}
      return updated;
    });

    try {
      const response = await api.askMemories({
        query: q,
        retrieval_mode: retrievalMode,
        top_k: topK,
        person_id: selectedPersonId || undefined,
        memory_type: selectedMemoryType || undefined,
        date_from: dateFrom ? `${dateFrom}T00:00:00` : undefined,
        date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
      });
      setResult(response);
    } catch (err: any) {
      setError(err.message || 'Failed to query memories.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCitationClick = async (citation: CitationItem) => {
    try {
      const memory = await api.getMemory(citation.memory_id);
      onSelectMemory(memory, citation.start_time);
    } catch (err) {
      console.error('Failed to load memory from citation', err);
    }
  };

  const clearHistory = () => {
    setHistory([]);
    try {
      localStorage.removeItem('digital_afterlife_rag_history');
    } catch {}
  };

  const exampleQuestions = [
    { label: 'Where did grandfather work in 1965?', query: 'Where did grandfather work in 1965?', lang: 'en' },
    { label: 'Summarize the 1960 wedding invitation', query: 'Summarize the 1960 wedding invitation and guest details', lang: 'en' },
    { label: 'What was said about the childhood home?', query: 'What was said in oral history interviews about the childhood home?', lang: 'en' },
    { label: 'दादाजी के पुराने पत्र का सारांश दें', query: 'दादाजी के पुराने पत्र का सारांश दें और मुख्य बातें बताएं', lang: 'hi' },
    { label: 'परिवार के आम के बगीचे की क्या यादें हैं?', query: 'परिवार के आम के बगीचे की क्या यादें और बातें दर्ज हैं?', lang: 'hi' },
  ];

  const getSourceIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'photograph':
        return <Camera className="w-4 h-4 text-emerald-400" />;
      case 'audio':
      case 'transcript':
        return <Music className="w-4 h-4 text-[#d4af37]" />;
      case 'video':
        return <Film className="w-4 h-4 text-purple-400" />;
      default:
        return <FileText className="w-4 h-4 text-blue-400" />;
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#202738] pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 rounded-lg bg-[#d4af37]/10 text-[#d4af37] border border-[#d4af37]/30">
              <Sparkles className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-serif font-bold text-white tracking-wide">
              Ask Your Memories
            </h1>
          </div>
          <p className="text-sm text-[#8e9bb0]">
            Local Semantic Search & Retrieval-Augmented Generation • Strict Non-Fabrication Guaranteed
          </p>
        </div>

        {/* System Health Indicators */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Capability Mode Pill */}
          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs ${
              indexStatus?.semantic_available
                ? 'bg-emerald-950/30 text-emerald-300 border-emerald-500/30'
                : 'bg-amber-950/30 text-amber-300 border-amber-600/30'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>
              {indexStatus?.semantic_available
                ? 'Semantic Embeddings: Ready'
                : 'Mode: Keyword-Only Fallback'}
            </span>
          </div>

          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs ${
              indexStatus?.vector_store.healthy
                ? 'bg-emerald-950/30 text-emerald-300 border-emerald-500/30'
                : 'bg-amber-950/30 text-amber-300 border-amber-600/30'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>{indexStatus?.vector_store.vector_count || 0} Chunks Indexed</span>
          </div>

          <div
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs ${
              aiStatus?.ollama_running
                ? 'bg-emerald-950/30 text-emerald-300 border-emerald-500/30'
                : 'bg-amber-950/30 text-amber-300 border-amber-600/30'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>{aiStatus?.ollama_running ? 'Qwen 2.5 3B Ready' : 'Ollama Offline'}</span>
          </div>
        </div>
      </div>

      {/* Main Search Input Card */}
      <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#232b3c] shadow-2xl space-y-4">
        <div className="relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleAsk();
              }
            }}
            placeholder="Ask anything about family letters, voice recordings, oral histories, or photos... (Supports English & हिंदी)"
            rows={3}
            className="w-full px-4 py-3 rounded-xl bg-[#07090c] border border-[#232b3c] text-white placeholder-[#505f77] text-base focus:outline-none focus:border-[#d4af37] focus:ring-1 focus:ring-[#d4af37]/30 transition-all resize-none"
          />

          <div className="absolute right-3 bottom-3 flex items-center gap-2">
            <button
              onClick={() => handleAsk()}
              disabled={isLoading || !query.trim()}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm bg-gradient-to-r from-[#d4af37] to-[#aa8214] text-black hover:from-[#f3d87b] hover:to-[#d4af37] disabled:opacity-40 transition-all shadow-lg shadow-[#d4af37]/15"
            >
              <Sparkles className="w-4 h-4" />
              <span>{isLoading ? 'Searching...' : 'Ask Memories'}</span>
            </button>
          </div>
        </div>

        {/* Filter Bar Toggle & Search Mode */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-xs text-[#8e9bb0]">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-colors ${
                showFilters || selectedPersonId || selectedMemoryType || dateFrom
                  ? 'bg-[#181f2c] text-[#f3d87b] border-[#d4af37]/40'
                  : 'bg-[#121620] text-[#8e9bb0] border-[#222a3a] hover:text-white'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>Search Controls & Filters</span>
              {showFilters ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {/* Retrieval Mode Toggle */}
            <div className="flex items-center bg-[#07090c] rounded-lg p-0.5 border border-[#1b2230]">
              <button
                onClick={() => setRetrievalMode('hybrid')}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  retrievalMode === 'hybrid'
                    ? 'bg-[#1b2230] text-[#f3d87b] font-medium'
                    : 'text-[#627088] hover:text-white'
                }`}
                title="Combines semantic vector proximity with exact keyword matching"
              >
                Hybrid (RRF)
              </button>
              <button
                onClick={() => setRetrievalMode('semantic')}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  retrievalMode === 'semantic'
                    ? 'bg-[#1b2230] text-[#f3d87b] font-medium'
                    : 'text-[#627088] hover:text-white'
                }`}
                title="Pure multilingual vector cosine search"
              >
                Pure Semantic
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[#627088]">Top Evidence:</span>
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="bg-[#121620] border border-[#222a3a] rounded-md px-2 py-1 text-white text-xs focus:outline-none focus:border-[#d4af37]"
            >
              <option value={3}>3 Sources</option>
              <option value={5}>5 Sources (Default)</option>
              <option value={10}>10 Sources</option>
            </select>
          </div>
        </div>

        {/* Semantic Missing Notification Banner */}
        {retrievalMode === 'semantic' && !indexStatus?.semantic_available && (
          <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-600/40 text-xs text-amber-200 flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-amber-300">Semantic Vector Model Not Installed</p>
              <p className="text-[#c8b688] mt-0.5">
                The local vector embedding model (<code className="font-mono text-amber-200">multilingual-e5-small</code>) has not been downloaded to disk. Pure semantic queries will return zero results. Please visit Settings to download the weights, or switch to <strong>Hybrid</strong> mode to search using SQLite keywords.
              </p>
            </div>
          </div>
        )}

        {/* Collapsible Filter Drawer */}
        {showFilters && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 p-4 rounded-xl bg-[#080b11] border border-[#1e2738] animate-fadeIn text-xs">
            <div>
              <label className="block text-[#8e9bb0] mb-1">Family Member</label>
              <select
                value={selectedPersonId}
                onChange={(e) => setSelectedPersonId(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-[#111622] border border-[#222a3a] text-white focus:outline-none focus:border-[#d4af37]"
              >
                <option value="">All Family Members</option>
                {people.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.full_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[#8e9bb0] mb-1">Memory Type</label>
              <select
                value={selectedMemoryType}
                onChange={(e) => setSelectedMemoryType(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-[#111622] border border-[#222a3a] text-white focus:outline-none focus:border-[#d4af37]"
              >
                <option value="">All Media Types</option>
                <option value="photograph">Photograph</option>
                <option value="audio">Audio / Oral History</option>
                <option value="video">Personal Video</option>
                <option value="document">Historical Document</option>
                <option value="story">Written Story</option>
              </select>
            </div>

            <div>
              <label className="block text-[#8e9bb0] mb-1">Date From</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-[#111622] border border-[#222a3a] text-white focus:outline-none focus:border-[#d4af37]"
              />
            </div>

            <div>
              <label className="block text-[#8e9bb0] mb-1">Date To</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full px-2.5 py-1.5 rounded-lg bg-[#111622] border border-[#222a3a] text-white focus:outline-none focus:border-[#d4af37]"
              />
            </div>
          </div>
        )}

        {/* Example Queries */}
        <div className="pt-2 flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-[#627088] flex items-center gap-1">
            <Languages className="w-3 h-3 text-[#d4af37]" /> Example questions:
          </span>
          {exampleQuestions.map((ex, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(ex.query);
                handleAsk(ex.query);
              }}
              className="text-[11px] px-2.5 py-1 rounded-full bg-[#121620] hover:bg-[#1a202c] text-[#8e9bb0] hover:text-[#f3d87b] border border-[#1f2736] transition-colors"
            >
              {ex.label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="p-8 rounded-2xl bg-[#0f131c] border border-[#232b3c] shadow-xl text-center space-y-4 animate-pulse">
          <div className="w-12 h-12 rounded-full bg-[#d4af37]/20 border border-[#d4af37]/40 flex items-center justify-center mx-auto text-[#d4af37]">
            <Sparkles className="w-6 h-6 animate-spin" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Searching Local Semantic Vault</h3>
            <p className="text-xs text-[#8e9bb0] mt-1">
              Extracting relevant passages, comparing multilingual embeddings, and synthesizing grounded answer...
            </p>
          </div>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/40 text-red-200 text-sm flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Query Processing Failed</p>
            <p className="text-xs text-red-300 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Answer & Citations Result */}
      {result && (
        <div className="space-y-6 animate-fadeIn">
          {/* Answer Card */}
          <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#232b3c] shadow-2xl space-y-4">
            <div className="flex items-center justify-between gap-4 border-b border-[#1f2736] pb-3">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-[#d4af37]" />
                <h2 className="text-base font-semibold text-white">Archival Answer</h2>
              </div>

              {/* Status Badge */}
              <div className="flex items-center gap-2 flex-wrap">
                {result.evidence_status === 'grounded' && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-emerald-950/40 text-emerald-300 border border-emerald-500/30">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Grounded in Evidence
                  </span>
                )}
                {result.evidence_status === 'insufficient_evidence' && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-950/40 text-amber-300 border border-amber-500/30">
                    <AlertCircle className="w-3.5 h-3.5" />
                    Insufficient Evidence
                  </span>
                )}
                {result.evidence_status === 'uninstalled_model' && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-950/40 text-amber-300 border border-amber-500/30">
                    <AlertCircle className="w-3.5 h-3.5" />
                    Model Uninstalled
                  </span>
                )}
                {result.evidence_status === 'offline_ai' && (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-purple-950/40 text-purple-300 border border-purple-500/30">
                    <Cpu className="w-3.5 h-3.5" />
                    Offline AI Mode (Raw Evidence)
                  </span>
                )}
                {result.fallback_mode === 'keyword_only' && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#1a1e28] text-amber-300 border border-amber-500/30">
                    Keyword-Only Fallback
                  </span>
                )}
                <span className="text-[11px] text-[#627088]">
                  Completed in {result.processing_time_seconds}s
                </span>
              </div>
            </div>

            {/* Answer Text */}
            <div className="text-base leading-relaxed text-[#e5e9f0] whitespace-pre-line bg-[#090b10] p-5 rounded-xl border border-[#1b2230] font-sans">
              {result.answer}
            </div>

            {result.warning && (
              <p className="text-xs text-[#f3d87b]/80 bg-[#141822] p-2.5 rounded-lg border border-[#232b3c]">
                Note: {result.warning}
              </p>
            )}
          </div>

          {/* Evidence Citations Panel */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-white tracking-wide flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-[#d4af37]" />
                <span>Verified Source Citations ({result.citations.length})</span>
              </h3>
              <p className="text-xs text-[#627088]">
                Every fact above is tied to these original family artifacts
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {result.citations.map((cite) => (
                <div
                  key={cite.index}
                  className="p-4 rounded-xl bg-[#0d1118] border border-[#1e2738] hover:border-[#d4af37]/40 transition-all flex flex-col justify-between space-y-3 group"
                >
                  <div className="space-y-2">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="w-5 h-5 rounded-md bg-[#d4af37]/20 text-[#d4af37] border border-[#d4af37]/40 text-xs font-bold flex items-center justify-center">
                          {cite.index}
                        </span>
                        <div className="flex items-center gap-1.5">
                          {getSourceIcon(cite.source_type || cite.memory_type)}
                          <span className="text-sm font-semibold text-white truncate max-w-[200px]">
                            {cite.title}
                          </span>
                        </div>
                      </div>

                      {cite.similarity > 0 && (
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#161f2e] text-[#f3d87b] border border-[#d4af37]/30">
                          {Math.round(cite.similarity * 100)}% match
                        </span>
                      )}
                    </div>

                    {/* Excerpt */}
                    <div className="text-xs text-[#9eb0c6] leading-relaxed line-clamp-4 bg-[#07090c] p-2.5 rounded-lg border border-[#161c28] font-mono">
                      "{cite.excerpt}"
                    </div>

                    {/* Meta info & Timestamps */}
                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-[#6d7c92]">
                      {cite.start_time !== undefined && cite.start_time !== null && (
                        <span className="inline-flex items-center gap-1 text-[#f3d87b] bg-[#161f2e] px-2 py-0.5 rounded font-mono">
                          <Clock className="w-3 h-3" />
                          {Math.floor(cite.start_time / 60)}:
                          {(cite.start_time % 60).toFixed(0).padStart(2, '0')} -{' '}
                          {cite.end_time ? `${Math.floor(cite.end_time / 60)}:${(cite.end_time % 60).toFixed(0).padStart(2, '0')}` : ''}
                        </span>
                      )}
                      {cite.speaker_label && (
                        <span>Speaker: {cite.speaker_label}</span>
                      )}
                      {cite.event_date && (
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {cite.event_date.split('T')[0]}
                        </span>
                      )}
                      <span className="truncate max-w-[140px]">{cite.original_filename}</span>
                    </div>
                  </div>

                  {/* Open / Play Action */}
                  <div className="pt-2 border-t border-[#18202e] flex items-center justify-end">
                    <button
                      onClick={() => handleCitationClick(cite)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#141b27] text-[#f3d87b] hover:bg-[#202b3d] border border-[#d4af37]/30 transition-colors"
                    >
                      {cite.start_time !== undefined && cite.start_time !== null ? (
                        <>
                          <Play className="w-3 h-3 text-[#d4af37]" />
                          <span>Play from Timestamp</span>
                        </>
                      ) : (
                        <>
                          <ExternalLink className="w-3 h-3" />
                          <span>Open Original Memory</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Query History */}
      {history.length > 0 && (
        <div className="p-5 rounded-2xl bg-[#0f131c] border border-[#232b3c] space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-[#d4af37]" />
              <span>Recent Inquiries</span>
            </h3>
            <button
              onClick={clearHistory}
              className="text-[11px] text-[#627088] hover:text-white transition-colors"
            >
              Clear
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {history.map((item, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setQuery(item);
                  handleAsk(item);
                }}
                className="text-xs px-3 py-1 rounded-lg bg-[#07090c] hover:bg-[#151a24] text-[#8e9bb0] hover:text-[#f3d87b] border border-[#1b2230] transition-colors flex items-center gap-1.5"
              >
                <RotateCcw className="w-3 h-3 text-[#505f77]" />
                <span className="truncate max-w-[280px]">{item}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
