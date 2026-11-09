-- Fase 2B: inspección por línea de devolución, idempotencia en PostgreSQL.
CREATE TABLE IF NOT EXISTS return_inspections (
  id SERIAL PRIMARY KEY,
  return_item_id INTEGER NOT NULL REFERENCES return_items(id) ON DELETE RESTRICT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
  inspector_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  decision VARCHAR(20) NOT NULL,
  note VARCHAR(500) NOT NULL,
  movement_id INTEGER UNIQUE REFERENCES inventory_movements(id) ON DELETE RESTRICT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_return_inspection_item UNIQUE (return_item_id),
  CONSTRAINT ck_return_inspection_decision CHECK (decision IN ('RESTOCKED','DAMAGED'))
);
CREATE INDEX IF NOT EXISTS ix_return_inspections_item ON return_inspections(return_item_id);
-- Protection against duplicate RETURN_IN movements even if a future code path bypasses inspection.
CREATE UNIQUE INDEX IF NOT EXISTS uq_return_in_by_return_item
  ON inventory_movements(reference_id)
  WHERE movement_type = 'RETURN_IN' AND reference_type = 'RETURN_ITEM';
