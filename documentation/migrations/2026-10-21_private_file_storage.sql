-- Private document storage for patient and client files.
--
-- Files live in a PRIVATE bucket. The browser uploads straight to Supabase Storage with a one-time
-- signed upload URL issued by the API (so large scans are not squeezed through the API's request
-- size limit), and every download goes through a signed URL that expires after a few minutes.
-- Nothing in the bucket is reachable through a public link.
--
-- Safe to run more than once.

begin;

-- ---------- Bucket ----------
-- 50 MB per file (the Supabase free-plan ceiling) and an explicit list of document, image,
-- audio and video types. SVG and HTML are deliberately not allowed (they can carry scripts).
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'user_assets_v1', 'user_assets_v1', false, 52428800,
  array[
    'application/pdf',
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/heic', 'image/heif', 'image/tiff', 'image/bmp',
    'application/dicom',
    'text/plain', 'text/csv', 'application/rtf',
    'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/vnd.oasis.opendocument.text', 'application/vnd.oasis.opendocument.spreadsheet',
    'audio/mpeg', 'audio/mp4', 'audio/wav', 'audio/x-wav', 'audio/webm', 'audio/ogg', 'audio/aac',
    'video/mp4', 'video/quicktime', 'video/webm', 'video/x-msvideo', 'video/mpeg'
  ]
)
on conflict (id) do update set
  public = false,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- ---------- Storage policies (anon = the API server's key, never shipped to browsers) ----------
-- insert: needed to issue signed upload URLs; select: signed download URLs and upload checks.
-- No update/delete: uploads never overwrite, and deleted documents are kept for the record.
drop policy if exists "binder_api_assets_upload" on storage.objects;
create policy "binder_api_assets_upload" on storage.objects
  for insert to anon
  with check (bucket_id = 'user_assets_v1');

drop policy if exists "binder_api_assets_read" on storage.objects;
create policy "binder_api_assets_read" on storage.objects
  for select to anon
  using (bucket_id = 'user_assets_v1');

-- ---------- File metadata ----------
-- Record ids are numbered per workspace, so the same client number exists in both the business
-- and the medical workspace: files are told apart by domain.
alter table public.file_metadata_v1
  add column if not exists domain text not null default 'business',
  add column if not exists storage_path text,
  add column if not exists size_bytes bigint;

create index if not exists file_metadata_v1_owner_idx
  on public.file_metadata_v1 (user_id, domain, client_no)
  where not is_deleted;

alter table public.file_metadata_v1 enable row level security;
grant select, insert, update on public.file_metadata_v1 to anon;

drop policy if exists "binder_api_files_select" on public.file_metadata_v1;
create policy "binder_api_files_select" on public.file_metadata_v1
  for select to anon using (user_id is not null);

drop policy if exists "binder_api_files_insert" on public.file_metadata_v1;
create policy "binder_api_files_insert" on public.file_metadata_v1
  for insert to anon with check (user_id is not null and domain in ('medical', 'business'));

drop policy if exists "binder_api_files_update" on public.file_metadata_v1;
create policy "binder_api_files_update" on public.file_metadata_v1
  for update to anon using (user_id is not null) with check (user_id is not null);

commit;
