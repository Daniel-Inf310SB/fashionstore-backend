CREATE TABLE IF NOT EXISTS return_refunds (
 id SERIAL PRIMARY KEY,
 return_request_id INTEGER NOT NULL REFERENCES return_requests(id) ON DELETE RESTRICT,
 tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
 payment_id INTEGER NOT NULL REFERENCES payments(id) ON DELETE RESTRICT,
 requested_by INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
 amount NUMERIC(12,2) NOT NULL CHECK (amount > 0),
 currency VARCHAR(3) NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'PREPARED' CHECK (status IN ('PREPARED','PROCESSING','SUCCEEDED','FAILED','MANUAL_REVIEW')),
 stripe_refund_id VARCHAR(150) UNIQUE,
 idempotency_key VARCHAR(120) NOT NULL UNIQUE,
 failure_reason VARCHAR(500),
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 CONSTRAINT uq_refund_return_request UNIQUE(return_request_id)
);
CREATE INDEX IF NOT EXISTS ix_return_refunds_payment_id ON return_refunds(payment_id);
CREATE INDEX IF NOT EXISTS ix_return_refunds_tenant_id ON return_refunds(tenant_id);
