-- supabase_rls_policies.sql
-- --------------------------------------------------------------------------------------------
-- Row-level security policies for the Binder API (api.bindersoftware.com).
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
alter table public."CRM_entities_v1" enable row level security;
alter table public."EMPLOYEE_entities_v1" enable row level security;
alter table public.prod_v1 enable row level security;
alter table public.service_catalog_v1 enable row level security;
grant select, insert, update, delete on
  public."CRM_entities_v1", public."EMPLOYEE_entities_v1", public.prod_v1, public.service_catalog_v1
  to anon;

drop policy if exists "binder_api_clients_all" on public."CRM_entities_v1";
create policy "binder_api_clients_all" on public."CRM_entities_v1"
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and domain in ('medical', 'business'));

drop policy if exists "binder_api_employees_all" on public."EMPLOYEE_entities_v1";
create policy "binder_api_employees_all" on public."EMPLOYEE_entities_v1"
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and domain in ('medical', 'business'));

drop policy if exists "binder_api_products_all" on public.prod_v1;
create policy "binder_api_products_all" on public.prod_v1
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and domain in ('medical', 'business'));

drop policy if exists "binder_api_services_all" on public.service_catalog_v1;
create policy "binder_api_services_all" on public.service_catalog_v1
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and domain in ('medical', 'business'));

-- ---------- Nested records: client interactions/visits and transactions ----------
alter table public."CRM_log_v1" enable row level security;
alter table public."CRM_ledger_v1" enable row level security;
grant select, insert, update, delete on public."CRM_log_v1", public."CRM_ledger_v1" to anon;

drop policy if exists "binder_api_interactions_all" on public."CRM_log_v1";
create policy "binder_api_interactions_all" on public."CRM_log_v1"
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and parent_id is not null and domain in ('medical', 'business'));

drop policy if exists "binder_api_transactions_all" on public."CRM_ledger_v1";
create policy "binder_api_transactions_all" on public."CRM_ledger_v1"
  for all to anon
  using (owner_id is not null)
  with check (owner_id is not null and parent_id is not null and domain in ('medical', 'business'));

-- ---------- Analytics events: write-only from the API ----------
alter table public.analytics_events_v1 enable row level security;
grant insert on public.analytics_events_v1 to anon;

drop policy if exists "binder_api_events_insert" on public.analytics_events_v1;
create policy "binder_api_events_insert" on public.analytics_events_v1
  for insert to anon
  with check (event_code is not null);

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
-- Uploads go to <user_id>/<client_no>/<folder>/<file>. Files are served through public URLs,
-- so the bucket itself must be public for downloads; the API only needs to upload.
drop policy if exists "binder_api_assets_upload" on storage.objects;
create policy "binder_api_assets_upload" on storage.objects
  for insert to anon
  with check (bucket_id = 'user_assets_v1');

commit;
