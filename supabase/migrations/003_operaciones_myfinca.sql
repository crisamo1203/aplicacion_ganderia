-- Módulos operativos de MyFinca Pro.
alter table public.profiles add column if not exists nombre text;
alter table public.profiles add column if not exists telefono text;
alter table public.profiles add column if not exists grupo text;
alter table public.profiles add column if not exists activo boolean not null default true;

alter table public.animales add column if not exists tipo text default 'Individual';
alter table public.animales add column if not exists clase text;
alter table public.animales add column if not exists proposito text;
alter table public.animales add column if not exists fecha_nacimiento date;
alter table public.animales add column if not exists peso_kg numeric(8,2);
alter table public.animales add column if not exists sexo text;
alter table public.animales add column if not exists raza text;
alter table public.animales add column if not exists color text;
alter table public.animales add column if not exists proveedor text;
alter table public.animales add column if not exists especie text;
alter table public.animales add column if not exists origen text;
alter table public.animales add column if not exists valor_compra numeric(14,2);
alter table public.animales add column if not exists valor_venta numeric(14,2);
alter table public.animales add column if not exists estado text default 'Activo';
alter table public.animales add column if not exists propietario text;
alter table public.animales add column if not exists marca text;
alter table public.animales add column if not exists comentarios text;

create table public.ventas (
  id uuid primary key default gen_random_uuid(), fecha date not null default current_date,
  predio_id uuid references public.predios(id) on delete restrict, clase text, tipo text,
  detalle text, cantidad numeric(14,3), valor_unitario numeric(14,2), valor_total numeric(14,2),
  metodo text, observaciones text, creado_por uuid not null default auth.uid() references public.profiles(id),
  created_at timestamptz not null default now()
);
create table public.produccion (
  id uuid primary key default gen_random_uuid(), fecha date not null default current_date,
  predio_id uuid references public.predios(id) on delete restrict, animal_id uuid references public.animales(id) on delete set null,
  clase text, nombre_referencia text, ordeno boolean, kilos_leche numeric(10,2),
  litros_leche numeric(10,2), cantidad_huevos integer check (cantidad_huevos >= 0),
  observaciones text, creado_por uuid not null default auth.uid() references public.profiles(id),
  created_at timestamptz not null default now()
);
create table public.movimientos (
  id uuid primary key default gen_random_uuid(), animal_id uuid references public.animales(id) on delete set null,
  predio_id uuid references public.predios(id) on delete restrict, tipo text not null, valor numeric(14,2),
  fecha timestamptz not null default now(), comentarios text,
  creado_por uuid not null default auth.uid() references public.profiles(id), created_at timestamptz not null default now()
);
create table public.salud (
  id uuid primary key default gen_random_uuid(), animal_id uuid not null references public.animales(id) on delete restrict,
  fecha date not null default current_date, tipo text not null, medicamento text, veterinario text,
  proxima_cita date, observaciones text, creado_por uuid not null default auth.uid() references public.profiles(id),
  created_at timestamptz not null default now()
);
create table public.gastos (
  id uuid primary key default gen_random_uuid(), fecha date not null default current_date,
  predio_id uuid references public.predios(id) on delete restrict, detalle text not null,
  valor numeric(14,2) not null check (valor >= 0), metodo text, inversor text, observaciones text,
  creado_por uuid not null default auth.uid() references public.profiles(id), created_at timestamptz not null default now()
);

create index ventas_predio_idx on public.ventas(predio_id);
create index produccion_predio_fecha_idx on public.produccion(predio_id, fecha desc);
create index movimientos_animal_fecha_idx on public.movimientos(animal_id, fecha desc);
create index salud_animal_fecha_idx on public.salud(animal_id, fecha desc);
create index gastos_predio_fecha_idx on public.gastos(predio_id, fecha desc);

create or replace function public.can_access_optional_predio(target_predio uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select public.is_admin() or (target_predio is not null and public.can_access_predio(target_predio));
$$;

grant select, insert on public.ventas, public.produccion, public.movimientos, public.salud, public.gastos to authenticated;
grant update, delete on public.ventas, public.produccion, public.movimientos, public.salud, public.gastos to authenticated;
alter table public.ventas enable row level security;
alter table public.produccion enable row level security;
alter table public.movimientos enable row level security;
alter table public.salud enable row level security;
alter table public.gastos enable row level security;

create policy ventas_read on public.ventas for select to authenticated using (public.can_access_optional_predio(predio_id));
create policy ventas_insert on public.ventas for insert to authenticated with check (public.can_access_optional_predio(predio_id) and creado_por = auth.uid());
create policy ventas_admin_mutate on public.ventas for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy ventas_admin_delete on public.ventas for delete to authenticated using (public.is_admin());
create policy produccion_read on public.produccion for select to authenticated using (public.can_access_optional_predio(predio_id));
create policy produccion_insert on public.produccion for insert to authenticated with check (public.can_access_optional_predio(predio_id) and creado_por = auth.uid());
create policy produccion_admin_mutate on public.produccion for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy produccion_admin_delete on public.produccion for delete to authenticated using (public.is_admin());
create policy movimientos_read on public.movimientos for select to authenticated using (public.is_admin() or (animal_id is not null and public.can_access_animal(animal_id)) or public.can_access_optional_predio(predio_id));
create policy movimientos_insert on public.movimientos for insert to authenticated with check ((animal_id is not null and public.can_access_animal(animal_id)) or public.can_access_optional_predio(predio_id));
create policy movimientos_admin_mutate on public.movimientos for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy movimientos_admin_delete on public.movimientos for delete to authenticated using (public.is_admin());
create policy salud_read on public.salud for select to authenticated using (public.can_access_animal(animal_id));
create policy salud_insert on public.salud for insert to authenticated with check (public.can_access_animal(animal_id) and creado_por = auth.uid());
create policy salud_admin_mutate on public.salud for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy salud_admin_delete on public.salud for delete to authenticated using (public.is_admin());
create policy gastos_read on public.gastos for select to authenticated using (public.can_access_optional_predio(predio_id));
create policy gastos_insert on public.gastos for insert to authenticated with check (public.can_access_optional_predio(predio_id) and creado_por = auth.uid());
create policy gastos_admin_mutate on public.gastos for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy gastos_admin_delete on public.gastos for delete to authenticated using (public.is_admin());
