"""
Storytelling and Memory Preservation Service for Digital Afterlife.
Phase 5: Grounded Biographies, Life Timelines, Memory Stories, Collections, and Remembrance Pages.

Ethical & Architecture Safeguards:
- 100% offline-first; no remote AI services or external transmission.
- Uses existing local Ollama (qwen2.5:3b) when online; clear offline errors when unavailable.
- Zero deceased impersonation: third-person only, never first-person ("I").
- Zero fabricated quotes, conversations, or dates.
- Strict cross-person memory isolation: rejects memories belonging to other individuals.
- Original memory files remain strictly immutable.
"""
import json
import uuid
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.models.person import Person
from backend.app.models.memory import Memory, MemoryPerson
from backend.app.models.transcript import Transcript
from backend.app.models.storytelling import (
    StoryArtifact,
    ArtifactSourceMemory,
    TimelineEvent,
    TimelineEventMemory,
    MemoryCollection,
    CollectionMemory,
    RemembrancePage,
    utc_now,
)
from backend.app.schemas.storytelling import (
    BiographyGenerateRequest,
    BiographySection,
    StoryGenerateRequest,
    TimelineGenerateRequest,
    TimelineEventCreate,
    TimelineEventUpdate,
    TimelineEventResponse,
    StoryArtifactUpdate,
    StoryArtifactResponse,
    SourceMemoryInfo,
    RemembrancePageCreate,
    RemembrancePageUpdate,
    RemembrancePageResponse,
    CollectionCreate,
    CollectionUpdate,
    CollectionItemAdd,
    CollectionResponse,
)
from backend.app.services.ai_service import ai_service
from backend.app.services.rag.rag_service import sanitize_untrusted_evidence


class StorytellingError(Exception):
    """Base error for storytelling operations."""
    pass


class PersonNotFoundError(StorytellingError):
    """Raised when a person record cannot be found."""
    pass


class CrossPersonMemoryError(StorytellingError):
    """Raised when a memory does not belong to the requested person."""
    pass


class InsufficientEvidenceError(StorytellingError):
    """Raised when there is not enough documented material to generate a requested artifact."""
    pass


class ModelUnavailableError(StorytellingError):
    """Raised when local Ollama is offline or uninstalled."""
    pass


class StorytellingService:
    """
    Manages grounded generation and persistence of biographies, stories, timelines,
    remembrance pages, and memory collections.
    """

    SYSTEM_PROMPT_BIOGRAPHY = """You are Digital Afterlife Biographer, an archivist creating an evidence-grounded biography of a family member.

NON-NEGOTIABLE RULES:
1. THIRD-PERSON ONLY: Always write respectfully about the person in the third person (e.g., "Ramesh was born in...", "She spent her youth in..."). NEVER use first-person voice ("I", "me", "my", "mine").
2. NO IMPERSONATION: NEVER pretend to be the person or speak as if the deceased is talking to the reader.
3. GROUNDING: Base every statement strictly on the provided <source_evidence> blocks.
4. NO FABRICATION: Do NOT invent missing dates, locations, family members, emotions, or achievements. If a detail is missing, omit it or state that it is not documented.
5. NO FABRICATED QUOTES: NEVER invent dialogue or words in someone's mouth. If quoting a preserved letter or transcript, attribute it clearly with quotation marks.
6. FORMAT: Output structured sections as requested.
"""

    SYSTEM_PROMPT_STORY = """You are Digital Afterlife Memory Narrator, preserving family memories as coherent, respectful narratives.

NON-NEGOTIABLE RULES:
1. THIRD-PERSON ONLY: Write the narrative ABOUT the person and the documented moments. NEVER write in the first-person voice of the deceased or family member.
2. NO IMPERSONATION: Do not pretend the person is speaking.
3. STRICT FACTUAL GROUNDING: Rely strictly on the details provided in <source_evidence>.
4. NO INVENTED DIALOGUE: Never create fictional conversations or quotes. Only reproduce authentic quotes found directly in the evidence.
5. RESPECTFUL & HONEST: If memories are fragmented, embrace the fragments honestly without filling blanks with imaginary events.
"""

    # -------------------------------------------------------------------------
    # Validation & Evidence Assembly
    # -------------------------------------------------------------------------

    def validate_person(self, db: Session, person_id: str) -> Person:
        """Ensures the person exists in the database."""
        person = db.query(Person).filter(Person.id == person_id).first()
        if not person:
            raise PersonNotFoundError(f"Person with ID '{person_id}' was not found.")
        return person

    def get_and_validate_person_memories(
        self,
        db: Session,
        person_id: str,
        requested_memory_ids: Optional[List[str]] = None,
    ) -> List[Memory]:
        """
        Retrieves memories associated with person_id.
        Strictly rejects cross-person memories if requested_memory_ids contains any
        memory not linked to person_id.
        """
        person = self.validate_person(db, person_id)

        # Query all memory IDs linked to this person
        linked_records = (
            db.query(MemoryPerson.memory_id)
            .filter(MemoryPerson.person_id == person_id)
            .all()
        )
        linked_set = {r[0] for r in linked_records}

        if requested_memory_ids is not None:
            # Check for invalid or cross-person memory IDs
            for mid in requested_memory_ids:
                if mid not in linked_set:
                    # Check if memory exists at all to provide precise error
                    mem_exists = db.query(Memory.id).filter(Memory.id == mid).first()
                    if not mem_exists:
                        raise CrossPersonMemoryError(f"Memory '{mid}' does not exist.")
                    raise CrossPersonMemoryError(
                        f"Memory '{mid}' is not associated with person '{person.full_name}' ({person_id}). "
                        "Cross-person memory access is strictly prohibited."
                    )
            target_ids = requested_memory_ids
        else:
            target_ids = list(linked_set)

        if not target_ids:
            return []

        memories = (
            db.query(Memory)
            .filter(Memory.id.in_(target_ids))
            .order_by(Memory.event_date.asc().nullslast(), Memory.created_at.asc())
            .all()
        )
        return memories

    def assemble_evidence_text(self, db: Session, memories: List[Memory]) -> Tuple[str, List[SourceMemoryInfo]]:
        """
        Extracts and sanitizes text evidence from memories, documents, and transcripts.
        Returns a formatted evidence block and structured SourceMemoryInfo list.
        """
        evidence_blocks = []
        source_infos: List[SourceMemoryInfo] = []

        for idx, mem in enumerate(memories, start=1):
            date_str = mem.event_date.strftime("%Y-%m-%d") if mem.event_date else (
                mem.original_created_at.strftime("%Y-%m-%d") if mem.original_created_at else "Undated"
            )
            loc_str = mem.location or "Unknown location"
            text_parts = [f"Title: {mem.title}", f"Type: {mem.memory_type}", f"Date: {date_str}", f"Location: {loc_str}"]

            from backend.app.services.encryption.field_cipher import decrypt_field
            dec_desc = decrypt_field(mem.description)
            dec_text = decrypt_field(mem.extracted_text)

            if dec_desc:
                text_parts.append(f"Description: {dec_desc}")
            if dec_text:
                text_parts.append(f"Document Text: {dec_text}")

            # Transcripts
            transcripts = db.query(Transcript).filter(Transcript.memory_id == mem.id).all()
            for t in transcripts:
                dec_trans = decrypt_field(t.transcript_text)
                if dec_trans:
                    text_parts.append(f"Audio Transcript: {dec_trans}")

            full_block_text = "\n".join(text_parts)
            sanitized = sanitize_untrusted_evidence(full_block_text)
            evidence_blocks.append(f"<source_evidence id=\"{idx}\" memory_id=\"{mem.id}\">\n{sanitized}\n</source_evidence>")

            excerpt = dec_desc or (dec_text[:120] if dec_text else mem.title)
            source_infos.append(
                SourceMemoryInfo(
                    memory_id=mem.id,
                    title=mem.title,
                    memory_type=mem.memory_type,
                    original_filename=mem.original_filename,
                    event_date=date_str if date_str != "Undated" else None,
                    location=mem.location,
                    excerpt=excerpt[:150] if excerpt else "",
                    evidence_classification="documented_fact"
                )
            )

        return "\n\n".join(evidence_blocks), source_infos

    def check_ollama_available(self) -> None:
        """Verifies local Ollama daemon is running. Never silently bypasses or invents AI output."""
        status = ai_service.check_status()
        if not status.ollama_running:
            raise ModelUnavailableError(
                "Local Ollama daemon is offline or unreachable at "
                f"{settings.OLLAMA_BASE_URL}. Start Ollama locally to enable AI generation."
            )

    # -------------------------------------------------------------------------
    # Biography Generation
    # -------------------------------------------------------------------------

    def generate_biography(
        self,
        db: Session,
        req: BiographyGenerateRequest,
    ) -> StoryArtifactResponse:
        """
        Generates a structured biography grounded strictly in the person's documented memories.
        """
        person = self.validate_person(db, req.person_id)
        memories = self.get_and_validate_person_memories(db, req.person_id, req.source_memory_ids)

        if not memories:
            msg = "Not enough saved information to create this section reliably. Add more memories or documents and try again."
            # Create a draft artifact with insufficient evidence warning
            artifact = StoryArtifact(
                id=str(uuid.uuid4()),
                person_id=person.id,
                artifact_type="biography",
                title=f"Biography: {person.full_name} (Insufficient Evidence)",
                content=msg,
                language=req.language,
                tone=req.tone,
                generation_status="failed",
                approval_status="rejected",
                evidence_coverage=0.0,
                warning=msg
            )
            db.add(artifact)
            db.commit()
            db.refresh(artifact)
            return self._build_artifact_response(artifact, [])

        self.check_ollama_available()
        evidence_text, source_infos = self.assemble_evidence_text(db, memories)

        sections = req.sections_to_include or [
            "Early Life & Origins",
            "Family & Relationships",
            "Education & Career",
            "Passions & Character",
            "Key Milestones",
            "Enduring Legacy"
        ]

        length_desc = {
            "short": "concise, 2-3 brief paragraphs total",
            "medium": "balanced narrative, 1-2 paragraphs per section",
            "detailed": "comprehensive narrative, detailed exploration of all evidence"
        }.get(req.length, "balanced narrative")

        lang_instruction = "Write in English."
        if req.language == "hi":
            lang_instruction = "Write in Hindi (हिंदी) with warm, respectful phrasing."

        user_prompt = (
            f"Subject Person: {person.full_name} ({person.relationship or 'Family Member'})\n"
            f"Requested Length: {length_desc}\n"
            f"Tone: {req.tone}\n"
            f"Language: {lang_instruction}\n"
            f"Requested Sections: {', '.join(sections)}\n\n"
            f"Retrieved Evidence:\n{evidence_text}\n\n"
            "Write an authentic biography strictly grounded in the evidence above. "
            "Write about the person in the third person. "
            "For each section, if there is no supporting evidence in the memories, write: "
            "\"Not enough saved information to create this section reliably.\"\n"
            "Do not invent any details."
        )

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "system": self.SYSTEM_PROMPT_BIOGRAPHY,
                        "prompt": user_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                            "top_p": 0.9,
                        }
                    }
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

                raw_content = resp.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama biography generation failed: {e}")
            raise ModelUnavailableError(f"Local AI inference failed: {e}")

        # Post-generation ethical & grounding audit
        sanitized_content, was_neutralized = self._enforce_third_person_and_ethics(raw_content, person.full_name)

        # Parse sections
        parsed_sections = self._parse_biography_sections(sanitized_content, sections, [m.id for m in memories])

        warning_msg = None
        if was_neutralized:
            warning_msg = "First-person narrative detected and neutralized to third-person archivist voice."

        artifact = StoryArtifact(
            id=str(uuid.uuid4()),
            person_id=person.id,
            artifact_type="biography",
            title=f"Life Biography: {person.full_name}",
            content=sanitized_content,
            sections_json=json.dumps([s.model_dump() for s in parsed_sections]),
            language=req.language,
            tone=req.tone,
            model_name=settings.OLLAMA_MODEL,
            generation_status="completed",
            approval_status="pending",
            evidence_coverage=1.0,
            warning=warning_msg
        )
        db.add(artifact)
        db.flush()

        # Link sources
        for s in source_infos:
            assoc = ArtifactSourceMemory(
                artifact_id=artifact.id,
                memory_id=s.memory_id,
                relevance_note="Biographical evidence",
                evidence_classification="documented_fact"
            )
            db.add(assoc)

        db.commit()
        db.refresh(artifact)

        return self._build_artifact_response(artifact, source_infos, parsed_sections)

    # -------------------------------------------------------------------------
    # Story Generation
    # -------------------------------------------------------------------------

    def generate_story(
        self,
        db: Session,
        req: StoryGenerateRequest,
    ) -> StoryArtifactResponse:
        """
        Creates a coherent story based on selected memories of a person.
        """
        person = self.validate_person(db, req.person_id)
        memories = self.get_and_validate_person_memories(db, req.person_id, req.source_memory_ids)

        if not memories:
            msg = "Not enough saved information to create this section reliably. Add more memories or documents and try again."
            raise InsufficientEvidenceError(msg)

        self.check_ollama_available()
        evidence_text, source_infos = self.assemble_evidence_text(db, memories)

        story_title = req.title or f"A Story of {person.full_name}"

        lang_instruction = "Write in English."
        if req.language == "hi":
            lang_instruction = "Write in Hindi (हिंदी) with a warm, respectful tone."

        user_prompt = (
            f"Subject Person: {person.full_name}\n"
            f"Story Title: {story_title}\n"
            f"Tone: {req.tone}\n"
            f"Language: {lang_instruction}\n\n"
            f"Retrieved Evidence:\n{evidence_text}\n\n"
            "Write a warm, respectful narrative connecting these specific documented moments. "
            "Write in the THIRD PERSON ABOUT the subject. Never write in first person ('I'). "
            "Never invent fictional dialogue or events not present in the evidence. "
            "Preserve authentic quotes if present with attribution."
        )

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                    json={
                        "model": settings.OLLAMA_MODEL,
                        "system": self.SYSTEM_PROMPT_STORY,
                        "prompt": user_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "top_p": 0.9,
                        }
                    }
                )
                if resp.status_code != 200:
                    raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")

                raw_content = resp.json().get("response", "").strip()
        except Exception as e:
            logger.error(f"Ollama story generation failed: {e}")
            raise ModelUnavailableError(f"Local AI inference failed: {e}")

        sanitized_content, was_neutralized = self._enforce_third_person_and_ethics(raw_content, person.full_name)

        warning_msg = None
        if was_neutralized:
            warning_msg = "First-person narrative detected and neutralized to third-person archivist voice."

        artifact = StoryArtifact(
            id=str(uuid.uuid4()),
            person_id=person.id,
            artifact_type="story",
            title=story_title,
            content=sanitized_content,
            sections_json=None,
            language=req.language,
            tone=req.tone,
            model_name=settings.OLLAMA_MODEL,
            generation_status="completed",
            approval_status="pending",
            evidence_coverage=1.0,
            warning=warning_msg
        )
        db.add(artifact)
        db.flush()

        for s in source_infos:
            assoc = ArtifactSourceMemory(
                artifact_id=artifact.id,
                memory_id=s.memory_id,
                relevance_note="Story scene evidence",
                evidence_classification="documented_fact"
            )
            db.add(assoc)

        db.commit()
        db.refresh(artifact)

        return self._build_artifact_response(artifact, source_infos)

    # -------------------------------------------------------------------------
    # Timeline Generation & Management
    # -------------------------------------------------------------------------

    def generate_timeline(
        self,
        db: Session,
        req: TimelineGenerateRequest,
    ) -> List[TimelineEventResponse]:
        """
        Extracts chronological milestone events from documented memories.
        Does NOT invent dates or guess missing years.
        """
        person = self.validate_person(db, req.person_id)
        memories = self.get_and_validate_person_memories(db, req.person_id, req.source_memory_ids)

        if not memories:
            return []

        # Delete previously generated unconfirmed ai_suggested events for this person
        db.query(TimelineEvent).filter(
            TimelineEvent.person_id == person.id,
            TimelineEvent.verification_status == "ai_suggested"
        ).delete()
        db.flush()

        created_events: List[TimelineEvent] = []

        # Sort memories: dated first, then undated
        sorted_memories = sorted(
            memories,
            key=lambda m: (m.event_date is None, m.event_date, m.original_created_at is None, m.original_created_at)
        )

        for idx, mem in enumerate(sorted_memories):
            # Determine date and confidence strictly based on evidence
            event_dt = mem.event_date
            approx_date: Optional[str] = None
            confidence = "unknown"

            if event_dt:
                confidence = "exact"
                approx_date = event_dt.strftime("%B %d, %Y")
            else:
                # Inspect description for year patterns (e.g., "circa 1965", "1970s")
                desc = mem.description or ""
                year_match = re.search(r'\b(circa\s+\d{4}|\d{4}s|\b(19\d\d|20\d\d)\b)', desc, re.IGNORECASE)
                if year_match:
                    approx_date = year_match.group(0)
                    confidence = "approximate"
                else:
                    approx_date = "Date Unknown"
                    confidence = "unknown"

            title = mem.title
            description = mem.description or f"Archived {mem.memory_type} memory: '{mem.original_filename}'."

            event = TimelineEvent(
                id=str(uuid.uuid4()),
                person_id=person.id,
                title=title,
                event_date=event_dt,
                approximate_date=approx_date,
                date_confidence=confidence,
                description=description,
                verification_status="ai_suggested",
                order_index=idx
            )
            db.add(event)
            db.flush()

            # Link memory
            db.add(TimelineEventMemory(event_id=event.id, memory_id=mem.id))
            created_events.append(event)

        db.commit()

        return [self._build_timeline_event_response(ev) for ev in created_events]

    def get_person_timeline(self, db: Session, person_id: str) -> List[TimelineEventResponse]:
        """Retrieves all timeline events for a person ordered by date and index."""
        self.validate_person(db, person_id)
        events = (
            db.query(TimelineEvent)
            .filter(TimelineEvent.person_id == person_id)
            .order_by(
                TimelineEvent.event_date.asc().nullslast(),
                TimelineEvent.order_index.asc(),
                TimelineEvent.created_at.asc()
            )
            .all()
        )
        return [self._build_timeline_event_response(ev) for ev in events]

    def create_timeline_event(self, db: Session, data: TimelineEventCreate) -> TimelineEventResponse:
        """Manually creates a timeline event."""
        person = self.validate_person(db, data.person_id)

        # Validate source memories belong to this person
        if data.source_memory_ids:
            self.get_and_validate_person_memories(db, person.id, data.source_memory_ids)

        event = TimelineEvent(
            id=str(uuid.uuid4()),
            person_id=data.person_id,
            artifact_id=data.artifact_id,
            title=data.title.strip(),
            event_date=data.event_date,
            approximate_date=data.approximate_date,
            date_confidence=data.date_confidence,
            description=data.description.strip(),
            verification_status=data.verification_status,
            order_index=data.order_index
        )
        db.add(event)
        db.flush()

        if data.source_memory_ids:
            for mid in data.source_memory_ids:
                db.add(TimelineEventMemory(event_id=event.id, memory_id=mid))

        db.commit()
        db.refresh(event)
        return self._build_timeline_event_response(event)

    def update_timeline_event(self, db: Session, event_id: str, data: TimelineEventUpdate) -> TimelineEventResponse:
        """Updates a timeline event (title, date, description, verification status)."""
        event = db.query(TimelineEvent).filter(TimelineEvent.id == event_id).first()
        if not event:
            raise StorytellingError(f"Timeline event '{event_id}' not found.")

        if data.title is not None:
            event.title = data.title.strip()
        if data.event_date is not None:
            event.event_date = data.event_date
        if data.approximate_date is not None:
            event.approximate_date = data.approximate_date
        if data.date_confidence is not None:
            event.date_confidence = data.date_confidence
        if data.description is not None:
            event.description = data.description.strip()
        if data.verification_status is not None:
            event.verification_status = data.verification_status
        if data.order_index is not None:
            event.order_index = data.order_index

        if data.source_memory_ids is not None:
            self.get_and_validate_person_memories(db, event.person_id, data.source_memory_ids)
            db.query(TimelineEventMemory).filter(TimelineEventMemory.event_id == event.id).delete()
            for mid in data.source_memory_ids:
                db.add(TimelineEventMemory(event_id=event.id, memory_id=mid))

        event.updated_at = utc_now()
        db.commit()
        db.refresh(event)
        return self._build_timeline_event_response(event)

    def delete_timeline_event(self, db: Session, event_id: str) -> None:
        """Deletes a timeline event."""
        event = db.query(TimelineEvent).filter(TimelineEvent.id == event_id).first()
        if not event:
            raise StorytellingError(f"Timeline event '{event_id}' not found.")
        db.delete(event)
        db.commit()

    # -------------------------------------------------------------------------
    # Remembrance Pages
    # -------------------------------------------------------------------------

    def get_or_create_remembrance_page(self, db: Session, person_id: str) -> RemembrancePageResponse:
        """Retrieves or initializes a private remembrance page for a person."""
        person = self.validate_person(db, person_id)

        page = db.query(RemembrancePage).filter(RemembrancePage.person_id == person_id).first()
        if not page:
            page = RemembrancePage(
                id=str(uuid.uuid4()),
                person_id=person.id,
                privacy_level="private"
            )
            db.add(page)
            db.commit()
            db.refresh(page)

        return self._build_remembrance_response(db, page)

    def update_remembrance_page(
        self,
        db: Session,
        person_id: str,
        data: RemembrancePageUpdate
    ) -> RemembrancePageResponse:
        """Updates private remembrance page details."""
        person = self.validate_person(db, person_id)
        page = db.query(RemembrancePage).filter(RemembrancePage.person_id == person_id).first()
        if not page:
            page = RemembrancePage(
                id=str(uuid.uuid4()),
                person_id=person.id,
                privacy_level="private"
            )
            db.add(page)

        if data.biography_artifact_id is not None:
            if data.biography_artifact_id:
                bio = db.query(StoryArtifact).filter(
                    StoryArtifact.id == data.biography_artifact_id,
                    StoryArtifact.person_id == person.id
                ).first()
                if not bio:
                    raise StorytellingError("Biography artifact not found or does not belong to this person.")
            page.biography_artifact_id = data.biography_artifact_id or None

        if data.featured_photograph_id is not None:
            if data.featured_photograph_id:
                mem = db.query(Memory).filter(Memory.id == data.featured_photograph_id).first()
                if not mem or mem.memory_type != "photograph":
                    raise StorytellingError("Featured memory must be a valid photograph.")
                is_linked = db.query(MemoryPerson).filter(
                    MemoryPerson.memory_id == mem.id,
                    MemoryPerson.person_id == person.id
                ).first()
                if not is_linked:
                    raise CrossPersonMemoryError(
                        f"Featured photograph '{data.featured_photograph_id}' is not associated with person '{person.full_name}'."
                    )
            page.featured_photograph_id = data.featured_photograph_id or None

        if data.user_personal_notes is not None:
            page.user_personal_notes = data.user_personal_notes.strip()

        page.updated_at = utc_now()
        db.commit()
        db.refresh(page)
        return self._build_remembrance_response(db, page)

    # -------------------------------------------------------------------------
    # Memory Collections
    # -------------------------------------------------------------------------

    def create_collection(self, db: Session, data: CollectionCreate) -> CollectionResponse:
        """Creates a thematic memory collection referencing existing memories."""
        if data.person_id:
            self.validate_person(db, data.person_id)

        col = MemoryCollection(
            id=str(uuid.uuid4()),
            title=data.title.strip(),
            description=data.description.strip() if data.description else None,
            collection_type=data.collection_type,
            person_id=data.person_id,
            cover_memory_id=data.cover_memory_id
        )
        db.add(col)
        db.flush()

        if data.memory_ids:
            seen_ids = set()
            order_idx = 0
            for mid in data.memory_ids:
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
                mem = db.query(Memory).filter(Memory.id == mid).first()
                if mem:
                    db.add(CollectionMemory(collection_id=col.id, memory_id=mid, order_index=order_idx))
                    order_idx += 1

        db.commit()
        db.refresh(col)
        return self._build_collection_response(db, col)

    def list_collections(self, db: Session, person_id: Optional[str] = None) -> List[CollectionResponse]:
        """Lists collections, optionally filtered by person."""
        q = db.query(MemoryCollection)
        if person_id:
            q = q.filter(MemoryCollection.person_id == person_id)
        cols = q.order_by(MemoryCollection.created_at.desc()).all()
        return [self._build_collection_response(db, c) for c in cols]

    def get_collection(self, db: Session, collection_id: str) -> CollectionResponse:
        """Retrieves a single collection with its referenced memories."""
        col = db.query(MemoryCollection).filter(MemoryCollection.id == collection_id).first()
        if not col:
            raise StorytellingError(f"Collection '{collection_id}' not found.")
        return self._build_collection_response(db, col)

    def update_collection(self, db: Session, collection_id: str, data: CollectionUpdate) -> CollectionResponse:
        """Updates collection metadata."""
        col = db.query(MemoryCollection).filter(MemoryCollection.id == collection_id).first()
        if not col:
            raise StorytellingError(f"Collection '{collection_id}' not found.")

        if data.title is not None:
            col.title = data.title.strip()
        if data.description is not None:
            col.description = data.description.strip() if data.description else None
        if data.collection_type is not None:
            col.collection_type = data.collection_type
        if data.person_id is not None:
            if data.person_id:
                self.validate_person(db, data.person_id)
            col.person_id = data.person_id or None
        if data.cover_memory_id is not None:
            col.cover_memory_id = data.cover_memory_id or None

        col.updated_at = utc_now()
        db.commit()
        db.refresh(col)
        return self._build_collection_response(db, col)

    def delete_collection(self, db: Session, collection_id: str) -> None:
        """Deletes a collection without deleting the underlying memories."""
        col = db.query(MemoryCollection).filter(MemoryCollection.id == collection_id).first()
        if not col:
            raise StorytellingError(f"Collection '{collection_id}' not found.")
        db.delete(col)
        db.commit()

    def add_collection_item(self, db: Session, collection_id: str, data: CollectionItemAdd) -> CollectionResponse:
        """Adds a memory reference to a collection."""
        col = db.query(MemoryCollection).filter(MemoryCollection.id == collection_id).first()
        if not col:
            raise StorytellingError(f"Collection '{collection_id}' not found.")

        mem = db.query(Memory).filter(Memory.id == data.memory_id).first()
        if not mem:
            raise StorytellingError(f"Memory '{data.memory_id}' not found.")

        exists = db.query(CollectionMemory).filter(
            CollectionMemory.collection_id == col.id,
            CollectionMemory.memory_id == mem.id
        ).first()

        if not exists:
            db.add(CollectionMemory(
                collection_id=col.id,
                memory_id=mem.id,
                order_index=data.order_index
            ))
            col.updated_at = utc_now()
            db.commit()

        db.refresh(col)
        return self._build_collection_response(db, col)

    def remove_collection_item(self, db: Session, collection_id: str, memory_id: str) -> CollectionResponse:
        """Removes a memory reference from a collection."""
        col = db.query(MemoryCollection).filter(MemoryCollection.id == collection_id).first()
        if not col:
            raise StorytellingError(f"Collection '{collection_id}' not found.")

        db.query(CollectionMemory).filter(
            CollectionMemory.collection_id == col.id,
            CollectionMemory.memory_id == memory_id
        ).delete()
        col.updated_at = utc_now()
        db.commit()
        db.refresh(col)
        return self._build_collection_response(db, col)

    # -------------------------------------------------------------------------
    # Artifact Management (Approval, Edits, Deletion)
    # -------------------------------------------------------------------------

    def get_artifact(self, db: Session, artifact_id: str) -> StoryArtifactResponse:
        """Retrieves a single artifact with its sources."""
        artifact = db.query(StoryArtifact).filter(StoryArtifact.id == artifact_id).first()
        if not artifact:
            raise StorytellingError(f"Artifact '{artifact_id}' not found.")
        return self._build_artifact_response(artifact, self._get_sources_for_artifact(db, artifact.id))

    def update_artifact(self, db: Session, artifact_id: str, data: StoryArtifactUpdate) -> StoryArtifactResponse:
        """Updates artifact content, title, or user approval status."""
        artifact = db.query(StoryArtifact).filter(StoryArtifact.id == artifact_id).first()
        if not artifact:
            raise StorytellingError(f"Artifact '{artifact_id}' not found.")

        if data.title is not None:
            artifact.title = data.title.strip()
        if data.content is not None:
            artifact.content = data.content.strip()
        if data.approval_status is not None:
            artifact.approval_status = data.approval_status
        if data.sections_json is not None:
            artifact.sections_json = data.sections_json

        artifact.updated_at = utc_now()
        db.commit()
        db.refresh(artifact)
        return self._build_artifact_response(artifact, self._get_sources_for_artifact(db, artifact.id))

    def delete_artifact(self, db: Session, artifact_id: str) -> None:
        """Deletes an artifact without modifying any original memory files."""
        artifact = db.query(StoryArtifact).filter(StoryArtifact.id == artifact_id).first()
        if not artifact:
            raise StorytellingError(f"Artifact '{artifact_id}' not found.")
        db.delete(artifact)
        db.commit()

    def list_person_artifacts(self, db: Session, person_id: str) -> List[StoryArtifactResponse]:
        """Lists all artifacts for a specific person."""
        self.validate_person(db, person_id)
        artifacts = (
            db.query(StoryArtifact)
            .filter(StoryArtifact.person_id == person_id)
            .order_by(desc(StoryArtifact.created_at))
            .all()
        )
        return [
            self._build_artifact_response(a, self._get_sources_for_artifact(db, a.id))
            for a in artifacts
        ]

    # -------------------------------------------------------------------------
    # Helper & Formatting Methods
    # -------------------------------------------------------------------------

    def _enforce_third_person_and_ethics(self, text: str, person_name: str) -> Tuple[str, bool]:
        """
        Enforces third-person perspective and neutralizes first-person deceased impersonation.
        Preserves authentic direct quotations enclosed in quotation marks ("..." or '...' or “...”).
        Returns (cleaned_text, was_neutralized).
        """
        if not text:
            return "", False

        # Split on quoted substrings to avoid corrupting authentic attributed quotations
        quote_pattern = re.compile(r'("[^"]*"|“[^”]*”|\'[^\']*\')')
        tokens = quote_pattern.split(text.strip())

        was_neutralized = False
        processed_tokens = []

        substitutions = [
            # Deceased impersonation & posthumous simulation phrases
            (r'\b(?:speaking|talking)\s+from\s+(?:beyond\s+the\s+grave|heaven|the\s+afterlife)\b', 'remembered fondly', re.IGNORECASE),
            (r'\b(?:watching\s+over\s+you\s+from\s+(?:above|heaven|beyond))\b', 'remembered in heart', re.IGNORECASE),
            (r'\bI\s+(?:am\s+speaking|speak)\s+to\s+you\b', f'{person_name} is remembered', re.IGNORECASE),

            # Biographical first-person statements
            (r'\bI\s+was\s+born\b', f'{person_name} was born', re.IGNORECASE),
            (r'\b(?:My\s+name\s+is|I\s+am)\b', f'{person_name} was', re.IGNORECASE),
            (r'\bI\s+(?:grew\s+up|lived|spent\s+my\s+youth)\b', f'{person_name} grew up', re.IGNORECASE),
            (r'\bI\s+(?:worked|served|studied|attended|graduated|taught)\b', lambda m: f'{person_name} ' + m.group(0).split()[1], re.IGNORECASE),
            (r'\bI\s+(?:married|wed)\b', f'{person_name} married', re.IGNORECASE),
            (r'\bI\s+(?:loved|enjoyed|cherished|remember|remembered|felt|believed)\b', lambda m: f'{person_name} ' + m.group(0).split()[1], re.IGNORECASE),
            (r'\bI\s+(?:had|have)\b', f'{person_name} had', re.IGNORECASE),
            (r'\bI\s+(?:was|became)\b', f'{person_name} was', re.IGNORECASE),

            # Possessive pronouns
            (r'\bmy\s+(?:life|childhood|youth|family|children|parents|husband|wife|mother|father|career|work|house|home)\b',
             lambda m: f"{person_name}'s " + m.group(0).split()[1], re.IGNORECASE),
            (r'\bmy\b', f"{person_name}'s", re.IGNORECASE),
            (r'\bI\b', f'{person_name}', 0),  # Case-sensitive for solitary pronoun 'I'
            (r'\bmyself\b', f'{person_name}', re.IGNORECASE),

            # Hindi first-person tokens outside quotes
            (r'\bमेरा\s+नाम\b', f'{person_name} का नाम', 0),
            (r'\bमैं\s+(?:पैदा\s+हुआ|पैदा\s+हुई|था|थी|रहता\s+था|रहती\s+थी)\b', f'{person_name} का जीवन', 0),
            (r'\bमैं\b', f'{person_name}', 0),
            (r'\bमेरा\b', f'{person_name} का', 0),
            (r'\bमेरी\b', f'{person_name} की', 0),
            (r'\bमेरे\b', f'{person_name} के', 0),
            (r'\bमुझे\b', f'{person_name} को', 0),
        ]

        for token in tokens:
            if token.startswith(('"', '“', "'")) and token.endswith(('"', '”', "'")):
                # Inside authentic quotation: preserve exact wording
                processed_tokens.append(token)
            else:
                # Outside quotation: apply third-person normalization
                cleaned_token = token
                for pattern, repl, flags in substitutions:
                    new_token = re.sub(pattern, repl, cleaned_token, flags=flags)
                    if new_token != cleaned_token:
                        was_neutralized = True
                        cleaned_token = new_token
                processed_tokens.append(cleaned_token)

        return "".join(processed_tokens), was_neutralized

    def _parse_biography_sections(
        self,
        full_text: str,
        section_titles: List[str],
        source_memory_ids: List[str]
    ) -> List[BiographySection]:
        """Parses LLM output into structured BiographySection objects."""
        sections: List[BiographySection] = []

        # Split on headers (e.g., "## Early Life", "**Early Life**", etc.)
        for idx, title in enumerate(section_titles, start=1):
            sec_id = f"sec_{idx}"
            # Extract section narrative if delineated, else provide whole or subsection
            pattern = rf'(?:##|\*\*|###)?\s*{re.escape(title)}[:\*\s]*\n*(.*?)(?=(?:##|\*\*|###)\s*|\Z)'
            match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)

            if match:
                narrative = match.group(1).strip()
            else:
                narrative = ""

            is_unknown = (
                not narrative or
                "not enough saved information" in narrative.lower() or
                "unknown" in narrative.lower() and len(narrative) < 100
            )

            classification = "unknown" if is_unknown else "documented_fact"

            sections.append(
                BiographySection(
                    section_id=sec_id,
                    section_title=title,
                    narrative=narrative or "Not enough saved information to create this section reliably.",
                    evidence_classification=classification,
                    source_memory_ids=source_memory_ids if not is_unknown else [],
                    is_unknown=is_unknown
                )
            )

        return sections

    def _get_sources_for_artifact(self, db: Session, artifact_id: str) -> List[SourceMemoryInfo]:
        """Retrieves the list of SourceMemoryInfo objects for an artifact."""
        assocs = (
            db.query(ArtifactSourceMemory)
            .filter(ArtifactSourceMemory.artifact_id == artifact_id)
            .all()
        )
        sources: List[SourceMemoryInfo] = []
        for a in assocs:
            mem = db.query(Memory).filter(Memory.id == a.memory_id).first()
            if mem:
                date_str = mem.event_date.strftime("%Y-%m-%d") if mem.event_date else None
                sources.append(
                    SourceMemoryInfo(
                        memory_id=mem.id,
                        title=mem.title,
                        memory_type=mem.memory_type,
                        original_filename=mem.original_filename,
                        event_date=date_str,
                        location=mem.location,
                        excerpt=mem.description or mem.title,
                        evidence_classification=a.evidence_classification
                    )
                )
        return sources

    def _build_artifact_response(
        self,
        artifact: StoryArtifact,
        sources: List[SourceMemoryInfo],
        sections: Optional[List[BiographySection]] = None
    ) -> StoryArtifactResponse:
        parsed_sections: List[BiographySection] = []
        if sections is not None:
            parsed_sections = sections
        elif artifact.sections_json:
            try:
                raw_list = json.loads(artifact.sections_json)
                parsed_sections = [BiographySection(**item) for item in raw_list]
            except Exception:
                parsed_sections = []

        person_name = artifact.person.full_name if artifact.person else None

        return StoryArtifactResponse(
            id=artifact.id,
            person_id=artifact.person_id,
            person_name=person_name,
            artifact_type=artifact.artifact_type,
            title=artifact.title,
            content=artifact.content,
            sections_json=artifact.sections_json,
            sections=parsed_sections,
            language=artifact.language,
            tone=artifact.tone,
            model_name=artifact.model_name,
            generation_status=artifact.generation_status,
            approval_status=artifact.approval_status,
            evidence_coverage=artifact.evidence_coverage,
            warning=artifact.warning,
            source_memories=sources,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at
        )

    def _build_timeline_event_response(self, event: TimelineEvent) -> TimelineEventResponse:
        sources: List[SourceMemoryInfo] = []
        source_ids: List[str] = []
        for assoc in event.memory_associations:
            mem = assoc.memory
            if mem:
                source_ids.append(mem.id)
                sources.append(
                    SourceMemoryInfo(
                        memory_id=mem.id,
                        title=mem.title,
                        memory_type=mem.memory_type,
                        original_filename=mem.original_filename,
                        event_date=mem.event_date.strftime("%Y-%m-%d") if mem.event_date else None,
                        location=mem.location,
                        excerpt=mem.description or mem.title,
                        evidence_classification="documented_fact"
                    )
                )

        return TimelineEventResponse(
            id=event.id,
            person_id=event.person_id,
            artifact_id=event.artifact_id,
            title=event.title,
            event_date=event.event_date,
            approximate_date=event.approximate_date,
            date_confidence=event.date_confidence,
            description=event.description,
            verification_status=event.verification_status,
            order_index=event.order_index,
            source_memory_ids=source_ids,
            source_memories=sources,
            created_at=event.created_at,
            updated_at=event.updated_at
        )

    def _build_collection_response(self, db: Session, col: MemoryCollection) -> CollectionResponse:
        mem_dicts = []
        for assoc in col.item_associations:
            m = assoc.memory
            if m:
                mem_dicts.append({
                    "id": m.id,
                    "title": m.title,
                    "memory_type": m.memory_type,
                    "original_filename": m.original_filename,
                    "thumbnail_path": m.thumbnail_path,
                    "event_date": m.event_date.isoformat() if m.event_date else None,
                    "order_index": assoc.order_index,
                    "added_at": assoc.added_at.isoformat()
                })

        return CollectionResponse(
            id=col.id,
            title=col.title,
            description=col.description,
            collection_type=col.collection_type,
            person_id=col.person_id,
            cover_memory_id=col.cover_memory_id,
            memories_count=len(mem_dicts),
            memories=mem_dicts,
            created_at=col.created_at,
            updated_at=col.updated_at
        )

    def _build_remembrance_response(self, db: Session, page: RemembrancePage) -> RemembrancePageResponse:
        person = page.person

        # Fetch biography artifact
        bio_resp: Optional[StoryArtifactResponse] = None
        if page.biography_artifact_id:
            bio_artifact = db.query(StoryArtifact).filter(StoryArtifact.id == page.biography_artifact_id).first()
            if bio_artifact:
                bio_resp = self._build_artifact_response(
                    bio_artifact,
                    self._get_sources_for_artifact(db, bio_artifact.id)
                )

        # Featured photograph (host filesystem file_path excluded to protect server internals)
        photo_dict: Optional[Dict[str, Any]] = None
        if page.featured_photograph_id:
            photo = db.query(Memory).filter(Memory.id == page.featured_photograph_id).first()
            if photo:
                photo_dict = {
                    "id": photo.id,
                    "title": photo.title,
                    "thumbnail_path": photo.thumbnail_path,
                    "original_filename": photo.original_filename,
                    "event_date": photo.event_date.isoformat() if photo.event_date else None
                }

        # Stories for this person
        stories_raw = (
            db.query(StoryArtifact)
            .filter(
                StoryArtifact.person_id == person.id,
                StoryArtifact.artifact_type == "story"
            )
            .order_by(desc(StoryArtifact.created_at))
            .all()
        )
        stories_list = [
            self._build_artifact_response(s, self._get_sources_for_artifact(db, s.id))
            for s in stories_raw
        ]

        # Timeline events
        timeline_events = self.get_person_timeline(db, person.id)

        return RemembrancePageResponse(
            id=page.id,
            person_id=person.id,
            person_name=person.full_name,
            person_relationship=person.relationship,
            biography_artifact_id=page.biography_artifact_id,
            biography=bio_resp,
            featured_photograph_id=page.featured_photograph_id,
            featured_photograph=photo_dict,
            user_personal_notes=page.user_personal_notes,
            privacy_level=page.privacy_level,
            stories=stories_list,
            timeline_events=timeline_events,
            created_at=page.created_at,
            updated_at=page.updated_at
        )


storytelling_service = StorytellingService()
