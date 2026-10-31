import { useState, useEffect } from 'react';
import { Tag as TagIcon, Plus, Trash2, Edit2, Check, AlertCircle } from 'lucide-react';
import type { Tag } from '../types';
import { api } from '../services/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from './ui/dialog';

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

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg bg-[#0f121a] border border-[#d4af37]/35 p-6 shadow-2xl">
        <DialogHeader className="pb-4 border-b border-[#202738]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
              <TagIcon className="w-5 h-5" />
            </div>
            <div>
              <DialogTitle className="text-lg font-serif font-bold text-white">
                Manage Memory Tags
              </DialogTitle>
              <DialogDescription className="text-xs text-[#8e9bb0]">
                Organize memories into meaningful family themes and life chapters.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {error && (
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 flex items-center gap-2 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleCreate} className="flex gap-2">
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

        <div className="max-h-72 overflow-y-auto space-y-2 pr-1">
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
                      className="p-1 rounded bg-[#d4af37] text-black hover:bg-[#f3d87b]"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="p-1 text-[#8e9bb0] hover:text-white"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white">#{t.name}</span>
                      <span className="px-1.5 py-0.5 rounded-full bg-[#151c28] text-[10px] text-[#8e9bb0]">
                        {t.memories_count || 0}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleStartEdit(t)}
                        className="p-1.5 rounded-lg text-[#8e9bb0] hover:text-white hover:bg-[#161c28] transition-colors"
                        title="Edit tag"
                      >
                        <Edit2 className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(t.id, t.name)}
                        className="p-1.5 rounded-lg text-[#8e9bb0] hover:text-rose-400 hover:bg-[#161c28] transition-colors"
                        title="Delete tag"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
