"""
Person domain service.
Handles people directory and family relationships.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.models.person import Person
from backend.app.models.memory import MemoryPerson
from backend.app.schemas.person import PersonCreate, PersonRead


class PersonService:
    @staticmethod
    def list_people(db: Session) -> List[PersonRead]:
        """Lists all registered people with associated memories count."""
        people = db.query(Person).order_by(Person.full_name.asc()).all()
        results = []

        for p in people:
            mem_count = db.query(MemoryPerson).filter(MemoryPerson.person_id == p.id).count()
            p_read = PersonRead(
                id=p.id,
                full_name=p.full_name,
                relationship=p.relationship,
                biography=p.biography,
                created_at=p.created_at,
                memories_count=mem_count
            )
            results.append(p_read)

        return results

    @staticmethod
    def get_person_by_id(db: Session, person_id: str) -> Optional[Person]:
        return db.query(Person).filter(Person.id == person_id).first()

    @staticmethod
    def create_person(db: Session, person_in: PersonCreate) -> Person:
        person = Person(
            full_name=person_in.full_name.strip(),
            relationship=person_in.relationship.strip() if person_in.relationship else None,
            biography=person_in.biography.strip() if person_in.biography else None
        )
        db.add(person)
        db.commit()
        db.refresh(person)
        return person


person_service = PersonService()


