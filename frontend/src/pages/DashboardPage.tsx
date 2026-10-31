import { useEffect, useState } from 'react';
import {
  Archive,
  Users,
  Mic,
  Image,
  FileText,
  Film,
  ShieldCheck,
  Plus,
  ArrowRight,
  Clock,
  Sparkles,
  BookOpen,
  Activity,
  ChevronRight
} from 'lucide-react';
import type { SystemStatus, Memory, AIStatus } from '../types';
import { api } from '../services/api';

interface DashboardPageProps {
  onNavigate: (tab: string) => void;
  onOpenUpload: () => void;
  onSelectMemory: (memory: Memory) => void;
}

export const DashboardPage = ({
  onNavigate,
  onOpenUpload,
  onSelectMemory,
}: DashboardPageProps) => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [recentMemories, setRecentMemories] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setIsLoading(true);
    try {
      const [sys, ai, memoriesRes] = await Promise.all([
        api.getSystemStatus(),
        api.getAIStatus(),
        api.getMemories({ page: 1, size: 6 }),
      ]);
      setSystemStatus(sys);
      setAiStatus(ai);
      setRecentMemories(memoriesRes.items || []);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
    } finally {
      setIsLoading(false);
    }
  };

  const stats = systemStatus?.statistics;
  const storage = systemStatus?.storage;

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Hero Showcase with Ambient Glow & Quick Actions */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-b from-[#111624] via-[#0c1018] to-[#080b12] border border-white/[0.08] p-6 sm:p-10 shadow-2xl">
        {/* Subtle radial ambient lights */}
        <div className="absolute -top-24 right-10 w-96 h-96 bg-[#d4af37]/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-10 w-80 h-80 bg-blue-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-8">
          <div className="max-w-2xl space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#d4af37]/10 border border-[#d4af37]/30 text-xs font-medium text-[#f3d87b]">
              <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
              <span>Offline-First AI Heritage Preservation</span>
            </div>

            <h1 className="text-3xl sm:text-5xl font-serif font-bold text-white tracking-tight leading-tight">
              Preserve What Truly <span className="gold-gradient-text">Matters.</span>
            </h1>

            <p className="text-sm sm:text-base text-[#93a3bd] font-light leading-relaxed">
              Every heirloom photograph, oral history recording, and personal letter is safeguarded locally
              with AES-256 encryption. Discover stories through private, on-device AI.
            </p>

            <div className="pt-2 flex flex-wrap items-center gap-3">
              <button
                onClick={onOpenUpload}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold bg-gradient-to-r from-[#d4af37] via-[#e2ba3d] to-[#e68a00] text-black shadow-lg shadow-[#d4af37]/20 hover:brightness-110 active:scale-95 transition-all"
              >
                <Plus className="w-4 h-4 stroke-[2.4]" />
                Preserve New Memory
              </button>

              <button
                onClick={() => onNavigate('ask-memories')}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-medium text-white bg-[#151c2a] hover:bg-[#1c2638] border border-[#2b374d] hover:border-[#d4af37]/40 transition-all"
              >
                <Sparkles className="w-4 h-4 text-[#f3d87b]" />
                Ask Memories RAG
              </button>

              <button
                onClick={() => onNavigate('vault')}
                className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-medium text-[#8c9cb3] hover:text-white transition-colors"
              >
                <span>Browse Vault</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Quick System Telemetry Widget */}
          <div className="shrink-0 w-full lg:w-80 p-5 rounded-2xl bg-[#080b12]/90 border border-white/[0.08] backdrop-blur-xl shadow-xl space-y-3.5">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <span className="text-[11px] font-mono uppercase tracking-wider text-[#798ba4] flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-[#d4af37]" />
                System Health
              </span>
              <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Operational
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[#8494ab]">Local Storage</span>
                <span className="text-white font-mono font-medium">
                  {isLoading ? '...' : storage?.formatted_size ?? '0 B'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#8494ab]">Vault Cipher</span>
                <span className="text-[#f3d87b] font-mono font-medium">AES-256-GCM</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#8494ab]">Local Neural Engine</span>
                <span className={`font-medium ${aiStatus?.ollama_running ? 'text-emerald-400' : 'text-amber-400'}`}>
                  {aiStatus?.ollama_running ? 'Qwen2.5 (Ready)' : 'Standby'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#8494ab]">Speech Transcription</span>
                <span className="text-white font-medium">Whisper Base</span>
              </div>
            </div>

            <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-[11px]">
              <span className="text-[#62738a]">Total Artifacts</span>
              <span className="text-white font-bold font-serif text-sm">
                {isLoading ? '...' : stats?.total_memories ?? 0}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Bento Grid: Statistics & Feature Gateways */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Bento 1: Memories & Media Breakdown */}
        <div
          onClick={() => onNavigate('vault')}
          className="card-modern rounded-2xl p-5 cursor-pointer group flex flex-col justify-between space-y-4"
        >
          <div className="flex items-start justify-between">
            <div className="p-2.5 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
              <Archive className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#687890] group-hover:text-[#d4af37] transition-colors">
              Vault →
            </span>
          </div>

          <div>
            <div className="text-3xl font-serif font-bold text-white group-hover:text-[#f3d87b] transition-colors">
              {isLoading ? '...' : stats?.total_memories ?? 0}
            </div>
            <p className="text-xs text-[#8292aa] mt-0.5">Preserved Artifacts</p>
          </div>

          <div className="grid grid-cols-4 gap-1.5 pt-3 border-t border-white/[0.06] text-center">
            <div className="p-1.5 rounded-lg bg-[#0a0e16]">
              <Image className="w-3.5 h-3.5 mx-auto text-sky-400 mb-0.5" />
              <span className="text-[10px] font-mono text-white block">{stats?.photographs ?? 0}</span>
            </div>
            <div className="p-1.5 rounded-lg bg-[#0a0e16]">
              <Mic className="w-3.5 h-3.5 mx-auto text-emerald-400 mb-0.5" />
              <span className="text-[10px] font-mono text-white block">{stats?.audio_recordings ?? 0}</span>
            </div>
            <div className="p-1.5 rounded-lg bg-[#0a0e16]">
              <FileText className="w-3.5 h-3.5 mx-auto text-violet-400 mb-0.5" />
              <span className="text-[10px] font-mono text-white block">{stats?.documents ?? 0}</span>
            </div>
            <div className="p-1.5 rounded-lg bg-[#0a0e16]">
              <Film className="w-3.5 h-3.5 mx-auto text-amber-400 mb-0.5" />
              <span className="text-[10px] font-mono text-white block">{stats?.videos ?? 0}</span>
            </div>
          </div>
        </div>

        {/* Bento 2: People & Relationships */}
        <div
          onClick={() => onNavigate('people')}
          className="card-modern rounded-2xl p-5 cursor-pointer group flex flex-col justify-between space-y-4"
        >
          <div className="flex items-start justify-between">
            <div className="p-2.5 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400">
              <Users className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#687890] group-hover:text-amber-400 transition-colors">
              People →
            </span>
          </div>

          <div>
            <div className="text-3xl font-serif font-bold text-white group-hover:text-amber-300 transition-colors">
              {isLoading ? '...' : stats?.total_people ?? 0}
            </div>
            <p className="text-xs text-[#8292aa] mt-0.5">Family & Friends Tracked</p>
          </div>

          <p className="text-[11px] text-[#7888a0] leading-relaxed pt-3 border-t border-white/[0.06]">
            Every person has linked memories, transcripts, biographical narratives, and milestones.
          </p>
        </div>

        {/* Bento 3: AI Storytelling Studio */}
        <div
          onClick={() => onNavigate('ai-studio')}
          className="card-modern rounded-2xl p-5 cursor-pointer group flex flex-col justify-between space-y-4"
        >
          <div className="flex items-start justify-between">
            <div className="p-2.5 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
              <BookOpen className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#687890] group-hover:text-[#d4af37] transition-colors">
              AI Studio →
            </span>
          </div>

          <div>
            <div className="text-base font-serif font-bold text-white group-hover:text-[#f3d87b] transition-colors">
              Heritage Studio
            </div>
            <p className="text-xs text-[#8292aa] mt-0.5">Biographies & Timelines</p>
          </div>

          <div className="flex flex-wrap gap-1.5 pt-3 border-t border-white/[0.06]">
            <span className="px-2 py-0.5 rounded-md bg-[#0a0e16] text-[10px] text-[#a0b0c8]">Life Timelines</span>
            <span className="px-2 py-0.5 rounded-md bg-[#0a0e16] text-[10px] text-[#a0b0c8]">Biographies</span>
            <span className="px-2 py-0.5 rounded-md bg-[#0a0e16] text-[10px] text-[#a0b0c8]">Remembrance</span>
          </div>
        </div>

        {/* Bento 4: Data Sovereignty & Security */}
        <div
          onClick={() => onNavigate('settings')}
          className="card-modern rounded-2xl p-5 cursor-pointer group flex flex-col justify-between space-y-4"
        >
          <div className="flex items-start justify-between">
            <div className="p-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-[#687890] group-hover:text-emerald-400 transition-colors">
              Security →
            </span>
          </div>

          <div>
            <div className="text-base font-serif font-bold text-white group-hover:text-emerald-300 transition-colors">
              Zero Telemetry
            </div>
            <p className="text-xs text-[#8292aa] mt-0.5">100% Offline Loopback</p>
          </div>

          <p className="text-[11px] text-[#7888a0] leading-relaxed pt-3 border-t border-white/[0.06]">
            Encrypted with Argon2id & AES-256-GCM. No external cloud or trackers touch your records.
          </p>
        </div>
      </div>

      {/* Recent Memories Section with Modern Visual Cards */}
      <div className="space-y-4">
        <div className="flex items-center justify-between pb-2 border-b border-white/[0.06]">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#d4af37]" />
            <h2 className="text-lg font-serif font-bold text-white">Recently Preserved Memories</h2>
          </div>
          <button
            onClick={() => onNavigate('vault')}
            className="text-xs font-medium text-[#d4af37] hover:text-[#f3d87b] transition-colors flex items-center gap-1"
          >
            <span>View all in vault ({stats?.total_memories ?? 0})</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {recentMemories.length === 0 ? (
          <div className="p-10 rounded-2xl card-modern-static text-center space-y-3">
            <Archive className="w-10 h-10 mx-auto text-[#62738a]" />
            <h3 className="text-sm font-semibold text-white">Vault is awaiting your first memory</h3>
            <p className="text-xs text-[#8596ae] max-w-sm mx-auto">
              Preserve your family heritage by uploading historical photographs, recorded voice memories, or letters.
            </p>
            <button
              onClick={onOpenUpload}
              className="mt-2 px-4 py-2 rounded-xl text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b] transition-colors"
            >
              Add First Memory
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {recentMemories.map((m) => {
              const fileUrl = api.getMemoryFileUrl(m.id);
              const previewUrl = m.has_thumbnail ? api.getMemoryThumbnailUrl(m.id) : fileUrl;
              const isImage = m.memory_type === 'photograph' || m.mime_type.startsWith('image/');

              return (
                <div
                  key={m.id}
                  onClick={() => onSelectMemory(m)}
                  className="card-modern rounded-2xl overflow-hidden cursor-pointer group flex flex-col justify-between"
                >
                  <div className="h-44 bg-[#080b12] relative overflow-hidden flex items-center justify-center">
                    {isImage ? (
                      <img
                        src={previewUrl}
                        alt={m.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        loading="lazy"
                      />
                    ) : (
                      <div className="flex flex-col items-center justify-center text-[#7e8fa6]">
                        {m.memory_type === 'audio' ? (
                          <Mic className="w-10 h-10 text-[#d4af37]/80" />
                        ) : m.memory_type === 'video' ? (
                          <Film className="w-10 h-10 text-emerald-400/80" />
                        ) : (
                          <FileText className="w-10 h-10 text-violet-400/80" />
                        )}
                        <span className="text-[10px] font-mono uppercase tracking-wider mt-2">
                          {m.memory_type}
                        </span>
                      </div>
                    )}
                    <span className="absolute top-3 right-3 px-2 py-0.5 rounded-md text-[9px] font-mono font-semibold uppercase tracking-wider bg-black/80 backdrop-blur-md text-[#f3d87b] border border-[#d4af37]/35 shadow-sm">
                      {m.memory_type}
                    </span>
                  </div>

                  <div className="p-4 space-y-2">
                    <h3 className="text-sm font-semibold text-white group-hover:text-[#f3d87b] transition-colors truncate">
                      {m.title}
                    </h3>
                    <p className="text-xs text-[#8494ab] line-clamp-2 font-light">
                      {m.description || 'No narrative recorded yet.'}
                    </p>
                    <div className="pt-2.5 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-[#63748c]">
                      <span>{m.event_date ? new Date(m.event_date).toLocaleDateString() : 'Undated'}</span>
                      <span className="font-mono">{(m.file_size / 1024 / 1024).toFixed(1)} MB</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
