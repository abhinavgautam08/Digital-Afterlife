# Speaker Consent & Voice Biometrics Framework

**Digital Afterlife – Memory Keeper**  
**Subsystem**: Speaker Consent & Privacy Compliance  
**Standard**: Strict User Sovereignty & Zero Cloud Biometrics

---

## 1. Ethical Principles

Voice recordings of ancestors and family members represent sensitive biometric data. In **Digital Afterlife**, the following invariants are enforced:

1. **Anonymous by Default**: Transcription generates anonymous speaker labels (`Speaker 1`, `Speaker 2`) without identifying individuals.
2. **Mandatory Prior Consent**: A voice signature or biometric profile CANNOT be stored for any person unless an explicit consent record exists with `consent_given = True`.
3. **Local Storage Only**: Voice feature vectors are stored strictly in the local SQLite database. They are never transmitted over the network.
4. **Immediate Deletion on Revocation**: Revoking consent immediately and permanently purges all associated voice profiles and biometric vectors.

---

## 2. Data Models

### `SpeakerConsent`
| Column | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Unique UUID identifier |
| `person_id` | `VARCHAR(36)` | Foreign key to `people.id` (Unique, Cascading) |
| `consent_given` | `BOOLEAN` | Whether affirmative consent has been granted |
| `consent_notes` | `TEXT` | Audit notes (e.g. "Oral history consent signed") |
| `consent_date` | `DATETIME` | Timestamp when consent was granted |
| `revoked_at` | `DATETIME` | Nullable timestamp when consent was revoked |

### `SpeakerProfile`
| Column | Type | Description |
|---|---|---|
| `id` | `VARCHAR(36)` | Unique UUID identifier |
| `person_id` | `VARCHAR(36)` | Foreign key to `people.id` (Unique, Cascading) |
| `voice_signature` | `TEXT` | JSON-serialized 20-dimensional normalized acoustic vector |
| `sample_count` | `INTEGER` | Number of audio segments averaged into profile |
| `created_at` | `DATETIME` | Creation timestamp |
| `updated_at` | `DATETIME` | Last update timestamp |

---

## 3. Enforcement Workflow

```
[User clicks "Enroll Voice Profile" in UI]
              │
              ▼
   Has explicit consent been granted?
         ├── NO ──► Block enrollment (HTTP 403 Forbidden)
         │          Prompt user to review consent agreement
         │
         └── YES ─► Extract 20-D acoustic feature signature
                    Store in `speaker_profiles`
                    Update `sample_count`
```

---

## 4. Revocation & Purge Protocol

When a user calls `POST /api/people/{id}/consent` with `consent_given = False`:
1. `SpeakerConsent.consent_given` is set to `False`.
2. `SpeakerConsent.revoked_at` is set to `now()`.
3. The matching row in `speaker_profiles` is hard-deleted immediately:
   ```python
   db.query(SpeakerProfile).filter(SpeakerProfile.person_id == person_id).delete()
   db.commit()
   ```
4. All future diarization matching skips this individual.

