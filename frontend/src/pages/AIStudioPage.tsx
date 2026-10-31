import { useState, useEffect } from 'react';
import {
  Cpu,
  RefreshCw,
  Terminal,
  ShieldCheck,
  Sparkles,
  Server,
  BookOpen,
  Feather,
  Clock,
  Heart,
  FolderHeart,
  CheckCircle2,
  AlertCircle,
  FileText,
  Calendar,
  Trash2,
  Edit3,
  Plus,
  Printer,
  ExternalLink,
  Check,
  X
} from 'lucide-react';
import type {
  Person,
  Memory,
  AIStatus,
  AIModelsResponse,
  StoryArtifact,
  TimelineEvent,
  RemembrancePage as RemembrancePageType,
  MemoryCollection,
  SourceMemoryInfo
} from '../types';
import { api } from '../services/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '../components/ui/dialog';

interface AIStudioPageProps {
  people?: Person[];
  onSelectMemory?: (memory: Memory, initialSeekTime?: number | null) => void;
  aiStatus?: AIStatus | null;
  onRefreshAIStatus?: () => void;
}

export const AIStudioPage = ({
  people = [],
  onSelectMemory,
  aiStatus,
  onRefreshAIStatus
}: AIStudioPageProps) => {
  // Navigation tabs within AI Studio
  const [activeTab, setActiveTab] = useState<
    'biography' | 'story' | 'timeline' | 'remembrance' | 'collections' | 'engine'
  >('biography');

  // Shared state
  const [selectedPersonId, setSelectedPersonId] = useState<string>('');
  const [personMemories, setPersonMemories] = useState<Memory[]>([]);
  const [isLoadingMemories, setIsLoadingMemories] = useState(false);

  // Diagnostics & Engine state
  const [modelsData, setModelsData] = useState<AIModelsResponse | null>(null);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Biography State
  // ---------------------------------------------------------------------------
  const [bioLength, setBioLength] = useState<'short' | 'medium' | 'detailed'>('medium');
  const [bioTone, setBioTone] = useState<'respectful' | 'warm' | 'factual' | 'reflective'>('respectful');
  const [bioLang, setBioLang] = useState<'en' | 'hi' | 'source_preserved'>('en');
  const [bioSelectedMemoryIds, setBioSelectedMemoryIds] = useState<string[]>([]);
  const [isGeneratingBio, setIsGeneratingBio] = useState(false);
  const [currentBio, setCurrentBio] = useState<StoryArtifact | null>(null);
  const [isEditingBio, setIsEditingBio] = useState(false);
  const [editableBioContent, setEditableBioContent] = useState('');
  const [bioHistory, setBioHistory] = useState<StoryArtifact[]>([]);
  const [bioError, setBioError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Story State
  // ---------------------------------------------------------------------------
  const [storyTitle, setStoryTitle] = useState('');
  const [storyTone, setStoryTone] = useState<'respectful' | 'warm' | 'factual' | 'reflective'>('warm');
  const [storyLang, setStoryLang] = useState<'en' | 'hi' | 'source_preserved'>('en');
  const [storySelectedMemoryIds, setStorySelectedMemoryIds] = useState<string[]>([]);
  const [isGeneratingStory, setIsGeneratingStory] = useState(false);
  const [currentStory, setCurrentStory] = useState<StoryArtifact | null>(null);
  const [isEditingStory, setIsEditingStory] = useState(false);
  const [editableStoryContent, setEditableStoryContent] = useState('');
  const [storyHistory, setStoryHistory] = useState<StoryArtifact[]>([]);
  const [storyError, setStoryError] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Timeline State
  // ---------------------------------------------------------------------------
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [isGeneratingTimeline, setIsGeneratingTimeline] = useState(false);
  const [timelineError, setTimelineError] = useState<string | null>(null);
  const [showAddEventModal, setShowAddEventModal] = useState(false);
  const [newEventTitle, setNewEventTitle] = useState('');
  const [newEventDate, setNewEventDate] = useState('');
  const [newEventApproxDate, setNewEventApproxDate] = useState('');
  const [newEventDesc, setNewEventDesc] = useState('');
  const [newEventConfidence, setNewEventConfidence] = useState<'exact' | 'approximate' | 'unknown'>('approximate');

  // ---------------------------------------------------------------------------
  // Remembrance Page State
  // ---------------------------------------------------------------------------
  const [remembrancePage, setRemembrancePage] = useState<RemembrancePageType | null>(null);
  const [remembranceNotes, setRemembranceNotes] = useState('');
  const [isSavingRemembrance, setIsSavingRemembrance] = useState(false);

  // ---------------------------------------------------------------------------
  // Collections State
  // ---------------------------------------------------------------------------
  const [collections, setCollections] = useState<MemoryCollection[]>([]);
  const [activeCollection, setActiveCollection] = useState<MemoryCollection | null>(null);
  const [isCreatingCollection, setIsCreatingCollection] = useState(false);
  const [newColTitle, setNewColTitle] = useState('');
  const [newColDesc, setNewColDesc] = useState('');
  const [newColType, setNewColType] = useState<
    'childhood' | 'family' | 'education' | 'career' | 'celebrations' | 'travel' | 'milestones' | 'custom'
  >('custom');

  // Auto-select first person if available
  useEffect(() => {
    if (people.length > 0 && !selectedPersonId) {
      setSelectedPersonId(people[0].id);
    }
  }, [people]);

  // Load memories & artifacts whenever selected person changes
  useEffect(() => {
    if (selectedPersonId) {
      loadPersonContext(selectedPersonId);
    }
  }, [selectedPersonId]);

  // Load models on engine tab
  useEffect(() => {
    if (activeTab === 'engine') {
      loadEngineModels();
    }
    if (activeTab === 'collections') {
      loadCollections();
    }
  }, [activeTab]);

  const loadPersonContext = async (personId: string) => {
    setIsLoadingMemories(true);
    try {
      const [memsResp, artifacts, timeline, remPage] = await Promise.all([
        api.getMemories({ person_id: personId, size: 100 }),
        api.getPersonArtifacts(personId),
        api.getPersonTimeline(personId),
        api.getRemembrancePage(personId)
      ]);

      setPersonMemories(memsResp.items);
      setBioSelectedMemoryIds(memsResp.items.map((m) => m.id));
      setStorySelectedMemoryIds(memsResp.items.slice(0, 3).map((m) => m.id));

      const bios = artifacts.filter((a) => a.artifact_type === 'biography');
      setBioHistory(bios);
      if (bios.length > 0) {
        setCurrentBio(bios[0]);
        setEditableBioContent(bios[0].content);
      } else {
        setCurrentBio(null);
        setEditableBioContent('');
      }

      const stories = artifacts.filter((a) => a.artifact_type === 'story');
      setStoryHistory(stories);
      if (stories.length > 0) {
        setCurrentStory(stories[0]);
        setEditableStoryContent(stories[0].content);
      } else {
        setCurrentStory(null);
        setEditableStoryContent('');
      }

      setTimelineEvents(timeline);
      setRemembrancePage(remPage);
      setRemembranceNotes(remPage.user_personal_notes || '');
    } catch (err) {
      console.error('Failed to load person context:', err);
    } finally {
      setIsLoadingMemories(false);
    }
  };

  const loadEngineModels = async () => {
    try {
      const models = await api.getAIModels();
      setModelsData(models);
    } catch (err) {
      console.error('Failed to load AI models', err);
    }
  };

  const loadCollections = async () => {
    try {
      const cols = await api.getCollections(selectedPersonId || undefined);
      setCollections(cols);
      if (cols.length > 0 && !activeCollection) {
        setActiveCollection(cols[0]);
      }
    } catch (err) {
      console.error('Failed to load collections', err);
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCmd(label);
    setTimeout(() => setCopiedCmd(null), 2500);
  };

  const selectedPerson = people.find((p) => p.id === selectedPersonId);
  const isOnline = aiStatus?.ollama_running ?? false;

  // ---------------------------------------------------------------------------
  // Handlers: Biography
  // ---------------------------------------------------------------------------
  const handleGenerateBiography = async () => {
    if (!selectedPersonId) return;
    setIsGeneratingBio(true);
    setBioError(null);
    try {
      const bio = await api.generateBiography({
        person_id: selectedPersonId,
        source_memory_ids: bioSelectedMemoryIds.length > 0 ? bioSelectedMemoryIds : undefined,
        length: bioLength,
        tone: bioTone,
        language: bioLang
      });
      setCurrentBio(bio);
      setEditableBioContent(bio.content);
      setIsEditingBio(false);
      setBioHistory((prev) => [bio, ...prev]);
    } catch (err: any) {
      setBioError(err?.message || 'Failed to generate biography.');
    } finally {
      setIsGeneratingBio(false);
    }
  };

  const handleSaveBioApproval = async (status: 'approved' | 'rejected' | 'pending') => {
    if (!currentBio) return;
    try {
      const updated = await api.updateArtifact(currentBio.id, {
        content: editableBioContent,
        approval_status: status
      });
      setCurrentBio(updated);
      setIsEditingBio(false);
      setBioHistory((prev) => prev.map((b) => (b.id === updated.id ? updated : b)));
    } catch (err: any) {
      alert(`Error updating biography: ${err?.message || 'Unknown error'}`);
    }
  };

  const handleDeleteBio = async (id: string) => {
    if (!confirm('Are you sure you want to delete this biography artifact? Original memory files will remain untouched.')) return;
    try {
      await api.deleteArtifact(id);
      setBioHistory((prev) => prev.filter((b) => b.id !== id));
      if (currentBio?.id === id) {
        const remaining = bioHistory.filter((b) => b.id !== id);
        setCurrentBio(remaining[0] || null);
        setEditableBioContent(remaining[0]?.content || '');
      }
    } catch (err: any) {
      alert(`Failed to delete artifact: ${err?.message}`);
    }
  };

  // ---------------------------------------------------------------------------
  // Handlers: Story
  // ---------------------------------------------------------------------------
  const handleGenerateStory = async () => {
    if (!selectedPersonId || storySelectedMemoryIds.length === 0) return;
    setIsGeneratingStory(true);
    setStoryError(null);
    try {
      const story = await api.generateStory({
        person_id: selectedPersonId,
        source_memory_ids: storySelectedMemoryIds,
        title: storyTitle.trim() || undefined,
        tone: storyTone,
        language: storyLang
      });
      setCurrentStory(story);
      setEditableStoryContent(story.content);
      setIsEditingStory(false);
      setStoryHistory((prev) => [story, ...prev]);
    } catch (err: any) {
      setStoryError(err?.message || 'Failed to generate story.');
    } finally {
      setIsGeneratingStory(false);
    }
  };

  const handleSaveStoryApproval = async (status: 'approved' | 'rejected' | 'pending') => {
    if (!currentStory) return;
    try {
      const updated = await api.updateArtifact(currentStory.id, {
        content: editableStoryContent,
        approval_status: status
      });
      setCurrentStory(updated);
      setIsEditingStory(false);
      setStoryHistory((prev) => prev.map((s) => (s.id === updated.id ? updated : s)));
    } catch (err: any) {
      alert(`Error updating story: ${err?.message}`);
    }
  };

  const handleDeleteStory = async (id: string) => {
    if (!confirm('Are you sure you want to delete this story? Original memory files will remain untouched.')) return;
    try {
      await api.deleteArtifact(id);
      setStoryHistory((prev) => prev.filter((s) => s.id !== id));
      if (currentStory?.id === id) {
        const remaining = storyHistory.filter((s) => s.id !== id);
        setCurrentStory(remaining[0] || null);
        setEditableStoryContent(remaining[0]?.content || '');
      }
    } catch (err: any) {
      alert(`Failed to delete artifact: ${err?.message}`);
    }
  };

  // ---------------------------------------------------------------------------
  // Handlers: Timeline
  // ---------------------------------------------------------------------------
  const handleAutoGenerateTimeline = async () => {
    if (!selectedPersonId) return;
    setIsGeneratingTimeline(true);
    setTimelineError(null);
    try {
      const events = await api.generateTimeline(selectedPersonId);
      setTimelineEvents(events);
    } catch (err: any) {
      setTimelineError(err?.message || 'Failed to generate timeline events.');
    } finally {
      setIsGeneratingTimeline(false);
    }
  };

  const handleConfirmTimelineEvent = async (eventId: string) => {
    try {
      const updated = await api.updateTimelineEvent(eventId, {
        verification_status: 'user_confirmed'
      });
      setTimelineEvents((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
    } catch (err: any) {
      alert(`Failed to confirm event: ${err?.message}`);
    }
  };

  const handleDeleteTimelineEvent = async (eventId: string) => {
    if (!confirm('Remove this milestone from the timeline?')) return;
    try {
      await api.deleteTimelineEvent(eventId);
      setTimelineEvents((prev) => prev.filter((e) => e.id !== eventId));
    } catch (err: any) {
      alert(`Failed to delete event: ${err?.message}`);
    }
  };

  const handleAddManualEvent = async () => {
    if (!selectedPersonId || !newEventTitle.trim()) return;
    try {
      const ev = await api.createTimelineEvent({
        person_id: selectedPersonId,
        title: newEventTitle.trim(),
        approximate_date: newEventApproxDate.trim() || undefined,
        event_date: newEventDate ? new Date(newEventDate).toISOString() : undefined,
        description: newEventDesc.trim() || 'User documented milestone.',
        date_confidence: newEventConfidence,
        verification_status: 'user_confirmed'
      });
      setTimelineEvents((prev) => [ev, ...prev]);
      setShowAddEventModal(false);
      setNewEventTitle('');
      setNewEventDate('');
      setNewEventApproxDate('');
      setNewEventDesc('');
    } catch (err: any) {
      alert(`Failed to add milestone: ${err?.message}`);
    }
  };

  // ---------------------------------------------------------------------------
  // Handlers: Remembrance Page
  // ---------------------------------------------------------------------------
  const handleSaveRemembrance = async () => {
    if (!selectedPersonId) return;
    setIsSavingRemembrance(true);
    try {
      const updated = await api.updateRemembrancePage(selectedPersonId, {
        user_personal_notes: remembranceNotes,
        biography_artifact_id: currentBio?.id || undefined
      });
      setRemembrancePage(updated);
      alert('Remembrance page updated successfully.');
    } catch (err: any) {
      alert(`Failed to update remembrance page: ${err?.message}`);
    } finally {
      setIsSavingRemembrance(false);
    }
  };

  const handlePrintRemembrance = () => {
    window.print();
  };

  // ---------------------------------------------------------------------------
  // Handlers: Collections
  // ---------------------------------------------------------------------------
  const handleCreateCollection = async () => {
    if (!newColTitle.trim()) return;
    try {
      const col = await api.createCollection({
        title: newColTitle.trim(),
        description: newColDesc.trim() || undefined,
        collection_type: newColType,
        person_id: selectedPersonId || undefined
      });
      setCollections((prev) => [col, ...prev]);
      setActiveCollection(col);
      setIsCreatingCollection(false);
      setNewColTitle('');
      setNewColDesc('');
    } catch (err: any) {
      alert(`Failed to create collection: ${err?.message}`);
    }
  };

  const handleAddMemoryToCollection = async (memoryId: string) => {
    if (!activeCollection) return;
    try {
      const updated = await api.addCollectionItem(activeCollection.id, memoryId);
      setActiveCollection(updated);
      setCollections((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err: any) {
      alert(`Failed to add item: ${err?.message}`);
    }
  };

  const handleRemoveMemoryFromCollection = async (memoryId: string) => {
    if (!activeCollection) return;
    try {
      const updated = await api.removeCollectionItem(activeCollection.id, memoryId);
      setActiveCollection(updated);
      setCollections((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
    } catch (err: any) {
      alert(`Failed to remove item: ${err?.message}`);
    }
  };

  const handleDeleteCollection = async (id: string) => {
    if (!confirm('Are you sure you want to delete this collection? Original memories will not be deleted.')) return;
    try {
      await api.deleteCollection(id);
      setCollections((prev) => prev.filter((c) => c.id !== id));
      setActiveCollection(null);
    } catch (err: any) {
      alert(`Failed to delete collection: ${err?.message}`);
    }
  };

  // Helper to open memory detail modal
  const handleOpenSourceMemory = async (source: SourceMemoryInfo) => {
    if (!onSelectMemory) return;
    try {
      const mem = await api.getMemory(source.memory_id);
      onSelectMemory(mem);
    } catch {
      // Fallback object if getMemory fails
      onSelectMemory({
        id: source.memory_id,
        title: source.title,
        memory_type: source.memory_type as any,
        original_filename: source.original_filename,
        stored_filename: source.original_filename,
        mime_type: 'application/octet-stream',
        file_size: 0,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        privacy_level: 'private',
        processing_status: 'completed',
        people: [],
        tags: [],
        transcripts: []
      });
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-16">
      {/* Top Banner & Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#202738]">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-serif font-bold text-white tracking-wide">
              AI Storytelling & Remembrance
            </h1>
            <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider rounded bg-[#d4af37]/15 text-[#d4af37] border border-[#d4af37]/30">
              Phase 5
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#8e9bb0] mt-0.5 font-light">
            Evidence-grounded biographies, timelines, stories, and private remembrance pages. Zero deceased impersonation.
          </p>
        </div>

        {/* Global Person Selector & Refresh */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-[#0e121a] border border-[#202738] rounded-xl px-3 py-1.5">
            <span className="text-xs text-[#6d7c92]">Person:</span>
            <select
              value={selectedPersonId}
              onChange={(e) => setSelectedPersonId(e.target.value)}
              className="bg-transparent text-xs font-semibold text-[#f3d87b] focus:outline-none cursor-pointer"
            >
              {people.map((p) => (
                <option key={p.id} value={p.id} className="bg-[#0b0e14] text-white">
                  {p.full_name} {p.relationship ? `(${p.relationship})` : ''}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => onRefreshAIStatus?.()}
            className="p-2 rounded-xl text-xs font-semibold bg-[#161c28] hover:bg-[#1d2535] text-[#d4af37] border border-[#d4af37]/30 transition-all shrink-0"
            title="Refresh AI Daemon State"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Offline Guard Banner */}
      {!isOnline && (
        <div className="p-4 rounded-2xl bg-amber-950/30 border border-amber-500/40 text-amber-300 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>
              <strong>Local Ollama is currently offline.</strong> AI generation features are disabled until Ollama is started locally. Manual timelines, collections, and edits remain 100% available.
            </span>
          </div>
          <button
            onClick={() => setActiveTab('engine')}
            className="px-3 py-1 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-200 border border-amber-500/40 font-semibold shrink-0"
          >
            Setup Guide
          </button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex items-center gap-1.5 p-1.5 bg-[#0a0e16]/80 rounded-2xl border border-white/[0.06] overflow-x-auto scrollbar-thin">
        {[
          { id: 'biography', label: 'Biography Generator', icon: BookOpen },
          { id: 'story', label: 'Memory Stories', icon: Feather },
          { id: 'timeline', label: 'Life Timeline', icon: Clock },
          { id: 'remembrance', label: 'Remembrance Page', icon: Heart },
          { id: 'collections', label: 'Collections', icon: FolderHeart },
          { id: 'engine', label: 'Local AI Engine', icon: Cpu },
        ].map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as any)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium transition-all whitespace-nowrap ${
                isActive
                  ? 'bg-[#182236] text-[#f3d87b] border border-[#d4af37]/35 font-semibold shadow-sm shadow-[#d4af37]/10'
                  : 'text-[#8494ab] hover:text-white hover:bg-[#121724]'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-[#f3d87b]' : 'text-[#627088]'}`} />
              {t.label}
            </button>
          );
        })}
      </div>

      {/* =====================================================================
          TAB 1: BIOGRAPHY GENERATOR
         ===================================================================== */}
      {activeTab === 'biography' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Controls Column */}
          <div className="space-y-5">
            <div className="p-5 rounded-2xl bg-[#0d1017] border border-[#202738] space-y-4">
              <h3 className="text-sm font-serif font-bold text-white flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-[#d4af37]" />
                Biography Parameters
              </h3>

              {/* Length */}
              <div>
                <label className="text-[11px] text-[#6d7c92] block mb-1.5 uppercase font-bold tracking-wider">
                  Narrative Length
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {(['short', 'medium', 'detailed'] as const).map((len) => (
                    <button
                      key={len}
                      onClick={() => setBioLength(len)}
                      className={`py-1.5 text-xs rounded-lg border capitalize transition-all ${
                        bioLength === len
                          ? 'bg-[#d4af37]/20 border-[#d4af37]/50 text-[#f3d87b] font-bold'
                          : 'bg-[#080a0e] border-[#1c2331] text-[#8e9bb0] hover:text-white'
                      }`}
                    >
                      {len}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tone */}
              <div>
                <label className="text-[11px] text-[#6d7c92] block mb-1.5 uppercase font-bold tracking-wider">
                  Tone of Voice
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {(['respectful', 'warm', 'factual', 'reflective'] as const).map((tone) => (
                    <button
                      key={tone}
                      onClick={() => setBioTone(tone)}
                      className={`py-1.5 text-xs rounded-lg border capitalize transition-all ${
                        bioTone === tone
                          ? 'bg-[#d4af37]/20 border-[#d4af37]/50 text-[#f3d87b] font-bold'
                          : 'bg-[#080a0e] border-[#1c2331] text-[#8e9bb0] hover:text-white'
                      }`}
                    >
                      {tone}
                    </button>
                  ))}
                </div>
              </div>

              {/* Language */}
              <div>
                <label className="text-[11px] text-[#6d7c92] block mb-1.5 uppercase font-bold tracking-wider">
                  Language
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'en', label: 'English' },
                    { id: 'hi', label: 'Hindi (हिंदी)' }
                  ].map((l) => (
                    <button
                      key={l.id}
                      onClick={() => setBioLang(l.id as any)}
                      className={`py-1.5 text-xs rounded-lg border transition-all ${
                        bioLang === l.id
                          ? 'bg-[#d4af37]/20 border-[#d4af37]/50 text-[#f3d87b] font-bold'
                          : 'bg-[#080a0e] border-[#1c2331] text-[#8e9bb0] hover:text-white'
                      }`}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Source Memories Picker */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-[11px] text-[#6d7c92] uppercase font-bold tracking-wider">
                    Source Evidence ({bioSelectedMemoryIds.length}/{personMemories.length})
                  </label>
                  <button
                    onClick={() =>
                      setBioSelectedMemoryIds(
                        bioSelectedMemoryIds.length === personMemories.length
                          ? []
                          : personMemories.map((m) => m.id)
                      )
                    }
                    className="text-[11px] text-[#d4af37] hover:underline"
                  >
                    {bioSelectedMemoryIds.length === personMemories.length ? 'Clear all' : 'Select all'}
                  </button>
                </div>

                <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1 border border-[#1a2130] p-2 rounded-xl bg-[#080a0e]">
                  {isLoadingMemories ? (
                    <p className="text-xs text-[#6d7c92] italic p-2 text-center">Loading memories...</p>
                  ) : personMemories.length === 0 ? (
                    <p className="text-xs text-[#6d7c92] italic p-2 text-center">
                      No memories linked to this person yet.
                    </p>
                  ) : (
                    personMemories.map((m) => {
                      const checked = bioSelectedMemoryIds.includes(m.id);
                      return (
                        <label
                          key={m.id}
                          className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-[#131924] cursor-pointer text-xs"
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setBioSelectedMemoryIds((prev) => [...prev, m.id]);
                              } else {
                                setBioSelectedMemoryIds((prev) => prev.filter((id) => id !== m.id));
                              }
                            }}
                            className="rounded border-[#263349] text-[#d4af37] focus:ring-0"
                          />
                          <span className="truncate text-white" title={m.title}>
                            {m.title}
                          </span>
                        </label>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Generate Button */}
              <button
                onClick={handleGenerateBiography}
                disabled={isGeneratingBio || !isOnline || !selectedPersonId}
                className="w-full py-2.5 rounded-xl font-bold text-xs bg-gradient-to-r from-[#d4af37] to-[#aa8214] text-black shadow-lg shadow-[#d4af37]/15 hover:opacity-95 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isGeneratingBio ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Generating Grounded Biography...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Generate Grounded Biography
                  </>
                )}
              </button>

              {bioError && (
                <div className="p-3 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs">
                  {bioError}
                </div>
              )}
            </div>

            {/* History List */}
            {bioHistory.length > 0 && (
              <div className="p-4 rounded-2xl bg-[#0d1017] border border-[#202738] space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#6d7c92]">
                  Biography Versions ({bioHistory.length})
                </h4>
                <div className="space-y-1.5">
                  {bioHistory.map((bio) => (
                    <div
                      key={bio.id}
                      onClick={() => {
                        setCurrentBio(bio);
                        setEditableBioContent(bio.content);
                        setIsEditingBio(false);
                      }}
                      className={`p-2.5 rounded-xl border text-xs cursor-pointer flex items-center justify-between transition-all ${
                        currentBio?.id === bio.id
                          ? 'bg-[#d4af37]/15 border-[#d4af37]/40 text-white'
                          : 'bg-[#080a0e] border-[#1a202c] text-[#8e9bb0] hover:text-white'
                      }`}
                    >
                      <div className="truncate pr-2">
                        <p className="font-semibold truncate">{bio.title}</p>
                        <p className="text-[10px] text-[#6d7c92]">
                          {new Date(bio.created_at).toLocaleDateString()} • {bio.approval_status}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteBio(bio.id);
                        }}
                        className="text-[#6d7c92] hover:text-red-400 p-1"
                        title="Delete this biography"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Results & Editor Column */}
          <div className="lg:col-span-2 space-y-5">
            {currentBio ? (
              <div className="p-6 rounded-3xl bg-[#0f131c] border border-[#202738] space-y-5 shadow-xl">
                {/* Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#1b2230]">
                  <div>
                    <h2 className="text-xl font-serif font-bold text-white">{currentBio.title}</h2>
                    <p className="text-xs text-[#8e9bb0] mt-0.5">
                      Subject: <strong className="text-[#f3d87b]">{selectedPerson?.full_name}</strong> • Language:{' '}
                      <span className="uppercase">{currentBio.language}</span> • Tone:{' '}
                      <span className="capitalize">{currentBio.tone}</span>
                    </p>
                  </div>

                  {/* Status Badge */}
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 ${
                        currentBio.approval_status === 'approved'
                          ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40'
                          : currentBio.approval_status === 'rejected'
                          ? 'bg-red-950/60 text-red-300 border border-red-500/40'
                          : 'bg-amber-950/60 text-amber-300 border border-amber-500/40'
                      }`}
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-current" />
                      {currentBio.approval_status === 'approved'
                        ? 'Approved & Preserved'
                        : currentBio.approval_status === 'rejected'
                        ? 'Draft Rejected'
                        : 'Pending User Review'}
                    </span>

                    <button
                      onClick={() => setIsEditingBio(!isEditingBio)}
                      className="p-2 rounded-xl bg-[#161c28] hover:bg-[#1d2535] text-[#d4af37] border border-[#d4af37]/30 text-xs flex items-center gap-1"
                    >
                      <Edit3 className="w-3.5 h-3.5" />
                      {isEditingBio ? 'Done Editing' : 'Edit Text'}
                    </button>
                  </div>
                </div>

                {/* Warning if insufficient evidence */}
                {currentBio.warning && (
                  <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-500/30 text-amber-300 text-xs flex items-center gap-2">
                    <AlertCircle className="w-4 h-4 shrink-0" />
                    <span>{currentBio.warning}</span>
                  </div>
                )}

                {/* Content Box */}
                {isEditingBio ? (
                  <div className="space-y-3">
                    <label className="text-xs text-[#6d7c92] uppercase font-bold">
                      Edit Narrative Before Approval:
                    </label>
                    <textarea
                      value={editableBioContent}
                      onChange={(e) => setEditableBioContent(e.target.value)}
                      rows={12}
                      className="w-full p-4 rounded-xl bg-[#080a0e] border border-[#232b3c] text-white text-sm font-serif leading-relaxed focus:outline-none focus:border-[#d4af37]/50"
                    />
                  </div>
                ) : (
                  <div className="prose prose-invert max-w-none text-sm text-[#e0e5ed] font-serif leading-relaxed whitespace-pre-wrap p-5 rounded-2xl bg-[#080a0e]/60 border border-[#181d26]">
                    {currentBio.content}
                  </div>
                )}

                {/* Structured Sections Badges */}
                {currentBio.sections && currentBio.sections.length > 0 && (
                  <div className="space-y-3 pt-3 border-t border-[#1a202c]">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[#6d7c92]">
                      Structured Section Evidence Classification
                    </h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                      {currentBio.sections.map((sec) => (
                        <div
                          key={sec.section_id}
                          className="p-3 rounded-xl bg-[#0b0e14] border border-[#1b2230] text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-white">{sec.section_title}</span>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                sec.evidence_classification === 'documented_fact'
                                  ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40'
                                  : sec.evidence_classification === 'unknown'
                                  ? 'bg-[#182030] text-[#8e9bb0]'
                                  : 'bg-amber-950/60 text-amber-300'
                              }`}
                            >
                              {sec.evidence_classification.replace('_', ' ')}
                            </span>
                          </div>
                          <p className="text-[11px] text-[#8e9bb0] line-clamp-2">{sec.narrative}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Supporting Evidence Chips */}
                {currentBio.source_memories && currentBio.source_memories.length > 0 && (
                  <div className="space-y-2 pt-3 border-t border-[#1a202c]">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[#6d7c92]">
                      Supporting Archival Sources ({currentBio.source_memories.length})
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {currentBio.source_memories.map((src) => (
                        <button
                          key={src.memory_id}
                          onClick={() => handleOpenSourceMemory(src)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#141a24] hover:bg-[#1c2433] text-xs text-[#f3d87b] border border-[#2a3449] transition-all group"
                          title="Click to inspect original memory"
                        >
                          <FileText className="w-3.5 h-3.5 text-[#d4af37]" />
                          <span className="font-medium truncate max-w-[160px]">{src.title}</span>
                          <ExternalLink className="w-3 h-3 text-[#6d7c92] group-hover:text-white" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* User Approval Action Row */}
                <div className="pt-4 border-t border-[#1a202c] flex items-center justify-end gap-3">
                  <button
                    onClick={() => handleSaveBioApproval('rejected')}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-red-400 hover:bg-red-950/30 border border-red-500/30 transition-all"
                  >
                    Mark as Rejected
                  </button>
                  <button
                    onClick={() => handleSaveBioApproval('approved')}
                    className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/40 transition-all flex items-center gap-2"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Approve & Preserve Biography
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-12 rounded-3xl bg-[#0f131c] border border-dashed border-[#202738] text-center space-y-3">
                <BookOpen className="w-10 h-10 text-[#6d7c92] mx-auto opacity-50" />
                <h3 className="text-base font-serif font-bold text-white">No Biography Generated Yet</h3>
                <p className="text-xs text-[#8e9bb0] max-w-md mx-auto">
                  Select parameters on the left and click "Generate Grounded Biography" to produce a verified life summary based strictly on preserved memories.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =====================================================================
          TAB 2: MEMORY STORYTELLING
         ===================================================================== */}
      {activeTab === 'story' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Controls Column */}
          <div className="space-y-5">
            <div className="p-5 rounded-2xl bg-[#0d1017] border border-[#202738] space-y-4">
              <h3 className="text-sm font-serif font-bold text-white flex items-center gap-2">
                <Feather className="w-4 h-4 text-[#d4af37]" />
                Storytelling Parameters
              </h3>

              {/* Title */}
              <div>
                <label className="text-[11px] text-[#6d7c92] block mb-1 uppercase font-bold tracking-wider">
                  Story Title (Optional)
                </label>
                <input
                  type="text"
                  value={storyTitle}
                  onChange={(e) => setStoryTitle(e.target.value)}
                  placeholder={`A Story of ${selectedPerson?.full_name || 'Family'}`}
                  className="w-full p-2.5 rounded-xl bg-[#080a0e] border border-[#1c2331] text-xs text-white placeholder-[#4d596c] focus:outline-none focus:border-[#d4af37]/50"
                />
              </div>

              {/* Tone */}
              <div>
                <label className="text-[11px] text-[#6d7c92] block mb-1.5 uppercase font-bold tracking-wider">
                  Tone
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {(['warm', 'respectful', 'factual', 'reflective'] as const).map((tone) => (
                    <button
                      key={tone}
                      onClick={() => setStoryTone(tone)}
                      className={`py-1.5 text-xs rounded-lg border capitalize transition-all ${
                        storyTone === tone
                          ? 'bg-[#d4af37]/20 border-[#d4af37]/50 text-[#f3d87b] font-bold'
                          : 'bg-[#080a0e] border-[#1c2331] text-[#8e9bb0] hover:text-white'
                      }`}
                    >
                      {tone}
                    </button>
                  ))}
                </div>
              </div>

              {/* Language */}
              <div>
                <label className="text-[11px] text-[#6d7c92] block mb-1.5 uppercase font-bold tracking-wider">
                  Language
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'en', label: 'English' },
                    { id: 'hi', label: 'Hindi (हिंदी)' }
                  ].map((l) => (
                    <button
                      key={l.id}
                      onClick={() => setStoryLang(l.id as any)}
                      className={`py-1.5 text-xs rounded-lg border transition-all ${
                        storyLang === l.id
                          ? 'bg-[#d4af37]/20 border-[#d4af37]/50 text-[#f3d87b] font-bold'
                          : 'bg-[#080a0e] border-[#1c2331] text-[#8e9bb0] hover:text-white'
                      }`}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Selected Memories */}
              <div>
                <label className="text-[11px] text-[#6d7c92] block mb-1.5 uppercase font-bold tracking-wider">
                  Select Memories to Weave ({storySelectedMemoryIds.length} selected)
                </label>
                <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1 border border-[#1a2130] p-2 rounded-xl bg-[#080a0e]">
                  {isLoadingMemories ? (
                    <p className="text-xs text-[#6d7c92] italic p-2 text-center">Loading memories...</p>
                  ) : personMemories.length === 0 ? (
                    <p className="text-xs text-[#6d7c92] italic p-2 text-center">No memories linked to this person.</p>
                  ) : (
                    personMemories.map((m) => {
                      const checked = storySelectedMemoryIds.includes(m.id);
                      return (
                        <label
                          key={m.id}
                          className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-[#131924] cursor-pointer text-xs"
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setStorySelectedMemoryIds((prev) => [...prev, m.id]);
                              } else {
                                setStorySelectedMemoryIds((prev) => prev.filter((id) => id !== m.id));
                              }
                            }}
                            className="rounded border-[#263349] text-[#d4af37] focus:ring-0"
                          />
                          <span className="truncate text-white" title={m.title}>
                            {m.title}
                          </span>
                        </label>
                      );
                    })
                  )}
                </div>
              </div>

              {/* Generate Button */}
              <button
                onClick={handleGenerateStory}
                disabled={isGeneratingStory || !isOnline || storySelectedMemoryIds.length === 0}
                className="w-full py-2.5 rounded-xl font-bold text-xs bg-gradient-to-r from-[#d4af37] to-[#aa8214] text-black shadow-lg shadow-[#d4af37]/15 hover:opacity-95 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isGeneratingStory ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Weaving Memory Narrative...
                  </>
                ) : (
                  <>
                    <Feather className="w-4 h-4" />
                    Weave Authentic Story
                  </>
                )}
              </button>

              {storyError && (
                <div className="p-3 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs">
                  {storyError}
                </div>
              )}
            </div>

            {/* Stories History */}
            {storyHistory.length > 0 && (
              <div className="p-4 rounded-2xl bg-[#0d1017] border border-[#202738] space-y-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-[#6d7c92]">
                  Saved Stories ({storyHistory.length})
                </h4>
                <div className="space-y-1.5">
                  {storyHistory.map((s) => (
                    <div
                      key={s.id}
                      onClick={() => {
                        setCurrentStory(s);
                        setEditableStoryContent(s.content);
                        setIsEditingStory(false);
                      }}
                      className={`p-2.5 rounded-xl border text-xs cursor-pointer flex items-center justify-between transition-all ${
                        currentStory?.id === s.id
                          ? 'bg-[#d4af37]/15 border-[#d4af37]/40 text-white'
                          : 'bg-[#080a0e] border-[#1a202c] text-[#8e9bb0] hover:text-white'
                      }`}
                    >
                      <div className="truncate pr-2">
                        <p className="font-semibold truncate">{s.title}</p>
                        <p className="text-[10px] text-[#6d7c92]">
                          {new Date(s.created_at).toLocaleDateString()} • {s.approval_status}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteStory(s.id);
                        }}
                        className="text-[#6d7c92] hover:text-red-400 p-1"
                        title="Delete this story"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Results Column */}
          <div className="lg:col-span-2 space-y-5">
            {currentStory ? (
              <div className="p-6 rounded-3xl bg-[#0f131c] border border-[#202738] space-y-5 shadow-xl">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-[#1b2230]">
                  <div>
                    <h2 className="text-xl font-serif font-bold text-white">{currentStory.title}</h2>
                    <p className="text-xs text-[#8e9bb0] mt-0.5">
                      Tone: <span className="capitalize">{currentStory.tone}</span> • Language:{' '}
                      <span className="uppercase">{currentStory.language}</span> • Status:{' '}
                      <strong className="text-[#f3d87b]">{currentStory.approval_status}</strong>
                    </p>
                  </div>

                  <button
                    onClick={() => setIsEditingStory(!isEditingStory)}
                    className="p-2 rounded-xl bg-[#161c28] hover:bg-[#1d2535] text-[#d4af37] border border-[#d4af37]/30 text-xs flex items-center gap-1 shrink-0"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    {isEditingStory ? 'Done Editing' : 'Edit Story'}
                  </button>
                </div>

                {isEditingStory ? (
                  <textarea
                    value={editableStoryContent}
                    onChange={(e) => setEditableStoryContent(e.target.value)}
                    rows={12}
                    className="w-full p-4 rounded-xl bg-[#080a0e] border border-[#232b3c] text-white text-sm font-serif leading-relaxed focus:outline-none focus:border-[#d4af37]/50"
                  />
                ) : (
                  <div className="prose prose-invert max-w-none text-sm text-[#e0e5ed] font-serif leading-relaxed whitespace-pre-wrap p-5 rounded-2xl bg-[#080a0e]/60 border border-[#181d26]">
                    {currentStory.content}
                  </div>
                )}

                {/* Sources */}
                {currentStory.source_memories && currentStory.source_memories.length > 0 && (
                  <div className="space-y-2 pt-3 border-t border-[#1a202c]">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-[#6d7c92]">
                      Memories Grounding this Story ({currentStory.source_memories.length})
                    </h4>
                    <div className="flex flex-wrap gap-2">
                      {currentStory.source_memories.map((src) => (
                        <button
                          key={src.memory_id}
                          onClick={() => handleOpenSourceMemory(src)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#141a24] hover:bg-[#1c2433] text-xs text-[#f3d87b] border border-[#2a3449] transition-all group"
                        >
                          <FileText className="w-3.5 h-3.5 text-[#d4af37]" />
                          <span className="font-medium truncate max-w-[160px]">{src.title}</span>
                          <ExternalLink className="w-3 h-3 text-[#6d7c92] group-hover:text-white" />
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="pt-4 border-t border-[#1a202c] flex items-center justify-end gap-3">
                  <button
                    onClick={() => handleSaveStoryApproval('rejected')}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-red-400 hover:bg-red-950/30 border border-red-500/30 transition-all"
                  >
                    Mark Rejected
                  </button>
                  <button
                    onClick={() => handleSaveStoryApproval('approved')}
                    className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/40 transition-all flex items-center gap-2"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Approve & Preserve Story
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-12 rounded-3xl bg-[#0f131c] border border-dashed border-[#202738] text-center space-y-3">
                <Feather className="w-10 h-10 text-[#6d7c92] mx-auto opacity-50" />
                <h3 className="text-base font-serif font-bold text-white">No Story Created Yet</h3>
                <p className="text-xs text-[#8e9bb0] max-w-md mx-auto">
                  Select memories on the left and click "Weave Authentic Story" to weave a narrative connecting specific family moments.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =====================================================================
          TAB 3: LIFE TIMELINE
         ===================================================================== */}
      {activeTab === 'timeline' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-5 rounded-2xl bg-[#0d1017] border border-[#202738]">
            <div>
              <h3 className="text-base font-serif font-bold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-[#d4af37]" />
                Life Timeline for {selectedPerson?.full_name}
              </h3>
              <p className="text-xs text-[#8e9bb0]">
                Chronological milestones derived strictly from documented memories. Dates are never invented.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowAddEventModal(true)}
                className="px-3 py-2 rounded-xl text-xs font-semibold bg-[#161c28] hover:bg-[#1d2535] text-white border border-[#2a3449] flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Milestone
              </button>

              <button
                onClick={handleAutoGenerateTimeline}
                disabled={isGeneratingTimeline || !selectedPersonId}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-[#d4af37] to-[#aa8214] text-black shadow-lg shadow-[#d4af37]/15 hover:opacity-95 disabled:opacity-40 flex items-center gap-1.5"
              >
                {isGeneratingTimeline ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    Extracting...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    Auto-Extract from Memories
                  </>
                )}
              </button>
            </div>
          </div>

          {timelineError && (
            <div className="p-3 rounded-xl bg-red-950/40 border border-red-500/40 text-red-300 text-xs">
              {timelineError}
            </div>
          )}

          {/* Timeline Events List */}
          {timelineEvents.length === 0 ? (
            <div className="p-12 rounded-3xl bg-[#0f131c] border border-dashed border-[#202738] text-center space-y-3">
              <Clock className="w-10 h-10 text-[#6d7c92] mx-auto opacity-50" />
              <h3 className="text-base font-serif font-bold text-white">No Timeline Events Recorded</h3>
              <p className="text-xs text-[#8e9bb0] max-w-md mx-auto">
                Click "Auto-Extract from Memories" to automatically discover chronological milestones from photos, documents, and transcripts.
              </p>
            </div>
          ) : (
            <div className="relative border-l-2 border-[#1c2331] ml-4 sm:ml-6 pl-6 space-y-6">
              {timelineEvents.map((ev) => (
                <div key={ev.id} className="relative group">
                  {/* Timeline Node dot */}
                  <div
                    className={`absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-2 border-[#090b0f] ${
                      ev.verification_status === 'user_confirmed'
                        ? 'bg-emerald-400 ring-4 ring-emerald-950/50'
                        : 'bg-[#d4af37] ring-4 ring-[#d4af37]/20'
                    }`}
                  />

                  {/* Event Card */}
                  <div className="p-5 rounded-2xl bg-[#0f131c] border border-[#202738] hover:border-[#2a3449] transition-all space-y-3">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        {/* Date badge */}
                        <span className="px-2.5 py-1 rounded-lg bg-[#141a24] text-[#f3d87b] border border-[#2a3449] text-xs font-mono font-bold flex items-center gap-1.5">
                          <Calendar className="w-3 h-3 text-[#d4af37]" />
                          {ev.approximate_date || 'Date Unknown'}
                        </span>

                        {/* Date Confidence Pill */}
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            ev.date_confidence === 'exact'
                              ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40'
                              : ev.date_confidence === 'approximate'
                              ? 'bg-[#182030] text-[#f3d87b] border border-[#263349]'
                              : 'bg-zinc-800 text-zinc-400'
                          }`}
                        >
                          {ev.date_confidence}
                        </span>

                        {/* Verification Status Pill */}
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                            ev.verification_status === 'user_confirmed'
                              ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40'
                              : 'bg-amber-950/50 text-amber-300 border border-amber-500/30'
                          }`}
                        >
                          {ev.verification_status === 'user_confirmed' ? 'User Confirmed' : 'AI Suggested'}
                        </span>
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2">
                        {ev.verification_status !== 'user_confirmed' && (
                          <button
                            onClick={() => handleConfirmTimelineEvent(ev.id)}
                            className="px-2.5 py-1 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/50 text-emerald-300 border border-emerald-500/40 text-[11px] font-semibold flex items-center gap-1"
                          >
                            <Check className="w-3 h-3" />
                            Confirm
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteTimelineEvent(ev.id)}
                          className="p-1 rounded-lg text-[#6d7c92] hover:text-red-400 hover:bg-[#161c28]"
                          title="Remove milestone"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <h4 className="text-sm font-bold text-white">{ev.title}</h4>
                    <p className="text-xs text-[#9db0cc] leading-relaxed">{ev.description}</p>

                    {/* Source Memories */}
                    {ev.source_memories && ev.source_memories.length > 0 && (
                      <div className="pt-2 border-t border-[#1a202c] flex items-center gap-2 flex-wrap">
                        <span className="text-[10px] uppercase font-bold text-[#6d7c92]">Evidence:</span>
                        {ev.source_memories.map((src) => (
                          <button
                            key={src.memory_id}
                            onClick={() => handleOpenSourceMemory(src)}
                            className="text-[11px] text-[#f3d87b] hover:underline flex items-center gap-1"
                          >
                            <span>{src.title}</span>
                            <ExternalLink className="w-2.5 h-2.5 text-[#6d7c92]" />
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Add Milestone Modal */}
          <Dialog open={showAddEventModal} onOpenChange={setShowAddEventModal}>
            <DialogContent className="p-6 rounded-3xl bg-[#0f131c] border border-[#202738] max-w-md w-full space-y-4 text-white">
              <DialogHeader className="flex flex-row items-center justify-between">
                <div>
                  <DialogTitle className="text-base font-serif font-bold text-white">Add Life Milestone</DialogTitle>
                  <DialogDescription className="text-xs text-[#6d7c92]">
                    Record an authenticated milestone on this person's timeline.
                  </DialogDescription>
                </div>
              </DialogHeader>

              <div className="space-y-3">
                <div>
                  <label className="text-[11px] text-[#6d7c92] block mb-1">Event Title *</label>
                  <input
                    type="text"
                    value={newEventTitle}
                    onChange={(e) => setNewEventTitle(e.target.value)}
                    placeholder="e.g., Graduation from University"
                    className="w-full p-2.5 rounded-xl bg-[#080a0e] border border-[#1c2331] text-xs text-white"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] text-[#6d7c92] block mb-1">Exact Date (Optional)</label>
                    <input
                      type="date"
                      value={newEventDate}
                      onChange={(e) => setNewEventDate(e.target.value)}
                      className="w-full p-2.5 rounded-xl bg-[#080a0e] border border-[#1c2331] text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] text-[#6d7c92] block mb-1">Approximate Date</label>
                    <input
                      type="text"
                      value={newEventApproxDate}
                      onChange={(e) => setNewEventApproxDate(e.target.value)}
                      placeholder="e.g., Summer 1968"
                      className="w-full p-2.5 rounded-xl bg-[#080a0e] border border-[#1c2331] text-xs text-white"
                    />
                  </div>
                </div>

                <div>
                  <label className="text-[11px] text-[#6d7c92] block mb-1">Date Confidence</label>
                  <select
                    value={newEventConfidence}
                    onChange={(e) => setNewEventConfidence(e.target.value as any)}
                    className="w-full p-2.5 rounded-xl bg-[#080a0e] border border-[#1c2331] text-xs text-white"
                  >
                    <option value="exact">Exact</option>
                    <option value="approximate">Approximate</option>
                    <option value="unknown">Unknown</option>
                  </select>
                </div>

                <div>
                  <label className="text-[11px] text-[#6d7c92] block mb-1">Description</label>
                  <textarea
                    value={newEventDesc}
                    onChange={(e) => setNewEventDesc(e.target.value)}
                    rows={3}
                    placeholder="Brief description of this milestone..."
                    className="w-full p-2.5 rounded-xl bg-[#080a0e] border border-[#1c2331] text-xs text-white"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  onClick={() => setShowAddEventModal(false)}
                  className="px-4 py-2 rounded-xl text-xs text-[#8e9bb0] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAddManualEvent}
                  className="px-5 py-2 rounded-xl text-xs font-bold bg-[#d4af37] text-black hover:bg-[#e6c250] transition-colors"
                >
                  Save Milestone
                </button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      )}

      {/* =====================================================================
          TAB 4: REMEMBRANCE PAGE
         ===================================================================== */}
      {activeTab === 'remembrance' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-5 rounded-2xl bg-[#0d1017] border border-[#202738]">
            <div>
              <h3 className="text-base font-serif font-bold text-white flex items-center gap-2">
                <Heart className="w-4 h-4 text-[#d4af37]" />
                Private Remembrance Page
              </h3>
              <p className="text-xs text-[#8e9bb0]">
                A private, local memorial tribute page for {selectedPerson?.full_name}. Never shared to cloud or remote servers.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handlePrintRemembrance}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#161c28] hover:bg-[#1d2535] text-[#d4af37] border border-[#d4af37]/30 flex items-center gap-1.5"
              >
                <Printer className="w-3.5 h-3.5" />
                Print / Save PDF
              </button>
              <button
                onClick={handleSaveRemembrance}
                disabled={isSavingRemembrance}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-[#d4af37] to-[#aa8214] text-black shadow-lg shadow-[#d4af37]/15 hover:opacity-95"
              >
                {isSavingRemembrance ? 'Saving...' : 'Save Notes'}
              </button>
            </div>
          </div>

          {/* Printable Memorial Container */}
          <div
            id="remembrance-printable-card"
            className="p-8 sm:p-12 rounded-3xl bg-[#090b10] border border-[#d4af37]/30 shadow-2xl space-y-8 print:p-0 print:border-none print:bg-white print:text-black"
          >
            {/* Header: Photo + Name */}
            <div className="flex flex-col sm:flex-row items-center gap-6 pb-8 border-b border-[#1c2331] print:border-black/20">
              {remembrancePage?.featured_photograph ? (
                <img
                  src={`/api/memories/${remembrancePage.featured_photograph.id}/file`}
                  alt={selectedPerson?.full_name}
                  className="w-28 h-28 sm:w-36 sm:h-36 rounded-2xl object-cover border-2 border-[#d4af37] shadow-xl"
                />
              ) : (
                <div className="w-28 h-28 sm:w-36 sm:h-36 rounded-2xl bg-[#141a24] border border-[#2a3449] flex items-center justify-center text-3xl font-serif font-bold text-[#d4af37]">
                  {selectedPerson?.full_name.charAt(0)}
                </div>
              )}

              <div className="text-center sm:text-left space-y-1">
                <span className="text-[10px] uppercase font-bold tracking-widest text-[#d4af37]">In Loving Remembrance</span>
                <h2 className="text-3xl sm:text-4xl font-serif font-bold text-white print:text-black">
                  {selectedPerson?.full_name}
                </h2>
                <p className="text-sm text-[#8e9bb0] print:text-gray-700">
                  {selectedPerson?.relationship || 'Family Member'} • Preserved Legacy Archive
                </p>
                <div className="pt-2 flex items-center gap-2 justify-center sm:justify-start">
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-950/60 text-emerald-300 border border-emerald-500/40">
                    Private & Offline Vault
                  </span>
                </div>
              </div>
            </div>

            {/* Biography Section */}
            {remembrancePage?.biography ? (
              <div className="space-y-3">
                <h3 className="text-lg font-serif font-bold text-[#f3d87b] print:text-black border-b border-[#1c2331] pb-2">
                  Life & Legacy
                </h3>
                <div className="text-sm font-serif leading-relaxed text-[#d0d7e3] print:text-black whitespace-pre-wrap">
                  {remembrancePage.biography.content}
                </div>
              </div>
            ) : currentBio ? (
              <div className="space-y-3">
                <h3 className="text-lg font-serif font-bold text-[#f3d87b] print:text-black border-b border-[#1c2331] pb-2">
                  Life & Legacy
                </h3>
                <div className="text-sm font-serif leading-relaxed text-[#d0d7e3] print:text-black whitespace-pre-wrap">
                  {currentBio.content}
                </div>
              </div>
            ) : null}

            {/* Personal Notes / Family Tribute */}
            <div className="space-y-3">
              <h3 className="text-lg font-serif font-bold text-[#f3d87b] print:text-black border-b border-[#1c2331] pb-2">
                Personal Reflections from the Family
              </h3>
              <textarea
                value={remembranceNotes}
                onChange={(e) => setRemembranceNotes(e.target.value)}
                placeholder="Write personal memories, eulogies, or words of remembrance here..."
                rows={4}
                className="w-full p-4 rounded-xl bg-[#040608] border border-[#1e2636] text-white print:hidden text-xs font-serif leading-relaxed focus:outline-none focus:border-[#d4af37]/50"
              />
              {remembranceNotes && (
                <div className="hidden print:block text-xs font-serif leading-relaxed text-black whitespace-pre-wrap">
                  {remembranceNotes}
                </div>
              )}
            </div>

            {/* Timeline Highlights */}
            {timelineEvents.length > 0 && (
              <div className="space-y-4">
                <h3 className="text-lg font-serif font-bold text-[#f3d87b] print:text-black border-b border-[#1c2331] pb-2">
                  Key Milestones
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {timelineEvents.slice(0, 6).map((ev) => (
                    <div
                      key={ev.id}
                      className="p-3.5 rounded-xl bg-[#0e121a] border border-[#1b2230] print:border-black/20 text-xs space-y-1"
                    >
                      <span className="font-mono text-[#d4af37] print:text-black font-bold">
                        {ev.approximate_date || 'Date Unknown'}
                      </span>
                      <p className="font-semibold text-white print:text-black">{ev.title}</p>
                      <p className="text-[11px] text-[#8e9bb0] print:text-gray-700">{ev.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =====================================================================
          TAB 5: MEMORY COLLECTIONS
         ===================================================================== */}
      {activeTab === 'collections' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Collections List */}
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-2xl bg-[#0d1017] border border-[#202738]">
              <h3 className="text-sm font-serif font-bold text-white flex items-center gap-2">
                <FolderHeart className="w-4 h-4 text-[#d4af37]" />
                Collections ({collections.length})
              </h3>
              <button
                onClick={() => setIsCreatingCollection(true)}
                className="px-3 py-1.5 rounded-xl text-xs font-bold bg-[#d4af37] text-black flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                New
              </button>
            </div>

            {/* Create Collection Form */}
            {isCreatingCollection && (
              <div className="p-4 rounded-2xl bg-[#0f131c] border border-[#d4af37]/30 space-y-3">
                <h4 className="text-xs font-bold text-white">Create Thematic Collection</h4>
                <input
                  type="text"
                  value={newColTitle}
                  onChange={(e) => setNewColTitle(e.target.value)}
                  placeholder="Collection Title (e.g. Childhood)"
                  className="w-full p-2.5 rounded-xl bg-[#080a0e] border border-[#1c2331] text-xs text-white"
                />
                <select
                  value={newColType}
                  onChange={(e) => setNewColType(e.target.value as any)}
                  className="w-full p-2 rounded-xl bg-[#080a0e] border border-[#1c2331] text-xs text-white"
                >
                  <option value="childhood">Childhood Memories</option>
                  <option value="family">Family Moments</option>
                  <option value="education">Education</option>
                  <option value="career">Career</option>
                  <option value="celebrations">Celebrations</option>
                  <option value="travel">Travel</option>
                  <option value="milestones">Important Milestones</option>
                  <option value="custom">Custom Collection</option>
                </select>
                <textarea
                  value={newColDesc}
                  onChange={(e) => setNewColDesc(e.target.value)}
                  placeholder="Description..."
                  rows={2}
                  className="w-full p-2 rounded-xl bg-[#080a0e] border border-[#1c2331] text-xs text-white"
                />
                <div className="flex justify-end gap-2">
                  <button
                    onClick={() => setIsCreatingCollection(false)}
                    className="px-3 py-1 text-xs text-[#8e9bb0]"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleCreateCollection}
                    className="px-4 py-1.5 rounded-xl text-xs font-bold bg-[#d4af37] text-black"
                  >
                    Create
                  </button>
                </div>
              </div>
            )}

            {/* Collections Cards */}
            <div className="space-y-2">
              {collections.map((col) => (
                <div
                  key={col.id}
                  onClick={() => setActiveCollection(col)}
                  className={`p-3.5 rounded-2xl border cursor-pointer transition-all flex items-center justify-between ${
                    activeCollection?.id === col.id
                      ? 'bg-[#d4af37]/15 border-[#d4af37]/40 text-white'
                      : 'bg-[#0b0e14] border-[#1b2230] text-[#8e9bb0] hover:text-white'
                  }`}
                >
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#d4af37] tracking-wider">
                      {col.collection_type}
                    </span>
                    <h4 className="text-xs font-bold text-white">{col.title}</h4>
                    <p className="text-[11px] text-[#6d7c92]">
                      {col.memories_count} {col.memories_count === 1 ? 'memory' : 'memories'}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteCollection(col.id);
                    }}
                    className="p-1.5 text-[#6d7c92] hover:text-red-400"
                    title="Delete collection"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Collection Details & Items */}
          <div className="lg:col-span-2 space-y-4">
            {activeCollection ? (
              <div className="p-6 rounded-3xl bg-[#0f131c] border border-[#202738] space-y-5">
                <div className="flex items-center justify-between pb-3 border-b border-[#1b2230]">
                  <div>
                    <span className="text-[10px] uppercase font-bold text-[#d4af37] tracking-wider">
                      {activeCollection.collection_type}
                    </span>
                    <h3 className="text-xl font-serif font-bold text-white">{activeCollection.title}</h3>
                    {activeCollection.description && (
                      <p className="text-xs text-[#8e9bb0] mt-0.5">{activeCollection.description}</p>
                    )}
                  </div>
                </div>

                {/* Items in collection */}
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[#6d7c92]">
                    Memories in this Collection ({activeCollection.memories.length})
                  </h4>

                  {activeCollection.memories.length === 0 ? (
                    <p className="text-xs text-[#6d7c92] italic p-6 text-center bg-[#080a0e] rounded-2xl border border-[#1a202c]">
                      No memories added to this collection yet. Select from the available memories below.
                    </p>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {activeCollection.memories.map((m) => (
                        <div
                          key={m.id}
                          className="p-3 rounded-xl bg-[#080a0e] border border-[#1c2331] flex items-center justify-between"
                        >
                          <div className="truncate pr-2">
                            <p className="text-xs font-bold text-white truncate">{m.title}</p>
                            <p className="text-[10px] text-[#6d7c92] uppercase">{m.memory_type}</p>
                          </div>
                          <button
                            onClick={() => handleRemoveMemoryFromCollection(m.id)}
                            className="text-[#6d7c92] hover:text-red-400 p-1"
                            title="Remove from collection"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Add memory to collection */}
                <div className="pt-4 border-t border-[#1a202c] space-y-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-[#6d7c92]">
                    Add Person Memories to Collection
                  </h4>
                  <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto pr-1">
                    {personMemories
                      .filter((m) => !activeCollection.memories.some((cm) => cm.id === m.id))
                      .map((m) => (
                        <button
                          key={m.id}
                          onClick={() => handleAddMemoryToCollection(m.id)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#141a24] hover:bg-[#1f2838] text-xs text-white border border-[#263349]"
                        >
                          <Plus className="w-3 h-3 text-[#d4af37]" />
                          <span className="truncate max-w-[150px]">{m.title}</span>
                        </button>
                      ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-12 rounded-3xl bg-[#0f131c] border border-dashed border-[#202738] text-center space-y-3">
                <FolderHeart className="w-10 h-10 text-[#6d7c92] mx-auto opacity-50" />
                <h3 className="text-base font-serif font-bold text-white">Select or Create a Collection</h3>
                <p className="text-xs text-[#8e9bb0]">
                  Group photographs, letters, and recordings thematically into curated milestone albums.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =====================================================================
          TAB 6: LOCAL AI ENGINE & STATUS
         ===================================================================== */}
      {activeTab === 'engine' && (
        <div className="space-y-6">
          {/* Main Status Hero Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738]">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`p-2.5 rounded-xl border ${
                      isOnline
                        ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-400'
                        : 'bg-amber-950/40 border-amber-500/40 text-amber-400'
                    }`}
                  >
                    <Server className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-serif font-bold text-white">Ollama Local Daemon</h3>
                    <p className="text-xs text-[#8e9bb0]">
                      Endpoint:{' '}
                      <span className="font-mono text-white">
                        {aiStatus?.base_url || 'http://127.0.0.1:11434'}
                      </span>
                    </p>
                  </div>
                </div>

                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 ${
                    isOnline
                      ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40'
                      : 'bg-amber-950/50 text-amber-300 border border-amber-500/40'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
                  {isOnline ? 'Online' : 'Offline / Standby'}
                </span>
              </div>

              <p className="text-xs text-[#9db0cc] leading-relaxed">
                {aiStatus?.message || 'Detecting Ollama background process on localhost...'}
              </p>

              <div className="mt-4 pt-4 border-t border-[#1a202c] text-xs text-[#6d7c92] flex items-center justify-between">
                <span>Inference Network: Loopback (127.0.0.1)</span>
                <span className="text-emerald-400 flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Airgap Capable
                </span>
              </div>
            </div>

            <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738]">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl border bg-emerald-950/40 border-emerald-500/40 text-emerald-400">
                    <Cpu className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-base font-serif font-bold text-white">Configured Model</h3>
                    <p className="text-xs font-mono text-[#f3d87b]">
                      {aiStatus?.configured_model || 'qwen2.5:3b'}
                    </p>
                  </div>
                </div>

                <span
                  className={`px-3 py-1 rounded-full text-xs font-semibold ${
                    aiStatus?.model_available
                      ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-500/40'
                      : 'bg-[#182030] text-[#8e9bb0] border border-[#263349]'
                  }`}
                >
                  {aiStatus?.model_available ? 'Installed & Ready' : 'Not Pulled'}
                </span>
              </div>

              <p className="text-xs text-[#9db0cc] leading-relaxed">
                Qwen2.5 3B Instruct provides high emotional resonance, factual grounding, and fits comfortably within 12 GB RAM on integrated graphics.
              </p>

              <div className="mt-4 pt-4 border-t border-[#1a202c] text-xs text-[#6d7c92] flex items-center justify-between">
                <span>License: Apache 2.0 Open-Weight</span>
                <span className="text-[#f3d87b]">3 Billion Parameters</span>
              </div>
            </div>
          </div>

          {/* Detected Models List */}
          {modelsData && modelsData.models && modelsData.models.length > 0 && (
            <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738]">
              <h4 className="text-sm font-serif font-bold text-white mb-3">
                Detected Ollama Models ({modelsData.count})
              </h4>
              <div className="flex flex-wrap gap-2">
                {modelsData.models.map((m) => (
                  <span
                    key={m.name}
                    className="px-3 py-1.5 rounded-xl bg-[#080a0e] border border-[#232b3c] text-xs font-mono text-[#f3d87b]"
                  >
                    {m.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Setup Guide */}
          <div className="p-7 rounded-3xl bg-[#0d1017] border border-[#d4af37]/25 shadow-xl space-y-6">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
                <Terminal className="w-5 h-5" />
              </div>
              <div>
                <h2 className="text-lg font-serif font-bold text-white">Local AI Engine Setup Guide</h2>
                <p className="text-xs text-[#8e9bb0]">
                  Follow these steps to activate private local memory rediscovery.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="p-5 rounded-2xl bg-[#080a0e] border border-[#1b2230] space-y-3">
                <span className="w-6 h-6 rounded-full bg-[#d4af37]/20 border border-[#d4af37]/40 text-[#d4af37] text-xs font-bold flex items-center justify-center">
                  1
                </span>
                <h4 className="text-sm font-semibold text-white">Install Ollama</h4>
                <p className="text-xs text-[#8e9bb0] font-light leading-relaxed">
                  Download the official runtime from{' '}
                  <a href="https://ollama.ai" target="_blank" rel="noreferrer" className="text-[#d4af37] underline">
                    ollama.ai
                  </a>
                  .
                </p>
              </div>

              <div className="p-5 rounded-2xl bg-[#080a0e] border border-[#1b2230] space-y-3">
                <span className="w-6 h-6 rounded-full bg-[#d4af37]/20 border border-[#d4af37]/40 text-[#d4af37] text-xs font-bold flex items-center justify-center">
                  2
                </span>
                <h4 className="text-sm font-semibold text-white">Start the Service</h4>
                <div
                  onClick={() => copyToClipboard('ollama serve', 'step2')}
                  className="cursor-pointer group flex items-center justify-between p-2.5 rounded-lg bg-[#040608] border border-[#232b3c] font-mono text-[11px] text-[#f3d87b]"
                >
                  <span>ollama serve</span>
                  <span className="text-[10px] text-[#6d7c92] group-hover:text-white">
                    {copiedCmd === 'step2' ? 'Copied!' : 'Copy'}
                  </span>
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-[#080a0e] border border-[#1b2230] space-y-3">
                <span className="w-6 h-6 rounded-full bg-[#d4af37]/20 border border-[#d4af37]/40 text-[#d4af37] text-xs font-bold flex items-center justify-center">
                  3
                </span>
                <h4 className="text-sm font-semibold text-white">Pull Qwen2.5 3B</h4>
                <div
                  onClick={() => copyToClipboard('ollama pull qwen2.5:3b', 'step3')}
                  className="cursor-pointer group flex items-center justify-between p-2.5 rounded-lg bg-[#040608] border border-[#232b3c] font-mono text-[11px] text-[#f3d87b]"
                >
                  <span>ollama pull qwen2.5:3b</span>
                  <span className="text-[10px] text-[#6d7c92] group-hover:text-white">
                    {copiedCmd === 'step3' ? 'Copied!' : 'Copy'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
