BEGIN;
CREATE TABLE IF NOT EXISTS return_requests (
 id SERIAL PRIMARY KEY,
 tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
 order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
 customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 status VARCHAR(24) NOT NULL DEFAULT 'REQUESTED',
 reason VARCHAR(500) NOT NULL,
 admin_note VARCHAR(500),
 reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
 received_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 reviewed_at TIMESTAMPTZ,
 received_at TIMESTAMPTZ,
 CONSTRAINT ck_return_status CHECK (status IN ('REQUESTED','APPROVED','REJECTED','RECEIVED','CANCELLED'))
);
CREATE INDEX IF NOT EXISTS ix_return_requests_tenant_id ON return_requests(tenant_id);
CREATE INDEX IF NOT EXISTS ix_return_requests_order_id ON return_requests(order_id);
CREATE INDEX IF NOT EXISTS ix_return_requests_customer_id ON return_requests(customer_id);
CREATE TABLE IF NOT EXISTS return_items (
 id SERIAL PRIMARY KEY,
 return_request_id INTEGER NOT NULL REFERENCES return_requests(id) ON DELETE CASCADE,
 order_item_id INTEGER NOT NULL REFERENCES order_items(id) ON DELETE RESTRICT,
 quantity INTEGER NOT NULL,
 CONSTRAINT uq_return_order_item UNIQUE(return_request_id,order_item_id),
 CONSTRAINT ck_return_quantity_positive CHECK (quantity > 0)
);
CREATE INDEX IF NOT EXISTS ix_return_items_return_request_id ON return_items(return_request_id);
COMMIT;
