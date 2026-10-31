import { useEffect, useState } from 'react';
import {
  Search,
  Upload,
  Archive,
  Image,
  Mic,
  FileText,
  Film,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  LayoutGrid,
  List as ListIcon,
  Tag as TagIcon,
  Clock,
  MapPin,
  X
} from 'lucide-react';
import type { Memory, MemoryListResponse, Person, Tag } from '../types';
import { api } from '../services/api';
import { TagManagerModal } from '../components/TagManagerModal';

interface VaultPageProps {
  onOpenUpload: () => void;
  onSelectMemory: (memory: Memory) => void;
  refreshTrigger: number;
}

export const VaultPage = ({
  onOpenUpload,
  onSelectMemory,
  refreshTrigger,
}: VaultPageProps) => {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [pageSize] = useState(12);

  // Filters & Controls
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState('all');
  const [selectedPerson, setSelectedPerson] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [sortBy, setSortBy] = useState<'created_at_desc' | 'created_at_asc' | 'event_date_desc' | 'event_date_asc' | 'title_asc' | 'size_desc'>('created_at_desc');

  // Metadata dropdowns
  const [people, setPeople] = useState<Person[]>([]);
  const [tags, setTags] = useState<Tag[]>([]);
  const [isTagModalOpen, setIsTagModalOpen] = useState(false);

  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    loadFilterOptions();
  }, []);

  useEffect(() => {
    loadMemories();
  }, [page, selectedType, selectedPerson, selectedTag, dateFrom, dateTo, sortBy, refreshTrigger]);

  const loadFilterOptions = async () => {
    try {
      const [peopleData, tagsData] = await Promise.all([
        api.getPeople(),
        api.getTags(),
      ]);
      setPeople(peopleData);
      setTags(tagsData);
    } catch (err) {
      console.warn('Failed loading filter metadata', err);
    }
  };

  const loadMemories = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res: MemoryListResponse = await api.getMemories({
        page,
        size: pageSize,
        search: searchTerm,
        memory_type: selectedType,
        person_id: selectedPerson,
        tag: selectedTag,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        sort_by: sortBy,
      });
      setMemories(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load vault items.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadMemories();
  };

  const clearAllFilters = () => {
    setSearchTerm('');
    setSelectedType('all');
    setSelectedPerson('');
    setSelectedTag('');
    setDateFrom('');
    setDateTo('');
    setSortBy('created_at_desc');
    setPage(1);
  };

  const hasActiveFilters =
    searchTerm ||
    selectedType !== 'all' ||
    selectedPerson ||
    selectedTag ||
    dateFrom ||
    dateTo ||
    sortBy !== 'created_at_desc';

  const filterChips = [
    { id: 'all', label: 'All Artifacts', icon: Archive },
    { id: 'photograph', label: 'Photographs', icon: Image },
    { id: 'audio', label: 'Audio / Oral Histories', icon: Mic },
    { id: 'video', label: 'Videos', icon: Film },
    { id: 'document', label: 'Documents & Letters', icon: FileText },
    { id: 'story', label: 'Written Stories', icon: BookOpen },
  ];

  const formatDuration = (seconds?: number | null) => {
    if (!seconds) return null;
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}m ${s < 10 ? '0' : ''}${s}s`;
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-white/[0.08]">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 rounded-md bg-[#d4af37]/15 border border-[#d4af37]/30 text-[10px] font-mono text-[#f3d87b] uppercase tracking-wider">
              Encrypted Repository
            </span>
          </div>
          <h1 className="text-2xl sm:text-4xl font-serif font-bold text-white tracking-tight">
            Memory Vault
          </h1>
          <p className="text-xs sm:text-sm text-[#8e9bb0] mt-0.5 font-light">
            {total} preserved multimedia artifacts indexed and secured in offline local storage
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsTagModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-2.5 rounded-xl text-xs font-semibold bg-[#121724] hover:bg-[#192233] text-[#f3d87b] border border-[#d4af37]/35 shadow-sm transition-all"
          >
            <TagIcon className="w-3.5 h-3.5 text-[#d4af37]" />
            <span>Manage Tags</span>
          </button>
          <button
            onClick={onOpenUpload}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold bg-gradient-to-r from-[#d4af37] via-[#e2ba3d] to-[#e68a00] text-black shadow-lg shadow-[#d4af37]/20 hover:brightness-110 active:scale-95 transition-all shrink-0"
          >
            <Upload className="w-4 h-4 stroke-[2.4]" />
            <span>Preserve Artifact</span>
          </button>
        </div>
      </div>

      {/* Category Pills & View Toggles */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
          {filterChips.map((chip) => {
            const Icon = chip.icon;
            const isSelected = selectedType === chip.id;
            return (
              <button
                key={chip.id}
                onClick={() => {
                  setSelectedType(chip.id);
                  setPage(1);
                }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg whitespace-nowrap font-medium transition-all ${
                  isSelected
                    ? 'bg-[#d4af37]/20 border border-[#d4af37] text-[#f3d87b] shadow-sm shadow-[#d4af37]/10'
                    : 'bg-[#0f121a] border border-[#202738] text-[#8e9bb0] hover:text-white hover:border-[#2f394f]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {chip.label}
              </button>
            );
          })}
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-1 self-end md:self-auto bg-[#0d1017] p-1 rounded-xl border border-[#202738]">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded-lg text-xs transition-colors ${
              viewMode === 'grid'
                ? 'bg-[#d4af37]/20 text-[#f3d87b]'
                : 'text-[#8e9bb0] hover:text-white'
            }`}
            title="Grid View"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-1.5 rounded-lg text-xs transition-colors ${
              viewMode === 'list'
                ? 'bg-[#d4af37]/20 text-[#f3d87b]'
                : 'text-[#8e9bb0] hover:text-white'
            }`}
            title="List View"
          >
            <ListIcon className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 rounded-2xl card-modern-static space-y-3">
        <form onSubmit={handleSearchSubmit} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#d4af37] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search across title, narrative notes, location, or extracted document text..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#080b12] border border-white/[0.08] focus:border-[#d4af37]/60 focus:outline-none text-white text-xs sm:text-sm placeholder-[#5e6f85]"
            />
          </div>
          <button
            type="submit"
            className="px-5 py-2.5 rounded-xl text-xs sm:text-sm font-semibold bg-[#161d2c] hover:bg-[#1e273a] text-[#f3d87b] border border-[#d4af37]/40 shadow-sm transition-all"
          >
            Search
          </button>
        </form>

        {/* Extended Filter Dropdowns */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 pt-1">
          {/* Person Filter */}
          <div>
            <select
              value={selectedPerson}
              onChange={(e) => {
                setSelectedPerson(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-1.5 rounded-lg bg-[#0f131c] border border-[#232b3c] text-xs text-[#b8c5d9] focus:outline-none focus:border-[#d4af37]"
            >
              <option value="">All Connected People</option>
              {people.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.full_name} {p.relationship ? `(${p.relationship})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Tag Filter */}
          <div>
            <select
              value={selectedTag}
              onChange={(e) => {
                setSelectedTag(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-1.5 rounded-lg bg-[#0f131c] border border-[#232b3c] text-xs text-[#b8c5d9] focus:outline-none focus:border-[#d4af37]"
            >
              <option value="">All Tags & Themes</option>
              {tags.map((t) => (
                <option key={t.id} value={t.name}>
                  #{t.name}
                </option>
              ))}
            </select>
          </div>

          {/* Sort By */}
          <div>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as any);
                setPage(1);
              }}
              className="w-full px-3 py-1.5 rounded-lg bg-[#0f131c] border border-[#232b3c] text-xs text-[#b8c5d9] focus:outline-none focus:border-[#d4af37]"
            >
              <option value="created_at_desc">Newest Ingested</option>
              <option value="created_at_asc">Oldest Ingested</option>
              <option value="event_date_desc">Event Date (Newest)</option>
              <option value="event_date_asc">Event Date (Oldest)</option>
              <option value="title_asc">Title (A-Z)</option>
              <option value="size_desc">File Size (Largest)</option>
            </select>
          </div>

          {/* Date Range Inputs */}
          <div className="flex items-center gap-1">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
              className="w-1/2 px-2 py-1.5 rounded-lg bg-[#0f131c] border border-[#232b3c] text-[11px] text-[#b8c5d9] focus:outline-none focus:border-[#d4af37]"
              title="From Date"
            />
            <span className="text-[#6d7c92] text-xs">-</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
              className="w-1/2 px-2 py-1.5 rounded-lg bg-[#0f131c] border border-[#232b3c] text-[11px] text-[#b8c5d9] focus:outline-none focus:border-[#d4af37]"
              title="To Date"
            />
          </div>
        </div>

        {hasActiveFilters && (
          <div className="flex items-center justify-between pt-2 border-t border-[#181f2c] text-xs">
            <span className="text-[#8e9bb0]">Filters active</span>
            <button
              type="button"
              onClick={clearAllFilters}
              className="flex items-center gap-1 text-[#d4af37] hover:underline"
            >
              <X className="w-3.5 h-3.5" />
              Reset all filters
            </button>
          </div>
        )}
      </div>

      {/* Error Message */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 flex items-center gap-3 text-xs text-rose-200">
          <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Main Content Area */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[...Array(8)].map((_, i) => (
            <div
              key={i}
              className="h-64 rounded-2xl bg-[#0d1017] border border-[#1b2230] animate-pulse"
            />
          ))}
        </div>
      ) : memories.length === 0 ? (
        <div className="p-12 rounded-2xl bg-[#0d1017] border border-dashed border-[#232b3c] text-center space-y-3">
          <Archive className="w-12 h-12 mx-auto text-[#6d7c92]" />
          <h3 className="text-base font-semibold text-white">No memories found</h3>
          <p className="text-xs text-[#8e9bb0] max-w-md mx-auto">
            {hasActiveFilters
              ? 'No artifacts match your selected filter criteria. Try clearing some filters.'
              : 'Begin preserving your family legacy by uploading photographs, voice recordings, documents, or videos.'}
          </p>
          {hasActiveFilters ? (
            <button
              onClick={clearAllFilters}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#1a2233] text-[#f3d87b] border border-[#d4af37]/30"
            >
              Reset Filters
            </button>
          ) : (
            <button
              onClick={onOpenUpload}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b]"
            >
              Preserve First Artifact
            </button>
          )}
        </div>
      ) : viewMode === 'grid' ? (
        /* GRID VIEW */
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {memories.map((m) => {
            const isImage = m.memory_type === 'photograph' || m.mime_type.startsWith('image/');
            const previewUrl = m.has_thumbnail
              ? api.getMemoryThumbnailUrl(m.id)
              : api.getMemoryFileUrl(m.id);

            return (
              <div
                key={m.id}
                onClick={() => onSelectMemory(m)}
                className="group cursor-pointer rounded-2xl card-modern overflow-hidden flex flex-col justify-between"
              >
                <div>
                  {/* Media Visual Header */}
                  <div className="h-44 bg-[#080a0e] relative overflow-hidden flex items-center justify-center">
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
                          <Mic className="w-10 h-10 text-[#d4af37]/80" />
                        ) : m.memory_type === 'video' ? (
                          <Film className="w-10 h-10 text-emerald-400/80" />
                        ) : (
                          <FileText className="w-10 h-10 text-violet-400/80" />
                        )}
                        <span className="text-[10px] uppercase tracking-wider mt-2 font-medium">
                          {m.memory_type}
                        </span>
                      </div>
                    )}

                    {/* Category pill */}
                    <span className="absolute top-2.5 right-2.5 px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider bg-black/75 backdrop-blur-sm text-[#f3d87b] border border-[#d4af37]/30">
                      {m.memory_type}
                    </span>

                    {/* Duration badge */}
                    {m.duration_seconds && (
                      <span className="absolute bottom-2.5 right-2.5 px-2 py-0.5 rounded text-[10px] font-mono bg-black/80 text-white flex items-center gap-1">
                        <Clock className="w-3 h-3 text-[#d4af37]" />
                        {formatDuration(m.duration_seconds)}
                      </span>
                    )}

                    {/* Resolution badge */}
                    {m.width && m.height && (
                      <span className="absolute bottom-2.5 left-2.5 px-2 py-0.5 rounded text-[10px] font-mono bg-black/80 text-white">
                        {m.width}×{m.height}
                      </span>
                    )}
                  </div>

                  {/* Body */}
                  <div className="p-4 space-y-2">
                    <h3 className="text-sm font-semibold text-white group-hover:text-[#f3d87b] transition-colors truncate">
                      {m.title}
                    </h3>

                    {m.location && (
                      <p className="text-[11px] text-sky-400 flex items-center gap-1">
                        <MapPin className="w-3 h-3 shrink-0" />
                        <span className="truncate">{m.location}</span>
                      </p>
                    )}

                    <p className="text-xs text-[#8e9bb0] line-clamp-2 font-light">
                      {m.description || (m.extracted_text ? `Extracted: ${m.extracted_text.slice(0, 80)}...` : 'No narrative recorded.')}
                    </p>

                    {/* Tag chips */}
                    {m.tags && m.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 pt-1">
                        {m.tags.slice(0, 3).map((t) => (
                          <span
                            key={t.id}
                            className="px-1.5 py-0.5 rounded text-[10px] bg-[#141d2c] text-[#d4af37] border border-[#d4af37]/20"
                          >
                            #{t.name}
                          </span>
                        ))}
                        {m.tags.length > 3 && (
                          <span className="text-[10px] text-[#6d7c92]">+{m.tags.length - 3}</span>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Footer Metadata */}
                <div className="p-4 pt-2.5 border-t border-[#1a202c] flex items-center justify-between text-[11px] text-[#6d7c92]">
                  <span>{m.event_date ? new Date(m.event_date).toLocaleDateString() : 'Undated'}</span>
                  <span>{(m.file_size / 1024 / 1024).toFixed(1)} MB</span>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* LIST VIEW */
        <div className="space-y-2">
          {memories.map((m) => {
            const isImage = m.memory_type === 'photograph' || m.mime_type.startsWith('image/');
            const previewUrl = m.has_thumbnail
              ? api.getMemoryThumbnailUrl(m.id)
              : api.getMemoryFileUrl(m.id);

            return (
              <div
                key={m.id}
                onClick={() => onSelectMemory(m)}
                className="group cursor-pointer p-3.5 rounded-xl bg-[#0f131c] border border-[#202738] hover:border-[#d4af37]/50 flex items-center justify-between gap-4 transition-colors"
              >
                <div className="flex items-center gap-3.5 min-w-0">
                  <div className="w-14 h-14 rounded-lg bg-[#080a0e] overflow-hidden flex items-center justify-center shrink-0 border border-[#1b2230]">
                    {isImage ? (
                      <img src={previewUrl} alt={m.title} className="w-full h-full object-cover" />
                    ) : m.memory_type === 'audio' ? (
                      <Mic className="w-6 h-6 text-[#d4af37]" />
                    ) : m.memory_type === 'video' ? (
                      <Film className="w-6 h-6 text-emerald-400" />
                    ) : (
                      <FileText className="w-6 h-6 text-violet-400" />
                    )}
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider bg-[#1a2233] text-[#d4af37] border border-[#d4af37]/30">
                        {m.memory_type}
                      </span>
                      <h3 className="text-sm font-semibold text-white group-hover:text-[#f3d87b] truncate">
                        {m.title}
                      </h3>
                    </div>
                    <p className="text-xs text-[#8e9bb0] truncate mt-0.5 font-light">
                      {m.description || (m.location ? `Location: ${m.location}` : m.original_filename)}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-xs text-[#8e9bb0] shrink-0">
                  {m.location && (
                    <span className="hidden md:flex items-center gap-1 text-sky-400 text-[11px]">
                      <MapPin className="w-3 h-3" />
                      {m.location}
                    </span>
                  )}
                  {m.duration_seconds && (
                    <span className="hidden sm:inline font-mono text-[11px] text-[#f3d87b]">
                      {formatDuration(m.duration_seconds)}
                    </span>
                  )}
                  <span className="hidden sm:inline">
                    {m.event_date ? new Date(m.event_date).toLocaleDateString() : 'Undated'}
                  </span>
                  <span className="font-mono text-[11px]">
                    {(m.file_size / 1024 / 1024).toFixed(1)} MB
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-[#202738]">
          <p className="text-xs text-[#8e9bb0]">
            Showing page {page} of {totalPages} ({total} total memories)
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-2 rounded-lg text-xs font-semibold bg-[#0f131c] border border-[#202738] text-[#8e9bb0] hover:text-white disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-medium text-white px-2">
              {page} / {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-2 rounded-lg text-xs font-semibold bg-[#0f131c] border border-[#202738] text-[#8e9bb0] hover:text-white disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Tag Manager Modal */}
      <TagManagerModal
        isOpen={isTagModalOpen}
        onClose={() => setIsTagModalOpen(false)}
        onTagsUpdated={() => {
          loadFilterOptions();
          loadMemories();
        }}
      />
    </div>
  );
};
