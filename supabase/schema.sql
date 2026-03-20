-- Run this in Supabase SQL editor
create extension if not exists pgcrypto;

create table if not exists public.onboarding_runs (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  candidate_name text,
  source_type text not null,
  recommended_role_family text,
  metrics jsonb not null default '{}'::jsonb,
  gaps jsonb not null default '[]'::jsonb,
  roadmap jsonb not null default '[]'::jsonb,
  trace jsonb not null default '[]'::jsonb,
  quality_checks jsonb not null default '{}'::jsonb,
  advanced_metrics jsonb not null default '{}'::jsonb,
  market_insights jsonb not null default '{}'::jsonb,
  resume_signals jsonb not null default '[]'::jsonb,
  jd_signals jsonb not null default '[]'::jsonb,
  input_meta jsonb not null default '{}'::jsonb
);

create index if not exists onboarding_runs_created_at_idx
on public.onboarding_runs (created_at desc);

-- For quick hackathon setup. Tighten RLS for production.
alter table public.onboarding_runs enable row level security;

drop policy if exists "Allow service role full access" on public.onboarding_runs;

create policy "Allow service role full access"
on public.onboarding_runs
as permissive
for all
to service_role
using (true)
with check (true);
