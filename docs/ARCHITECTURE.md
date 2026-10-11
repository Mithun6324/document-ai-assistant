# Architecture

## System overview

```mermaid
flowchart TB
    subgraph Frontend
      UI[React + Tailwind]
      RQ[React Query]
      AX[Axios / Fetch SSE]
    end

    subgraph Backend[FastAPI]
      AUTH[Auth API]
      DOCS[Documents API]
      CHAT[Chat API]
      SVC[Services]
    end

    subgraph Data
      PG[(PostgreSQL)]
      CH[(ChromaDB)]
    end

    subgraph AI
      EMB[all-MiniLM-L6-v2]
      SPACY[spaCy chunking]
      GEM[Gemini 2.0 Flash]
    end

    UI --> RQ --> AX
    AX --> AUTH & DOCS & CHAT
    AUTH & DOCS & CHAT --> SVC
    SVC --> PG
    SVC --> CH
    SVC --> EMB & SPACY & GEM
```

## Ingestion pipeline

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant BG as Background task
    participant PG as PostgreSQL
    participant CH as ChromaDB

    U->>API: Upload PDF/DOCX
    API->>API: Validate + hash (duplicate check)
    API->>PG: Create document (pending)
    API-->>U: document_id + status
    API->>BG: process_document
    BG->>BG: extract → clean → chunk → embed
    BG->>PG: save chunks
    BG->>CH: upsert vectors + metadata
    BG->>PG: status=ready
```

## Retrieval + RAG

```mermaid
flowchart LR
    Q[User question] --> E[Embed query]
    E --> V[Chroma vector top-20]
    Q --> K[Keyword search top-20]
    V --> M[Hybrid merge 0.7/0.3]
    K --> M
    M --> R[Cross-encoder re-rank]
    R --> T[Top-5 + threshold]
    T --> C[Trim token budget]
    C --> G[Gemini 2.0 Flash stream]
    G --> A[Answer + citations]
```

## Data ownership

Every document, chunk, conversation, and message is scoped to the authenticated `user_id`.  
Chroma metadata includes `user_id` and `document_id` for filtered retrieval.

## LLM provider abstraction

```
services/llm/base.py          → LLMProvider interface
services/llm/gemini_service.py → Gemini 2.0 Flash (primary)
services/llm/deepseek_service.py → optional fallback
```

Switch with `LLM_PROVIDER=gemini|deepseek`.
