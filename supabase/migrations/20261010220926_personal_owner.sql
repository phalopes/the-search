create table private.personal_owner (singleton boolean primary key default true check(singleton), email text not null unique);
alter table private.personal_owner enable row level security;
revoke all on private.personal_owner from public,anon,authenticated;
create or replace function private.can_travel() returns boolean language sql stable security definer set search_path='' as $$ select exists(select 1 from public.members m join auth.users u on u.id=m.user_id join private.personal_owner o on o.email=lower(u.email) where m.user_id=(select auth.uid()) and m.admin) and exists(select 1 from public.feature_flags where name='personal_travel' and enabled); $$;
create or replace function private.on_signup() returns trigger language plpgsql security definer set search_path='' as $$
declare owner_admin boolean;
begin
 select admin into owner_admin from private.allowed_emails where email=lower(new.email);
 if owner_admin is null or new.is_anonymous then raise exception 'Cadastro restrito a convites'; end if;
 insert into public.members(user_id,admin) values(new.id,owner_admin);
 if owner_admin and exists(select 1 from private.personal_owner where email=lower(new.email)) then insert into public.travel_times values(new.id,'mole',35),(new.id,'campeche',25),(new.id,'matadeiro',33),(new.id,'joaquina',35),(new.id,'barra-da-lagoa',41); end if;
 return new;
end; $$;
