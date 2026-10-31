import { useEffect, useState } from 'react';
import {
  Archive,
  Users,
  Mic,
  Image,
  FileText,
  Film,
  HardDrive,
  Cpu,
  ShieldCheck,
  Plus,
  ArrowRight,
  Clock,
  Sparkles
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
      setRecentMemories(memoriesRes.items);
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
      {/* Hero Header with Brand Vision */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-[#121622] via-[#0d1017] to-[#171c26] border border-[#d4af37]/25 p-8 sm:p-10 shadow-2xl">
        <div className="absolute top-0 right-0 w-96 h-96 bg-[#d4af37]/5 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#d4af37]/15 border border-[#d4af37]/30 text-xs font-semibold text-[#f3d87b] mb-4">
            <Sparkles className="w-3.5 h-3.5 text-[#d4af37]" />
            Your memories. Your machine. Your legacy.
          </div>
          <h1 className="text-3xl sm:text-4xl font-serif font-bold text-white tracking-wide leading-tight">
            Preserve Your Heritage With Open-Weight Local AI
          </h1>
          <p className="mt-3 text-sm sm:text-base text-[#9db0cc] font-light leading-relaxed">
            Every photograph, recorded voice, and personal story is preserved strictly inside
            your machine. No external clouds. No subscriptions. 100% private.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={onOpenUpload}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-[#d4af37] to-[#e68a00] text-black shadow-lg shadow-[#d4af37]/25 hover:brightness-110 active:scale-98 transition-all"
            >
              <Plus className="w-4 h-4 stroke-[2.5]" />
              Preserve New Memory
            </button>
            <button
              onClick={() => onNavigate('vault')}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-[#dce2ec] bg-[#161c28] hover:bg-[#1d2535] border border-[#273347] transition-all"
            >
              Explore Vault
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Actual Database Statistics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {/* Total Memories */}
        <div className="p-5 rounded-2xl bg-[#0f131c] border border-[#202738] hover:border-[#d4af37]/40 transition-colors">
          <div className="flex items-center justify-between text-[#8e9bb0] mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Memories</span>
            <Archive className="w-4 h-4 text-[#d4af37]" />
          </div>
          <div className="text-2xl sm:text-3xl font-serif font-bold text-white">
            {isLoading ? '...' : stats?.total_memories ?? 0}
          </div>
          <p className="text-[11px] text-[#6d7c92] mt-1">Preserved items</p>
        </div>

        {/* People */}
        <div className="p-5 rounded-2xl bg-[#0f131c] border border-[#202738] hover:border-[#d4af37]/40 transition-colors">
          <div className="flex items-center justify-between text-[#8e9bb0] mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">People</span>
            <Users className="w-4 h-4 text-[#ff9e1b]" />
          </div>
          <div className="text-2xl sm:text-3xl font-serif font-bold text-white">
            {isLoading ? '...' : stats?.total_people ?? 0}
          </div>
          <p className="text-[11px] text-[#6d7c92] mt-1">Family & friends</p>
        </div>

        {/* Audio Recordings */}
        <div className="p-5 rounded-2xl bg-[#0f131c] border border-[#202738] hover:border-[#d4af37]/40 transition-colors">
          <div className="flex items-center justify-between text-[#8e9bb0] mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Voice</span>
            <Mic className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-serif font-bold text-white">
            {isLoading ? '...' : stats?.audio_recordings ?? 0}
          </div>
          <p className="text-[11px] text-[#6d7c92] mt-1">Oral histories</p>
        </div>

        {/* Photographs */}
        <div className="p-5 rounded-2xl bg-[#0f131c] border border-[#202738] hover:border-[#d4af37]/40 transition-colors">
          <div className="flex items-center justify-between text-[#8e9bb0] mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Photos</span>
            <Image className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-serif font-bold text-white">
            {isLoading ? '...' : stats?.photographs ?? 0}
          </div>
          <p className="text-[11px] text-[#6d7c92] mt-1">Historical images</p>
        </div>

        {/* Documents */}
        <div className="p-5 rounded-2xl bg-[#0f131c] border border-[#202738] hover:border-[#d4af37]/40 transition-colors">
          <div className="flex items-center justify-between text-[#8e9bb0] mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Docs</span>
            <FileText className="w-4 h-4 text-violet-400" />
          </div>
          <div className="text-2xl sm:text-3xl font-serif font-bold text-white">
            {isLoading ? '...' : stats?.documents ?? 0}
          </div>
          <p className="text-[11px] text-[#6d7c92] mt-1">Letters & records</p>
        </div>

        {/* Local Storage */}
        <div className="p-5 rounded-2xl bg-[#0f131c] border border-[#202738] hover:border-[#d4af37]/40 transition-colors">
          <div className="flex items-center justify-between text-[#8e9bb0] mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Storage</span>
            <HardDrive className="w-4 h-4 text-amber-300" />
          </div>
          <div className="text-2xl sm:text-3xl font-serif font-bold text-white">
            {isLoading ? '...' : storage?.formatted_size ?? '0 B'}
          </div>
          <p className="text-[11px] text-[#6d7c92] mt-1">Disk space used</p>
        </div>
      </div>

      {/* Subsystem & Status Banners */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Local AI Engine Status */}
        <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
                  <Cpu className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">Local Ollama Engine</h3>
                  <p className="text-xs text-[#8e9bb0]">Private neural inference</p>
                </div>
              </div>
              <span
                className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
                  aiStatus?.ollama_running
                    ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40'
                    : 'bg-amber-950/50 text-amber-300 border border-amber-500/40'
                }`}
              >
                {aiStatus?.ollama_running ? 'Online & Running' : 'Offline / Standby'}
              </span>
            </div>
            <p className="text-xs text-[#9db0cc] leading-relaxed">
              Target Model:{' '}
              <span className="font-mono text-[#f3d87b]">{aiStatus?.configured_model || 'qwen2.5:3b'}</span>
              <br />
              {aiStatus?.message || 'Checking local inference daemon...'}
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-[#1a202c] flex items-center justify-between">
            <span className="text-[11px] text-[#6d7c92]">Endpoint: {aiStatus?.base_url || 'http://127.0.0.1:11434'}</span>
            <button
              onClick={() => onNavigate('ai-studio')}
              className="text-xs font-medium text-[#d4af37] hover:underline"
            >
              Configure AI Studio →
            </button>
          </div>
        </div>

        {/* Privacy & Sovereignty Assurance */}
        <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-white">Data Sovereignty</h3>
                  <p className="text-xs text-[#8e9bb0]">Zero External Telemetry</p>
                </div>
              </div>
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-500/40">
                Active
              </span>
            </div>
            <p className="text-xs text-[#9db0cc] leading-relaxed">
              All personal stories and files reside purely on your hard disk. The database binds
              strictly to local loopback (127.0.0.1). No analytics, trackers, or third-party APIs.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-[#1a202c] flex items-center justify-between">
            <span className="text-[11px] text-[#6d7c92]">
              Vault Path: <span className="font-mono">{storage?.storage_directory ? '.../data/memories' : 'data/memories'}</span>
            </span>
            <button
              onClick={() => onNavigate('settings')}
              className="text-xs font-medium text-[#d4af37] hover:underline"
            >
              Review Architecture →
            </button>
          </div>
        </div>
      </div>

      {/* Recent Memories Section */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#d4af37]" />
            <h2 className="text-lg font-serif font-bold text-white">Recently Preserved</h2>
          </div>
          <button
            onClick={() => onNavigate('vault')}
            className="text-xs font-medium text-[#d4af37] hover:underline flex items-center gap-1"
          >
            View all ({stats?.total_memories ?? 0})
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {recentMemories.length === 0 ? (
          <div className="p-8 rounded-2xl bg-[#0d1017] border border-dashed border-[#232b3c] text-center">
            <Archive className="w-10 h-10 mx-auto text-[#6d7c92] mb-3" />
            <h3 className="text-sm font-semibold text-white">Vault is empty</h3>
            <p className="text-xs text-[#8e9bb0] max-w-sm mx-auto mt-1 mb-4">
              Begin preserving your family legacy by uploading your first photograph, voice recording, or personal letter.
            </p>
            <button
              onClick={onOpenUpload}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b] transition-colors"
            >
              Add First Memory
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {recentMemories.map((m) => {
              const fileUrl = api.getMemoryFileUrl(m.id);
              const previewUrl = m.has_thumbnail ? api.getMemoryThumbnailUrl(m.id) : fileUrl;
              const isImage = m.memory_type === 'photograph' || m.mime_type.startsWith('image/');
              return (
                <div
                  key={m.id}
                  onClick={() => onSelectMemory(m)}
                  className="group cursor-pointer rounded-2xl bg-[#0f131c] border border-[#202738] hover:border-[#d4af37]/50 overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-xl hover:shadow-black"
                >
                  <div className="h-40 bg-[#080a0e] relative overflow-hidden flex items-center justify-center">
                    {isImage ? (
                      <img
                        src={previewUrl}
                        alt={m.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        loading="lazy"
                      />
                    ) : (
                      <div className="flex flex-col items-center justify-center text-[#8e9bb0]">
                        {m.memory_type === 'audio' ? (
                          <Mic className="w-10 h-10 text-[#d4af37]/70" />
                        ) : m.memory_type === 'video' ? (
                          <Film className="w-10 h-10 text-emerald-400/70" />
                        ) : (
                          <FileText className="w-10 h-10 text-violet-400/70" />
                        )}
                        <span className="text-[11px] uppercase tracking-wider mt-2 font-medium">
                          {m.memory_type}
                        </span>
                      </div>
                    )}
                    <span className="absolute top-2.5 right-2.5 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider bg-black/75 backdrop-blur-sm text-[#f3d87b] border border-[#d4af37]/30">
                      {m.memory_type}
                    </span>
                  </div>
                  <div className="p-4">
                    <h3 className="text-sm font-semibold text-white group-hover:text-[#f3d87b] transition-colors truncate">
                      {m.title}
                    </h3>
                    <p className="text-xs text-[#8e9bb0] line-clamp-2 mt-1 font-light">
                      {m.description || 'No narrative recorded yet.'}
                    </p>
                    <div className="mt-3 pt-2.5 border-t border-[#1a202c] flex items-center justify-between text-[11px] text-[#6d7c92]">
                      <span>{m.event_date ? new Date(m.event_date).toLocaleDateString() : 'Undated'}</span>
                      <span>{(m.file_size / 1024 / 1024).toFixed(1)} MB</span>
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
