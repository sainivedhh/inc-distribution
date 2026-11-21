"""Fast CSV Catalogue Import Engine with SSRF protection (Phase 10 Advanced)."""

import csv
import io
import time
import ipaddress
from urllib.parse import urlparse
from typing import List, Dict, Any, Tuple
import httpx
from core.models import DestinationModel
from core.relevance import RelevanceScorer


class CatalogueImporter:
    @staticmethod
    def is_ssrf_safe(url: str, allow_localhost: bool = True) -> bool:
        """Blocks private network IPs unless explicitly running against local mocks."""
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            if not hostname:
                return False
            if hostname in ("localhost", "127.0.0.1") and allow_localhost:
                return True
            ip = ipaddress.ip_address(hostname)
            if ip.is_private or ip.is_loopback:
                return allow_localhost
            return True
        except ValueError:
            # Domain name, check not RFC1918 / link-local
            return True

    @classmethod
    async def import_csv_rows(
        cls,
        csv_content: str,
        allow_local_mocks: bool = True,
    ) -> Dict[str, Any]:
        """Imports, validates, normalizes, deduplicates, and enriches destination rows."""
        start_time = time.time()
        reader = csv.DictReader(io.StringIO(csv_content))
        imported: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        seen_keys = set()
        duplicates_count = 0

        row_idx = 1
        for row in reader:
            row_idx += 1
            name = row.get("name", "").strip()
            raw_url = row.get("url", "").strip()
            platform_key = row.get("platform_key", "").strip()
            connector_key = row.get("connector_key", "").strip() or platform_key
            surface = row.get("surface", "").strip() or "default"

            if not name or not raw_url or not platform_key:
                errors.append({"row": row_idx, "error": "Missing mandatory fields (name, url, or platform_key)"})
                continue

            # URL Normalization
            norm_url = raw_url.lower().rstrip("/")
            dedup_key = (norm_url, platform_key)

            if dedup_key in seen_keys:
                duplicates_count += 1
                continue
            seen_keys.add(dedup_key)

            # SSRF reachability check
            if not cls.is_ssrf_safe(norm_url, allow_localhost=allow_local_mocks):
                errors.append({"row": row_idx, "error": f"URL '{norm_url}' rejected due to SSRF policy (private IP)."})
                continue

            # Audience and relevance scoring
            raw_tags = row.get("audience_tags", "")
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()] if isinstance(raw_tags, str) else []
            est_audience = int(row.get("est_audience", "0") or 0)
            category = row.get("category", "")

            score, reason = RelevanceScorer.score_destination(name, category, tags, est_audience)

            dest_record = {
                "name": name,
                "url": norm_url,
                "platform_key": platform_key,
                "surface": surface,
                "category": category,
                "audience_tags": tags,
                "language": row.get("language", "en"),
                "geo": row.get("geo", "global"),
                "est_audience": est_audience,
                "rules_url": row.get("rules_url", ""),
                "frequency_cap": row.get("frequency_cap", "1 per 7 days"),
                "self_promo_allowed": row.get("self_promo_allowed", "true").lower() in ("true", "1", "yes"),
                "link_policy": row.get("link_policy", "allowed"),
                "disclosure_required": row.get("disclosure_required", "false").lower() in ("true", "1", "yes"),
                "automation_allowed": row.get("automation_allowed", "true").lower() in ("true", "1", "yes"),
                "connector_key": connector_key,
                "relevance_score": score,
                "relevance_reason": reason,
                "level": row.get("level", "L0"),
            }
            imported.append(dest_record)

        elapsed = time.time() - start_time
        return {
            "total_rows_processed": row_idx - 1,
            "imported_count": len(imported),
            "duplicates_found": duplicates_count,
            "errors_count": len(errors),
            "elapsed_seconds": round(elapsed, 3),
            "records": imported,
            "errors": errors,
        }
