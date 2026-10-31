import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { VaultPage } from './pages/VaultPage';
import { PeoplePage } from './pages/PeoplePage';
import { AIStudioPage } from './pages/AIStudioPage';
import { SettingsPage } from './pages/SettingsPage';
import { AskMemoriesPage } from './pages/AskMemoriesPage';
import { UploadModal } from './components/UploadModal';
import { AddPersonModal } from './components/AddPersonModal';
import { MemoryDetailModal } from './components/MemoryDetailModal';
import { VaultLockModal } from './components/VaultLockModal';
import type { Person, Memory, AIStatus, VaultStatus } from './types';
import { api } from './services/api';

export function App() {
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [people, setPeople] = useState<Person[]>([]);
  const [aiStatus, setAiStatus] = useState<AIStatus | null>(null);
  const [vaultStatus, setVaultStatus] = useState<VaultStatus | null>(null);

  // Modals state
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isAddPersonOpen, setIsAddPersonOpen] = useState(false);
  const [isVaultModalOpen, setIsVaultModalOpen] = useState(false);
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);
  const [selectedSeekTime, setSelectedSeekTime] = useState<number | null>(null);

  const handleOpenMemoryWithSeek = (memory: Memory, seekTime?: number | null) => {
    setSelectedMemory(memory);
    setSelectedSeekTime(seekTime ?? null);
  };

  // Trigger re-fetches across pages when data mutations occur
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const triggerRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  useEffect(() => {
    loadGlobalData();
  }, [refreshTrigger]);

  const loadGlobalData = async () => {
    try {
      const [peopleList, ai, vs] = await Promise.all([
        api.getPeople(),
        api.getAIStatus(),
        api.getVaultStatus().catch(() => null),
      ]);
      setPeople(peopleList);
      setAiStatus(ai);
      if (vs) setVaultStatus(vs);
    } catch (err) {
      console.error('Failed to load global data', err);
    }
  };

  return (
    <div className="min-h-screen bg-[#07090c] text-[#e5e9f0] flex flex-col selection:bg-[#d4af37]/30 selection:text-[#f3d87b]">
      {/* Top Navigation */}
      <Navbar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        aiStatus={aiStatus}
        vaultStatus={vaultStatus}
        onOpenVaultModal={() => setIsVaultModalOpen(true)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentTab === 'dashboard' && (
          <DashboardPage
            onNavigate={(tab) => setCurrentTab(tab)}
            onOpenUpload={() => setIsUploadOpen(true)}
            onSelectMemory={(m) => setSelectedMemory(m)}
          />
        )}

        {currentTab === 'vault' && (
          <VaultPage
            onOpenUpload={() => setIsUploadOpen(true)}
            onSelectMemory={(m) => handleOpenMemoryWithSeek(m)}
            refreshTrigger={refreshTrigger}
          />
        )}

        {currentTab === 'ask-memories' && (
          <AskMemoriesPage
            people={people}
            onSelectMemory={handleOpenMemoryWithSeek}
            aiStatus={aiStatus}
          />
        )}

        {currentTab === 'people' && (
          <PeoplePage
            onOpenAddPerson={() => setIsAddPersonOpen(true)}
            onSelectMemory={(m) => handleOpenMemoryWithSeek(m)}
            refreshTrigger={refreshTrigger}
          />
        )}

        {currentTab === 'ai-studio' && (
          <AIStudioPage
            people={people}
            onSelectMemory={(m) => handleOpenMemoryWithSeek(m)}
            aiStatus={aiStatus}
            onRefreshAIStatus={loadGlobalData}
          />
        )}

        {currentTab === 'settings' && <SettingsPage />}
      </main>

      {/* Modals */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={triggerRefresh}
        people={people}
      />

      <AddPersonModal
        isOpen={isAddPersonOpen}
        onClose={() => setIsAddPersonOpen(false)}
        onSuccess={triggerRefresh}
      />

      <MemoryDetailModal
        memory={selectedMemory}
        initialSeekTime={selectedSeekTime}
        onClose={() => {
          setSelectedMemory(null);
          setSelectedSeekTime(null);
        }}
        onDeleted={triggerRefresh}
        onUpdated={() => {
          triggerRefresh();
          setSelectedMemory(null);
          setSelectedSeekTime(null);
        }}
        people={people}
      />

      {/* Global Vault Lock / Setup Modal */}
      <VaultLockModal
        isOpen={isVaultModalOpen}
        onClose={() => setIsVaultModalOpen(false)}
        vaultStatus={vaultStatus}
        onStatusChanged={loadGlobalData}
      />

      {/* Minimal Footer */}
      <footer className="border-t border-[#181d28] bg-[#07090c] py-6 text-center text-xs text-[#6d7c92]">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>Digital Afterlife • "Your memories. Your machine. Your legacy."</p>
          <p className="text-[11px] text-[#4d596c]">Phase 6: Encryption, Data Protection & Privacy Audit • 100% Offline-First</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
