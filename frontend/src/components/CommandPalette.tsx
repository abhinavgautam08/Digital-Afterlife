import React, { useState, useEffect, useRef } from 'react';
import {
  Search,
  Compass,
  Archive,
  Sparkles,
  Users,
  Cpu,
  Settings,
  Plus,
  Lock,
  ArrowRight,
  FileText,
  Image,
  Mic,
  Film,
  BookOpen
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription
} from './ui/dialog';
import { api } from '../services/api';
import type { Memory } from '../types';

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (tab: string) => void;
  onOpenUpload: () => void;
  onOpenAddPerson: () => void;
  onOpenVaultModal: () => void;
  onSelectMemory: (memory: Memory) => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigate,
  onOpenUpload,
  onOpenAddPerson,
  onOpenVaultModal,
  onSelectMemory
}) => {
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Memory[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSearchResults([]);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!query.trim()) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await api.getMemories({ search: query.trim(), size: 5 });
        setSearchResults(res.items || []);
      } catch (err) {
        console.error('Command palette search failed', err);
      } finally {
        setIsSearching(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  const handleAction = (callback: () => void) => {
    onClose();
    callback();
  };

  const navCommands = [
    { label: 'Go to Dashboard', tab: 'dashboard', icon: Compass, shortcut: 'G D' },
    { label: 'Explore Memory Vault', tab: 'vault', icon: Archive, shortcut: 'G V' },
    { label: 'Ask Memories (Local RAG)', tab: 'ask-memories', icon: Sparkles, shortcut: 'G A' },
    { label: 'People & Heritage Tree', tab: 'people', icon: Users, shortcut: 'G P' },
    { label: 'AI Storytelling Studio', tab: 'ai-studio', icon: Cpu, shortcut: 'G S' },
    { label: 'Security & System Settings', tab: 'settings', icon: Settings, shortcut: 'G ,' },
  ];

  const quickActions = [
    { label: 'Preserve New Memory / File', action: onOpenUpload, icon: Plus, badge: 'Upload' },
    { label: 'Add Person to Heritage Tree', action: onOpenAddPerson, icon: Users, badge: 'New Person' },
    { label: 'Lock / Unlock Encryption Vault', action: onOpenVaultModal, icon: Lock, badge: 'Security' },
  ];

  const getMemoryIcon = (type: string) => {
    switch (type) {
      case 'audio': return Mic;
      case 'photograph': return Image;
      case 'video': return Film;
      case 'document': return FileText;
      case 'story': return BookOpen;
      default: return Archive;
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl bg-[#0b0e14]/95 border border-[#263147] backdrop-blur-2xl p-0 overflow-hidden shadow-2xl rounded-2xl text-white">
        <DialogHeader className="sr-only">
          <DialogTitle>Quick Command Bar</DialogTitle>
          <DialogDescription>Search memories, jump to views, or trigger actions</DialogDescription>
        </DialogHeader>

        {/* Search Input Bar */}
        <div className="flex items-center px-4 border-b border-[#1f283b] bg-[#0f1420]/80">
          <Search className="w-5 h-5 text-[#d4af37] shrink-0 mr-3" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memories, jump to page, or run a command..."
            className="w-full py-4 text-sm bg-transparent text-white placeholder-[#687892] focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="text-xs text-[#687892] hover:text-white px-2 py-1 rounded bg-[#182030]"
            >
              Clear
            </button>
          )}
          <div className="ml-3 px-1.5 py-0.5 rounded bg-[#161c28] border border-[#232d40] text-[10px] font-mono text-[#8e9bb0]">
            ESC
          </div>
        </div>

        {/* Command Body */}
        <div className="max-h-[380px] overflow-y-auto p-3 space-y-4">
          {/* Live Search Results */}
          {query.trim() && (
            <div>
              <div className="px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-[#d4af37] flex items-center justify-between">
                <span>Memory Search Matches</span>
                {isSearching && <span className="text-[10px] text-[#6d7c92]">Searching local vault...</span>}
              </div>
              <div className="mt-1 space-y-1">
                {searchResults.length > 0 ? (
                  searchResults.map((mem) => {
                    const Icon = getMemoryIcon(mem.memory_type);
                    return (
                      <button
                        key={mem.id}
                        onClick={() => handleAction(() => onSelectMemory(mem))}
                        className="w-full flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-[#151c2a] text-left transition-colors group"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="p-2 rounded-lg bg-[#141a26] border border-[#20293b] text-[#d4af37] group-hover:border-[#d4af37]/40">
                            <Icon className="w-4 h-4" />
                          </div>
                          <div className="truncate">
                            <p className="text-xs font-semibold text-white group-hover:text-[#f3d87b] truncate">
                              {mem.title}
                            </p>
                            <p className="text-[10px] text-[#718299] truncate">
                              {mem.memory_type} • {mem.event_date || 'No date'} {mem.location ? `• ${mem.location}` : ''}
                            </p>
                          </div>
                        </div>
                        <ArrowRight className="w-3.5 h-3.5 text-[#45546d] group-hover:text-[#d4af37] shrink-0 ml-2" />
                      </button>
                    );
                  })
                ) : !isSearching ? (
                  <p className="px-3 py-4 text-center text-xs text-[#6e809c]">
                    No memories match "{query}". Try a different keyword.
                  </p>
                ) : null}
              </div>
            </div>
          )}

          {/* Quick Actions */}
          {!query.trim() && (
            <div>
              <div className="px-3 py-1 text-[10px] font-mono uppercase tracking-wider text-[#798ba5]">
                Quick Actions
              </div>
              <div className="mt-1 space-y-1">
                {quickActions.map((qa) => {
                  const Icon = qa.icon;
                  return (
                    <button
                      key={qa.label}
                      onClick={() => handleAction(qa.action)}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-xl hover:bg-[#161d2c] text-left transition-colors group"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="p-1.5 rounded-lg bg-[#111724] text-[#d4af37]">
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <span className="text-xs font-medium text-white group-hover:text-[#f3d87b]">
                          {qa.label}
                        </span>
                      </div>
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-[#141c2a] text-[#8e9bb0] border border-[#1f2838]">
                        {qa.badge}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Navigation Items */}
          <div>
            <div className="px-3 py-1 text-[10px] font-mono uppercase tracking-wider text-[#798ba5]">
              Navigation Views
            </div>
            <div className="mt-1 space-y-1">
              {navCommands
                .filter((nc) => !query.trim() || nc.label.toLowerCase().includes(query.toLowerCase()))
                .map((nc) => {
                  const Icon = nc.icon;
                  return (
                    <button
                      key={nc.tab}
                      onClick={() => handleAction(() => onNavigate(nc.tab))}
                      className="w-full flex items-center justify-between px-3 py-2 rounded-xl hover:bg-[#161d2c] text-left transition-colors group"
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="p-1.5 rounded-lg bg-[#111724] text-[#8e9bb0] group-hover:text-[#d4af37]">
                          <Icon className="w-3.5 h-3.5" />
                        </div>
                        <span className="text-xs font-medium text-[#c8d4e5] group-hover:text-white">
                          {nc.label}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono text-[#52637a] group-hover:text-[#8e9bb0]">
                        {nc.shortcut}
                      </span>
                    </button>
                  );
                })}
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="px-4 py-2.5 border-t border-[#1a2130] bg-[#0a0d13] flex items-center justify-between text-[11px] text-[#6d7c92]">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            100% Offline Local Search
          </span>
          <div className="flex items-center gap-3">
            <span>Use ↑↓ to navigate</span>
            <span>↵ to select</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};
