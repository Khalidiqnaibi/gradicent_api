-- supabase_rls_policies.sql
-- --------------------------------------------------------------------------------------------
-- Row-level security policies for the Binder API (api.bindersoftware.com).
-- Table names match the production database (the API reads them from DB_TABLE_* env vars).
--
-- The API talks to Supabase with the project's `anon` key and signs users in with its own JWTs
-- (not Supabase Auth), so Postgres cannot tell which Binder user a request is for. These
-- policies therefore grant the `anon` role exactly the operations the API code performs on each
-- table and nothing more; per-user ownership is enforced in the API itself (every query is
-- filtered by owner_id / user_id taken from the signed-in session).
--
-- Keep the `anon` key server-side only (Vercel env var SUPABASE_KEY). Anyone holding it gets the
-- access below.
--
-- Safe to re-run: every policy is dropped and recreated.
-- Run in Supabase: Dashboard -> SQL Editor -> paste -> Run.
-- --------------------------------------------------------------------------------------------

begin;

-- ---------- Users: sign-in provisioning, profile, settings, appointments ----------
-- Appointments, plan and settings are stored inside the user's record_data.
-- No DELETE: the API exposes no route that deletes accounts.
alter table public.user_accounts_v1 enable row level security;
grant select, insert, update on public.user_accounts_v1 to anon;

drop policy if exists "binder_api_users_select" on public.user_accounts_v1;
create policy "binder_api_users_select" on public.user_accounts_v1
  for select to anon using (true);

drop policy if exists "binder_api_users_insert" on public.user_accounts_v1;
create policy "binder_api_users_insert" on public.user_accounts_v1
  for insert to anon
  with check (id is not null and domain in ('medical', 'business'));

drop policy if exists "binder_api_users_update" on public.user_accounts_v1;
create policy "binder_api_users_update" on public.user_accounts_v1
  for update to anon
  using (true)
  with check (id is not null and domain in ('medical', 'business'));

-- ---------- Owned records: clients/patients, employees, products, services ----------
-- Every row belongs to a user (owner_id) within a domain.
alter table public.crm_entities_v1 enable row level security;
alter table public.hr_entities_v1 enable row level security;
alter table public.product_items_v1 enable row level security;
alter table public.service_catalog_v1 enable row level security;
grant select, insert, update, delete on
  public.crm_entities_v1, public.hr_entities_v1, public.product_items_v1, public.service_catalog_v1
  to anon;

drop policy if exists "binder_api_clients_all" on public.crm_entities_v1;
create policy "binder_api_clients_all" on public.crm_entities_v1
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and domain in ('medical', 'business'));

drop policy if exists "binder_api_employees_all" on public.hr_entities_v1;
create policy "binder_api_employees_all" on public.hr_entities_v1
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and domain in ('medical', 'business'));

drop policy if exists "binder_api_products_all" on public.product_items_v1;
create policy "binder_api_products_all" on public.product_items_v1
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and domain in ('medical', 'business'));

drop policy if exists "binder_api_services_all" on public.service_catalog_v1;
create policy "binder_api_services_all" on public.service_catalog_v1
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and domain in ('medical', 'business'));

-- ---------- Nested records: client interactions/visits and transactions ----------
alter table public.logs_v1 enable row level security;
alter table public.ledgers_v1 enable row level security;
grant select, insert, update, delete on public.logs_v1, public.ledgers_v1 to anon;

drop policy if exists "binder_api_interactions_all" on public.logs_v1;
create policy "binder_api_interactions_all" on public.logs_v1
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and parent_id is not null and domain in ('medical', 'business'));

drop policy if exists "binder_api_transactions_all" on public.ledgers_v1;
create policy "binder_api_transactions_all" on public.ledgers_v1
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and parent_id is not null and domain in ('medical', 'business'));

-- ---------- Analytics events ----------
-- This project has no events table (DB_TABLE_EVENTS); log_event() catches the failure, so
-- nothing is needed here. If you add the table later, grant anon INSERT on it only.

-- ---------- File metadata: upload, list, soft delete (no hard deletes) ----------
alter table public.file_metadata_v1 enable row level security;
grant select, insert, update on public.file_metadata_v1 to anon;

drop policy if exists "binder_api_files_select" on public.file_metadata_v1;
create policy "binder_api_files_select" on public.file_metadata_v1
  for select to anon using (user_id is not null);

drop policy if exists "binder_api_files_insert" on public.file_metadata_v1;
create policy "binder_api_files_insert" on public.file_metadata_v1
  for insert to anon with check (user_id is not null);

drop policy if exists "binder_api_files_update" on public.file_metadata_v1;
create policy "binder_api_files_update" on public.file_metadata_v1
  for update to anon using (user_id is not null) with check (user_id is not null);

-- ---------- Storage bucket for uploaded files ----------
-- The bucket is PRIVATE: see migrations/2026-10-21_private_file_storage.sql, which creates it and
-- adds the read policy used for signed download URLs.
drop policy if exists "binder_api_assets_upload" on storage.objects;
create policy "binder_api_assets_upload" on storage.objects
  for insert to anon
  with check (bucket_id = 'user_assets_v1');

commit;
