-- 2026-10-20_per_owner_primary_keys.sql
-- --------------------------------------------------------------------------------------------
-- Record ids are numbered per owner ("1", "2", ... for each user and workspace), but these tables
-- were keyed by id alone, so a second user's first record (or any reused number) collided with an
-- existing row and the insert failed. Key them by (domain, owner_id, id) instead.
--
-- Checked before writing this: no rows have a null domain/owner_id and there are no duplicate
-- (domain, owner_id, id) combinations, and no foreign keys reference these tables.
-- The API (commit 18978dc) already scopes every update/delete by domain + owner_id.
--
-- Run in Supabase: Dashboard -> SQL Editor -> paste -> Run. All-or-nothing.
-- --------------------------------------------------------------------------------------------

begin;

alter table public.crm_entities_v1    drop constraint crm_entities_v1_pkey,    add primary key (domain, owner_id, id);
alter table public.hr_entities_v1     drop constraint hr_entities_v1_pkey,     add primary key (domain, owner_id, id);
alter table public.product_items_v1   drop constraint product_items_v1_pkey,   add primary key (domain, owner_id, id);
alter table public.service_catalog_v1 drop constraint service_catalog_v1_pkey, add primary key (domain, owner_id, id);
alter table public.logs_v1            drop constraint logs_v1_pkey,            add primary key (domain, owner_id, id);
alter table public.ledgers_v1         drop constraint ledgers_v1_pkey,         add primary key (domain, owner_id, id);

commit;

-- Verify (should list (domain, owner_id, id) for the six tables above and (id, domain) for users):
select conrelid::regclass::text as table_name, pg_get_constraintdef(oid) as primary_key
from pg_constraint
where connamespace = 'public'::regnamespace and contype = 'p'
order by 1;
