import { useState, useRef, useEffect } from 'react';
import {
  X,
  Calendar,
  Users,
  HardDrive,
  Trash2,
  FileText,
  Music,
  Download,
  AlertTriangle,
  Edit2,
  Save,
  MapPin,
  Clock,
  Hash,
  Copy,
  Check,
  Tag as TagIcon,
  Mic,
  Play,
  RotateCw,
  UserCheck,
  ShieldCheck,
  Sparkles
} from 'lucide-react';
import type { Memory, Person, Transcript, TranscriptSegment, TranscriptionJob } from '../types';
import { api } from '../services/api';

interface MemoryDetailModalProps {
  memory: Memory | null;
  onClose: () => void;
  onDeleted: () => void;
  onUpdated?: () => void;
  people?: Person[];
  initialSeekTime?: number | null;
}

export const MemoryDetailModal = ({
  memory,
  onClose,
  onDeleted,
  onUpdated,
  people = [],
  initialSeekTime = null,
}: MemoryDetailModalProps) => {
  const mediaRef = useRef<HTMLMediaElement | null>(null);

  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [copiedText, setCopiedText] = useState(false);
  const [copiedTranscript, setCopiedTranscript] = useState(false);

  // Editable fields
  const [editTitle, setEditTitle] = useState(memory?.title || '');
  const [editDescription, setEditDescription] = useState(memory?.description || '');
  const [editLocation, setEditLocation] = useState(memory?.location || '');
  const [editEventDate, setEditEventDate] = useState(
    memory?.event_date ? memory.event_date.split('T')[0] : ''
  );
  const [editPrivacy, setEditPrivacy] = useState(memory?.privacy_level || 'private');
  const [editTags, setEditTags] = useState<string>(
    memory?.tags ? memory.tags.map((t) => t.name).join(', ') : ''
  );
  const [editPeople, setEditPeople] = useState<string[]>(
    memory?.people ? memory.people.map((p) => p.id) : []
  );
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Phase 3 Speech-to-Text State
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [activeJob, setActiveJob] = useState<TranscriptionJob | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('base');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('auto');
  const [enableDiarization, setEnableDiarization] = useState<boolean>(true);
  const [isSubmittingJob, setIsSubmittingJob] = useState<boolean>(false);
  const [isEditingTranscript, setIsEditingTranscript] = useState<boolean>(false);
  const [editableSegments, setEditableSegments] = useState<TranscriptSegment[]>([]);
  const [transcriptSaveMsg, setTranscriptSaveMsg] = useState<string | null>(null);
  const [speakerConsentPerson, setSpeakerConsentPerson] = useState<Person | null>(null);
  const [enrollTargetSegment, setEnrollTargetSegment] = useState<TranscriptSegment | null>(null);
  const [enrollStatusMsg, setEnrollStatusMsg] = useState<string | null>(null);

  useEffect(() => {
    if (memory) {
      setEditTitle(memory.title);
      setEditDescription(memory.description || '');
      setEditLocation(memory.location || '');
      setEditEventDate(memory.event_date ? memory.event_date.split('T')[0] : '');
      setEditPrivacy(memory.privacy_level || 'private');
      setEditTags(memory.tags ? memory.tags.map((t) => t.name).join(', ') : '');
      setEditPeople(memory.people ? memory.people.map((p) => p.id) : []);

      if (memory.memory_type === 'audio' || memory.memory_type === 'video') {
        loadTranscriptAndJobs();
      }

      if (initialSeekTime !== undefined && initialSeekTime !== null) {
        setTimeout(() => {
          handleSeek(initialSeekTime);
        }, 500);
      }
    }
  }, [memory, initialSeekTime]);

  // Polling for active transcription jobs
  useEffect(() => {
    let timer: any = null;
    if (activeJob && ['queued', 'preprocessing', 'transcribing', 'diarizing'].includes(activeJob.status)) {
      timer = setInterval(async () => {
        try {
          const updated = await api.getTranscriptionJob(activeJob.id);
          setActiveJob(updated);
          if (updated.status === 'completed') {
            await loadTranscriptAndJobs();
            if (onUpdated) onUpdated();
          } else if (updated.status === 'failed' || updated.status === 'cancelled') {
            clearInterval(timer);
          }
        } catch (err) {
          console.error('Error polling job', err);
        }
      }, 1500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [activeJob]);

  if (!memory) return null;

  const fileUrl = api.getMemoryFileUrl(memory.id);
  const isImage = memory.memory_type === 'photograph';
  const isAudio = memory.memory_type === 'audio';
  const isVideo = memory.memory_type === 'video';

  const loadTranscriptAndJobs = async () => {
    try {
      // 1. Check for existing transcript
      try {
        const tr = await api.getTranscript(memory.id);
        setTranscript(tr);
        setEditableSegments(tr.segments || []);
      } catch {
        setTranscript(null);
        setEditableSegments([]);
      }

      // 2. Check for active transcription jobs
      const jobs = await api.getTranscriptionJobs(memory.id);
      const active = jobs.find((j) =>
        ['queued', 'preprocessing', 'transcribing', 'diarizing'].includes(j.status)
      );
      if (active) {
        setActiveJob(active);
      } else if (jobs.length > 0) {
        setActiveJob(jobs[0]); // Latest completed or failed job
      }
    } catch (err) {
      console.error('Failed to load transcription state', err);
    }
  };

  const handleStartTranscription = async () => {
    setIsSubmittingJob(true);
    setSaveError(null);
    try {
      const job = await api.startTranscription(memory.id, {
        model_name: selectedModel,
        language: selectedLanguage,
        enable_diarization: enableDiarization,
      });
      setActiveJob(job);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to start transcription.');
    } finally {
      setIsSubmittingJob(false);
    }
  };

  const handleCancelJob = async () => {
    if (!activeJob) return;
    try {
      const cancelled = await api.cancelTranscriptionJob(activeJob.id);
      setActiveJob(cancelled);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to cancel job.');
    }
  };

  const handleSeek = (seconds: number) => {
    if (mediaRef.current) {
      mediaRef.current.currentTime = seconds;
      mediaRef.current.play();
    }
  };

  const handleSaveTranscriptEdits = async () => {
    if (!transcript) return;
    setIsSaving(true);
    setTranscriptSaveMsg(null);
    try {
      const updated = await api.updateTranscript(transcript.id, {
        segments: editableSegments.map((s) => ({
          id: s.id,
          text: s.text,
          speaker_label: s.speaker_label,
          speaker_id: s.speaker_id || null,
          start_time: s.start_time,
          end_time: s.end_time,
        })),
      });
      setTranscript(updated);
      setEditableSegments(updated.segments);
      setIsEditingTranscript(false);
      setTranscriptSaveMsg('Transcript and speaker assignments saved successfully.');
      setTimeout(() => setTranscriptSaveMsg(null), 3000);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to save transcript updates.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteTranscript = async () => {
    if (!transcript) return;
    if (!window.confirm('Delete this transcript and all timestamped segments permanently?')) return;
    try {
      await api.deleteTranscript(transcript.id);
      setTranscript(null);
      setEditableSegments([]);
      setActiveJob(null);
      if (onUpdated) onUpdated();
    } catch (err: any) {
      setSaveError(err.message || 'Failed to delete transcript.');
    }
  };

  const handleEnrollSpeakerProfile = async (segment: TranscriptSegment, person: Person) => {
    setEnrollTargetSegment(segment);
    setSpeakerConsentPerson(person);
    setEnrollStatusMsg(null);

    // Verify existing consent
    try {
      const consent = await api.getSpeakerConsent(person.id);
      if (!consent || !consent.consent_given) {
        setEnrollStatusMsg('Consent required: Please record consent first.');
      } else {
        // Enroll immediately
        await api.enrollSpeakerProfile(person.id, memory.id, segment.start_time, segment.end_time);
        setEnrollStatusMsg(`Voice profile enrolled for ${person.full_name}!`);
        setTimeout(() => {
          setEnrollTargetSegment(null);
          setSpeakerConsentPerson(null);
          setEnrollStatusMsg(null);
        }, 2500);
      }
    } catch (err: any) {
      setEnrollStatusMsg(err.message || 'Enrollment check failed.');
    }
  };

  const handleGrantConsentAndEnroll = async () => {
    if (!speakerConsentPerson || !enrollTargetSegment) return;
    try {
      await api.recordSpeakerConsent(
        speakerConsentPerson.id,
        true,
        `Explicit oral history consent recorded in modal for ${memory.title}`
      );
      await api.enrollSpeakerProfile(
        speakerConsentPerson.id,
        memory.id,
        enrollTargetSegment.start_time,
        enrollTargetSegment.end_time
      );
      setEnrollStatusMsg(`Consent saved & Voice profile enrolled for ${speakerConsentPerson.full_name}!`);
      setTimeout(() => {
        setEnrollTargetSegment(null);
        setSpeakerConsentPerson(null);
        setEnrollStatusMsg(null);
      }, 2500);
    } catch (err: any) {
      setEnrollStatusMsg(err.message || 'Failed to record consent and enroll.');
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteMemory(memory.id);
      onDeleted();
      onClose();
    } catch (err) {
      console.error('Failed to delete memory', err);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveError(null);
    try {
      const parsedTags = editTags
        .split(',')
        .map((t) => t.trim().toLowerCase().replace(/^#/, ''))
        .filter((t) => t.length > 0);

      await api.updateMemory(memory.id, {
        title: editTitle.trim(),
        description: editDescription.trim() || null,
        location: editLocation.trim() || null,
        event_date: editEventDate.trim() || null,
        privacy_level: editPrivacy,
        person_ids: editPeople,
        tags: parsedTags,
      });

      setIsEditing(false);
      if (onUpdated) onUpdated();
    } catch (err: any) {
      setSaveError(err.message || 'Failed to update memory.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleCopyExtractedText = () => {
    if (memory.extracted_text) {
      navigator.clipboard.writeText(memory.extracted_text);
      setCopiedText(true);
      setTimeout(() => setCopiedText(false), 2000);
    }
  };

  const handleCopyTranscript = () => {
    if (transcript?.transcript_text) {
      navigator.clipboard.writeText(transcript.transcript_text);
      setCopiedTranscript(true);
      setTimeout(() => setCopiedTranscript(false), 2000);
    }
  };

  const formatDuration = (seconds?: number | null) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const formatTimestamp = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins < 10 ? '0' : ''}${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  const isJobActive = activeJob && ['queued', 'preprocessing', 'transcribing', 'diarizing'].includes(activeJob.status);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-4xl max-h-[92vh] overflow-y-auto rounded-2xl bg-[#0f131c] border border-[#232b3c] p-6 text-white shadow-2xl">
        {/* Modal Header */}
        <div className="flex items-start justify-between pb-4 border-b border-[#202738]">
          <div className="flex-1 pr-4">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-[#d4af37]/15 text-[#f3d87b] border border-[#d4af37]/30">
                {memory.memory_type}
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-[#1a202c] text-[#8e9bb0]">
                {memory.privacy_level}
              </span>
              {memory.location && (
                <span className="inline-flex items-center gap-1 text-[11px] text-[#8e9bb0]">
                  <MapPin className="w-3 h-3 text-[#d4af37]" />
                  {memory.location}
                </span>
              )}
            </div>

            {isEditing ? (
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="w-full text-xl font-serif font-bold text-white bg-[#0b0e14] border border-[#d4af37] rounded-lg px-3 py-1 focus:outline-none"
              />
            ) : (
              <h2 className="text-2xl font-serif font-bold text-white tracking-wide">
                {memory.title}
              </h2>
            )}
          </div>

          <div className="flex items-center gap-2">
            {!isEditing && (
              <button
                onClick={() => setIsEditing(true)}
                className="p-1.5 rounded-lg text-[#8e9bb0] hover:text-[#d4af37] hover:bg-[#1a202e] transition-colors"
                title="Edit Memory Details"
              >
                <Edit2 className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#8e9bb0] hover:text-white hover:bg-[#1a202e] transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {saveError && (
          <div className="mt-4 p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 text-xs text-rose-300">
            {saveError}
          </div>
        )}

        {/* Media Preview Section */}
        <div className="mt-5 rounded-xl overflow-hidden bg-[#07090d] border border-[#1d2433] flex items-center justify-center min-h-[200px]">
          {isImage ? (
            <img
              src={fileUrl}
              alt={memory.title}
              className="max-h-[420px] w-auto max-w-full object-contain mx-auto"
            />
          ) : isAudio ? (
            <div className="w-full p-8 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 rounded-full bg-[#d4af37]/15 border border-[#d4af37]/30 flex items-center justify-center text-[#d4af37] mb-4 shadow-lg shadow-[#d4af37]/10">
                <Music className="w-8 h-8" />
              </div>
              <p className="text-sm font-medium text-white mb-1">Oral History Audio Playback</p>
              {memory.duration_seconds && (
                <p className="text-xs text-[#8e9bb0] mb-4">
                  Duration: {formatDuration(memory.duration_seconds)}
                </p>
              )}
              <audio
                ref={(el) => {
                  mediaRef.current = el;
                }}
                controls
                className="w-full max-w-md"
                src={fileUrl}
              />
            </div>
          ) : isVideo ? (
            <video
              ref={(el) => {
                mediaRef.current = el;
              }}
              controls
              className="max-h-[420px] w-full"
              src={fileUrl}
            />
          ) : (
            <div className="p-8 text-center space-y-3">
              <FileText className="w-12 h-12 mx-auto text-[#d4af37]/60" />
              <p className="text-sm font-medium text-white">{memory.original_filename}</p>
              <a
                href={fileUrl}
                download={memory.original_filename}
                className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[#1a2233] text-[#d4af37] border border-[#d4af37]/30 hover:bg-[#232e44] transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                Download Original Document
              </a>
            </div>
          )}
        </div>

        {/* Phase 3: Speech-to-Text & Transcript Section (Audio / Video only) */}
        {(isAudio || isVideo) && (
          <div className="mt-6 p-5 rounded-xl bg-[#090c12] border border-[#1e2535] space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#181f2c]">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-[#d4af37]/15 border border-[#d4af37]/30 text-[#d4af37]">
                  <Mic className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-serif font-bold text-white flex items-center gap-2">
                    Speech-to-Text & Diarization
                    {transcript && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/60 text-emerald-400 border border-emerald-500/30">
                        {transcript.detected_language ? transcript.detected_language.toUpperCase() : 'TRANSCRIPT'}
                      </span>
                    )}
                  </h3>
                  <p className="text-xs text-[#8e9bb0]">
                    Local faster-whisper transcription with timestamped speaker segments.
                  </p>
                </div>
              </div>

              {transcript && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopyTranscript}
                    className="flex items-center gap-1 px-2.5 py-1 rounded text-xs bg-[#161d2b] border border-[#263145] text-[#b8c5d9] hover:text-[#d4af37] transition-colors"
                    title="Copy complete transcript text"
                  >
                    {copiedTranscript ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedTranscript ? 'Copied' : 'Copy'}</span>
                  </button>
                  <button
                    onClick={() => setIsEditingTranscript(!isEditingTranscript)}
                    className="flex items-center gap-1 px-2.5 py-1 rounded text-xs bg-[#161d2b] border border-[#263145] text-[#b8c5d9] hover:text-[#d4af37] transition-colors"
                  >
                    <Edit2 className="w-3 h-3" />
                    <span>{isEditingTranscript ? 'Done Editing' : 'Edit Segments'}</span>
                  </button>
                  <button
                    onClick={handleDeleteTranscript}
                    className="p-1 rounded text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 transition-colors"
                    title="Delete Transcript"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>

            {transcriptSaveMsg && (
              <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/40 text-xs text-emerald-300 flex items-center gap-2">
                <Check className="w-4 h-4" />
                <span>{transcriptSaveMsg}</span>
              </div>
            )}

            {/* Active Transcription Job Progress Card */}
            {isJobActive && (
              <div className="p-4 rounded-xl bg-[#0e131d] border border-[#d4af37]/30 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-[#f3d87b] flex items-center gap-2">
                    <RotateCw className="w-3.5 h-3.5 animate-spin text-[#d4af37]" />
                    {activeJob.current_stage || 'Processing oral history...'}
                  </span>
                  <span className="font-mono text-white font-bold">{Math.round(activeJob.progress)}%</span>
                </div>
                <div className="w-full bg-[#161c28] rounded-full h-2 overflow-hidden border border-[#252f40]">
                  <div
                    className="bg-gradient-to-r from-[#d4af37] to-[#f3d87b] h-full transition-all duration-300"
                    style={{ width: `${Math.max(5, activeJob.progress)}%` }}
                  />
                </div>
                <div className="flex items-center justify-between text-[11px] text-[#6d7c92]">
                  <span>Model: {activeJob.model_name} (CPU int8)</span>
                  <button
                    onClick={handleCancelJob}
                    className="text-rose-400 hover:text-rose-300 underline"
                  >
                    Cancel Processing
                  </button>
                </div>
              </div>
            )}

            {/* If no transcript and not currently running: Trigger Card */}
            {!transcript && !isJobActive && (
              <div className="p-4 rounded-xl bg-[#0e131d] border border-[#202838] space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div>
                    <label className="block text-[#8e9bb0] mb-1 font-semibold">Whisper Model</label>
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-[#141a26] border border-[#273347] text-white focus:outline-none focus:border-[#d4af37]"
                    >
                      <option value="base">Base (Recommended ~145MB)</option>
                      <option value="tiny">Tiny (Fast preview ~75MB)</option>
                      <option value="small">Small (High Accuracy ~480MB)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[#8e9bb0] mb-1 font-semibold">Spoken Language</label>
                    <select
                      value={selectedLanguage}
                      onChange={(e) => setSelectedLanguage(e.target.value)}
                      className="w-full px-3 py-1.5 rounded-lg bg-[#141a26] border border-[#273347] text-white focus:outline-none focus:border-[#d4af37]"
                    >
                      <option value="auto">Auto-detect Language</option>
                      <option value="en">English</option>
                      <option value="hi">Hindi (हिंदी)</option>
                    </select>
                  </div>

                  <div className="flex items-center pt-5">
                    <label className="flex items-center gap-2 cursor-pointer text-xs text-[#b8c5d9]">
                      <input
                        type="checkbox"
                        checked={enableDiarization}
                        onChange={(e) => setEnableDiarization(e.target.checked)}
                        className="rounded border-[#273347] text-[#d4af37] focus:ring-0"
                      />
                      <span>Cluster Multiple Speakers (Experimental)</span>
                    </label>
                  </div>
                </div>

                <p className="text-[11px] text-[#f3d87b]/80 bg-[#161a24] p-2 rounded-lg border border-[#273245]">
                  Note: Speaker diarization uses heuristic acoustic grouping and may be inaccurate. Unknown speakers remain anonymous until manually mapped to a family member.
                </p>

                <div className="flex items-center justify-between pt-2">
                  <p className="text-[11px] text-[#6d7c92]">
                    Processes 100% locally on CPU with int8 quantization. No audio uploaded anywhere.
                  </p>
                  <button
                    onClick={handleStartTranscription}
                    disabled={isSubmittingJob}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b] transition-colors disabled:opacity-50"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    {isSubmittingJob ? 'Queueing...' : 'Transcribe Audio'}
                  </button>
                </div>
              </div>
            )}

            {/* Display Transcript Segments & Interactive Synchronizer */}
            {transcript && (
              <div className="space-y-3">
                {/* Transcript Meta Summary */}
                <div className="flex flex-wrap items-center gap-3 text-xs text-[#8e9bb0]">
                  <span className="text-white font-medium">
                    {transcript.segments?.length || 0} Segments
                  </span>
                  <span>•</span>
                  <span>Model: {transcript.model_name || 'base'}</span>
                  {transcript.processing_duration && (
                    <>
                      <span>•</span>
                      <span>Completed in {transcript.processing_duration}s</span>
                    </>
                  )}
                  {transcript.detected_language && (
                    <>
                      <span>•</span>
                      <span>Detected: {transcript.detected_language.toUpperCase()}</span>
                    </>
                  )}
                </div>

                {/* Segments Timeline List */}
                <div className="max-h-80 overflow-y-auto space-y-2.5 pr-2">
                  {editableSegments.map((seg, idx) => {
                    const matchedPerson = people.find((p) => p.id === seg.speaker_id);
                    return (
                      <div
                        key={seg.id || idx}
                        className="p-3 rounded-lg bg-[#0d121c] border border-[#1b2230] hover:border-[#2e3b52] transition-colors"
                      >
                        <div className="flex items-center justify-between gap-2 mb-1.5 flex-wrap">
                          <button
                            onClick={() => handleSeek(seg.start_time)}
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono bg-[#161f2e] text-[#f3d87b] border border-[#d4af37]/30 hover:bg-[#202b3d] transition-colors"
                            title="Jump audio player to this segment"
                          >
                            <Play className="w-3 h-3 text-[#d4af37]" />
                            {formatTimestamp(seg.start_time)} - {formatTimestamp(seg.end_time)}
                          </button>

                          {isEditingTranscript ? (
                            <div className="flex items-center gap-2">
                              {/* Custom label input */}
                              <input
                                type="text"
                                value={seg.speaker_label}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setEditableSegments((prev) =>
                                    prev.map((s, i) => (i === idx ? { ...s, speaker_label: val } : s))
                                  );
                                }}
                                className="px-2 py-0.5 rounded text-[11px] bg-[#141a26] border border-[#2a364a] text-white w-28 focus:outline-none focus:border-[#d4af37]"
                                placeholder="Speaker Label"
                              />

                              {/* Assign to Person */}
                              <select
                                value={seg.speaker_id || ''}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  setEditableSegments((prev) =>
                                    prev.map((s, i) => (i === idx ? { ...s, speaker_id: val || null } : s))
                                  );
                                }}
                                className="px-2 py-0.5 rounded text-[11px] bg-[#141a26] border border-[#2a364a] text-[#b8c5d9] focus:outline-none focus:border-[#d4af37]"
                              >
                                <option value="">Assign to Person...</option>
                                {people.map((p) => (
                                  <option key={p.id} value={p.id}>
                                    {p.full_name}
                                  </option>
                                ))}
                              </select>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2">
                              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium bg-[#141d2c] text-[#f3d87b] border border-[#2b374a]">
                                <span className="w-1.5 h-1.5 rounded-full bg-[#d4af37]" />
                                {matchedPerson ? matchedPerson.full_name : seg.speaker_label}
                              </span>

                              {/* Voice enrollment button if matched to a person */}
                              {matchedPerson && (
                                <button
                                  onClick={() => handleEnrollSpeakerProfile(seg, matchedPerson)}
                                  className="inline-flex items-center gap-1 text-[10px] text-[#8e9bb0] hover:text-[#d4af37] transition-colors"
                                  title={`Enroll this voice sample for ${matchedPerson.full_name}`}
                                >
                                  <UserCheck className="w-3 h-3" />
                                  Enroll Voice
                                </button>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Segment Text */}
                        {isEditingTranscript ? (
                          <textarea
                            rows={2}
                            value={seg.text}
                            onChange={(e) => {
                              const val = e.target.value;
                              setEditableSegments((prev) =>
                                prev.map((s, i) => (i === idx ? { ...s, text: val } : s))
                              );
                            }}
                            className="w-full px-2.5 py-1.5 rounded bg-[#131924] border border-[#273347] text-xs text-white leading-relaxed focus:outline-none focus:border-[#d4af37]"
                          />
                        ) : (
                          <p className="text-xs text-[#dce2ec] leading-relaxed font-light">
                            {seg.text}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>

                {isEditingTranscript && (
                  <div className="pt-2 flex items-center justify-end gap-2 border-t border-[#181f2c]">
                    <button
                      onClick={() => {
                        setEditableSegments(transcript.segments);
                        setIsEditingTranscript(false);
                      }}
                      className="px-3 py-1.5 rounded-lg text-xs text-[#8e9bb0] hover:text-white bg-[#141924]"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveTranscriptEdits}
                      disabled={isSaving}
                      className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b] transition-colors"
                    >
                      <Save className="w-3.5 h-3.5" />
                      {isSaving ? 'Saving...' : 'Save Transcript Changes'}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Consent & Biometric Enrollment Dialog */}
            {speakerConsentPerson && enrollTargetSegment && (
              <div className="p-4 rounded-xl bg-[#111724] border border-[#d4af37]/40 space-y-3 mt-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#f3d87b]">
                  <ShieldCheck className="w-4 h-4 text-[#d4af37]" />
                  <span>Biometric Voice Enrollment: {speakerConsentPerson.full_name}</span>
                </div>
                <p className="text-xs text-[#9db0cc] leading-relaxed">
                  Voice profiles extract acoustic characteristics to identify family members in future recordings.
                  In accordance with privacy requirements, explicit consent is required before saving voice profiles.
                </p>
                {enrollStatusMsg && (
                  <p className="text-xs font-medium text-[#f3d87b]">{enrollStatusMsg}</p>
                )}
                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    onClick={() => {
                      setSpeakerConsentPerson(null);
                      setEnrollTargetSegment(null);
                      setEnrollStatusMsg(null);
                    }}
                    className="px-3 py-1 rounded-lg text-xs text-[#8e9bb0] hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleGrantConsentAndEnroll}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b] transition-colors"
                  >
                    Grant Consent & Enroll Voice
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Edit Form or Display Fields */}
        {isEditing ? (
          <div className="mt-5 space-y-4 p-4 rounded-xl bg-[#0b0e14] border border-[#232b3c]">
            <div>
              <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1">
                Narrative / Description
              </label>
              <textarea
                rows={3}
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#111622] border border-[#273347] text-white text-xs focus:border-[#d4af37] focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1">
                  Location
                </label>
                <input
                  type="text"
                  value={editLocation}
                  onChange={(e) => setEditLocation(e.target.value)}
                  placeholder="e.g. Grandma's Homestead"
                  className="w-full px-3 py-2 rounded-lg bg-[#111622] border border-[#273347] text-white text-xs focus:border-[#d4af37] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1">
                  Event Date
                </label>
                <input
                  type="date"
                  value={editEventDate}
                  onChange={(e) => setEditEventDate(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#111622] border border-[#273347] text-white text-xs focus:border-[#d4af37] focus:outline-none"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1">
                  Tags (comma separated)
                </label>
                <input
                  type="text"
                  value={editTags}
                  onChange={(e) => setEditTags(e.target.value)}
                  placeholder="family, interview, childhood"
                  className="w-full px-3 py-2 rounded-lg bg-[#111622] border border-[#273347] text-white text-xs focus:border-[#d4af37] focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1">
                  Privacy Level
                </label>
                <select
                  value={editPrivacy}
                  onChange={(e) => setEditPrivacy(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#111622] border border-[#273347] text-white text-xs focus:border-[#d4af37] focus:outline-none"
                >
                  <option value="private">Private (Only me)</option>
                  <option value="family">Family (Trusted circle)</option>
                  <option value="archive">Archive (Permanent record)</option>
                </select>
              </div>
            </div>

            {people.length > 0 && (
              <div>
                <label className="block text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1">
                  Connected People
                </label>
                <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                  {people.map((p) => {
                    const isSelected = editPeople.includes(p.id);
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => {
                          setEditPeople((prev) =>
                            prev.includes(p.id) ? prev.filter((id) => id !== p.id) : [...prev, p.id]
                          );
                        }}
                        className={`px-2 py-0.5 rounded text-[11px] ${
                          isSelected
                            ? 'bg-[#d4af37] text-black font-semibold'
                            : 'bg-[#182030] text-[#8e9bb0] hover:text-white'
                        }`}
                      >
                        {p.full_name}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#1a202c]">
              <button
                onClick={() => setIsEditing(false)}
                className="px-3.5 py-1.5 rounded-lg text-xs text-[#8e9bb0] hover:text-white bg-[#141924]"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold bg-[#d4af37] text-black hover:bg-[#f3d87b]"
              >
                <Save className="w-3.5 h-3.5" />
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Description & Narrative */}
            {memory.description && (
              <div className="mt-5 p-4 rounded-xl bg-[#0b0e14] border border-[#1b212f]">
                <h4 className="text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-1.5">
                  Narrative & Preservation Notes
                </h4>
                <p className="text-sm text-[#dce2ec] leading-relaxed whitespace-pre-line font-light">
                  {memory.description}
                </p>
              </div>
            )}

            {/* Extracted Document Text Preview */}
            {memory.extracted_text && (
              <div className="mt-4 p-4 rounded-xl bg-[#080a0e] border border-[#1c2230]">
                <div className="flex items-center justify-between mb-2 pb-2 border-b border-[#181e2b]">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-[#d4af37]" />
                    <span className="text-xs font-semibold text-white uppercase tracking-wider">
                      Extracted Document Text
                    </span>
                  </div>
                  <button
                    onClick={handleCopyExtractedText}
                    className="flex items-center gap-1 text-[11px] text-[#8e9bb0] hover:text-[#d4af37] transition-colors"
                  >
                    {copiedText ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-400" />
                        <span className="text-emerald-400">Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" />
                        <span>Copy Text</span>
                      </>
                    )}
                  </button>
                </div>
                <div className="max-h-56 overflow-y-auto text-xs text-[#b8c5d9] font-mono whitespace-pre-wrap leading-relaxed pr-2">
                  {memory.extracted_text}
                </div>
              </div>
            )}

            {/* Metadata Grid */}
            <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-[#0b0e14] border border-[#1c2230] flex items-center gap-2.5">
                <Calendar className="w-4 h-4 text-[#d4af37] shrink-0" />
                <div>
                  <span className="text-[#6d7c92] block">Event Date:</span>
                  <span className="text-white font-medium">
                    {memory.event_date ? new Date(memory.event_date).toLocaleDateString() : 'Undated'}
                  </span>
                </div>
              </div>

              {memory.width && memory.height && (
                <div className="p-3 rounded-lg bg-[#0b0e14] border border-[#1c2230] flex items-center gap-2.5">
                  <FileText className="w-4 h-4 text-[#d4af37] shrink-0" />
                  <div>
                    <span className="text-[#6d7c92] block">Dimensions:</span>
                    <span className="text-white font-medium">
                      {memory.width} × {memory.height} px
                    </span>
                  </div>
                </div>
              )}

              {memory.duration_seconds && (
                <div className="p-3 rounded-lg bg-[#0b0e14] border border-[#1c2230] flex items-center gap-2.5">
                  <Clock className="w-4 h-4 text-[#d4af37] shrink-0" />
                  <div>
                    <span className="text-[#6d7c92] block">Duration:</span>
                    <span className="text-white font-medium">
                      {formatDuration(memory.duration_seconds)}
                    </span>
                  </div>
                </div>
              )}

              <div className="p-3 rounded-lg bg-[#0b0e14] border border-[#1c2230] flex items-center gap-2.5">
                <HardDrive className="w-4 h-4 text-[#d4af37] shrink-0" />
                <div>
                  <span className="text-[#6d7c92] block">Size & Format:</span>
                  <span className="text-white font-medium">
                    {(memory.file_size / 1024 / 1024).toFixed(2)} MB • {memory.mime_type}
                  </span>
                </div>
              </div>

              {memory.sha256_hash && (
                <div className="p-3 rounded-lg bg-[#0b0e14] border border-[#1c2230] flex items-center gap-2.5 sm:col-span-2">
                  <Hash className="w-4 h-4 text-[#d4af37] shrink-0" />
                  <div className="min-w-0">
                    <span className="text-[#6d7c92] block">SHA-256 Hash:</span>
                    <span className="text-[#b8c5d9] font-mono text-[11px] truncate block" title={memory.sha256_hash}>
                      {memory.sha256_hash}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Tags Badges */}
            {memory.tags && memory.tags.length > 0 && (
              <div className="mt-4">
                <span className="text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <TagIcon className="w-3.5 h-3.5 text-[#d4af37]" />
                  Preserved Tags
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {memory.tags.map((t) => (
                    <span
                      key={t.id}
                      className="px-2.5 py-0.5 rounded-md text-xs font-medium bg-[#141d2c] text-[#f3d87b] border border-[#d4af37]/30"
                    >
                      #{t.name}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Associated People */}
            {memory.people && memory.people.length > 0 && (
              <div className="mt-4">
                <span className="text-xs font-semibold text-[#8e9bb0] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-[#d4af37]" />
                  Connected Individuals ({memory.people.length})
                </span>
                <div className="flex flex-wrap gap-2">
                  {memory.people.map((p) => (
                    <span
                      key={p.id}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs bg-[#161c28] border border-[#252f40] text-white"
                    >
                      <span className="w-1.5 h-1.5 rounded-full bg-[#d4af37]" />
                      {p.full_name}
                      {p.relationship && (
                        <span className="text-[#8e9bb0] text-[11px]">({p.relationship})</span>
                      )}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Footer Actions */}
        <div className="mt-6 pt-4 border-t border-[#202738] flex items-center justify-between">
          <div>
            {confirmDelete ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-rose-400 font-semibold flex items-center gap-1">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Irreversible! Confirm?
                </span>
                <button
                  onClick={handleDelete}
                  disabled={isDeleting}
                  className="px-3 py-1 rounded-lg text-xs font-semibold bg-rose-600 text-white hover:bg-rose-500 transition-colors"
                >
                  {isDeleting ? 'Deleting...' : 'Yes, Delete Permanently'}
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-3 py-1 rounded-lg text-xs text-[#8e9bb0] hover:text-white"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmDelete(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 transition-colors"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete Memory
              </button>
            )}
          </div>

          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl text-xs font-semibold bg-[#1a2233] text-[#f3d87b] border border-[#d4af37]/30 hover:bg-[#232e44] transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
