-- SpaceOps KB RAG: pgvector table for runbooks and postmortems
-- Run once after: docker compose -f infra/docker-compose.yml up -d
--
-- From repo root, either:
--   docker exec -i spaceops-postgres psql -U spaceops -d spaceops < infra/sql/001_kb_vector.sql
-- Or (with psql on host): psql -h localhost -U spaceops -d spaceops -f infra/sql/001_kb_vector.sql
--   (password from .env: POSTGRES_PASSWORD)

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS kb_chunks (
  id BIGSERIAL PRIMARY KEY,
  doc_id TEXT NOT NULL,
  doc_type TEXT NOT NULL CHECK (doc_type IN ('runbook', 'postmortem')),
  content TEXT NOT NULL,
  embedding vector(1536) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS kb_chunks_doc_type ON kb_chunks(doc_type);
-- Optional: ivfflat index for large KB (tune lists when row count grows)
-- CREATE INDEX kb_chunks_embedding_cosine ON kb_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

COMMENT ON TABLE kb_chunks IS 'RAG chunks from kb/runbooks and kb/postmortems; embedding from OpenAI text-embedding-3-small (1536 dims).';
