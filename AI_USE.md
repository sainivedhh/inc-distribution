# AI Use Disclosure

In accordance with IncuBrix Engineering Assessment 4 guidelines, this document provides full transparency on all AI tools, models, and assistants utilized during the design, implementation, and benchmarking of this project.

## 1. AI Coding Assistants & Agentic Environments

| Tool / Assistant | Provider | Scope of Use |
|---|---|---|
| Antigravity (Google DeepMind) | Google DeepMind | Primary autonomous development agent: scaffolding code, generating test suites, executing gate verifications, structuring documentation, and writing traceability matrices. |
| Claude 3.5 Sonnet / Gemini | Anthropic / Google | Used during conceptual review for Appendix A contract edge cases and regex frequency parsing logic. |

## 2. Integrated AI Adapters in the Shipped Service

To allow 100% offline testing with zero API keys while remaining swappable for production deployments, the system uses an adapter interface pattern (`core/relevance.py` and `core/tailoring.py`):

1. **Default Heuristic Mock Adapter**:
   - Analyzes rules pages for frequency caps, self-promo bans, link constraints, and AI disclosure requirements with quote extraction.
   - Evaluates destination relevance (1-5) against IncuBrix target audiences (AI, video, marketing, SaaS, creators, founders) based on deterministic tag and demographic overlap.
   - Requires zero network calls or paid API keys.
2. **Pluggable LLM Adapter**:
   - Selected when `AI_PROVIDER=gemini` and `AI_API_KEY` is supplied in the environment.
   - Connects to Gemini 1.5 Flash / Pro for dynamic rules extraction and nuance classification.
