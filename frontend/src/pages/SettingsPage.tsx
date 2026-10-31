import { useEffect, useState } from 'react';
import {
  HardDrive,
  Shield,
  Info,
  Lock,
  CheckCircle,
  Database,
  Mic,
  Cpu,
  Download,
  Trash2,
  RefreshCw,
  AlertCircle,
  Sparkles,
  Unlock,
  Key,
  FileArchive,
  Undo2,
} from 'lucide-react';
import type {
  SystemStatus,
  WhisperModelInfo,
  TranscriptionEngineStatus,
  IndexStatus,
  EmbeddingModelInfo,
  VaultStatus,
  MigrationStatus,
} from '../types';
import { api } from '../services/api';
import { VaultLockModal } from '../components/VaultLockModal';

export const SettingsPage = () => {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [engineStatus, setEngineStatus] = useState<TranscriptionEngineStatus | null>(null);
  const [models, setModels] = useState<WhisperModelInfo[]>([]);
  const [downloadingModel, setDownloadingModel] = useState<string | null>(null);
  const [modelActionMsg, setModelActionMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isLoadingModels, setIsLoadingModels] = useState(false);

  // Phase 4: Vector Store & Embeddings
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null);
  const [embModels, setEmbModels] = useState<EmbeddingModelInfo[]>([]);
  const [isRebuildingIndex, setIsRebuildingIndex] = useState(false);
  const [rebuildResult, setRebuildResult] = useState<any | null>(null);
  const [isRetryingJobs, setIsRetryingJobs] = useState(false);
  const [downloadingEmbModel, setDownloadingEmbModel] = useState<string | null>(null);

  // Phase 6: Vault Encryption & Data Protection
  const [vaultStatus, setVaultStatus] = useState<VaultStatus | null>(null);
  const [migrationStatus, setMigrationStatus] = useState<MigrationStatus | null>(null);
  const [isVaultModalOpen, setIsVaultModalOpen] = useState(false);
  const [isMigrating, setIsMigrating] = useState(false);
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [securityMsg, setSecurityMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    loadSettings();
    loadSpeechStatus();
    loadRagStatus();
    loadVaultStatus();
  }, []);

  const loadVaultStatus = async () => {
    try {
      const vs = await api.getVaultStatus();
      setVaultStatus(vs);
    } catch (err) {
      console.error('Failed to load vault status', err);
    }
  };

  const handleStartMigration = async () => {
    if (!vaultStatus?.is_unlocked) {
      setIsVaultModalOpen(true);
      return;
    }
    if (!window.confirm('Start safe migration to encrypt all original media and thumbnails? Plaintext copies will be backed up safely before encryption, and each file will be verified via SHA-256 roundtrip.')) return;

    setIsMigrating(true);
    setSecurityMsg(null);
    try {
      await api.startMigration();
      // Poll migration status
      const interval = setInterval(async () => {
        try {
          const ms = await api.getMigrationStatus();
          setMigrationStatus(ms);
          if (!ms.is_running) {
            clearInterval(interval);
            setIsMigrating(false);
            setSecurityMsg({
              type: ms.failed_files === 0 ? 'success' : 'error',
              text: `Migration finished: ${ms.successful_files} files encrypted, ${ms.failed_files} errors.`,
            });
            await loadVaultStatus();
          }
        } catch {
          clearInterval(interval);
          setIsMigrating(false);
        }
      }, 1000);
    } catch (err: any) {
      setIsMigrating(false);
      setSecurityMsg({ type: 'error', text: err.message || 'Failed to start file migration.' });
    }
  };

  const handleCancelMigration = async () => {
    try {
      await api.cancelMigration();
      setSecurityMsg({ type: 'success', text: 'Migration cancellation requested.' });
    } catch (err: any) {
      setSecurityMsg({ type: 'error', text: err.message || 'Failed to cancel migration.' });
    }
  };

  const handleRollbackMigration = async () => {
    if (!window.confirm('Roll back encrypted files to their pre-migration plaintext backups?')) return;
    try {
      const res = await api.rollbackMigration();
      setSecurityMsg({ type: 'success', text: `Rollback completed: ${res.restored_files} files restored.` });
      await loadVaultStatus();
    } catch (err: any) {
      setSecurityMsg({ type: 'error', text: err.message || 'Rollback failed.' });
    }
  };

  const handleCreateBackup = async () => {
    setIsBackingUp(true);
    setSecurityMsg(null);
    try {
      const res = await api.createBackup();
      setSecurityMsg({
        type: 'success',
        text: `Encrypted backup created: ${res.backup_file} (${Math.round(res.size_bytes / 1024)} KB)`,
      });
    } catch (err: any) {
      setSecurityMsg({ type: 'error', text: err.message || 'Backup creation failed.' });
    } finally {
      setIsBackingUp(false);
    }
  };

  const loadRagStatus = async () => {
    try {
      const [idx, embs] = await Promise.all([
        api.getIndexStatus(),
        api.getEmbeddingModels(),
      ]);
      setIndexStatus(idx);
      setEmbModels(embs);
    } catch (err) {
      console.error('Failed to load RAG index status', err);
    }
  };

  const handleRebuildIndex = async () => {
    if (!window.confirm('Rebuild the entire vector store from scratch? SQLite records and original media will not be affected.')) return;
    setIsRebuildingIndex(true);
    setRebuildResult(null);
    try {
      const res = await api.rebuildIndex();
      setRebuildResult(res);
      await loadRagStatus();
    } catch (err: any) {
      alert(err.message || 'Failed to rebuild index.');
    } finally {
      setIsRebuildingIndex(false);
    }
  };

  const handleRetryJobs = async () => {
    setIsRetryingJobs(true);
    try {
      const res = await api.retryFailedIndexing();
      alert(`Retried: ${res.retried_count}, Succeeded: ${res.succeeded_count}, Failed: ${res.failed_count}`);
      await loadRagStatus();
    } catch (err: any) {
      alert(err.message || 'Failed to retry indexing jobs.');
    } finally {
      setIsRetryingJobs(false);
    }
  };

  const handleDownloadEmbModel = async (name: string) => {
    setDownloadingEmbModel(name);
    try {
      await api.downloadEmbeddingModel(name);
      alert(`Model '${name}' downloaded successfully.`);
      await loadRagStatus();
    } catch (err: any) {
      alert(err.message || 'Download failed.');
    } finally {
      setDownloadingEmbModel(null);
    }
  };

  const loadSettings = async () => {
    try {
      const data = await api.getSystemStatus();
      setSystemStatus(data);
    } catch (err) {
      console.error('Failed to load system settings', err);
    }
  };

  const loadSpeechStatus = async () => {
    setIsLoadingModels(true);
    try {
      const [statusData, modelsData] = await Promise.all([
        api.getTranscriptionStatus(),
        api.getWhisperModels(),
      ]);
      setEngineStatus(statusData);
      setModels(modelsData);
    } catch (err) {
      console.error('Failed to load speech engine info', err);
    } finally {
      setIsLoadingModels(false);
    }
  };

  const handleDownloadModel = async (modelName: string) => {
    setDownloadingModel(modelName);
    setModelActionMsg(null);
    try {
      await api.downloadWhisperModel(modelName);
      setModelActionMsg({
        type: 'success',
        text: `Download started for '${modelName}'. This may take a minute depending on your connection.`,
      });
      // Poll model list
      setTimeout(loadSpeechStatus, 3000);
    } catch (err: any) {
      setModelActionMsg({
        type: 'error',
        text: err.message || `Failed to download '${modelName}'.`,
      });
    } finally {
      setDownloadingModel(null);
    }
  };

  const handleDeleteModel = async (modelName: string) => {
    if (!window.confirm(`Delete local files for '${modelName}' model to free up space?`)) return;
    setModelActionMsg(null);
    try {
      await api.deleteWhisperModel(modelName);
      setModelActionMsg({
        type: 'success',
        text: `Model '${modelName}' deleted from disk.`,
      });
      await loadSpeechStatus();
    } catch (err: any) {
      setModelActionMsg({
        type: 'error',
        text: err.message || `Failed to delete '${modelName}'.`,
      });
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn max-w-5xl">
      {/* Page Header */}
      <div className="pb-4 border-b border-[#202738]">
        <h1 className="text-2xl sm:text-3xl font-serif font-bold text-white tracking-wide">
          Settings & Architecture
        </h1>
        <p className="text-xs sm:text-sm text-[#8e9bb0] mt-0.5 font-light">
          Inspect local storage roots, privacy configuration, encryption vault, and AI models.
        </p>
      </div>

      {/* Phase 6: Vault Encryption & Data Protection */}
      <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738] space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl border ${
              !vaultStatus?.is_initialized
                ? 'bg-[#182030] border-[#25324c] text-[#8e9bb0]'
                : vaultStatus?.is_unlocked
                ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-400'
                : 'bg-amber-950/40 border-amber-500/40 text-amber-400'
            }`}>
              {vaultStatus?.is_unlocked ? <Unlock className="w-5 h-5" /> : <Lock className="w-5 h-5" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-serif font-bold text-white">
                  Vault Encryption & Data Protection
                </h2>
                <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${
                  !vaultStatus?.is_initialized
                    ? 'bg-zinc-800/60 border-zinc-700 text-zinc-300'
                    : vaultStatus?.is_unlocked
                    ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-300'
                    : 'bg-amber-950/60 border-amber-500/40 text-amber-300'
                }`}>
                  {!vaultStatus?.is_initialized
                    ? 'Unconfigured'
                    : vaultStatus?.is_unlocked
                    ? 'Unlocked & Protected'
                    : 'Locked'}
                </span>
              </div>
              <p className="text-xs text-[#8e9bb0]">
                Authenticated AES-256-GCM chunked file streaming + Argon2id envelope key derivation.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsVaultModalOpen(true)}
              className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b] transition-all flex items-center gap-1.5 shadow-sm"
            >
              {!vaultStatus?.is_initialized ? (
                <>
                  <Key className="w-3.5 h-3.5" />
                  <span>Setup Encryption</span>
                </>
              ) : vaultStatus?.is_unlocked ? (
                <>
                  <Lock className="w-3.5 h-3.5" />
                  <span>Lock Vault</span>
                </>
              ) : (
                <>
                  <Unlock className="w-3.5 h-3.5" />
                  <span>Unlock Vault</span>
                </>
              )}
            </button>
            <button
              onClick={loadVaultStatus}
              className="p-1.5 rounded-lg text-[#8e9bb0] hover:text-[#d4af37] hover:bg-[#1a202e] transition-colors"
              title="Refresh vault status"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {securityMsg && (
          <div
            className={`p-3 rounded-xl border text-xs flex items-center gap-2 ${
              securityMsg.type === 'success'
                ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                : 'bg-rose-950/40 border-rose-500/40 text-rose-300'
            }`}
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{securityMsg.text}</span>
          </div>
        )}

        {/* Vault Telemetry */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase font-semibold">Cipher & Mode</span>
            <span className="text-white font-medium mt-0.5 block font-mono">
              {vaultStatus?.algorithm || 'AES-256-GCM'}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase font-semibold">Key Derivation</span>
            <span className="text-[#f3d87b] font-medium mt-0.5 block font-mono">
              {vaultStatus?.kdf || 'Argon2id'} (64 MB)
            </span>
          </div>

          <div className="p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase font-semibold">Inactivity Timeout</span>
            <span className="text-white font-medium mt-0.5 block">
              {vaultStatus?.auto_lock_minutes ?? 15} minutes
            </span>
          </div>

          <div className="p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase font-semibold">File Encryption Ratio</span>
            <span className={`font-medium mt-0.5 block ${vaultStatus?.is_fully_encrypted ? 'text-emerald-400' : 'text-amber-400'}`}>
              {vaultStatus?.encrypted_files ?? 0} / {vaultStatus?.total_files ?? 0} files
              {vaultStatus?.is_fully_encrypted ? ' (100%)' : ''}
            </span>
          </div>
        </div>

        {/* Safe Migration & Backup Controls */}
        <div className="p-4 rounded-xl bg-[#080a0e] border border-[#1a2130] space-y-3">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h4 className="text-xs font-semibold text-white uppercase tracking-wider">
                Safe File Encryption Migration
              </h4>
              <p className="text-[11px] text-[#78879e] mt-0.5">
                Encrypts all unprotected disk files with automatic pre-migration backup and SHA-256 verification.
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {migrationStatus?.is_running ? (
                <button
                  onClick={handleCancelMigration}
                  className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-red-950/50 border border-red-500/40 text-red-300 hover:bg-red-900/40 transition-colors"
                >
                  Cancel Migration
                </button>
              ) : (
                <>
                  <button
                    onClick={handleRollbackMigration}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#141b28] border border-[#232e42] text-[#8e9bb0] hover:text-white hover:bg-[#1a2436] transition-colors flex items-center gap-1.5"
                    title="Restore plaintext files from pre-migration backup"
                  >
                    <Undo2 className="w-3.5 h-3.5" />
                    <span>Rollback</span>
                  </button>
                  <button
                    onClick={handleStartMigration}
                    disabled={isMigrating || !vaultStatus?.is_unlocked}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[#18263e] border border-[#2d4774] text-[#82b1ff] hover:bg-[#203354] transition-colors disabled:opacity-40"
                  >
                    {isMigrating ? 'Migrating...' : 'Encrypt Unprotected Files'}
                  </button>
                </>
              )}
              <button
                onClick={handleCreateBackup}
                disabled={isBackingUp || !vaultStatus?.is_unlocked}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 hover:bg-emerald-900/40 transition-colors flex items-center gap-1.5 disabled:opacity-40"
              >
                <FileArchive className="w-3.5 h-3.5" />
                <span>{isBackingUp ? 'Creating...' : 'Create .da-backup'}</span>
              </button>
            </div>
          </div>

          {/* Migration Progress Bar if running */}
          {migrationStatus && migrationStatus.is_running && (
            <div className="space-y-1.5 pt-2 border-t border-[#192232]">
              <div className="flex justify-between text-[11px] text-[#8e9bb0]">
                <span>
                  Encrypting: {migrationStatus.processed_files} / {migrationStatus.total_files} files
                </span>
                <span>{migrationStatus.progress_percent}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-[#141a24] overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-[#d4af37] to-emerald-400 transition-all duration-300"
                  style={{ width: `${migrationStatus.progress_percent}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Vault Modal */}
      <VaultLockModal
        isOpen={isVaultModalOpen}
        onClose={() => setIsVaultModalOpen(false)}
        vaultStatus={vaultStatus}
        onStatusChanged={loadVaultStatus}
      />

      {/* Phase 3: Speech-to-Text & Whisper Models Section */}
      <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738] space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
              <Mic className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-serif font-bold text-white">Local Speech-to-Text Engine (Whisper)</h2>
              <p className="text-xs text-[#8e9bb0]">
                Private, CPU-quantized oral history transcription with zero cloud dependency.
              </p>
            </div>
          </div>
          <button
            onClick={loadSpeechStatus}
            disabled={isLoadingModels}
            className="p-1.5 rounded-lg text-[#8e9bb0] hover:text-[#d4af37] hover:bg-[#1a202e] transition-colors"
            title="Refresh speech models status"
          >
            <RefreshCw className={`w-4 h-4 ${isLoadingModels ? 'animate-spin text-[#d4af37]' : ''}`} />
          </button>
        </div>

        {modelActionMsg && (
          <div
            className={`p-3 rounded-xl border text-xs flex items-center gap-2 ${
              modelActionMsg.type === 'success'
                ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
                : 'bg-rose-950/40 border-rose-500/40 text-rose-300'
            }`}
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{modelActionMsg.text}</span>
          </div>
        )}

        {/* Engine Telemetry Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase font-semibold">Compute Architecture</span>
            <span className="text-white font-medium flex items-center gap-1 mt-0.5">
              <Cpu className="w-3.5 h-3.5 text-[#d4af37]" />
              {engineStatus?.device?.toUpperCase() || 'CPU'} ({engineStatus?.compute_type || 'int8'})
            </span>
          </div>

          <div className="p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase font-semibold">Queue Concurrency</span>
            <span className="text-emerald-400 font-medium mt-0.5 block">
              {engineStatus?.queue_concurrency || 1} Worker (Strict Memory Guard)
            </span>
          </div>

          <div className="p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase font-semibold">Audio Decoders</span>
            <span className="text-[#f3d87b] font-medium mt-0.5 block">
              PyAV (Native) {engineStatus?.ffmpeg_available ? '+ FFmpeg' : ''}
            </span>
          </div>

          <div className="p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase font-semibold">Models Ready</span>
            <span className="text-white font-medium mt-0.5 block">
              {engineStatus?.models_installed_count || 0} Installed Locally
            </span>
          </div>
        </div>

        {/* Models Management Grid */}
        <div className="space-y-3 pt-1">
          <span className="text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider block">
            Offline Speech Models
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {models.map((m) => {
              const isBusy = downloadingModel === m.name || m.is_downloading;
              return (
                <div
                  key={m.name}
                  className={`p-4 rounded-xl border flex flex-col justify-between transition-all ${
                    m.is_installed
                      ? 'bg-[#0d121c] border-[#d4af37]/40 shadow-sm shadow-[#d4af37]/5'
                      : 'bg-[#080a0e] border-[#1b2230]'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5">
                        <span className="text-sm font-bold text-white uppercase tracking-wide">
                          {m.name}
                        </span>
                        {m.recommended && (
                          <span className="px-1.5 py-0.5 text-[9px] font-semibold bg-[#d4af37]/20 text-[#f3d87b] border border-[#d4af37]/40 rounded">
                            Recommended
                          </span>
                        )}
                      </div>
                      <span className="text-[11px] text-[#6d7c92] font-mono">
                        ~{m.disk_size_mb} MB
                      </span>
                    </div>
                    <p className="text-xs text-[#8e9bb0] leading-relaxed mb-4">
                      {m.description}
                    </p>
                  </div>

                  <div className="pt-3 border-t border-[#181e2b] flex items-center justify-between">
                    <div>
                      {m.is_installed ? (
                        <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                          <CheckCircle className="w-3.5 h-3.5" />
                          Ready ({m.actual_size_mb} MB)
                        </span>
                      ) : (
                        <span className="text-[11px] text-[#6d7c92]">Not installed</span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {m.is_installed ? (
                        <button
                          onClick={() => handleDeleteModel(m.name)}
                          className="p-1.5 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 transition-colors"
                          title="Delete model files"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleDownloadModel(m.name)}
                          disabled={isBusy}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#1a2233] text-[#d4af37] border border-[#d4af37]/40 hover:bg-[#232e44] transition-colors disabled:opacity-50"
                        >
                          <Download className="w-3.5 h-3.5" />
                          {isBusy ? 'Downloading...' : 'Install'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-[11px] text-[#6d7c92] italic pt-1">
            Privacy safeguard: Models are never downloaded automatically. Installation only begins when you click Install.
          </p>
        </div>
      </div>

      {/* Storage Architecture Section */}
      <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738] space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
            <HardDrive className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-serif font-bold text-white">Local Storage Subsystem</h2>
            <p className="text-xs text-[#8e9bb0]">Where artifacts and SQLite files reside on this machine.</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
          <div className="p-4 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <span className="text-xs text-[#6d7c92] block mb-1">Memories Directory</span>
            <span className="text-xs font-mono text-[#f3d87b] break-all">
              {systemStatus?.storage.storage_directory || 'data/memories'}
            </span>
          </div>

          <div className="p-4 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <span className="text-xs text-[#6d7c92] block mb-1">Storage Utilized</span>
            <span className="text-sm font-semibold text-white">
              {systemStatus?.storage.formatted_size || '0 B'} (
              {systemStatus?.storage.total_files || 0} physical files)
            </span>
          </div>
        </div>
      </div>

      {/* Privacy & Philosophy Section */}
      <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738] space-y-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-serif font-bold text-white">Privacy & Ethical Boundaries</h2>
            <p className="text-xs text-[#8e9bb0]">Strict principles governing this application.</p>
          </div>
        </div>

        <div className="space-y-3 pt-2 text-xs text-[#9db0cc] leading-relaxed">
          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-white block font-medium">1. Absolute Sovereignty</strong>
              Memories belong exclusively to their owners. No personal artifacts or transcripts are
              ever dispatched to third-party clouds or external LLM APIs.
            </div>
          </div>

          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-white block font-medium">2. Offline-First Reality</strong>
              The backend binds strictly to the loopback interface (`127.0.0.1`). The software operates
              entirely without an active internet connection.
            </div>
          </div>

          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-[#090c12] border border-[#1b2230]">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-white block font-medium">3. Historical Authenticity & Biometric Consent</strong>
              AI speech processing adheres to strict user consent before recording speaker voice signatures. AI-generated interpretations must never be passed off as authentic historical facts without provenance.
            </div>
          </div>
        </div>
      </div>

      {/* Encryption & Desktop Readiness */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738] space-y-3">
          <div className="flex items-center gap-2.5">
            <Lock className="w-4 h-4 text-[#d4af37]" />
            <h3 className="text-sm font-semibold text-white">Encryption Abstraction</h3>
          </div>
          <p className="text-xs text-[#8e9bb0] leading-relaxed">
            Phase 1 and Phase 2 incorporate cryptographic integrity (`BaseEncryptionProvider` and SHA-256 artifact
            verification). Full authenticated <span className="text-[#f3d87b] font-medium">AES-256-GCM</span> envelope
            encryption with passkey derivation is structured for future phase activation.
          </p>
          <span className="inline-block px-2.5 py-1 rounded text-[10px] font-semibold uppercase bg-[#182030] text-[#8e9bb0] border border-[#253247]">
            Architecture Ready
          </span>
        </div>

        <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738] space-y-3">
          <div className="flex items-center gap-2.5">
            <Database className="w-4 h-4 text-sky-400" />
            <h3 className="text-sm font-semibold text-white">Desktop & Tauri Readiness</h3>
          </div>
          <p className="text-xs text-[#8e9bb0] leading-relaxed">
            The frontend is decoupled from server-side dependencies and communicates solely via
            standard REST endpoints, allowing seamless embedding into native desktop shells (such as
            Tauri or Electron) in subsequent phases.
          </p>
          <span className="inline-block px-2.5 py-1 rounded text-[10px] font-semibold uppercase bg-[#182030] text-[#8e9bb0] border border-[#253247]">
            Browser / Tauri Compatible
          </span>
        </div>
      </div>

      {/* Phase 4: Local Vector Store & Semantic Search */}
      <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738] space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-3 pb-4 border-b border-[#1f2736]">
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-5 h-5 text-[#d4af37]" />
            <div>
              <h3 className="text-sm font-semibold text-white">Semantic Search & Vector Storage</h3>
              <p className="text-xs text-[#8e9bb0]">
                ChromaDB Persistent Local Store • Multilingual E5 Small • Zero External Cloud APIs
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleRetryJobs}
              disabled={isRetryingJobs}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium bg-[#141b27] text-[#8e9bb0] hover:text-white border border-[#222c3d] transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRetryingJobs ? 'animate-spin' : ''}`} />
              <span>Retry Failed Jobs</span>
            </button>
            <button
              onClick={handleRebuildIndex}
              disabled={isRebuildingIndex}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b] transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRebuildingIndex ? 'animate-spin' : ''}`} />
              <span>{isRebuildingIndex ? 'Rebuilding Index...' : 'Rebuild Complete Index'}</span>
            </button>
          </div>
        </div>

        {/* Rebuild Summary Banner */}
        {rebuildResult && (
          <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-xs text-emerald-200 flex items-center justify-between">
            <span>
              Index rebuilt: {rebuildResult.indexed_memories}/{rebuildResult.total_memories} memories indexed ({rebuildResult.total_chunks} chunks).
            </span>
            <span className="font-mono text-[11px] text-emerald-400 font-semibold uppercase">{rebuildResult.status}</span>
          </div>
        )}

        {/* Index Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-[#090b10] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase">Vector Chunks</span>
            <span className="text-lg font-semibold text-white">{indexStatus?.vector_store.vector_count || 0}</span>
          </div>
          <div className="p-3 rounded-xl bg-[#090b10] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase">Authoritative Memories</span>
            <span className="text-lg font-semibold text-[#f3d87b]">{indexStatus?.total_memories || 0}</span>
          </div>
          <div className="p-3 rounded-xl bg-[#090b10] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase">Synchronized Status</span>
            <span className={`text-xs font-semibold ${indexStatus?.is_synchronized ? 'text-emerald-400' : 'text-amber-400'}`}>
              {indexStatus?.is_synchronized ? '100% In Sync' : `${indexStatus?.pending_jobs || 0} Pending`}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-[#090b10] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase">Store Path</span>
            <span className="text-white font-mono text-[11px] truncate block" title={indexStatus?.vector_store.persist_directory}>
              data/vector_store/
            </span>
          </div>
        </div>

        {/* Local Embedding Models */}
        <div className="space-y-3">
          <h4 className="text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider">
            Local Embedding Models (CPU ONNX)
          </h4>
          <div className="space-y-2">
            {embModels.map((m) => (
              <div
                key={m.name}
                className="p-3.5 rounded-xl bg-[#090c12] border border-[#1b2230] flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-white text-xs">{m.name}</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-[#161f2e] text-[#f3d87b] border border-[#d4af37]/30">
                      {m.dimension}-D • Multilingual
                    </span>
                    {m.is_default && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-[#1f2736] text-[#8e9bb0]">
                        Default
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-[#6d7c92] mt-0.5">{m.description}</p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {m.installed ? (
                    <span className="inline-flex items-center gap-1 text-emerald-400 text-xs font-medium bg-emerald-950/40 px-2.5 py-1 rounded-lg border border-emerald-500/30">
                      <CheckCircle className="w-3.5 h-3.5" />
                      Installed ({m.size_mb} MB)
                    </span>
                  ) : (
                    <button
                      onClick={() => handleDownloadEmbModel(m.name)}
                      disabled={downloadingEmbModel === m.name}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b] disabled:opacity-50 transition-colors"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>{downloadingEmbModel === m.name ? 'Downloading...' : 'Download Weights'}</span>
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* System Diagnostics */}
      <div className="p-6 rounded-2xl bg-[#0f131c] border border-[#202738]">
        <div className="flex items-center gap-2.5 mb-4">
          <Info className="w-4 h-4 text-[#d4af37]" />
          <h3 className="text-sm font-semibold text-white">Application Diagnostics</h3>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-[#080a0e] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase">Application</span>
            <span className="text-white font-medium">{systemStatus?.application_name || 'Digital Afterlife'}</span>
          </div>

          <div className="p-3 rounded-lg bg-[#080a0e] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase">Version</span>
            <span className="text-[#f3d87b] font-medium">{systemStatus?.version || '0.3.0'}</span>
          </div>

          <div className="p-3 rounded-lg bg-[#080a0e] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase">Database</span>
            <span className="text-emerald-400 font-medium">SQLite WAL</span>
          </div>

          <div className="p-3 rounded-lg bg-[#080a0e] border border-[#1b2230]">
            <span className="text-[#6d7c92] block text-[10px] uppercase">Binding</span>
            <span className="text-white font-medium">127.0.0.1:8000</span>
          </div>
        </div>
      </div>
    </div>
  );
};
