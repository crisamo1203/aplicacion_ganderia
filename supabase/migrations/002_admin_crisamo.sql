-- Asigna el administrador solicitado, incluso si ya inició sesión.
update public.profiles
set rol = 'admin'
where lower(email) = 'crisamo1203@gmail.com';

-- También lo asigna automáticamente cuando esa cuenta ingrese por primera vez.
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, email, rol)
  values (
    new.id,
    coalesce(new.email, 'sin-correo-' || new.id::text),
    case when lower(coalesce(new.email, '')) = 'crisamo1203@gmail.com'
      then 'admin'::public.app_role else 'cliente'::public.app_role end
  )
  on conflict (id) do update set
    email = excluded.email,
    rol = case when lower(excluded.email) = 'crisamo1203@gmail.com'
      then 'admin'::public.app_role else public.profiles.rol end;
  return new;
end;
$$;
