import React, { useState } from 'react';
import { UserPlus, AlertCircle } from 'lucide-react';
import { api } from '../services/api';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from './ui/dialog';

interface AddPersonModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const AddPersonModal: React.FC<AddPersonModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [fullName, setFullName] = useState('');
  const [relationship, setRelationship] = useState('');
  const [biography, setBiography] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) {
      setErrorMessage('Full name is required.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await api.createPerson({
        full_name: fullName.trim(),
        relationship: relationship.trim() || undefined,
        biography: biography.trim() || undefined,
      });
      setFullName('');
      setRelationship('');
      setBiography('');
      onSuccess();
      onClose();
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to register person.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-lg bg-[#0f121a] border border-[#d4af37]/30 p-6 sm:p-8">
        <DialogHeader className="pb-4 border-b border-[#202738]">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
              <UserPlus className="w-5 h-5" />
            </div>
            <div>
              <DialogTitle className="text-xl font-serif font-bold text-white">
                Add Family Member / Individual
              </DialogTitle>
              <DialogDescription className="text-xs text-[#8e9bb0]">
                Connect memories with ancestors, relatives, or loved ones.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {errorMessage && (
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 flex items-start gap-2.5 text-xs text-rose-200">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1.5">
              Full Name *
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Margaret Evelyn Thorne"
              required
              className="w-full px-3.5 py-2.5 rounded-lg bg-[#0b0e14] border border-[#232b3c] focus:border-[#d4af37] focus:outline-none text-white text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1.5">
              Relationship / Role
            </label>
            <input
              type="text"
              value={relationship}
              onChange={(e) => setRelationship(e.target.value)}
              placeholder="e.g. Maternal Grandmother, Great Uncle, Self"
              className="w-full px-3.5 py-2.5 rounded-lg bg-[#0b0e14] border border-[#232b3c] focus:border-[#d4af37] focus:outline-none text-white text-sm"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1.5">
              Biographical Background
            </label>
            <textarea
              value={biography}
              onChange={(e) => setBiography(e.target.value)}
              rows={4}
              placeholder="Born 1924, Edinburgh. Served as botanist, loved classic literature..."
              className="w-full px-3.5 py-2.5 rounded-lg bg-[#0b0e14] border border-[#232b3c] focus:border-[#d4af37] focus:outline-none text-white text-sm resize-none"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#202738]">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 text-sm font-medium rounded-lg text-[#8e9bb0] hover:text-white hover:bg-[#151a26] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold bg-gradient-to-r from-[#d4af37] to-[#e68a00] text-black shadow-lg shadow-[#d4af37]/20 hover:brightness-110 transition-all disabled:opacity-50"
            >
              {isSubmitting ? 'Registering...' : 'Add Person'}
            </button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
