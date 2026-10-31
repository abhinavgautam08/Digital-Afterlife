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
} from 'lucide-react';
import type { AIStatus, VaultStatus } from '../types';

interface NavbarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  aiStatus: AIStatus | null;
  vaultStatus?: VaultStatus | null;
  onOpenVaultModal?: () => void;
}

export const Navbar = ({
  currentTab,
  setCurrentTab,
  aiStatus,
  vaultStatus,
  onOpenVaultModal,
}: NavbarProps) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: Compass },
    { id: 'vault', label: 'Memory Vault', icon: Archive },
    { id: 'ask-memories', label: 'Ask Memories', icon: Sparkles },
    { id: 'people', label: 'People', icon: Users },
    { id: 'ai-studio', label: 'AI Studio', icon: Cpu },
    { id: 'settings', label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[#232b3c] bg-[#090b0f]/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => setCurrentTab('dashboard')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#d4af37] via-[#aa8214] to-[#ff9e1b] flex items-center justify-center shadow-lg shadow-[#d4af37]/20 border border-[#f3d87b]/40">
              <HardDrive className="w-5 h-5 text-black stroke-[2.2]" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-serif text-lg font-bold tracking-wide text-white">
                  Digital Afterlife
                </span>
                <span className="px-1.5 py-0.5 text-[10px] uppercase font-semibold tracking-wider rounded bg-[#d4af37]/15 text-[#d4af37] border border-[#d4af37]/30">
                  Phase 6
                </span>
              </div>
              <p className="text-[11px] text-[#8e9bb0] -mt-0.5 font-light">
                Memory Keeper & Preservation Vault
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setCurrentTab(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-[#181f2c] text-[#f3d87b] border border-[#d4af37]/30 shadow-sm shadow-[#d4af37]/10'
                      : 'text-[#8e9bb0] hover:text-white hover:bg-[#121620]'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-[#d4af37]' : 'text-[#627088]'}`} />
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* Right Badges: Local Privacy, Vault Lock State, & AI Indicator */}
          <div className="flex items-center gap-2.5">
            {/* Vault Encryption Status Pill */}
            {vaultStatus && (
              <button
                onClick={onOpenVaultModal}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${
                  !vaultStatus.is_initialized
                    ? 'bg-[#151a24] text-[#8e9bb0] border-[#222c3e] hover:border-[#384762]'
                    : vaultStatus.is_unlocked
                    ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/40 hover:bg-emerald-900/40'
                    : 'bg-amber-950/40 text-amber-300 border-amber-600/40 hover:bg-amber-900/40 animate-pulse'
                }`}
                title={
                  !vaultStatus.is_initialized
                    ? 'Vault uninitialized - Click to setup encryption'
                    : vaultStatus.is_unlocked
                    ? 'Vault Unlocked - Click to manage or lock'
                    : 'Vault Locked - Click to unlock memories'
                }
              >
                {!vaultStatus.is_initialized ? (
                  <ShieldAlert className="w-3.5 h-3.5 text-[#8e9bb0]" />
                ) : vaultStatus.is_unlocked ? (
                  <Unlock className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Lock className="w-3.5 h-3.5 text-amber-400" />
                )}
                <span>
                  {!vaultStatus.is_initialized
                    ? 'Setup Vault'
                    : vaultStatus.is_unlocked
                    ? 'Vault Unlocked'
                    : 'Vault Locked'}
                </span>
              </button>
            )}

            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#111622] border border-[#1e2738] text-[11px] text-[#93a2b7]">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Offline AES-256</span>
            </div>

            <button
              onClick={() => setCurrentTab('ai-studio')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${
                aiStatus?.ollama_running
                  ? 'bg-emerald-950/40 text-emerald-300 border-emerald-500/40'
                  : 'bg-amber-950/30 text-amber-300 border-amber-600/30 hover:bg-amber-900/40'
              }`}
              title="Click to open AI Studio"
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  aiStatus?.ollama_running ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
                }`}
              />
              <span>{aiStatus?.ollama_running ? 'Ollama Online' : 'Ollama Offline'}</span>
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="flex md:hidden overflow-x-auto py-2 gap-1 border-t border-[#181d28]">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setCurrentTab(item.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs whitespace-nowrap font-medium ${
                  isActive
                    ? 'bg-[#181f2c] text-[#f3d87b] border border-[#d4af37]/30'
                    : 'text-[#8e9bb0]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {item.label}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
