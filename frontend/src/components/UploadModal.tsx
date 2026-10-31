import { useState, useEffect, useRef } from 'react';
import { X, Upload, AlertCircle, MapPin, Tag as TagIcon, Users, Calendar, Shield, FileCheck } from 'lucide-react';
import type { Person, Tag } from '../types';
import { api, ApiError } from '../services/api';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  people: Person[];
}

export const UploadModal = ({
  isOpen,
  onClose,
  onSuccess,
  people,
}: UploadModalProps) => {
  const [files, setFiles] = useState<File[]>([]);
  const [title, setTitle] = useState('');
  const [memoryType, setMemoryType] = useState<'photograph' | 'audio' | 'document' | 'story' | 'video'>('photograph');
  const [description, setDescription] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [location, setLocation] = useState('');
  const [privacyLevel, setPrivacyLevel] = useState('private');
  const [selectedPeople, setSelectedPeople] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [availableTags, setAvailableTags] = useState<Tag[]>([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      loadTags();
    }
  }, [isOpen]);

  const loadTags = async () => {
    try {
      const data = await api.getTags();
      setAvailableTags(data);
    } catch (err) {
      console.warn('Could not load tags', err);
    }
  };

  if (!isOpen) return null;

  const handleFilesSelected = (newFiles: FileList | null) => {
    if (!newFiles || newFiles.length === 0) return;
    const validList: File[] = [];
    const maxBytes = 100 * 1024 * 1024; // 100 MB

    for (let i = 0; i < newFiles.length; i++) {
      const f = newFiles[i];
      if (f.size > maxBytes) {
        setErrorMessage(`File "${f.name}" exceeds the 100 MB limit.`);
        return;
      }
      validList.push(f);
    }

    setFiles(validList);
    setErrorMessage(null);

    const first = validList[0];
    if (first) {
      const cleanName = first.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
      setTitle(cleanName.charAt(0).toUpperCase() + cleanName.slice(1));

      // Auto-detect memory type from file extension & MIME
      const ext = first.name.split('.').pop()?.toLowerCase() || '';
      if (['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(ext) || first.type.startsWith('image/')) {
        setMemoryType('photograph');
      } else if (['mp3', 'wav', 'm4a', 'ogg', 'flac'].includes(ext) || first.type.startsWith('audio/')) {
        setMemoryType('audio');
      } else if (['mp4', 'mov', 'webm'].includes(ext) || first.type.startsWith('video/')) {
        setMemoryType('video');
      } else {
        setMemoryType('document');
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFilesSelected(e.dataTransfer.files);
  };

  const togglePerson = (id: string) => {
    setSelectedPeople((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const toggleTag = (tagName: string) => {
    const clean = tagName.toLowerCase().trim();
    setSelectedTags((prev) =>
      prev.includes(clean) ? prev.filter((t) => t !== clean) : [...prev, clean]
    );
  };

  const handleAddCustomTag = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const val = tagInput.trim().toLowerCase().replace(/^#/, '');
      if (val && !selectedTags.includes(val)) {
        setSelectedTags((prev) => [...prev, val]);
      }
      setTagInput('');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (files.length === 0) {
      setErrorMessage('Please select at least one file to preserve.');
      return;
    }
    if (!title.trim()) {
      setErrorMessage('Please provide a title for this memory.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      // Process each file
      for (let i = 0; i < files.length; i++) {
        const currentFile = files[i];
        setUploadProgress(
          files.length > 1
            ? `Preserving artifact ${i + 1} of ${files.length}: ${currentFile.name}...`
            : `Preserving ${currentFile.name}...`
        );

        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append(
          'title',
          files.length === 1
            ? title.trim()
            : `${title.trim()} (${i + 1})`
        );
        formData.append('memory_type', memoryType);
        if (description.trim()) formData.append('description', description.trim());
        if (eventDate.trim()) formData.append('event_date', eventDate.trim());
        if (location.trim()) formData.append('location', location.trim());
        formData.append('privacy_level', privacyLevel);
        if (selectedPeople.length > 0) formData.append('person_ids', selectedPeople.join(','));
        if (selectedTags.length > 0) formData.append('tags', selectedTags.join(','));

        await api.uploadMemory(formData);
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      if (err instanceof ApiError && err.status === 409) {
        setErrorMessage(
          err.message || 'Duplicate detected: A memory with identical content already exists in the vault.'
        );
      } else {
        setErrorMessage(err.message || 'Failed to preserve memory artifact.');
      }
    } finally {
      setIsSubmitting(false);
      setUploadProgress(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-2xl max-h-[92vh] overflow-y-auto rounded-2xl bg-[#0f121a] border border-[#d4af37]/35 shadow-2xl shadow-black p-6 sm:p-8">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#202738]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-serif font-bold text-white">Preserve Artifact</h2>
              <p className="text-xs text-[#8e9bb0]">
                Stored locally with SHA-256 verification, safe EXIF parsing, and offline privacy.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[#8e9bb0] hover:text-white hover:bg-[#1a202e] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMessage && (
          <div className="mt-4 p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/40 flex items-start gap-2.5 text-xs text-rose-200">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span className="flex-1">{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-5">
          {/* File Upload Drop Zone */}
          <div>
            <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-2">
              Memory Artifact (Photos, Audio, Video, Documents) *
            </label>
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all bg-[#0b0e14] ${
                isDragOver
                  ? 'border-[#d4af37] bg-[#d4af37]/5 scale-[0.99]'
                  : 'border-[#273145] hover:border-[#d4af37]/50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={(e) => handleFilesSelected(e.target.files)}
                accept=".jpg,.jpeg,.png,.webp,.gif,.mp3,.wav,.m4a,.ogg,.flac,.mp4,.webm,.mov,.pdf,.txt,.md,.docx"
                className="hidden"
              />
              {files.length > 0 ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-center gap-3 text-emerald-400">
                    <FileCheck className="w-7 h-7 shrink-0" />
                    <div className="text-left">
                      <p className="text-sm font-semibold text-white">
                        {files.length === 1 ? files[0].name : `${files.length} artifacts selected`}
                      </p>
                      <p className="text-xs text-[#8e9bb0]">
                        {files.length === 1
                          ? `${(files[0].size / 1024 / 1024).toFixed(2)} MB • ${files[0].type || 'Binary'}`
                          : `Total: ${(files.reduce((a, b) => a + b.size, 0) / 1024 / 1024).toFixed(2)} MB`}
                      </p>
                    </div>
                  </div>
                  <p className="text-[11px] text-[#6d7c92]">Click or drop to replace selected files</p>
                </div>
              ) : (
                <div className="space-y-1">
                  <Upload className="w-8 h-8 mx-auto text-[#d4af37]/70 mb-2" />
                  <p className="text-sm font-medium text-white">
                    Drag and drop files here, or <span className="text-[#d4af37] underline">browse</span>
                  </p>
                  <p className="text-[11px] text-[#6d7c92]">
                    JPG, PNG, WEBP, GIF, MP3, WAV, M4A, OGG, FLAC, MP4, WEBM, MOV, PDF, TXT, MD, DOCX (Max 100 MB)
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Title & Category Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1.5">
                Memory Title *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Grandma's 80th Birthday Speech"
                required
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b0e14] border border-[#232b3c] focus:border-[#d4af37] focus:outline-none text-white text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1.5">
                Category
              </label>
              <select
                value={memoryType}
                onChange={(e) => setMemoryType(e.target.value as any)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b0e14] border border-[#232b3c] focus:border-[#d4af37] focus:outline-none text-white text-sm cursor-pointer"
              >
                <option value="photograph">Photograph (Images)</option>
                <option value="audio">Audio / Oral History</option>
                <option value="video">Personal Video</option>
                <option value="document">Document / Letter / Note</option>
                <option value="story">Written Family Story</option>
              </select>
            </div>
          </div>

          {/* Event Date & Location */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-[#d4af37]" />
                Event Date (Optional)
              </label>
              <input
                type="date"
                value={eventDate}
                onChange={(e) => setEventDate(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b0e14] border border-[#232b3c] focus:border-[#d4af37] focus:outline-none text-white text-sm"
              />
              <span className="text-[10px] text-[#6d7c92] mt-1 block">
                If blank, EXIF capture date will be used when available.
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-[#d4af37]" />
                Location (Optional)
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Kyoto, Japan or Family Home"
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b0e14] border border-[#232b3c] focus:border-[#d4af37] focus:outline-none text-white text-sm"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1.5">
              Preservation Notes & Narrative (Optional)
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What makes this memory meaningful? Record the context, emotional nuance, or stories behind it..."
              className="w-full px-3.5 py-2.5 rounded-xl bg-[#0b0e14] border border-[#232b3c] focus:border-[#d4af37] focus:outline-none text-white text-sm leading-relaxed"
            />
          </div>

          {/* Associated People */}
          <div>
            <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-[#d4af37]" />
              Associated Family Members & Friends
            </label>
            {people.length === 0 ? (
              <p className="text-xs text-[#6d7c92] italic">
                No people added yet. You can create people profiles in the People tab.
              </p>
            ) : (
              <div className="flex flex-wrap gap-2 max-h-32 overflow-y-auto p-2 rounded-xl bg-[#0b0e14] border border-[#232b3c]">
                {people.map((p) => {
                  const isSelected = selectedPeople.includes(p.id);
                  return (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => togglePerson(p.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                        isSelected
                          ? 'bg-[#d4af37] text-black font-semibold shadow-sm'
                          : 'bg-[#141a24] text-[#8e9bb0] hover:text-white hover:bg-[#1a2332]'
                      }`}
                    >
                      {p.full_name} {p.relationship ? `(${p.relationship})` : ''}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Tags */}
          <div>
            <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <TagIcon className="w-3.5 h-3.5 text-[#d4af37]" />
              Tags & Themes
            </label>
            <div className="space-y-2">
              <div className="flex flex-wrap gap-1.5">
                {availableTags.map((t) => {
                  const isSelected = selectedTags.includes(t.name.toLowerCase());
                  return (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => toggleTag(t.name)}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                        isSelected
                          ? 'bg-[#d4af37]/25 text-[#f3d87b] border border-[#d4af37]'
                          : 'bg-[#111622] text-[#8e9bb0] border border-[#202838] hover:border-[#d4af37]/40'
                      }`}
                    >
                      #{t.name}
                    </button>
                  );
                })}
              </div>
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleAddCustomTag}
                placeholder="Type tag name and press Enter to add..."
                className="w-full px-3 py-1.5 rounded-lg bg-[#0b0e14] border border-[#232b3c] focus:border-[#d4af37] focus:outline-none text-white text-xs"
              />
              {selectedTags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1 text-xs text-[#d4af37]">
                  Selected: {selectedTags.map((t) => `#${t}`).join(', ')}
                </div>
              )}
            </div>
          </div>

          {/* Privacy Level */}
          <div className="pt-2 border-t border-[#1a202c] flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-[#8e9bb0]">
              <Shield className="w-4 h-4 text-emerald-400" />
              <span>Preserved offline strictly on this machine.</span>
            </div>
            <select
              value={privacyLevel}
              onChange={(e) => setPrivacyLevel(e.target.value)}
              className="px-3 py-1.5 rounded-lg bg-[#0b0e14] border border-[#232b3c] text-white text-xs"
            >
              <option value="private">Private (Restricted)</option>
              <option value="family">Family (Shared Vault)</option>
              <option value="public">Legacy Public</option>
            </select>
          </div>

          {/* Actions */}
          <div className="pt-4 border-t border-[#202738] flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-[#8e9bb0] hover:text-white bg-[#141924] hover:bg-[#1a202e] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 px-6 py-2.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-[#d4af37] to-[#e68a00] text-black shadow-lg shadow-[#d4af37]/20 hover:brightness-110 active:scale-98 transition-all disabled:opacity-50"
            >
              <Upload className="w-4 h-4 stroke-[2.4]" />
              {isSubmitting
                ? uploadProgress || 'Processing Ingestion...'
                : files.length > 1
                ? `Preserve ${files.length} Artifacts`
                : 'Preserve Memory'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
