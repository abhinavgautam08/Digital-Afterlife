import { useEffect, useState } from 'react';
import { Users, UserPlus, Archive, ArrowRight, X } from 'lucide-react';
import type { Person, Memory } from '../types';
import { api } from '../services/api';

interface PeoplePageProps {
  onOpenAddPerson: () => void;
  onSelectMemory: (memory: Memory) => void;
  refreshTrigger: number;
}

export const PeoplePage = ({
  onOpenAddPerson,
  onSelectMemory,
  refreshTrigger,
}: PeoplePageProps) => {
  const [people, setPeople] = useState<Person[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null);
  const [personMemories, setPersonMemories] = useState<Memory[]>([]);
  const [loadingMemories, setLoadingMemories] = useState(false);

  useEffect(() => {
    loadPeople();
  }, [refreshTrigger]);

  const loadPeople = async () => {
    setIsLoading(true);
    try {
      const data = await api.getPeople();
      setPeople(data);
    } catch (err) {
      console.error('Failed to load people directory', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectPerson = async (person: Person) => {
    setSelectedPerson(person);
    setLoadingMemories(true);
    try {
      const mems = await api.getPersonMemories(person.id);
      setPersonMemories(mems);
    } catch (err) {
      console.error('Failed to fetch person memories', err);
    } finally {
      setLoadingMemories(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#202738]">
        <div>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold text-white tracking-wide">
            Family & Lineage Directory
          </h1>
          <p className="text-xs sm:text-sm text-[#8e9bb0] mt-0.5 font-light">
            {people.length} individuals connected to preserved family heritage
          </p>
        </div>

        <button
          onClick={onOpenAddPerson}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-[#d4af37] to-[#e68a00] text-black shadow-lg shadow-[#d4af37]/20 hover:brightness-110 active:scale-98 transition-all shrink-0"
        >
          <UserPlus className="w-4 h-4 stroke-[2.4]" />
          Add Family Member
        </button>
      </div>

      {isLoading ? (
        <div className="py-20 text-center space-y-3">
          <div className="w-8 h-8 mx-auto border-2 border-[#d4af37] border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-[#8e9bb0]">Loading family directory...</p>
        </div>
      ) : people.length === 0 ? (
        <div className="p-12 rounded-2xl bg-[#0d1017] border border-dashed border-[#232b3c] text-center space-y-3">
          <div className="w-14 h-14 rounded-2xl bg-[#141b28] border border-[#232b3c] flex items-center justify-center text-[#d4af37] mx-auto">
            <Users className="w-7 h-7" />
          </div>
          <h3 className="text-base font-serif font-bold text-white">No people recorded yet</h3>
          <p className="text-xs text-[#8e9bb0] max-w-sm mx-auto">
            Register your ancestors, parents, grandparents, or loved ones so memories can be linked directly to their personal stories.
          </p>
          <div className="pt-2">
            <button
              onClick={onOpenAddPerson}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b] transition-colors"
            >
              Add First Family Member
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {people.map((p) => (
            <div
              key={p.id}
              onClick={() => handleSelectPerson(p)}
              className={`group cursor-pointer rounded-2xl card-modern p-5 flex flex-col justify-between ${
                selectedPerson?.id === p.id
                  ? 'border-[#d4af37] shadow-xl shadow-[#d4af37]/15 ring-1 ring-[#d4af37]'
                  : ''
              }`}
            >
              <div>
                <div className="flex items-start justify-between mb-3">
                  <div className="w-12 h-12 rounded-2xl bg-[#141b28] border border-[#d4af37]/35 flex items-center justify-center text-[#f3d87b] font-serif font-bold text-lg group-hover:scale-105 transition-transform shadow-sm">
                    {p.full_name.charAt(0)}
                  </div>
                  {p.relationship && (
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[#161d2b] border border-[#273347] text-[#9db0cc]">
                      {p.relationship}
                    </span>
                  )}
                </div>

                <h3 className="text-base font-serif font-bold text-white group-hover:text-[#f3d87b] transition-colors">
                  {p.full_name}
                </h3>

                <p className="text-xs text-[#8e9bb0] line-clamp-3 mt-2 font-light leading-relaxed">
                  {p.biography || 'No biographical background recorded yet.'}
                </p>
              </div>

              <div className="mt-5 pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs">
                <span className="inline-flex items-center gap-1.5 text-[#d4af37] font-medium">
                  <Archive className="w-3.5 h-3.5" />
                  {p.memories_count ?? 0} Associated Memories
                </span>
                <span className="text-[#6d7c92] group-hover:text-white transition-colors flex items-center gap-0.5">
                  View <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Selected Person Memories Drawer / Panel */}
      {selectedPerson && (
        <div className="mt-8 p-6 rounded-2xl card-modern-static border-[#d4af37]/40 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 flex items-center justify-center text-[#d4af37] font-bold">
                {selectedPerson.full_name.charAt(0)}
              </div>
              <div>
                <h3 className="text-base font-serif font-bold text-white">
                  Memories of {selectedPerson.full_name}
                </h3>
                <p className="text-xs text-[#8e9bb0]">
                  {selectedPerson.relationship || 'Individual'} • {personMemories.length} connected artifacts
                </p>
              </div>
            </div>
            <button
              onClick={() => setSelectedPerson(null)}
              className="p-1 rounded text-[#8e9bb0] hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {loadingMemories ? (
            <p className="text-xs text-[#8e9bb0] py-4">Loading associated artifacts...</p>
          ) : personMemories.length === 0 ? (
            <div className="py-6 text-center text-xs text-[#8e9bb0] bg-[#07090d] rounded-xl border border-[#1b2230]">
              No memories linked to {selectedPerson.full_name} yet. When uploading a memory, tag this person to link them.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 pt-2">
              {personMemories.map((m) => (
                <div
                  key={m.id}
                  onClick={() => onSelectMemory(m)}
                  className="cursor-pointer p-3 rounded-xl bg-[#0f131c] border border-[#202738] hover:border-[#d4af37] transition-all flex items-center justify-between"
                >
                  <div className="truncate pr-2">
                    <p className="text-xs font-semibold text-white truncate">{m.title}</p>
                    <span className="text-[10px] text-[#6d7c92] uppercase">{m.memory_type}</span>
                  </div>
                  <span className="text-[11px] text-[#d4af37] shrink-0">Open →</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
