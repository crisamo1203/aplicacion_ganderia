-- MiFinca Pro. Ejecutar en Supabase SQL Editor o con Supabase CLI.
create type public.app_role as enum ('admin', 'cliente');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  rol public.app_role not null default 'cliente',
  created_at timestamptz not null default now()
);
create table public.predios (
  id uuid primary key default gen_random_uuid(),
  nombre text not null check (char_length(trim(nombre)) > 0),
  owner_id uuid not null references public.profiles(id) on delete restrict,
  created_at timestamptz not null default now(), unique (owner_id, nombre)
);
create table public.lotes (
  id uuid primary key default gen_random_uuid(),
  nombre text not null check (char_length(trim(nombre)) > 0),
  predio_id uuid not null references public.predios(id) on delete restrict,
  activo boolean not null default true, created_at timestamptz not null default now(),
  unique (predio_id, nombre)
);
create table public.animales (
  id uuid primary key default gen_random_uuid(),
  arete text not null unique check (char_length(trim(arete)) > 0),
  lote_id uuid not null references public.lotes(id) on delete restrict,
  fecha_ingreso date not null default current_date, activo boolean not null default true,
  created_at timestamptz not null default now()
);
create table public.pesajes (
  id uuid primary key default gen_random_uuid(),
  animal_id uuid not null references public.animales(id) on delete restrict,
  fecha date not null default current_date, peso_kg numeric(8,2) not null check (peso_kg > 0),
  nota text check (char_length(nota) <= 300),
  creado_por uuid not null default auth.uid() references public.profiles(id) on delete restrict,
  created_at timestamptz not null default now()
);
create index predios_owner_id_idx on public.predios(owner_id);
create index lotes_predio_id_idx on public.lotes(predio_id);
create index animales_lote_id_idx on public.animales(lote_id);
create index pesajes_animal_fecha_idx on public.pesajes(animal_id, fecha desc, created_at desc);

-- Perfil automático al primer acceso con Google.
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email)
  values (new.id, coalesce(new.email, 'sin-correo-' || new.id::text))
  on conflict (id) do update set email = excluded.email;
  return new;
end;
$$;
create trigger on_auth_user_created after insert on auth.users
for each row execute procedure public.handle_new_user();

-- Funciones SECURITY DEFINER: evitan recursión de RLS.
create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists(select 1 from public.profiles where id = auth.uid() and rol = 'admin');
$$;
create or replace function public.can_access_predio(target_predio uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select public.is_admin() or exists(select 1 from public.predios where id = target_predio and owner_id = auth.uid());
$$;
create or replace function public.can_access_lote(target_lote uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists(select 1 from public.lotes where id = target_lote and public.can_access_predio(predio_id));
$$;
create or replace function public.can_access_animal(target_animal uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists(select 1 from public.animales where id = target_animal and public.can_access_lote(lote_id));
$$;

grant usage on schema public to authenticated;
grant select on public.profiles, public.predios, public.lotes, public.animales, public.pesajes to authenticated;
grant insert on public.pesajes to authenticated;
grant insert, update, delete on public.predios, public.lotes, public.animales to authenticated;
grant update on public.profiles to authenticated;
alter table public.profiles enable row level security;
alter table public.predios enable row level security;
alter table public.lotes enable row level security;
alter table public.animales enable row level security;
alter table public.pesajes enable row level security;

create policy profiles_read on public.profiles for select to authenticated using (id = auth.uid() or public.is_admin());
create policy profiles_admin_write on public.profiles for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy predios_read on public.predios for select to authenticated using (public.can_access_predio(id));
create policy predios_admin_write on public.predios for all to authenticated using (public.is_admin()) with check (public.is_admin());
create policy lotes_read on public.lotes for select to authenticated using (public.can_access_lote(id));
create policy lotes_admin_write on public.lotes for all to authenticated using (public.is_admin()) with check (public.is_admin());
create policy animales_read on public.animales for select to authenticated using (public.can_access_animal(id));
create policy animales_admin_write on public.animales for all to authenticated using (public.is_admin()) with check (public.is_admin());
create policy pesajes_read on public.pesajes for select to authenticated using (public.can_access_animal(animal_id));
create policy pesajes_insert on public.pesajes for insert to authenticated with check (public.can_access_animal(animal_id) and creado_por = auth.uid());
create policy pesajes_admin_update on public.pesajes for update to authenticated using (public.is_admin()) with check (public.is_admin());
create policy pesajes_admin_delete on public.pesajes for delete to authenticated using (public.is_admin());

-- Tras el primer login del administrador, ejecutar una única vez:
-- update public.profiles set rol = 'admin' where email = 'tu-correo@gmail.com';
