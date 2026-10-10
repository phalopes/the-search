create table private.initial_sessions (legacy_id integer primary key, entry jsonb not null);
alter table private.initial_sessions enable row level security;
revoke all on private.initial_sessions from public,anon,authenticated;
create function private.import_history() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if exists(select 1 from private.personal_owner where email=lower(new.email)) then
  insert into public.surf_sessions(user_id,surf_date,spot_id,starts_at,kind,rating,notes,recommendation)
  select new.id,(entry->>'surf_date')::date,entry->>'spot_id',nullif(entry->>'starts_at','')::time,entry->>'kind',nullif(entry->>'rating','')::numeric,entry->>'notes',entry->'recommendation' from private.initial_sessions order by legacy_id;
 end if;
 return new;
end; $$;
revoke all on function private.import_history() from public,anon,authenticated;
create trigger the_search_import_history after insert on auth.users for each row execute function private.import_history();
