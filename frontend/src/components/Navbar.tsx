import React from 'react';
import {
  Compass,
  Archive,
  Users,
  Cpu,
  Settings as SettingsIcon,
  ShieldCheck,
  HardDrive,
  Sparkles,
  Lock,
  Unlock,
  ShieldAlert,
  Search,
  Plus
} from 'lucide-react';
import type { AIStatus, VaultStatus } from '../types';
import {
  TooltipProvider,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from './ui/tooltip';

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  aiStatus: AIStatus | null;
  vaultStatus?: VaultStatus | null;
  onOpenVaultModal?: () => void;
  onOpenCommandPalette?: () => void;
  onOpenUpload?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  setCurrentTab,
  aiStatus,
  vaultStatus,
  onOpenVaultModal,
  onOpenCommandPalette,
  onOpenUpload,
}) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Compass },
    { id: 'vault', label: 'Memory Vault', icon: Archive },
    { id: 'ask-memories', label: 'Ask Memories', icon: Sparkles },
    { id: 'people', label: 'People', icon: Users },
    { id: 'ai-studio', label: 'AI Studio', icon: Cpu },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-white/[0.07] bg-[#080b12]/85 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-3">
          {/* Logo & Brand */}
          <div
            className="flex items-center gap-3 cursor-pointer group shrink-0"
            onClick={() => setCurrentTab('dashboard')}
          >
            <div className="relative w-9 h-9 rounded-xl bg-gradient-to-br from-[#d4af37] via-[#aa8214] to-[#f3d87b] p-0.5 shadow-md shadow-[#d4af37]/20 group-hover:shadow-[#d4af37]/35 transition-all">
              <div className="w-full h-full bg-[#0a0d14] rounded-[10px] flex items-center justify-center">
                <HardDrive className="w-4 h-4 text-[#f3d87b] stroke-[2.2]" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif text-base font-bold tracking-wide text-white group-hover:text-[#f3d87b] transition-colors">
                  Digital Afterlife
                </span>
                <span className="px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-wider rounded-md bg-[#d4af37]/15 text-[#f3d87b] border border-[#d4af37]/30">
                  Vault
                </span>
              </div>
              <p className="text-[10px] text-[#6d7c92] -mt-0.5 hidden sm:block font-light">
                Private Heritage & Memory Preservation
              </p>
            </div>
          </div>

          {/* Center Navigation Tabs */}
          <nav className="hidden lg:flex items-center gap-1 bg-[#0d121c]/80 p-1 rounded-xl border border-white/[0.06] shadow-inner">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentTab(item.id)}
                  className={`relative flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${
                    isActive
                      ? 'text-white bg-[#192234] shadow-sm border border-[#d4af37]/35'
                      : 'text-[#8594ab] hover:text-white hover:bg-[#121824]'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#f3d87b]' : 'text-[#627088]'}`} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Quick Search & Actions Right Area */}
          <div className="flex items-center gap-2">
            {/* Command Palette Trigger */}
            <button
              onClick={onOpenCommandPalette}
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#0e131e] border border-[#212b3e] hover:border-[#d4af37]/40 text-[#7d8ea5] hover:text-white transition-all text-xs"
              title="Open Command Palette (Ctrl+K or ⌘K)"
            >
              <Search className="w-3.5 h-3.5 text-[#d4af37]" />
              <span className="hidden md:inline text-[11px]">Search...</span>
              <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-[#161d2a] border border-[#232e42] text-[9px] font-mono text-[#8e9bb0]">
                ⌘K
              </kbd>
            </button>

            {/* Quick Upload Button */}
            {onOpenUpload && (
              <button
                onClick={onOpenUpload}
                className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-[#d4af37] to-[#e68a00] text-black hover:brightness-110 active:scale-95 transition-all shadow-sm shadow-[#d4af37]/25 shrink-0"
              >
                <Plus className="w-3.5 h-3.5 stroke-[2.5]" />
                <span>Preserve</span>
              </button>
            )}

            {/* Status Badges with Radix Tooltip */}
            <TooltipProvider delayDuration={150}>
              <div className="flex items-center gap-1.5">
                {/* Vault Encryption Status Pill */}
                {vaultStatus && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={onOpenVaultModal}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[11px] font-medium border transition-colors ${
                          !vaultStatus.is_initialized
                            ? 'bg-[#151a24] text-[#8e9bb0] border-[#222c3e] hover:border-[#384762]'
                            : vaultStatus.is_unlocked
                            ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/40 hover:bg-emerald-900/40'
                            : 'bg-amber-950/40 text-amber-300 border-amber-600/40 hover:bg-amber-900/40 animate-pulse'
                        }`}
                      >
                        {!vaultStatus.is_initialized ? (
                          <ShieldAlert className="w-3.5 h-3.5 text-[#8e9bb0]" />
                        ) : vaultStatus.is_unlocked ? (
                          <Unlock className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Lock className="w-3.5 h-3.5 text-amber-400" />
                        )}
                        <span className="hidden sm:inline">
                          {!vaultStatus.is_initialized
                            ? 'Setup'
                            : vaultStatus.is_unlocked
                            ? 'Unlocked'
                            : 'Locked'}
                        </span>
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>
                      {!vaultStatus.is_initialized
                        ? 'Vault uninitialized - Click to setup encryption'
                        : vaultStatus.is_unlocked
                        ? 'Vault Unlocked - Click to manage or lock'
                        : 'Vault Locked - Click to unlock memories'}
                    </TooltipContent>
                  </Tooltip>
                )}

                {/* Local Privacy Pill */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-[#0f1420] border border-[#1f283b] text-[11px] text-[#93a2b7] cursor-help">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>AES-256</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    Hardware-accelerated AES-256-GCM encryption with Argon2id KDF. No telemetry.
                  </TooltipContent>
                </Tooltip>

                {/* Ollama Status Pill */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={() => setCurrentTab('ai-studio')}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[11px] font-medium border transition-colors ${
                        aiStatus?.ollama_running
                          ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/40'
                          : 'bg-amber-950/30 text-amber-300 border-amber-600/30 hover:bg-amber-900/40'
                      }`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          aiStatus?.ollama_running ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                        }`}
                      />
                      <span className="hidden md:inline">
                        {aiStatus?.ollama_running ? 'Ollama' : 'Offline'}
                      </span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    {aiStatus?.ollama_running
                      ? 'Local Ollama service active and ready for private neural inference.'
                      : 'Local Ollama offline. Click to visit setup guide in AI Studio.'}
                  </TooltipContent>
                </Tooltip>
              </div>
            </TooltipProvider>
          </div>
        </div>

        {/* Mobile Navigation Bar */}
        <div className="flex lg:hidden overflow-x-auto py-2 gap-1 border-t border-white/[0.05] scrollbar-thin">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs whitespace-nowrap font-medium transition-colors ${
                  isActive
                    ? 'bg-[#192234] text-[#f3d87b] border border-[#d4af37]/35'
                    : 'text-[#8594ab] hover:text-white'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
