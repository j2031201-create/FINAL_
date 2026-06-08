-- =====================================================================
-- 정비사업 수주 타당성 분석 툴 · Supabase 스키마
-- 실행 위치: Supabase 콘솔 > SQL Editor > New query > 아래 전체 붙여넣기 > Run
-- =====================================================================

-- 1) 분석 구역 테이블 -------------------------------------------------
create table if not exists public.analysis_regions (
    id            bigint generated always as identity primary key,
    created_at    timestamptz not null default now(),

    -- 구역 식별
    region_name   text not null,                 -- 예: ○○3 후보구역
    sido          text,                          -- 시도
    sigungu       text,                          -- 시군구
    dong          text,                          -- 행정동
    project_type  text not null,                 -- rebuild | redevelop | small
    small_type    text,                          -- garo | srebuild (소규모만)

    -- 구역 요건 입력값
    area_sqm      numeric,                        -- 구역면적(㎡)
    built_year    int,                            -- 준공연도(재건축)
    diagnosis     text,                           -- pass | fail (안전진단)
    old_ratio     numeric,                        -- 노후 동수 비율(%)
    small_lot     numeric,                        -- 과소필지율(%)
    agree_ratio   numeric,                        -- 주민동의율(%)

    -- 사업성 입력값
    units         int,                            -- 세대수
    prev_asset    numeric,                        -- 종전자산(억)
    sale_price    numeric,                        -- 일반분양가(만/평)
    construct_cost numeric,                       -- 공사비(만/평)
    gen_ratio     numeric,                        -- 일반분양비율(%)

    -- 계산 결과 (스냅샷 저장 → 추세분석용)
    biryul        numeric,                        -- 비례율(%)
    total_cost    numeric,                        -- 총사업비(억)
    profit        numeric,                        -- 사업이익(억)
    jeongbi_score numeric,                        -- 주거정비지수
    verdict       text,                           -- 판정 결과
    req_pass      boolean,                        -- 법정요건 충족 여부

    -- 메모
    note          text
);

-- 2) 인덱스 ---------------------------------------------------------
create index if not exists idx_regions_created on public.analysis_regions (created_at desc);
create index if not exists idx_regions_dong    on public.analysis_regions (sido, sigungu, dong);
create index if not exists idx_regions_type    on public.analysis_regions (project_type);

-- 3) RLS (Row Level Security) ---------------------------------------
-- ★ "저장이 안 됨" 의 가장 흔한 원인이 여기입니다.
--   RLS를 켜되, anon 키로 insert/select가 되도록 정책을 명시합니다.
alter table public.analysis_regions enable row level security;

-- 기존 정책이 있으면 지우고 다시 생성 (재실행 안전)
drop policy if exists "anon_select" on public.analysis_regions;
drop policy if exists "anon_insert" on public.analysis_regions;

-- 누구나 읽기 (공개 누적 DB 컨셉)
create policy "anon_select"
    on public.analysis_regions
    for select
    to anon
    using (true);

-- 누구나 쓰기 (무료 분석 → 자동 데이터 축적 컨셉)
create policy "anon_insert"
    on public.analysis_regions
    for insert
    to anon
    with check (true);

-- =====================================================================
-- 확인용: 아래를 실행하면 테스트 row가 들어가는지 즉시 검증됩니다.
-- insert into public.analysis_regions (region_name, project_type, biryul)
-- values ('테스트구역', 'rebuild', 105.3);
-- select * from public.analysis_regions order by created_at desc limit 5;
-- =====================================================================
