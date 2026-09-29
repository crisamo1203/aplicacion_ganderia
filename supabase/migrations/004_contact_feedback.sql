-- Contact info fields for profiles + Feedback system

-- Add contact info columns to profiles
alter table public.profiles add column if not exists direccion text;
alter table public.profiles add column if not exists ciudad text;
alter table public.profiles add column if not exists notas_contacto text;

-- Create feedback table
create table if not exists public.feedback (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  tipo text not null check (tipo in ('problema', 'sugerencia', 'mejora', 'otro')),
  titulo text not null check (char_length(trim(titulo)) > 0 and char_length(trim(titulo)) <= 200),
  descripcion text not null check (char_length(trim(descripcion)) > 0),
  modulo text,
  prioridad text not null default 'media' check (prioridad in ('baja', 'media', 'alta', 'critica')),
  estado text not null default 'nuevo' check (estado in ('nuevo', 'en_revision', 'resuelto', 'cerrado')),
  respuesta_admin text,
  responded_by uuid references auth.users(id) on delete set null,
  responded_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists feedback_user_idx on public.feedback(user_id);
create index if not exists feedback_estado_idx on public.feedback(estado);
create index if not exists feedback_tipo_idx on public.feedback(tipo);
create index if not exists feedback_prioridad_idx on public.feedback(prioridad);
create index if not exists feedback_created_idx on public.feedback(created_at desc);

-- Trigger for updated_at
create or replace function public.update_updated_at_column()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists feedback_updated_at on public.feedback;
create trigger feedback_updated_at before update on public.feedback
for each row execute procedure public.update_updated_at_column();

-- RLS for feedback
alter table public.feedback enable row level security;

-- Users see only their own feedback
create policy feedback_user_read on public.feedback for select to authenticated
using (user_id = auth.uid());

-- Users can create their own feedback
create policy feedback_user_insert on public.feedback for insert to authenticated
with check (user_id = auth.uid());

-- Users can update their own feedback (only if 'nuevo')
create policy feedback_user_update on public.feedback for update to authenticated
using (user_id = auth.uid() and estado = 'nuevo')
with check (user_id = auth.uid());

-- Admins see all
create policy feedback_admin_read on public.feedback for select to authenticated
using (public.is_admin());

-- Admins can update any
create policy feedback_admin_update on public.feedback for update to authenticated
using (public.is_admin())
with check (public.is_admin());

-- Admins can delete
create policy feedback_admin_delete on public.feedback for delete to authenticated
using (public.is_admin());

grant select, insert on public.feedback to authenticated;
grant update, delete on public.feedback to authenticated;
