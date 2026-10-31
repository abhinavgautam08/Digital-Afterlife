import { useState, useEffect } from 'react';
import { X, Tag as TagIcon, Plus, Trash2, Edit2, Check, AlertCircle } from 'lucide-react';
import type { Tag } from '../types';
import { api } from '../services/api';

interface TagManagerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTagsUpdated: () => void;
}

export const TagManagerModal = ({
  isOpen,
  onClose,
  onTagsUpdated,
}: TagManagerModalProps) => {
  const [tags, setTags] = useState<Tag[]>([]);
  const [newTagName, setNewTagName] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      loadTags();
    }
  }, [isOpen]);

  const loadTags = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getTags();
      setTags(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load tags.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTagName.trim()) return;
    setError(null);
    try {
      await api.createTag(newTagName.trim());
      setNewTagName('');
      await loadTags();
      onTagsUpdated();
    } catch (err: any) {
      setError(err.message || 'Failed to create tag.');
    }
  };

  const handleStartEdit = (tag: Tag) => {
    setEditingId(tag.id);
    setEditingName(tag.name);
  };

  const handleSaveEdit = async (id: string) => {
    if (!editingName.trim()) return;
    setError(null);
    try {
      await api.updateTag(id, editingName.trim());
      setEditingId(null);
      await loadTags();
      onTagsUpdated();
    } catch (err: any) {
      setError(err.message || 'Failed to update tag.');
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete tag "#${name}"? It will be unlinked from memories.`)) {
      return;
    }
    setError(null);
    try {
      await api.deleteTag(id);
      await loadTags();
      onTagsUpdated();
    } catch (err: any) {
      setError(err.message || 'Failed to delete tag.');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-lg rounded-2xl bg-[#0f121a] border border-[#d4af37]/35 shadow-2xl shadow-black p-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#202738]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
              <TagIcon className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-serif font-bold text-white">Manage Memory Tags</h2>
              <p className="text-xs text-[#8e9bb0]">
                Organize memories into meaningful family themes and life chapters.
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

        {error && (
          <div className="mt-4 p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 flex items-center gap-2 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Create Tag Form */}
        <form onSubmit={handleCreate} className="mt-4 flex gap-2">
          <input
            type="text"
            value={newTagName}
            onChange={(e) => setNewTagName(e.target.value)}
            placeholder="New tag name (e.g. Childhood, Letters, Travel)..."
            className="flex-1 px-3.5 py-2 rounded-xl bg-[#0b0e14] border border-[#232b3c] focus:border-[#d4af37] focus:outline-none text-white text-xs"
          />
          <button
            type="submit"
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b] transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Tag
          </button>
        </form>

        {/* Tags List */}
        <div className="mt-5 max-h-72 overflow-y-auto space-y-2 pr-1">
          {isLoading ? (
            <p className="text-center py-6 text-xs text-[#8e9bb0]">Loading tags...</p>
          ) : tags.length === 0 ? (
            <p className="text-center py-6 text-xs text-[#6d7c92]">No tags created yet.</p>
          ) : (
            tags.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between p-2.5 rounded-xl bg-[#0b0e14] border border-[#1b2230] text-xs hover:border-[#273347] transition-colors"
              >
                {editingId === t.id ? (
                  <div className="flex items-center gap-2 flex-1 mr-2">
                    <input
                      type="text"
                      value={editingName}
                      onChange={(e) => setEditingName(e.target.value)}
                      className="flex-1 px-2.5 py-1 rounded-lg bg-[#141a24] border border-[#d4af37] text-white text-xs focus:outline-none"
                      autoFocus
                    />
                    <button
                      onClick={() => handleSaveEdit(t.id)}
                      className="p-1 rounded text-emerald-400 hover:bg-emerald-950/40"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="p-1 rounded text-[#8e9bb0] hover:bg-[#1a202e]"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-white">#{t.name}</span>
                    {t.memories_count !== undefined && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] bg-[#1a2233] text-[#8e9bb0]">
                        {t.memories_count} {t.memories_count === 1 ? 'memory' : 'memories'}
                      </span>
                    )}
                  </div>
                )}

                {editingId !== t.id && (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleStartEdit(t)}
                      className="p-1.5 rounded-lg text-[#8e9bb0] hover:text-[#d4af37] hover:bg-[#161c28] transition-colors"
                      title="Rename tag"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(t.id, t.name)}
                      className="p-1.5 rounded-lg text-[#8e9bb0] hover:text-rose-400 hover:bg-rose-950/30 transition-colors"
                      title="Delete tag"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="mt-5 pt-3 border-t border-[#1a202c] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-[#8e9bb0] hover:text-white bg-[#141924] hover:bg-[#1a202e] transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};

