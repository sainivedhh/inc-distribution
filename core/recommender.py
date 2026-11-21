"""Content Recommender Engine with precision evaluation (Phase 11 Outstanding)."""

from typing import List, Dict, Any, Tuple
from core.contract import ContentRendition, DestinationConfig


class ContentRecommender:
    @staticmethod
    def rank_destinations(
        rendition: ContentRendition,
        destinations: List[DestinationConfig],
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """Ranks destinations by fit: audience tags, rules compatibility, language, and relevance score."""
        ranked = []
        content_tokens = set(re_tokenize(f"{rendition.title or ''} {rendition.body} {' '.join(rendition.tags or [])}"))

        for dest in destinations:
            score = 0.0
            reasons = []

            # 1. Base relevance score (1-5 mapped to 10-50 pts)
            base_pts = (dest.relevance_score or 3) * 10
            score += base_pts
            reasons.append(f"Base relevance score {dest.relevance_score}/5 (+{base_pts})")

            # 2. Audience tags overlap
            dest_tags = set([t.lower() for t in (dest.audience_tags or [])])
            overlap = dest_tags.intersection(content_tokens)
            if overlap:
                tag_pts = len(overlap) * 15
                score += tag_pts
                reasons.append(f"Matched audience tags: {list(overlap)} (+{tag_pts})")

            # 3. Language match
            if dest.language == rendition.language:
                score += 10
                reasons.append(f"Language match ({dest.language}) (+10)")
            else:
                score -= 20
                reasons.append(f"Language mismatch ({dest.language} vs {rendition.language}) (-20)")

            # 4. Rules compatibility check
            if not dest.self_promo_allowed:
                # Deduct if promotional tone detected
                if any(w in content_tokens for w in ("buy", "discount", "offer", "sale")):
                    score -= 50
                    reasons.append("Penalized: Content is promotional but destination bans self-promo (-50)")

            ranked.append({
                "destination_id": dest.destination_id or dest.name,
                "name": dest.name,
                "score": round(score, 1),
                "reasons": reasons,
                "connector_key": dest.connector_key,
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:top_k]

    @staticmethod
    def evaluate_precision_at_k(
        recommendations: List[Dict[str, Any]],
        ground_truth_relevant_ids: List[str],
        k: int = 10,
    ) -> float:
        """Calculates Precision@K = (relevant recommendations in top K) / K."""
        top_k_rec = recommendations[:k]
        if not top_k_rec:
            return 0.0
        relevant_set = set(ground_truth_relevant_ids)
        hits = sum(1 for r in top_k_rec if r["destination_id"] in relevant_set or r["name"] in relevant_set)
        return hits / len(top_k_rec)


def re_tokenize(text: str) -> List[str]:
    import re
    return [w.lower() for w in re.findall(r"\b[a-zA-Z0-9_\-]{2,}\b", text)]
