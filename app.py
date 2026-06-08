"""
정비사업 수주 타당성 분석 플랫폼
시행사 사업개발팀용 · 재건축/재개발/소규모정비 후보지 사업성 자동 진단
"""
import streamlit as st
import pandas as pd
import datetime as dt

st.set_page_config(page_title="정비사업 수주 타당성 분석", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
html, body, .stApp { font-family:'Noto Sans KR',sans-serif !important; background:#F5F6F7 !important; color:#1A1A1A !important; }
#MainMenu, footer, header { display:none !important; }
.main .block-container { padding:0 2rem 3rem !important; max-width:1500px !important; }
.top-header { background:#03C75A; margin:0 -2rem 0; padding:14px 2rem; display:flex; align-items:center; gap:16px; }
.top-header .brand { font-size:18px; font-weight:900; color:#fff; display:flex; align-items:center; gap:8px; letter-spacing:-0.02em; }
.top-header .brand-sub { font-size:11px; font-weight:500; color:rgba(255,255,255,.85); padding:2px 9px; background:rgba(255,255,255,.18); border-radius:100px; }
.top-header .spacer { flex:1; }
.top-header .head-link { font-size:13px; color:rgba(255,255,255,.92); font-weight:500; }
.region-bar { background:#fff; border:1px solid #E5E8EB; border-top:none; margin:0 -2rem 20px; padding:14px 2rem; display:flex; align-items:center; gap:12px; }
.region-bar .rname { font-size:17px; font-weight:700; color:#191F28; }
.region-bar .rtag { font-size:12px; font-weight:500; padding:3px 10px; border-radius:6px; }
.rtag.sample { background:#E7F9F0; color:#03864A; }
.rtag.law { background:#F2F4F6; color:#4E5968; }
.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:18px; }
.kpi-card { background:#fff; border:1px solid #E5E8EB; border-radius:12px; padding:18px 20px; transition:border-color .15s,box-shadow .15s; }
.kpi-card:hover { border-color:#03C75A; box-shadow:0 2px 12px rgba(3,199,90,.1); }
.kpi-card .kl { font-size:12px; color:#8B95A1; font-weight:500; margin-bottom:8px; }
.kpi-card .kv { font-size:1.9rem; font-weight:900; color:#191F28; line-height:1; letter-spacing:-0.02em; }
.kpi-card .kv small { font-size:13px; font-weight:500; color:#8B95A1; margin-left:3px; }
.kpi-card .kd { font-size:11px; margin-top:7px; font-weight:500; }
.verdict { border-radius:12px; padding:16px 20px; margin-bottom:20px; display:flex; align-items:center; gap:14px; }
.verdict .vi { font-size:28px; }
.verdict .vt h4 { margin:0; font-size:16px; font-weight:700; }
.verdict .vt p { margin:3px 0 0; font-size:13px; }
.v-success { background:#E7F9F0; } .v-success h4,.v-success p { color:#03864A; }
.v-info { background:#E8F3FF; } .v-info h4,.v-info p { color:#1B64DA; }
.v-warning { background:#FFF4E6; } .v-warning h4,.v-warning p { color:#E8590C; }
.sec-title { font-size:15px; font-weight:700; color:#191F28; margin:20px 0 12px; display:flex; align-items:center; gap:8px; }
.sec-title::before { content:''; width:3px; height:15px; background:#03C75A; border-radius:2px; }
[data-testid="stSidebar"] { background:#fff !important; border-right:1px solid #E5E8EB !important; }
[data-testid="stSidebar"] * { font-family:'Noto Sans KR',sans-serif !important; }
.side-h { font-size:13px; font-weight:700; color:#191F28; margin:6px 0 2px; }
.stNumberInput input, .stTextInput input { border:1.5px solid #D1D6DB !important; border-radius:8px !important; font-size:14px !important; color:#191F28 !important; }
.stNumberInput input:focus, .stTextInput input:focus { border-color:#03C75A !important; box-shadow:0 0 0 3px rgba(3,199,90,.12) !important; }
.stButton>button { background:#03C75A !important; color:#fff !important; border:none !important; border-radius:8px !important; font-weight:700 !important; font-size:14px !important; padding:10px 20px !important; transition:.15s !important; }
.stButton>button:hover { background:#02B350 !important; transform:translateY(-1px); }
.stButton>button:disabled { background:#D1D6DB !important; }
label { font-size:12px !important; font-weight:500 !important; color:#4E5968 !important; }
.chips { display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }
.chip { font-size:11px; font-weight:500; padding:4px 11px; border-radius:100px; display:inline-flex; align-items:center; gap:4px; }
.chip.ok { background:#E7F9F0; color:#03864A; } .chip.no { background:#FFF4E6; color:#E8590C; }
.struct { background:#fff; border:1px solid #E5E8EB; border-radius:12px; padding:18px 20px; }
.bar-line { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.bar-line .bl { font-size:13px; color:#4E5968; flex:0 0 80px; font-weight:500; }
.bar-track { flex:1; height:10px; background:#F2F4F6; border-radius:100px; overflow:hidden; }
.bar-fill { height:100%; border-radius:100px; background:#03C75A; }
.bar-line .bv { font-size:13px; font-weight:700; color:#191F28; flex:0 0 80px; text-align:right; }
</style>
""", unsafe_allow_html=True)

SB_ON = False
supabase = None
try:
    from supabase import create_client
    if "supabase" in st.secrets:
        s = st.secrets["supabase"]
        url = s.get("url") or s.get("URL")
        key = s.get("anon_key") or s.get("KEY")
        if url and key:
            supabase = create_client(url, key)
            SB_ON = True
except Exception:
    SB_ON = False

AVG_PYEONG = 25
PT_LABEL = {"rebuild":"재건축","redevelop":"재개발","small":"소규모정비"}

def calc_business(units, prev, price, cc, gr, pt):
    tp = units*AVG_PYEONG
    sales = tp*(gr/100)*price/10000
    con = tp*cc/10000
    total_cost = con*(1+(0.28 if pt=="small" else 0.35))
    post = sales + tp*(1-gr/100)*price*0.85/10000
    biryul = ((post-total_cost)/prev*100) if prev>0 else 0
    return dict(sales=sales, post=post, total_cost=total_cost,
                biryul=biryul, profit=post-total_cost-prev)

def calc_req(pt, area, year, diag, oldr, lot, agree, stype, units):
    reqs, score, sd = [], None, ""
    if pt=="rebuild":
        age=dt.date.today().year-year
        a,d,ar = age>=30, diag=="통과(D/E)", area>=10000
        reqs=[("안전진단",d),("준공30년",a),("면적1만㎡",ar)]; okv=a and d and ar; sd="적합" if okv else "미달"
    elif pt=="redevelop":
        oo,ar = oldr>=66.7, area>=10000
        sa=50 if agree>=80 else 40 if agree>=75 else 30 if agree>=70 else 20 if agree>=60 else 0
        so=30 if oldr>=80 else 20 if oldr>=75 else 10 if oldr>=66.7 else 0
        sl=5 if lot>=40 else 4 if lot>=30 else 3 if lot>=20 else 2
        score=sa+so+sl+10
        reqs=[("노후2/3",oo),("면적1만㎡",ar),(f"정비지수{round(score)}",score>=60)]; okv=oo and ar; sd=f"{round(score)}/100"
    else:
        ar=area<10000; oo=oldr>=66.7; uo=units<200 if stype=="소규모재건축" else True
        reqs=[("면적1만㎡미만",ar),("노후2/3",oo)]
        if stype=="소규모재건축": reqs.append(("200세대미만",uo))
        okv=ar and oo and uo; sd="적합" if okv else "미달"
    return reqs, okv, sd, score

def verdict(b, okv):
    if b>=110 and okv: return "success","✅","사업성 우수 · 수주 우선 검토","비례율·법정요건 모두 충족"
    if b>=100 and okv: return "info","🔵","사업성 양호 · 조건부 검토","추가 변수 점검 후 추진 가능"
    return "warning","⚠️","사업성 부족 · 재검토 필요","비례율 100% 미만 또는 요건 미달"

st.markdown("""
<div class="top-header">
  <div class="brand">🏗️ 정비사업 수주 타당성 분석<span class="brand-sub">시행사 사업개발팀용</span></div>
  <div class="spacer"></div>
  <div class="head-link">재건축 · 재개발 · 소규모정비 후보지 진단</div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown('<div class="side-h">📍 구역 정보</div>', unsafe_allow_html=True)
    region_name = st.text_input("구역명", "○○3 후보구역", label_visibility="collapsed")
    pt = st.radio("사업 유형", ["rebuild","redevelop","small"], format_func=lambda x:PT_LABEL[x])
    st.markdown('<div class="side-h">🏘️ 구역 요건</div>', unsafe_allow_html=True)
    area = st.number_input("구역면적 (㎡)", 0, value=35000, step=1000)
    year, diag, oldr, lot, stype = 1992, "통과(D/E)", 75.0, 30.0, "가로주택"
    if pt=="rebuild":
        diag = st.radio("안전진단", ["통과(D/E)","미통과"], horizontal=True)
        year = st.number_input("준공연도", 1960, 2025, 1992)
        st.caption(f"경과 {dt.date.today().year-year}년 (법정 30년 이상)")
    elif pt=="redevelop":
        oldr = st.slider("노후 동수 비율 (%)", 50.0, 100.0, 75.0)
        lot = st.slider("과소필지율 (%)", 0.0, 60.0, 30.0)
    else:
        stype = st.radio("세부유형", ["가로주택","소규모재건축"], horizontal=True)
        oldr = st.slider("노후 동수 비율 (%)", 50.0, 100.0, 70.0)
        st.caption("가로주택: 1만㎡ 미만 · 안전진단 면제" if stype=="가로주택" else "소규모재건축: 1만㎡·200세대 미만 + 안전진단")
    agree = st.slider("주민동의율 (%)", 50.0, 100.0, 75.0)
    st.markdown('<div class="side-h">💰 사업성 입력</div>', unsafe_allow_html=True)
    units = st.number_input("세대수", 1, value=600, step=10)
    prev = st.number_input("종전자산 (억)", 0, value=2000, step=100)
    price = st.slider("일반분양가 (만원/평)", 1500, 5000, 2800, step=50)
    cc = st.slider("공사비 (만원/평)", 400, 900, 650, step=10)
    gr = st.slider("일반분양 비율 (%)", 20, 70, 45)

biz = calc_business(units, prev, price, cc, gr, pt)
reqs, okv, sd, score = calc_req(pt, area, year, diag, oldr, lot, agree, stype, units)
vk, vi, vt, vd = verdict(biz["biryul"], okv)

law = "빈집·소규모주택 정비 특례법" if pt=="small" else "도시 및 주거환경정비법"
st.markdown(f"""
<div class="region-bar">
  <span class="rtag sample">예시 데이터</span>
  <span class="rname">{region_name}</span>
  <span class="rtag law">{PT_LABEL[pt]} · {law}</span>
</div>
""", unsafe_allow_html=True)

bcolor = "#03864A" if biz["biryul"]>=100 else "#E8590C"
pcolor = "#03864A" if biz["profit"]>=0 else "#E8590C"
st.markdown(f"""
<div class="kpi-grid">
  <div class="kpi-card"><div class="kl">정비지수 / 요건</div><div class="kv">{sd}</div><div class="kd" style="color:#8B95A1;">법정 요건 평가</div></div>
  <div class="kpi-card"><div class="kl">비례율</div><div class="kv" style="color:{bcolor};">{biz['biryul']:.1f}<small>%</small></div><div class="kd" style="color:{bcolor};">100% 이상 사업성</div></div>
  <div class="kpi-card"><div class="kl">총사업비</div><div class="kv">{biz['total_cost']:,.0f}<small>억</small></div><div class="kd" style="color:#8B95A1;">공사비+기타사업비</div></div>
  <div class="kpi-card"><div class="kl">사업이익</div><div class="kv" style="color:{pcolor};">{biz['profit']:,.0f}<small>억</small></div><div class="kd" style="color:{pcolor};">종후-사업비-종전</div></div>
</div>
""", unsafe_allow_html=True)

chips = "".join(f'<span class="chip {"ok" if o else "no"}">{"✓" if o else "✗"} {n}</span>' for n,o in reqs)
st.markdown(f"""
<div class="verdict v-{vk}">
  <span class="vi">{vi}</span>
  <div class="vt"><h4>{vt}</h4><p>{vd}</p><div class="chips">{chips}</div></div>
</div>
""", unsafe_allow_html=True)

st.markdown(f'<div class="sec-title">사업성 구조 ({PT_LABEL[pt]})</div>', unsafe_allow_html=True)
mx = max(biz["post"], biz["total_cost"], prev, biz["sales"], 1)
items = [("분양수입",biz["sales"]),("종후자산",biz["post"]),("총사업비",biz["total_cost"]),("종전자산",prev)]
bars = "".join(f'<div class="bar-line"><span class="bl">{n}</span><div class="bar-track"><div class="bar-fill" style="width:{min(v/mx*100,100):.0f}%;"></div></div><span class="bv">{v:,.0f}억</span></div>' for n,v in items)
st.markdown(f'<div class="struct">{bars}</div>', unsafe_allow_html=True)

st.markdown('<div class="sec-title">분석 결과 저장</div>', unsafe_allow_html=True)
if SB_ON:
    st.caption("☁️ Supabase 연결됨 · 분석할수록 후보구역 데이터가 누적됩니다")
else:
    st.caption("💾 로컬 모드 · 연결 설정(secrets) 시 영구 저장 활성화")

col1, col2 = st.columns(2)
with col1:
    if st.button("💾 이 분석 저장", use_container_width=True, disabled=not SB_ON):
        row = dict(region_name=region_name, project_type=pt,
                   small_type=stype if pt=="small" else None,
                   area_sqm=area, built_year=year if pt=="rebuild" else None,
                   diagnosis=diag if pt=="rebuild" else None, old_ratio=oldr,
                   small_lot=lot, agree_ratio=agree, units=units, prev_asset=prev,
                   sale_price=price, construct_cost=cc, gen_ratio=gr,
                   biryul=round(biz["biryul"],2), total_cost=round(biz["total_cost"],1),
                   profit=round(biz["profit"],1),
                   jeongbi_score=round(score,1) if score is not None else None,
                   verdict=vt, req_pass=okv)
        try:
            r = supabase.table("analysis_regions").insert(row).execute()
            st.success(f"저장 완료 (id: {r.data[0]['id']})")
        except Exception as e:
            st.error(f"저장 실패: {e}")
with col2:
    if st.button("📊 누적 데이터 보기", use_container_width=True, disabled=not SB_ON):
        try:
            r = supabase.table("analysis_regions").select(
                "created_at,region_name,project_type,biryul,profit,verdict"
            ).order("created_at", desc=True).limit(50).execute()
            if r.data:
                df = pd.DataFrame(r.data)
                df["project_type"] = df["project_type"].map(PT_LABEL).fillna(df["project_type"])
                df.columns = ["분석일시","구역명","유형","비례율(%)","사업이익(억)","판정"]
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("저장된 데이터가 없습니다.")
        except Exception as e:
            st.error(f"조회 실패: {e}")

st.caption("⚠️ 예시 데이터 기반 시뮬레이션 · 실제 사업 판단 시 정식 감정평가·정비계획 수립 필요")
