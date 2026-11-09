-- Aplicar UNA SOLA VEZ en fashionstore_db ANTES de iniciar backend actualizado.
-- El enlace único evita cobrar/crear dos ventas sobre una reserva.
ALTER TABLE sales ADD COLUMN IF NOT EXISTS reservation_id INTEGER;
CREATE UNIQUE INDEX IF NOT EXISTS ix_sales_reservation_id ON sales (reservation_id);
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_sales_reservation_id') THEN
    ALTER TABLE sales ADD CONSTRAINT fk_sales_reservation_id
      FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE RESTRICT;
  END IF;
END $$;
