-- ============================================================
-- SAFE MIGRATION - Run in Supabase SQL Editor
-- Handles existing objects with IF NOT EXISTS / DROP IF EXISTS
-- ============================================================

-- 1. Ensure app_role type exists (safe)
DO $$ BEGIN
    CREATE TYPE public.app_role AS ENUM ('admin', 'cliente');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- 2. Add missing columns to profiles
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS nombre text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS telefono text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS grupo text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS activo boolean NOT NULL DEFAULT true;

-- 3. Add missing columns to animales
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS tipo text DEFAULT 'Individual';
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS clase text;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS proposito text;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS fecha_nacimiento date;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS peso_kg numeric(8,2);
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS sexo text;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS raza text;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS color text;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS proveedor text;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS especie text;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS origen text;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS valor_compra numeric(14,2);
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS valor_venta numeric(14,2);
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS estado text DEFAULT 'Activo';
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS propietario text;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS marca text;
ALTER TABLE public.animales ADD COLUMN IF NOT EXISTS comentarios text;

-- 4. Create operational tables (if not exist)
CREATE TABLE IF NOT EXISTS public.ventas (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  fecha date NOT NULL DEFAULT current_date,
  predio_id uuid REFERENCES public.predios(id) ON DELETE RESTRICT,
  clase text, tipo text, detalle text, metodo text, observaciones text,
  creado_por uuid NOT NULL DEFAULT auth.uid() REFERENCES public.profiles(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.produccion (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  fecha date NOT NULL DEFAULT current_date,
  predio_id uuid REFERENCES public.predios(id) ON DELETE RESTRICT,
  animal_id uuid REFERENCES public.animales(id) ON DELETE SET NULL,
  clase text, nombre_referencia text, ordeno boolean,
  kilos_leche numeric(10,2), litros_leche numeric(10,2),
  cantidad_huevos integer CHECK (cantidad_huevos >= 0),
  observaciones text, creado_por uuid NOT NULL DEFAULT auth.uid() REFERENCES public.profiles(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.movimientos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  animal_id uuid REFERENCES public.animales(id) ON DELETE SET NULL,
  predio_id uuid REFERENCES public.predios(id) ON DELETE RESTRICT,
  tipo text NOT NULL, valor numeric(14,2),
  fecha timestamptz NOT NULL DEFAULT now(),
  comentarios text, creado_por uuid NOT NULL DEFAULT auth.uid() REFERENCES public.profiles(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.salud (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  animal_id uuid NOT NULL REFERENCES public.animales(id) ON DELETE RESTRICT,
  fecha date NOT NULL DEFAULT current_date,
  tipo text NOT NULL, medicamento text, veterinario text,
  proxima_cita date, observaciones text,
  creado_por uuid NOT NULL DEFAULT auth.uid() REFERENCES public.profiles(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.gastos (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  fecha date NOT NULL DEFAULT current_date,
  predio_id uuid REFERENCES public.predios(id) ON DELETE RESTRICT,
  detalle text NOT NULL, valor numeric(14,2) NOT NULL CHECK (valor >= 0),
  metodo text, inversor text, observaciones text,
  creado_por uuid NOT NULL DEFAULT auth.uid() REFERENCES public.profiles(id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  tipo text NOT NULL CHECK (tipo IN ('problema','sugerencia','mejora','otro')),
  titulo text NOT NULL CHECK (char_length(trim(titulo)) > 0 AND char_length(trim(titulo)) <= 200),
  descripcion text NOT NULL CHECK (char_length(trim(descripcion)) > 0),
  modulo text, prioridad text NOT NULL DEFAULT 'media' CHECK (prioridad IN ('baja','media','alta','critica')),
  estado text NOT NULL DEFAULT 'nuevo' CHECK (estado IN ('nuevo','en_revision','resuelto','cerrado')),
  respuesta_admin text, responded_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  responded_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- 5. Indexes
CREATE INDEX IF NOT EXISTS ventas_predio_idx ON public.ventas(predio_id);
CREATE INDEX IF NOT EXISTS produccion_predio_fecha_idx ON public.produccion(predio_id, fecha DESC);
CREATE INDEX IF NOT EXISTS movimientos_animal_fecha_idx ON public.movimientos(animal_id, fecha DESC);
CREATE INDEX IF NOT EXISTS salud_animal_fecha_idx ON public.salud(animal_id, fecha DESC);
CREATE INDEX IF NOT EXISTS gastos_predio_fecha_idx ON public.gastos(predio_id, fecha DESC);
CREATE INDEX IF NOT EXISTS feedback_user_idx ON public.feedback(user_id);
CREATE INDEX IF NOT EXISTS feedback_estado_idx ON public.feedback(estado);
CREATE INDEX IF NOT EXISTS feedback_tipo_idx ON public.feedback(tipo);
CREATE INDEX IF NOT EXISTS feedback_prioridad_idx ON public.feedback(prioridad);
CREATE INDEX IF NOT EXISTS feedback_created_idx ON public.feedback(created_at DESC);

-- 6. Updated_at triggers
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$;

DROP TRIGGER IF EXISTS feedback_updated_at ON public.feedback;
CREATE TRIGGER feedback_updated_at BEFORE UPDATE ON public.feedback
FOR EACH ROW EXECUTE PROCEDURE public.update_updated_at_column();

DROP TRIGGER IF EXISTS animales_updated_at ON public.animales;
CREATE TRIGGER animales_updated_at BEFORE UPDATE ON public.animales
FOR EACH ROW EXECUTE PROCEDURE public.update_updated_at_column();

-- 6b. Helper function for optional predio access
CREATE OR REPLACE FUNCTION public.can_access_optional_predio(target_predio uuid)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER SET SEARCH_PATH = PUBLIC AS $$
  SELECT public.is_admin() OR (target_predio IS NOT NULL AND public.can_access_predio(target_predio));
$$;

-- 7. RLS & Policies (safe with DROP IF EXISTS)
ALTER TABLE public.ventas ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.produccion ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.movimientos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.salud ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gastos ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feedback ENABLE ROW LEVEL SECURITY;

-- Helper function for optional predio access
CREATE OR REPLACE FUNCTION public.can_access_optional_predio(target_predio uuid)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER SET SEARCH_PATH = PUBLIC AS $$
  SELECT public.is_admin() OR (target_predio IS NOT NULL AND public.can_access_predio(target_predio));
$$;

-- Grant permissions
GRANT SELECT, INSERT ON PUBLIC.VENTAS, PUBLIC.PRODUCCION, PUBLIC.MOVIMIENTOS, PUBLIC.SALUD, PUBLIC.GASTOS, PUBLIC.FEEDBACK TO AUTHENTICATED;
GRANT UPDATE, DELETE ON PUBLIC.VENTAS, PUBLIC.PRODUCCION, PUBLIC.MOVIMIENTOS, PUBLIC.SALUD, PUBLIC.GASTOS, PUBLIC.FEEDBACK TO AUTHENTICATED;

-- Policies (safe with DROP IF EXISTS)
DO $$ BEGIN
  -- Ventas
  DROP POLICY IF EXISTS ventas_read ON PUBLIC.VENTAS;
  DROP POLICY IF EXISTS ventas_insert ON PUBLIC.VENTAS;
  DROP POLICY IF EXISTS ventas_admin_mutate ON PUBLIC.VENTAS;
  DROP POLICY IF EXISTS ventas_admin_delete ON PUBLIC.VENTAS;
  CREATE POLICY ventas_read ON PUBLIC.VENTAS FOR SELECT TO AUTHENTICATED USING (PUBLIC.CAN_ACCESS_OPTIONAL_PREDIO(PREDIO_ID));
  CREATE POLICY ventas_insert ON PUBLIC.VENTAS FOR INSERT TO AUTHENTICATED WITH CHECK (PUBLIC.CAN_ACCESS_OPTIONAL_PREDIO(PREDIO_ID) AND CREADO_POR = AUTH.UID());
  CREATE POLICY ventas_admin_mutate ON PUBLIC.VENTAS FOR UPDATE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN()) WITH CHECK (PUBLIC.IS_ADMIN());
  CREATE POLICY ventas_admin_delete ON PUBLIC.VENTAS FOR DELETE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN());

  -- Produccion
  DROP POLICY IF EXISTS produccion_read ON PUBLIC.PRODUCCION;
  DROP POLICY IF EXISTS produccion_insert ON PUBLIC.PRODUCCION;
  DROP POLICY IF EXISTS produccion_admin_mutate ON PUBLIC.PRODUCCION;
  DROP POLICY IF EXISTS produccion_admin_delete ON PUBLIC.PRODUCCION;
  CREATE POLICY produccion_read ON PUBLIC.PRODUCCION FOR SELECT TO AUTHENTICATED USING (PUBLIC.CAN_ACCESS_OPTIONAL_PREDIO(PREDIO_ID));
  CREATE POLICY produccion_insert ON PUBLIC.PRODUCCION FOR INSERT TO AUTHENTICATED WITH CHECK (PUBLIC.CAN_ACCESS_OPTIONAL_PREDIO(PREDIO_ID) AND CREADO_POR = AUTH.UID());
  CREATE POLICY produccion_admin_mutate ON PUBLIC.PRODUCCION FOR UPDATE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN()) WITH CHECK (PUBLIC.IS_ADMIN());
  CREATE POLICY produccion_admin_delete ON PUBLIC.PRODUCCION FOR DELETE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN());

  -- Movimientos
  DROP POLICY IF EXISTS movimientos_read ON PUBLIC.MOVIMIENTOS;
  DROP POLICY IF EXISTS movimientos_insert ON PUBLIC.MOVIMIENTOS;
  DROP POLICY IF EXISTS movimientos_admin_mutate ON PUBLIC.MOVIMIENTOS;
  DROP POLICY IF EXISTS movimientos_admin_delete ON PUBLIC.MOVIMIENTOS;
  CREATE POLICY movimientos_read ON PUBLIC.MOVIMIENTOS FOR SELECT TO AUTHENTICATED USING (PUBLIC.IS_ADMIN() OR (ANIMAL_ID IS NOT NULL AND PUBLIC.CAN_ACCESS_ANIMAL(ANIMAL_ID)) OR PUBLIC.CAN_ACCESS_OPTIONAL_PREDIO(PREDIO_ID));
  CREATE POLICY movimientos_insert ON PUBLIC.MOVIMIENTOS FOR INSERT TO AUTHENTICATED WITH CHECK ((ANIMAL_ID IS NOT NULL AND PUBLIC.CAN_ACCESS_ANIMAL(ANIMAL_ID)) OR PUBLIC.CAN_ACCESS_OPTIONAL_PREDIO(PREDIO_ID));
  CREATE POLICY movimientos_admin_mutate ON PUBLIC.MOVIMIENTOS FOR UPDATE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN()) WITH CHECK (PUBLIC.IS_ADMIN());
  CREATE POLICY movimientos_admin_delete ON PUBLIC.MOVIMIENTOS FOR DELETE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN());

  -- Salud
  DROP POLICY IF EXISTS salud_read ON PUBLIC.SALUD;
  DROP POLICY IF EXISTS salud_insert ON PUBLIC.SALUD;
  DROP POLICY IF EXISTS salud_admin_mutate ON PUBLIC.SALUD;
  DROP POLICY IF EXISTS salud_admin_delete ON PUBLIC.SALUD;
  CREATE POLICY salud_read ON PUBLIC.SALUD FOR SELECT TO AUTHENTICATED USING (PUBLIC.CAN_ACCESS_ANIMAL(ANIMAL_ID));
  CREATE POLICY salud_insert ON PUBLIC.SALUD FOR INSERT TO AUTHENTICATED WITH CHECK (PUBLIC.CAN_ACCESS_ANIMAL(ANIMAL_ID) AND CREADO_POR = AUTH.UID());
  CREATE POLICY salud_admin_mutate ON PUBLIC.SALUD FOR UPDATE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN()) WITH CHECK (PUBLIC.IS_ADMIN());
  CREATE POLICY salud_admin_delete ON PUBLIC.SALUD FOR DELETE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN());

  -- Gastos
  DROP POLICY IF EXISTS gastos_read ON PUBLIC.GASTOS;
  DROP POLICY IF EXISTS gastos_insert ON PUBLIC.GASTOS;
  DROP POLICY IF EXISTS gastos_admin_mutate ON PUBLIC.GASTOS;
  DROP POLICY IF EXISTS gastos_admin_delete ON PUBLIC.GASTOS;
  CREATE POLICY gastos_read ON PUBLIC.GASTOS FOR SELECT TO AUTHENTICATED USING (PUBLIC.CAN_ACCESS_OPTIONAL_PREDIO(PREDIO_ID));
  CREATE POLICY gastos_insert ON PUBLIC.GASTOS FOR INSERT TO AUTHENTICATED WITH CHECK (PUBLIC.CAN_ACCESS_OPTIONAL_PREDIO(PREDIO_ID) AND CREADO_POR = AUTH.UID());
  CREATE POLICY gastos_admin_mutate ON PUBLIC.GASTOS FOR UPDATE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN()) WITH CHECK (PUBLIC.IS_ADMIN());
  CREATE POLICY gastos_admin_delete ON PUBLIC.GASTOS FOR DELETE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN());

  -- Feedback
  DROP POLICY IF EXISTS feedback_user_read ON PUBLIC.FEEDBACK;
  DROP POLICY IF EXISTS feedback_user_insert ON PUBLIC.FEEDBACK;
  DROP POLICY IF EXISTS feedback_user_update ON PUBLIC.FEEDBACK;
  DROP POLICY IF EXISTS feedback_admin_read ON PUBLIC.FEEDBACK;
  DROP POLICY IF EXISTS feedback_admin_update ON PUBLIC.FEEDBACK;
  DROP POLICY IF EXISTS feedback_admin_delete ON PUBLIC.FEEDBACK;
  CREATE POLICY feedback_user_read ON PUBLIC.FEEDBACK FOR SELECT TO AUTHENTICATED USING (USER_ID = AUTH.UID());
  CREATE POLICY feedback_user_insert ON PUBLIC.FEEDBACK FOR INSERT TO AUTHENTICATED WITH CHECK (USER_ID = AUTH.UID());
  CREATE POLICY feedback_user_update ON PUBLIC.FEEDBACK FOR UPDATE TO AUTHENTICATED USING (USER_ID = AUTH.UID() AND ESTADO = 'nuevo') WITH CHECK (USER_ID = AUTH.UID());
  CREATE POLICY feedback_admin_read ON PUBLIC.FEEDBACK FOR SELECT TO AUTHENTICATED USING (PUBLIC.IS_ADMIN());
  CREATE POLICY feedback_admin_update ON PUBLIC.FEEDBACK FOR UPDATE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN()) WITH CHECK (PUBLIC.IS_ADMIN());
  CREATE POLICY feedback_admin_delete ON PUBLIC.FEEDBACK FOR DELETE TO AUTHENTICATED USING (PUBLIC.IS_ADMIN());

EXCEPTION WHEN OTHERS THEN NULL; END $$;

-- 8. Updated_at triggers
CREATE OR REPLACE FUNCTION PUBLIC.UPDATE_UPDATED_AT_COLUMN() RETURNS TRIGGER LANGUAGE PLPGSQL AS $$
BEGIN NEW.UPDATED_AT = NOW(); RETURN NEW; END; $$;

DROP TRIGGER IF EXISTS FEEDBACK_UPDATED_AT ON PUBLIC.FEEDBACK;
CREATE TRIGGER FEEDBACK_UPDATED_AT BEFORE UPDATE ON PUBLIC.FEEDBACK FOR EACH ROW EXECUTE PROCEDURE PUBLIC.UPDATE_UPDATED_AT_COLUMN();

DROP TRIGGER IF EXISTS ANIMALES_UPDATED_AT ON PUBLIC.ANIMALES;
CREATE TRIGGER ANIMALES_UPDATED_AT BEFORE UPDATE ON PUBLIC.ANIMALES FOR EACH ROW EXECUTE PROCEDURE PUBLIC.UPDATE_UPDATED_AT_COLUMN();

-- 9. Grant permissions
GRANT SELECT, INSERT ON PUBLIC.VENTAS, PUBLIC.PRODUCCION, PUBLIC.MOVIMIENTOS, PUBLIC.SALUD, PUBLIC.GASTOS, PUBLIC.FEEDBACK TO AUTHENTICATED;
GRANT UPDATE, DELETE ON PUBLIC.VENTAS, PUBLIC.PRODUCCION, PUBLIC.MOVIMIENTOS, PUBLIC.SALUD, PUBLIC.GASTOS, PUBLIC.FEEDBACK TO AUTHENTICATED;

-- 9b. Make your user admin (REPLACE WITH YOUR EMAIL)
-- UPDATE PUBLIC.PROFILES SET ROL = 'admin' WHERE EMAIL = 'cisamo1203@gmail.com';
