# API Documentation

Base URL: `http://localhost:8000`

Auth header: `Authorization: Bearer <access_token>`

Interactive docs: `/docs` (Swagger) and `/redoc`.

---

## Auth

### POST `/auth/register`

```json
{ "email": "user@example.com", "password": "password123", "full_name": "Ada" }
```

### POST `/auth/login`

```json
{ "email": "user@example.com", "password": "password123" }
```

Response:

```json
{ "access_token": "...", "token_type": "bearer" }
```

### GET `/auth/me`

Returns the authenticated user.

---

## Documents

### POST `/documents/upload`

`multipart/form-data` with field `file` (PDF or DOCX).

Returns document metadata. If the same file hash already exists for the user and is `ready`, `duplicate: true` is set.

### GET `/documents`

List all non-deleted documents for the user.

### GET `/documents/{id}/status`

```json
{
  "id": "...",
  "status": "processing",
  "progress_stage": "embedding",
  "progress_percent": 70,
  "processing_error": null,
  "chunk_count": 0,
  "page_count": 3
}
```

### GET `/documents/{id}/questions`

Questions asked about this document (linked via answer sources).

### GET `/documents/{id}/suggested-questions`

```json
["Summarize this resume", "List the key skills"]
```

### DELETE `/documents/{id}`

Soft-deletes the document and removes Chroma vectors.

---

## Chat

### POST `/chat`

```json
{
  "question": "What skills are listed?",
  "conversation_id": null,
  "document_ids": ["optional-uuid"]
}
```

Omit `document_ids` (or send empty) to search **all** user documents.

### POST `/chat/stream`

Same body as `/chat`. Returns `text/event-stream` with JSON events:

| type | meaning |
|---|---|
| `meta` | conversation id + title |
| `sources` | citation list |
| `token` | streamed text chunk |
| `done` | final message id + sources |
| `end` | stream closed |

### GET `/chat/history`

Conversation summaries.

### GET `/chat/history/{id}`

Full message thread.

### GET `/chat/history/{id}/export`

Markdown download of the conversation.

### PATCH `/chat/messages/{id}/feedback`

```json
{ "rating": "up", "comment": null }
```

---

## Dashboard & Health

### GET `/dashboard`

Counts + recent documents/conversations.

### GET `/health`

```json
{
  "status": "ok",
  "database": "ok",
  "chroma": "ok",
  "embedding_model": "all-MiniLM-L6-v2"
}
```
