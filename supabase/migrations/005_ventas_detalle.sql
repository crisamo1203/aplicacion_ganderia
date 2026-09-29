-- MyFinca Pro: campos de cantidad e importe para ventas.
-- Idempotente: seguro para instalaciones nuevas (que ya los incluyan) y existentes.
ALTER TABLE public.ventas
  ADD COLUMN IF NOT EXISTS cantidad numeric(14,3),
  ADD COLUMN IF NOT EXISTS valor_unitario numeric(14,2),
  ADD COLUMN IF NOT EXISTS valor_total numeric(14,2);

-- Completa importes previos cuando existan los dos componentes.
UPDATE public.ventas
SET valor_total = cantidad * valor_unitario
WHERE valor_total IS NULL
  AND cantidad IS NOT NULL
  AND valor_unitario IS NOT NULL;
