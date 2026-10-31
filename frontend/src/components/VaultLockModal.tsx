import { useState } from 'react';
import {
  Lock,
  Unlock,
  Key,
  ShieldCheck,
  AlertTriangle,
  Copy,
  Check,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';
import type { VaultStatus, VaultSetupResponse } from '../types';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from './ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from './ui/tabs';

interface VaultLockModalProps {
  isOpen: boolean;
  onClose: () => void;
  vaultStatus: VaultStatus | null;
  onStatusChanged: () => void;
}

export const VaultLockModal = ({
  isOpen,
  onClose,
  vaultStatus,
  onStatusChanged,
}: VaultLockModalProps) => {
  const [tab, setTab] = useState<'unlock' | 'recover'>('unlock');

  // Form states
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [recoveryKeyInput, setRecoveryKeyInput] = useState('');
  const [autoLockMinutes, setAutoLockMinutes] = useState(15);

  // Status/feedback
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [setupResult, setSetupResult] = useState<VaultSetupResponse | null>(null);
  const [copiedKey, setCopiedKey] = useState(false);

  const isInitialized = vaultStatus?.is_initialized ?? false;
  const isUnlocked = vaultStatus?.is_unlocked ?? false;

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (tab === 'recover' && recoveryKeyInput.trim()) {
        await api.unlockVault({ recovery_key: recoveryKeyInput.trim() });
      } else {
        await api.unlockVault({ password });
      }
      setPassword('');
      setRecoveryKeyInput('');
      setSuccessMessage('Vault unlocked successfully.');
      onStatusChanged();
      setTimeout(() => {
        onClose();
        setSuccessMessage(null);
      }, 1000);
    } catch (err: any) {
      setError(err?.message || 'Failed to unlock vault. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleSetup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const res = await api.setupVault({
        password,
        auto_lock_minutes: autoLockMinutes,
      });
      setSetupResult(res);
      setPassword('');
      setConfirmPassword('');
      onStatusChanged();
    } catch (err: any) {
      setError(err?.message || 'Failed to set up encryption vault.');
    } finally {
      setLoading(false);
    }
  };

  const handleLock = async () => {
    setError(null);
    setLoading(true);
    try {
      await api.lockVault();
      setSuccessMessage('Vault locked. Memory keys safely purged from memory.');
      onStatusChanged();
      setTimeout(() => {
        setSuccessMessage(null);
      }, 1500);
    } catch (err: any) {
      setError(err?.message || 'Failed to lock vault.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopyRecoveryKey = () => {
    if (!setupResult?.recovery_key) return;
    navigator.clipboard.writeText(setupResult.recovery_key);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-md bg-[#0f141f] border border-[#232b3c] p-6 shadow-2xl">
        <DialogHeader className="pb-4 border-b border-[#1c2434]">
          <div className="flex items-center gap-3">
            <div
              className={`w-9 h-9 rounded-xl flex items-center justify-center border ${
                isUnlocked
                  ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-400'
                  : 'bg-amber-950/40 border-amber-500/40 text-amber-400'
              }`}
            >
              {isUnlocked ? <Unlock className="w-5 h-5" /> : <Lock className="w-5 h-5" />}
            </div>
            <div>
              <DialogTitle className="text-base font-semibold text-white">
                {!isInitialized
                  ? 'Setup Vault Encryption'
                  : isUnlocked
                  ? 'Vault Active & Unlocked'
                  : 'Unlock Memory Vault'}
              </DialogTitle>
              <DialogDescription className="text-xs text-[#7b899e]">
                Phase 6 • Authenticated AES-256-GCM + Argon2id
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        {error && (
          <div className="p-3 rounded-lg bg-red-950/40 border border-red-800/50 text-red-300 text-xs flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMessage && (
          <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-emerald-300 text-xs flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 shrink-0" />
            <span>{successMessage}</span>
          </div>
        )}

        {setupResult ? (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-600/40 space-y-3">
              <div className="flex items-center gap-2 text-amber-400 text-sm font-semibold">
                <Key className="w-4 h-4" />
                <span>Save Your Emergency Recovery Key</span>
              </div>
              <p className="text-xs text-[#a0aec0] leading-relaxed">
                If you forget your master passphrase, this is the <strong>only way</strong> to
                recover your memories. Store it in a secure location (e.g. password manager, paper safe).
              </p>
              <div className="flex items-center justify-between p-3 rounded-lg bg-black/60 border border-amber-500/30 font-mono text-sm tracking-wider text-amber-200">
                <span>{setupResult.recovery_key}</span>
                <button
                  onClick={handleCopyRecoveryKey}
                  className="flex items-center gap-1 px-2.5 py-1 rounded bg-[#1c2434] hover:bg-[#28354c] text-xs text-white transition-colors"
                >
                  {copiedKey ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedKey ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            </div>

            <button
              onClick={() => {
                setSetupResult(null);
                onClose();
              }}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[#d4af37] to-[#aa8214] text-black font-semibold text-sm hover:brightness-110 transition-all shadow-md"
            >
              I Have Saved My Recovery Key
            </button>
          </div>
        ) : !isInitialized ? (
          <form onSubmit={handleSetup} className="space-y-4">
            <p className="text-xs text-[#8e9bb0] leading-relaxed">
              Initialize your cryptographic vault. Your master passphrase derives an Argon2id key to wrap your
              vault's AES-256 data encryption key. All processing stays 100% on this computer.
            </p>

            <div>
              <label className="block text-xs font-medium text-[#abb8cb] mb-1">
                Vault Master Passphrase
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters..."
                className="w-full px-3 py-2 rounded-lg bg-[#07090c] border border-[#232b3c] text-sm text-white focus:outline-none focus:border-[#d4af37]"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[#abb8cb] mb-1">
                Confirm Passphrase
              </label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter master passphrase..."
                className="w-full px-3 py-2 rounded-lg bg-[#07090c] border border-[#232b3c] text-sm text-white focus:outline-none focus:border-[#d4af37]"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[#abb8cb] mb-1">
                Auto-Lock Inactivity Timeout (Minutes)
              </label>
              <input
                type="number"
                min={1}
                max={120}
                value={autoLockMinutes}
                onChange={(e) => setAutoLockMinutes(parseInt(e.target.value) || 15)}
                className="w-full px-3 py-2 rounded-lg bg-[#07090c] border border-[#232b3c] text-sm text-white focus:outline-none focus:border-[#d4af37]"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[#d4af37] to-[#aa8214] text-black font-semibold text-sm hover:brightness-110 transition-all shadow-md flex items-center justify-center gap-2"
            >
              {loading && <RefreshCw className="w-4 h-4 animate-spin" />}
              <span>Initialize Vault & Generate Recovery Key</span>
            </button>
          </form>
        ) : isUnlocked ? (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-600/30 text-xs text-[#a0aec0] space-y-2">
              <p className="text-emerald-400 font-semibold flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4" />
                <span>Vault is Unlocked & Operational</span>
              </p>
              <p>
                Files and sensitive database fields are decrypted on-demand in memory. Locking the vault
                immediately purges the DEK from RAM and requires your passphrase to view memories.
              </p>
            </div>

            <button
              onClick={handleLock}
              disabled={loading}
              className="w-full py-2.5 rounded-xl bg-red-950/50 hover:bg-red-900/60 border border-red-500/40 text-red-200 font-semibold text-sm transition-all flex items-center justify-center gap-2"
            >
              {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Lock className="w-4 h-4" />}
              <span>Lock Vault Now (Purge Memory Keys)</span>
            </button>
          </div>
        ) : (
          <Tabs value={tab} onValueChange={(val: any) => setTab(val)} className="w-full space-y-4">
            <TabsList className="grid grid-cols-2 w-full">
              <TabsTrigger value="unlock">Passphrase</TabsTrigger>
              <TabsTrigger value="recover">Recovery Key</TabsTrigger>
            </TabsList>

            <form onSubmit={handleUnlock} className="space-y-4">
              <TabsContent value="unlock">
                <div>
                  <label className="block text-xs font-medium text-[#abb8cb] mb-1">
                    Master Passphrase
                  </label>
                  <input
                    type="password"
                    required={tab === 'unlock'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter vault passphrase..."
                    autoFocus
                    className="w-full px-3 py-2 rounded-lg bg-[#07090c] border border-[#232b3c] text-sm text-white focus:outline-none focus:border-[#d4af37]"
                  />
                </div>
              </TabsContent>

              <TabsContent value="recover">
                <div>
                  <label className="block text-xs font-medium text-[#abb8cb] mb-1">
                    32-Character Recovery Key
                  </label>
                  <input
                    type="text"
                    required={tab === 'recover'}
                    value={recoveryKeyInput}
                    onChange={(e) => setRecoveryKeyInput(e.target.value)}
                    placeholder="XXXX-XXXX-XXXX-XXXX-..."
                    autoFocus
                    className="w-full px-3 py-2 rounded-lg bg-[#07090c] border border-[#232b3c] text-sm font-mono text-amber-300 focus:outline-none focus:border-amber-500"
                  />
                </div>
              </TabsContent>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-xl bg-gradient-to-r from-[#d4af37] to-[#aa8214] text-black font-semibold text-sm hover:brightness-110 transition-all shadow-md flex items-center justify-center gap-2"
              >
                {loading && <RefreshCw className="w-4 h-4 animate-spin" />}
                <span>Unlock Vault</span>
              </button>
            </form>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
  );
};
