create table if not exists breakout_failures (
  id bigint generated always as identity primary key,
  company text,
  ticker text,
  location text,
  failure_time timestamptz,
  created_at timestamptz default now()
);
