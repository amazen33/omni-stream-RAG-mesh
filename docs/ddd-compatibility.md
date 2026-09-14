# DDD naming compatibility

The executable bounded contexts are `contexts/ingestion`, `contexts/ai`, and
`contexts/governance`; they are intentionally preserved. In architecture
discussions, **AI retrieval** (or `ai_retrieval`) is the capability name for
the existing `contexts/ai` context. It is not a second Python package and must
not be introduced by duplicating domain code. Integrations should map
`ai_retrieval` to `contexts.ai` until a separately approved bounded-context
split exists.
