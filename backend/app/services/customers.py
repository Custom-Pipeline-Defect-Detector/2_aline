import re
from difflib import SequenceMatcher
from typing import Optional
from sqlalchemy.orm import Session
from app import models


def _normalize_name(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "", value.lower())
    return cleaned.strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def find_similar_customer(db: Session, name: str, threshold: float = 0.86) -> Optional[models.Customer]:
    if not name:
        return None
    normalized = _normalize_name(name)
    best_match = None
    best_score = 0.0
    customers = db.query(models.Customer).all()
    for customer in customers:
        candidates = [customer.name, *(customer.aliases or [])]
        for candidate in candidates:
            if not candidate:
                continue
            candidate_norm = _normalize_name(candidate)
            if candidate_norm == normalized:
                return customer
            score = _similarity(normalized, candidate_norm)
            if score > best_score:
                best_score = score
                best_match = customer
    if best_score >= threshold:
        return best_match
    return None
