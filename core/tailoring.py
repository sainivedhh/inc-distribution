"""Content Tailoring Engine (Phase 10 Advanced)."""

import re
from typing import Tuple, List
from core.contract import ContentRendition, DestinationConfig


class TailoringEngine:
    @staticmethod
    def truncate_at_word_boundary(text: str, max_chars: int) -> Tuple[str, bool]:
        """Truncates string at word boundary without cutting codepoints (Unicode/emoji safe)."""
        if len(text) <= max_chars:
            return text, False
        truncated = text[:max_chars]
        last_space = truncated.rfind(" ")
        if last_space > 0:
            truncated = truncated[:last_space]
        return truncated + "...", True

    @classmethod
    def tailor_rendition(
        cls,
        rendition: ContentRendition,
        destination: DestinationConfig,
    ) -> Tuple[ContentRendition, List[str]]:
        warnings: List[str] = []
        tailored_body = rendition.body
        tailored_title = rendition.title or ""

        # 1. Discussion-first framing for forums (Discourse / Lemmy)
        if destination.platform_key in ("discourse", "lemmy"):
            if not tailored_title.endswith("?"):
                tailored_title = f"{tailored_title} — What are your thoughts?"
                warnings.append("Adapted title to discussion-first question format for forum.")
            if not any(tailored_body.strip().endswith(p) for p in ("?", "thoughts?", "discuss.")):
                tailored_body += "\n\nWould love to hear how others approach this!"
                warnings.append("Appended discussion prompt to forum body.")

        # 2. Canonical URL for dev blogs & articles (Dev.to / Ghost / Hashnode)
        canonical = rendition.canonical_url
        if destination.platform_key in ("devto", "ghost", "hashnode") and not canonical:
            canonical = f"https://incubrix.com/posts/{hash(tailored_title) % 1000000}"
            warnings.append(f"Auto-injected canonical URL: {canonical}")

        # 3. AI-Content Disclosure Line
        if destination.disclosure_required or rendition.ai_generated:
            disclosure_line = rendition.ai_disclosure_text or "[AI-Assisted: Created with IncuBrix AI distribution tools]"
            if disclosure_line not in tailored_body:
                tailored_body = f"{tailored_body}\n\n---\n*{disclosure_line}*"
                warnings.append("Auto-appended required AI disclosure line.")

        # 4. Truncation at word boundary if spec requires
        max_title = 255
        max_body = 30000
        if destination.spec_overrides:
            max_title = destination.spec_overrides.title_max_chars or max_title
            max_body = destination.spec_overrides.body_max_chars or max_body

        tailored_title, title_truncated = cls.truncate_at_word_boundary(tailored_title, max_title)
        if title_truncated:
            warnings.append(f"Title truncated at word boundary to {max_title} chars.")

        tailored_body, body_truncated = cls.truncate_at_word_boundary(tailored_body, max_body)
        if body_truncated:
            warnings.append(f"Body truncated at word boundary to {max_body} chars.")

        new_rendition = ContentRendition(
            title=tailored_title,
            body=tailored_body,
            media=rendition.media,
            tags=rendition.tags,
            canonical_url=canonical,
            ai_generated=rendition.ai_generated,
            ai_disclosure_text=rendition.ai_disclosure_text,
            language=rendition.language,
        )

        return new_rendition, warnings
