-- Khởi tạo extension xử lý tiếng Việt không dấu (unaccent) và tìm kiếm vector (pgvector)
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS vector;

-- Hàm bất biến (IMMUTABLE) bọc unaccent để có thể tạo chỉ mục GIN trên cột tsvector
CREATE OR REPLACE FUNCTION immutable_unaccent(text)
RETURNS text
LANGUAGE sql
IMMUTABLE PARALLEL SAFE STRICT
AS $$
    SELECT public.unaccent('public.unaccent', $1);
$$;

-- Bảng lưu các đoạn bằng chứng gắn chặt theo tenant_id và sku_id
CREATE TABLE IF NOT EXISTS evidence_chunks (
    evidence_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    sku_id TEXT NOT NULL,
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    knowledge_version INT NOT NULL,
    approval_status TEXT NOT NULL,
    tsv_raw tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
    tsv_unaccent tsvector GENERATED ALWAYS AS (to_tsvector('simple', immutable_unaccent(content))) STORED,
    embedding vector(384)
);

-- Chỉ mục lọc cứng theo tenant + SKU trước khi tìm kiếm
CREATE INDEX IF NOT EXISTS idx_evidence_tenant_sku ON evidence_chunks (tenant_id, sku_id);
-- Chỉ mục GIN phục vụ PostgreSQL Full-Text Search
CREATE INDEX IF NOT EXISTS idx_evidence_tsv_raw ON evidence_chunks USING GIN (tsv_raw);
CREATE INDEX IF NOT EXISTS idx_evidence_tsv_unaccent ON evidence_chunks USING GIN (tsv_unaccent);
