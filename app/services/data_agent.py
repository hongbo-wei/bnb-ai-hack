import hashlib
import re
from typing import List, Optional

import httpx
import numpy as np
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import (
    EMBED_API_BASE,
    EMBED_API_KEY,
    EMBED_MODEL,
    EMBED_PROVIDER,
    OLLAMA_BASE,
    VECTOR_DIM,
)
from app.models import OnChainEvent


class DataAgent:
    def __init__(self, db: Session):
        self.db = db

    def _extract_metadata(self, payload: str) -> dict:
        lower = payload.lower()
        tags = []
        for tag in (
            "nft",
            "inscription",
            "swap",
            "bridge",
            "defi",
            "staking",
            "mint",
            "transfer",
            "liquidity",
            "whale",
            "airdrop",
            "memecoin",
        ):
            if tag in lower:
                tags.append(tag)

        address_match = re.findall(r"0x[a-f0-9]{40}", lower)
        from_address = address_match[0] if len(address_match) >= 1 else None
        to_address = address_match[1] if len(address_match) >= 2 else None

        value_match = re.search(r"value\s+([0-9.]+)", lower)
        block_match = re.search(r"block\s+([0-9]+)", lower)

        value = float(value_match.group(1)) if value_match else None
        block_number = int(block_match.group(1)) if block_match else None
        return {
            "tags": tags,
            "from_address": from_address,
            "to_address": to_address,
            "value": value,
            "block_number": block_number,
        }

    def embed(self, text: str) -> List[float]:
        if EMBED_PROVIDER == "openai":
            if not EMBED_API_KEY:
                raise RuntimeError("EMBED_API_KEY must be set for openai embeddings")
            payload = {"model": EMBED_MODEL, "input": text}
            headers = {"Authorization": f"Bearer {EMBED_API_KEY}"}
            response = httpx.post(
                f"{EMBED_API_BASE}/embeddings",
                json=payload,
                headers=headers,
                timeout=20,
            )
            response.raise_for_status()
            embedding = response.json()["data"][0]["embedding"]
            if len(embedding) != VECTOR_DIM:
                raise RuntimeError(
                    f"Embedding dimension {len(embedding)} does not match VECTOR_DIM={VECTOR_DIM}"
                )
            return embedding
        if EMBED_PROVIDER == "ollama":
            payload = {"model": EMBED_MODEL, "prompt": text}
            response = httpx.post(f"{OLLAMA_BASE}/api/embeddings", json=payload, timeout=30)
            response.raise_for_status()
            embedding = response.json()["embedding"]
            if len(embedding) != VECTOR_DIM:
                raise RuntimeError(
                    f"Embedding dimension {len(embedding)} does not match VECTOR_DIM={VECTOR_DIM}"
                )
            return embedding

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "big")
        rng = np.random.default_rng(seed)
        vec = rng.normal(0, 1, VECTOR_DIM).astype("float32")
        norm = np.linalg.norm(vec) or 1.0
        return (vec / norm).tolist()

    def ingest(
        self,
        tx_hash: str,
        payload: str,
        chain: str,
        *,
        from_address: Optional[str] = None,
        to_address: Optional[str] = None,
        value: Optional[float] = None,
        block_number: Optional[int] = None,
        tags: Optional[list[str]] = None,
    ) -> OnChainEvent:
        existing = self.db.execute(
            select(OnChainEvent).where(OnChainEvent.tx_hash == tx_hash)
        ).scalar_one_or_none()
        if existing:
            return existing

        metadata = self._extract_metadata(payload)
        tags = tags or metadata["tags"]
        from_address = from_address or metadata["from_address"]
        to_address = to_address or metadata["to_address"]
        value = value if value is not None else metadata["value"]
        block_number = block_number if block_number is not None else metadata["block_number"]

        embedding = self.embed(payload)
        event = OnChainEvent(
            tx_hash=tx_hash,
            payload=payload,
            chain=chain,
            from_address=from_address,
            to_address=to_address,
            value=value,
            block_number=block_number,
            tags=",".join(tags) if tags else None,
            embedding=embedding,
        )
        self.db.add(event)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.db.execute(
                select(OnChainEvent).where(OnChainEvent.tx_hash == tx_hash)
            ).scalar_one_or_none()
            if existing:
                return existing
            raise
        self.db.refresh(event)
        return event

    def search(
        self, query: str, top_k: int, chain: str | None, *, probes: int | None = None
    ) -> List[tuple[OnChainEvent, float]]:
        query_vec = self.embed(query)
        return self.search_by_vector(query_vec, top_k, chain, probes=probes)

    def search_by_vector(
        self,
        query_vec: List[float],
        top_k: int,
        chain: str | None,
        *,
        probes: int | None = None,
    ) -> List[tuple[OnChainEvent, float]]:
        if probes and probes > 0:
            probes_int = int(probes)
            self.db.execute(text(f"SET LOCAL ivfflat.probes = {probes_int}"))
        distance = OnChainEvent.embedding.cosine_distance(query_vec)
        stmt = select(OnChainEvent, distance.label("distance"))
        if chain:
            stmt = stmt.where(OnChainEvent.chain == chain)
        stmt = stmt.order_by(distance).limit(top_k)
        results = self.db.execute(stmt).all()
        hits: List[tuple[OnChainEvent, float]] = []
        for event, distance in results:
            score = float(1.0 - distance)
            hits.append((event, score))
        return hits

    def insights(self, limit: int = 50) -> dict:
        events = (
            self.db.execute(select(OnChainEvent).order_by(OnChainEvent.created_at.desc()).limit(limit))
            .scalars()
            .all()
        )
        tag_counter: dict[str, int] = {}
        term_counter: dict[str, int] = {}
        total_value = 0.0
        for event in events:
            if event.value is not None:
                total_value += float(event.value)
            if event.tags:
                for tag in event.tags.split(","):
                    tag_counter[tag] = tag_counter.get(tag, 0) + 1
            tokens = re.findall(r"[a-z0-9]+", event.payload.lower())
            for token in tokens:
                if len(token) <= 2:
                    continue
                term_counter[token] = term_counter.get(token, 0) + 1
        top_tags = sorted(tag_counter.items(), key=lambda item: item[1], reverse=True)[:6]
        top_terms = sorted(term_counter.items(), key=lambda item: item[1], reverse=True)[:8]
        return {
            "total_events": len(events),
            "top_tags": [{"tag": tag, "count": count} for tag, count in top_tags],
            "top_terms": [{"term": term, "count": count} for term, count in top_terms],
            "total_value": total_value,
        }
