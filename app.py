"""
정비사업 수주 타당성 분석 플랫폼 / Urban Redevelopment Bid Feasibility Platform
시행사 사업개발팀용 · Basic / Advanced 2-모드 · 결과기반 동적 테마 · 한/영 토글
"""
import streamlit as st
import pandas as pd
import datetime as dt
import requests, json
import streamlit.components.v1 as components

st.set_page_config(page_title="정비사업 수주 타당성 분석 / Redevelopment Feasibility", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="expanded")

# ════════════════════════════════════════════════════════
# i18n : 언어 상태 + 전체 UI 문구 딕셔너리 + 헬퍼
# ════════════════════════════════════════════════════════
if "lang" not in st.session_state:
    st.session_state.lang = "ko"
EN = st.session_state.lang == "en"

# (ko, en) — 화면에 보이는 모든 문구. T("key")로 현재 언어 문구를 꺼낸다.
L = {
    # 헤더 · 모드
    "app_title":   ("정비사업 수주 타당성 분석", "Redevelopment Bid Feasibility"),
    "app_badge":   ("시행사 사업개발팀용", "For Developer BD Teams"),
    "mode_adv":    ("Advanced · 상세 수지분석", "Advanced · Detailed Pro-forma"),
    "mode_basic":  ("Basic · 초기 스크리닝", "Basic · Initial Screening"),
    # 사이드바 헤더
    "side_lang":   ("🌐 언어 / Language", "🌐 언어 / Language"),
    "side_mode":   ("⚙️ 분석 모드", "⚙️ Analysis Mode"),
    "side_region": ("📍 구역 정보", "📍 Project Area"),
    "side_cond":   ("🏘️ 구역 요건", "🏘️ Eligibility Inputs"),
    "side_sale":   ("🏢 분양 계획", "🏢 Sales Plan"),
    "side_fin":    ("💰 사업성 입력", "💰 Feasibility Inputs"),
    "side_inc":    ("🎯 인센티브 · 상가 · 금융 (Advanced)", "🎯 Incentive · Retail · Finance (Advanced)"),
    # 모드 라디오
    "mode_basic_opt": ("Basic (초기 스크리닝)", "Basic (Initial Screening)"),
    "mode_adv_opt":   ("Advanced (상세 수지)", "Advanced (Detailed Pro-forma)"),
    # 사이드바 입력 라벨
    "in_region":   ("구역명", "Project name"),
    "in_pt":       ("사업 유형", "Project type"),
    "in_area":     ("구역면적 (㎡)", "Site area (㎡)"),
    "in_diag":     ("안전진단", "Safety diagnosis"),
    "in_year":     ("준공연도", "Year built"),
    "cap_age":     ("경과 {n}년 (법정 30년 이상)", "Age {n} yrs (legal min. 30)"),
    "in_oldr":     ("노후 동수 비율 (%)", "Aging-building ratio (%)"),
    "in_lot":      ("과소필지율 (%)", "Undersized-lot ratio (%)"),
    "in_subtype":  ("세부유형", "Sub-type"),
    "in_agree":    ("주민동의율 (%)", "Resident consent rate (%)"),
    "in_total":    ("신축 총세대", "Total new units"),
    "in_member":   ("조합원 분양세대", "Member-allocated units"),
    "help_member": ("나머지가 일반분양분", "Remainder goes to general sale"),
    "in_avgm2":    ("세대당 분양면적 (㎡)", "Unit floor area (㎡)"),
    "help_avgm2":  ("전용 84㎡ ≈ 국민주택규모", "84㎡ ≈ standard housing size"),
    "in_prev":     ("종전자산 총액 (억)", "Pre-project asset value (100M KRW)"),
    "help_prev":   ("조합원 보유 토지·건물 감정가 합계", "Total appraised value of members' land & buildings"),
    "in_gprice":   ("일반분양가 (만원/㎡)", "General sale price (10K KRW/㎡)"),
    "in_mprice":   ("조합원분양가 (만원/㎡)", "Member sale price (10K KRW/㎡)"),
    "in_cc":       ("공사비 (만원/㎡)", "Construction cost (10K KRW/㎡)"),
    "in_other":    ("기타사업비율 (공사비 대비 %)", "Other-cost ratio (% of construction)"),
    "help_other":  ("설계·감리비, 각종 부담금, 신탁보수, 예비비 등 공사비 외 부대비용을 하나의 비율로 묶어 추정합니다 (사전타당성 단계의 표준 방식 · 세부 항목은 본 타당성에서 산정). PF 금융비용은 Advanced에서 별도 계산.",
                    "Bundles design/supervision fees, levies, trust fees and contingency as one ratio (standard at pre-feasibility stage). PF financing cost is calculated separately in Advanced."),
    "in_donation": ("기부채납률 (%)", "Public-contribution ratio (%)"),
    "help_donation":("높을수록 용적률 인센티브로 세대수 증가", "Higher ratio → FAR incentive → more units"),
    "in_shoparea": ("상가 연면적 (㎡)", "Retail floor area (㎡)"),
    "in_shopprice":("상가 분양가 (만원/㎡)", "Retail sale price (10K KRW/㎡)"),
    "in_pfrate":   ("예상 PF 금리 (%)", "Expected PF rate (%)"),
    "in_delay":    ("사업 지연 기간 (개월)", "Project delay (months)"),
    # 구역정보 바
    "tag_sample":  ("예시 데이터", "Sample Data"),
    "save_btn":    ("💾 이 분석 저장", "💾 Save Analysis"),
    "restore_open":("📂 저장 분석 불러오기", "📂 Load Saved Analysis"),
    # KPI
    "kpi_index":   ("정비지수 / 요건", "Index / Eligibility"),
    "kpi_index_d": ("법정 요건 평가", "Statutory requirement check"),
    "kpi_biryul":  ("비례율", "Proportion Rate"),
    "kpi_biryul_d":("100% 이상 사업성", "≥100% = feasible"),
    "kpi_cost":    ("총사업비", "Total Project Cost"),
    "kpi_cost_adv":("공사비+기타+금융", "Construction+Other+Finance"),
    "kpi_cost_bas":("공사비+기타사업비", "Construction+Other"),
    "kpi_profit":  ("사업이익", "Project Profit"),
    "kpi_profit_d":("종후-사업비-종전", "Post − Cost − Pre"),
    "unit_oku":    ("억", "×100M"),
    # verdict
    "v_excellent": ("사업성 우수 · 수주 우선 검토", "Strong feasibility · Priority bid"),
    "v_excellent_d":("비례율·법정요건 모두 충족", "Both proportion rate & requirements met"),
    "v_good":      ("사업성 양호 · 조건부 검토", "Good feasibility · Conditional review"),
    "v_good_d":    ("추가 변수 점검 후 추진 가능", "Proceed after checking extra variables"),
    "v_weak":      ("사업성 부족 · 재검토 필요", "Weak feasibility · Re-review needed"),
    "v_weak_d":    ("비례율 100% 미만 또는 요건 미달", "Proportion rate <100% or requirements unmet"),
    # 구조도
    "struct_title":("사업성 구조", "Feasibility Structure"),
    "struct_eff":  ("유효 {e}세대 · 일반분양 {g}세대", "Effective {e} units · General sale {g}"),
    "struct_gen":  ("일반분양 {g}세대", "General sale {g} units"),
    "bar_housing": ("주택분양", "Housing Sale"),
    "bar_shop":    ("상가수입", "Retail Income"),
    "bar_base":    ("공사+기타", "Constr.+Other"),
    "bar_finance": ("금융비용", "Finance Cost"),
    "bar_prev":    ("종전자산", "Pre-project"),
    "bar_profit":  ("사업이익", "Profit"),
    "bar_post":    ("종후자산", "Post-project"),
    "bar_cost":    ("총사업비", "Total Cost"),
    "biryul_form": ("비례율 = (종후자산 − 총사업비) ÷ 종전자산 × 100 · 실무 표준 공식",
                    "Proportion Rate = (Post − Total Cost) ÷ Pre × 100 · industry standard"),
    "biryul_form_adv":(" · 총사업비에 PF 금융비용 포함", " · Total cost includes PF financing"),
    # 누적 데이터
    "data_title":  ("누적 분석 데이터", "Saved Analyses"),
    "data_on":     ("☁️ Supabase 연결됨 · 행을 선택해 그때 분석을 다시 불러올 수 있습니다",
                    "☁️ Supabase connected · pick a row to restore that analysis"),
    "data_off":    ("💾 로컬 모드 · 연결 설정(secrets) 시 영구 저장 활성화",
                    "💾 Local mode · set secrets to enable persistent storage"),
    "col_date":    ("분석일자", "Date"),
    "col_region":  ("구역명", "Project"),
    "col_type":    ("유형", "Type"),
    "col_biryul":  ("비례율(%)", "Prop.Rate(%)"),
    "col_cost":    ("총사업비(억)", "Cost(100M)"),
    "col_profit":  ("사업이익(억)", "Profit(100M)"),
    "col_verdict": ("판정", "Verdict"),
    "restore_lbl": ("🔄 저장된 분석 불러오기", "🔄 Restore a saved analysis"),
    "restore_sel": ("불러올 분석 선택", "Select an analysis"),
    "restore_do":  ("📂 이 분석 다시 보기", "📂 Reload this analysis"),
    "restore_none":("복원 가능한 저장 항목이 아직 없습니다. (이후 저장분부터 불러오기 지원)",
                    "No restorable entries yet (supported from future saves)."),
    "data_empty":  ("저장된 데이터가 없습니다.", "No saved data yet."),
    "data_off_info":("연결 설정 시 누적 데이터가 표시됩니다.", "Connect storage to see saved analyses."),
    "save_ok":     ("저장 완료 (id: {id})", "Saved (id: {id})"),
    "save_fail":   ("저장 실패: {e}", "Save failed: {e}"),
    "query_fail":  ("조회 실패: {e}", "Query failed: {e}"),
    "restore_fail":("복원 실패: {e}", "Restore failed: {e}"),
    # 사업지 설정 (지도)
    "site_title":  ("📍 사업지 설정", "📍 Site Location"),
    "site_search": ("📍 구역명·단지명·주소 검색", "📍 Search area / complex / address"),
    "site_ph":     ("예: 한남더힐, 성수전략정비구역, 잠실 자이, 왕십리역",
                    "e.g. Hannam, Seongsu, Jamsil, Wangsimni Stn"),
    "site_default":("서울시청 (기본 위치)", "Seoul City Hall (default)"),
    "site_found":  ("📍 {place}", "📍 {place}"),
    "site_notfound":("위치를 찾지 못했습니다. 단지명이 안 되면 '동 이름'이나 '가까운 역'으로 검색해보세요.",
                     "Location not found. Try a district name or the nearest station."),
    "site_nokey":("⚠️ 카카오 지도 API 키가 필요합니다. Streamlit secrets에 KAKAO_API_KEY를 추가하세요.",
                  "⚠️ Kakao Map API key required. Add KAKAO_API_KEY to Streamlit secrets."),
    "site_nojskey":("⚠️ 지도 표시용 카카오 JavaScript 키가 필요합니다. Streamlit secrets에 KAKAO_JS_KEY를 추가하세요.",
                    "⚠️ Kakao JavaScript key required to render the map. Add KAKAO_JS_KEY to Streamlit secrets."),
    "site_radius": ("📐 사업단지 반경 (m)", "📐 Project radius (m)"),
    "site_tip":    ("📐 파란 원 = 사업단지 반경 {r}m · 이 범위를 기준으로 AI가 분석합니다.",
                    "📐 Blue circle = {r}m project radius · AI analyzes within this range."),
    # AI 어시스턴트
    "ai_title":    ("🤖 AI 어시스턴트", "🤖 AI Assistant"),
    "ai_consult_btn":("🤖 AI 컨설턴트 분석", "🤖 AI Consultant Review"),
    "ai_consult_sp":("🤖 AI 컨설턴트 분석 중...", "🤖 Running AI consultant..."),
    "ai_consult_h":("🤖 AI 사업성 컨설턴트 의견", "🤖 AI Feasibility Consultant Opinion"),
    "ai_risk_btn": ("⚠️ 주요 리스크 분석", "⚠️ Key Risk Analysis"),
    "ai_risk_sp":  ("⚠️ 리스크 분석 중...", "⚠️ Analyzing risks..."),
    "ai_risk_h":   ("⚠️ AI 리스크 분석 결과", "⚠️ AI Risk Analysis"),
    "ai_report_btn":("📄 AI 보고서 생성", "📄 Generate AI Report"),
    "ai_report_sp":("📄 AI 보고서 생성 중...", "📄 Generating report..."),
    "ai_report_h": ("📄 AI 생성 사업성 검토 보고서", "📄 AI Feasibility Review Report"),
    "ai_report_dl":("⬇️ 보고서 텍스트 다운로드", "⬇️ Download report (.txt)"),
    "ai_report_fn":("{region}_AI사업성보고서.txt", "{region}_AI_feasibility_report.txt"),
    "ai_eval_title":("🎯 AI 종합평가", "🎯 AI Location & Bid Score"),
    "ai_loc_info": ("📍 위 **사업지 설정**에서 주소를 입력하면 입지·수주 분석이 활성화됩니다.",
                    "📍 Enter an address in **Site Location** above to unlock location & bid analysis."),
    "ai_loc_btn":  ("🤖 입지·수주 성공률 분석", "🤖 Location & Bid-Win Analysis"),
    "ai_loc_sp":   ("🤖 입지·수주 분석 중... (지도 + AI)", "🤖 Analyzing location & bid... (map + AI)"),
    "ai_loc_h":    ("🎯 AI 입지·수주 종합평가", "🎯 AI Location & Bid Assessment"),
    "ai_loc_note": ("※ AI 추정 분석입니다. 실제 사업 판단 시 현장 실사와 공공데이터 확인이 필요합니다.",
                    "※ AI estimate. Field survey & public data verification required for real decisions."),
    # 푸터
    "footer":      ("⚠️ 예시 데이터 기반 간이 시뮬레이션 · 실제 사업 판단 시 정식 감정평가·정비계획 수립 필요",
                    "⚠️ Simplified simulation on sample data · formal appraisal & redevelopment plan required for real decisions."),
}

def T(key, **kw):
    s = L.get(key, (key, key))[1 if EN else 0]
    return s.format(**kw) if kw else s

# 사업유형 라벨 (내부키→표시) · 내부 로직은 한글키 유지
PT_LABEL_KO = {"rebuild":"재건축","redevelop":"재개발","small":"소규모정비"}
PT_LABEL_EN = {"rebuild":"Reconstruction","redevelop":"Redevelopment","small":"Small-scale"}
def PT(pt): return (PT_LABEL_EN if EN else PT_LABEL_KO).get(pt, pt)
PT_LABEL = PT_LABEL_KO  # 내부 저장/복원 호환

# 소규모 세부유형: 표시(영문) ↔ 내부(한글) 매핑
STYPE_KO = ["가로주택정비","자율주택정비","소규모재건축","소규모재개발"]
STYPE_EN = ["Street-block Housing","Self-managed Housing","Small Reconstruction","Small Redevelopment"]
STYPE_KO2EN = dict(zip(STYPE_KO, STYPE_EN))
STYPE_EN2KO = dict(zip(STYPE_EN, STYPE_KO))
def stype_disp(ko): return STYPE_KO2EN.get(ko, ko) if EN else ko
def stype_to_ko(disp): return STYPE_EN2KO.get(disp, disp) if EN else disp

# 안전진단 표시 ↔ 내부
DIAG_KO = ["통과(D/E)","미통과"]
DIAG_EN = ["Pass (D/E)","Fail"]
def diag_disp(ko): return (dict(zip(DIAG_KO,DIAG_EN)).get(ko,ko)) if EN else ko
def diag_to_ko(disp): return (dict(zip(DIAG_EN,DIAG_KO)).get(disp,disp)) if EN else disp

# 법정요건 칩 라벨 (내부 한글 → 표시)
REQ_EN = {
    "안전진단":"Safety diag.", "준공30년":"30+ yrs", "면적1만㎡":"≥10,000㎡",
    "노후2/3":"Aging ≥2/3", "면적5천㎡미만":"<5,000㎡", "면적1만㎡미만":"<10,000㎡",
    "20세대미만":"<20 units", "200세대미만":"<200 units",
}
def req_label(n):
    if not EN: return n
    if n.startswith("정비지수"):  # 동적: "정비지수62"
        return "Index " + n.replace("정비지수","")
    return REQ_EN.get(n, n)

def sd_label(sd):
    if not EN: return sd
    return {"적합":"Pass","미달":"Fail"}.get(sd, sd)  # 점수형(62/100)은 그대로

# ── Gemini API 공통 호출 함수 ──────────────────────────
def call_gemini(prompt: str, max_tokens: int = 2048) -> str:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        msg = ("⚠️ Gemini API 키가 설정되지 않았습니다. Streamlit secrets에 GEMINI_API_KEY를 입력하세요."
               if not EN else "⚠️ Gemini API key not set. Add GEMINI_API_KEY to Streamlit secrets.")
        return msg
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    body = {"contents":[{"parts":[{"text": prompt}]}],
            "generationConfig":{"maxOutputTokens": max_tokens, "temperature": 0.7,
                                "thinkingConfig":{"thinkingBudget": 0}}}
    try:
        r = requests.post(url, json=body, timeout=25)
        r.raise_for_status()
        cand = r.json()["candidates"][0]
        parts = cand.get("content",{}).get("parts",[])
        text = "".join(p.get("text","") for p in parts)
        if text.strip(): return text.strip()
        return "⚠️ AI 응답이 비어 있습니다. 다시 시도해주세요." if not EN else "⚠️ Empty AI response. Please retry."
    except Exception as e:
        return f"⚠️ AI 응답 오류: {str(e)[:80]}" if not EN else f"⚠️ AI error: {str(e)[:80]}"

def _kakao_headers():
    key = st.secrets.get("KAKAO_API_KEY", "")
    return {"Authorization": f"KakaoAK {key}"} if key else None

def _kakao_keyword(q, headers):
    """카카오 키워드 검색 — 역·단지·구역명 등 장소명에 강함"""
    r = requests.get("https://dapi.kakao.com/v2/local/search/keyword.json",
        params={"query": q, "size": 1}, headers=headers, timeout=8)
    if r.status_code==200:
        docs=r.json().get("documents",[])
        if docs:
            d=docs[0]
            name=d.get("place_name","")
            addr=d.get("road_address_name") or d.get("address_name","")
            label=f"{name} ({addr})" if addr else name
            return float(d["y"]), float(d["x"]), label
    return None

def _kakao_address(q, headers):
    """카카오 주소 검색 — 도로명·지번 주소에 강함 (키워드 실패 시 폴백)"""
    r = requests.get("https://dapi.kakao.com/v2/local/search/address.json",
        params={"query": q, "size": 1}, headers=headers, timeout=8)
    if r.status_code==200:
        docs=r.json().get("documents",[])
        if docs:
            d=docs[0]
            return float(d["y"]), float(d["x"]), d.get("address_name","")
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def geocode(query: str):
    """카카오 로컬 API로 한국 지명·역·단지·주소 검색. 키워드→주소 폴백.
    반환: (lat, lon, label) / 실패 None / 키없음 'NOKEY'"""
    headers = _kakao_headers()
    if not headers:
        return "NOKEY"
    q = query.strip()
    for fn in (_kakao_keyword, _kakao_address):
        try:
            res = fn(q, headers)
            if res: return res
        except Exception:
            continue
    return None

if "mode" not in st.session_state:
    st.session_state.mode = "basic"
if "ai_results" not in st.session_state:
    st.session_state.ai_results = {}

# 누적 데이터에서 "불러오기" 클릭 시: 입력값을 위젯 생성 전에 주입
if "_restore" in st.session_state:
    rd = st.session_state.pop("_restore")
    st.session_state.mode = rd.get("mode", "basic")
    _map = {"region":"v_region","pt":"v_pt","area":"v_area","year":"v_year","diag":"v_diag",
            "oldr":"v_oldr","lot":"v_lot","stype":"v_stype","agree":"v_agree","total":"v_total",
            "member":"v_member","avgm2":"v_avgm2","prev":"v_prev","gprice":"v_gprice",
            "mprice":"v_mprice","cc":"v_cc","other":"v_other","donation":"v_donation",
            "shoparea":"v_shoparea","shopprice":"v_shopprice","pfrate":"v_pfrate","delay":"v_delay",
            "radius":"biz_radius","addr":"addr_q"}
    for k, v in rd.items():
        # diag/stype은 내부 한글값으로 저장됨 → EN 라디오 옵션과 충돌하므로 EN일 땐 주입 생략
        if k in ("diag","stype") and EN:
            continue
        if k in _map and v is not None:
            st.session_state[_map[k]] = v
    if rd.get("pt")=="small" and rd.get("oldr") is not None and not (("stype" in rd) and EN):
        st.session_state["v_oldr2"] = rd["oldr"]
    if rd.get("ai_results"):
        st.session_state.ai_results = rd["ai_results"]
    else:
        st.session_state.ai_results = {}

ADV = st.session_state.mode == "advanced"

SB_ON, supabase = False, None
try:
    from supabase import create_client
    if "supabase" in st.secrets:
        s = st.secrets["supabase"]
        url = s.get("url") or s.get("URL")
        key = s.get("anon_key") or s.get("KEY")
        if url and key:
            supabase = create_client(url, key); SB_ON = True
except Exception:
    SB_ON = False

# ── Basic 수지 엔진 (㎡ 단위) ─────────────────────────
def calc_business(total_units, member_units, avg_m2, m_price, g_price, cc, other_rate, prev):
    general_units = max(total_units-member_units, 0)
    member_a = member_units*avg_m2; general_a = general_units*avg_m2; total_a = total_units*avg_m2
    post = (member_a*m_price + general_a*g_price)/10000
    construct = total_a*cc/10000
    total_cost = construct*(1+other_rate)
    biryul = ((post-total_cost)/prev*100) if prev>0 else 0
    return dict(general_units=general_units, housing=post, shop=0, post=post, construct=construct,
                base_cost=total_cost, finance=0, total_cost=total_cost, biryul=biryul,
                profit=post-total_cost-prev, eff_units=total_units)

# ── Advanced 수지 엔진 (㎡ 단위) ──────────────────────
def calc_advanced_business(total_units, member_units, avg_m2, m_price, g_price, cc, other_rate, prev,
                           donation_rate, shop_area_m2, shop_price, pf_rate, delay_months):
    eff_units = round(total_units*(1+donation_rate/100*1.5))
    general_units = max(eff_units-member_units, 0)
    member_a = member_units*avg_m2; general_a = general_units*avg_m2; total_a = eff_units*avg_m2
    housing = (member_a*m_price + general_a*g_price)/10000
    shop = (shop_area_m2*shop_price)/10000
    post = housing + shop
    construct = total_a*cc/10000
    base_cost = construct*(1+other_rate)
    loan = base_cost*0.6
    months = 24 + delay_months
    finance = loan*(pf_rate/100)*(months/12)
    total_cost = base_cost + finance
    biryul = ((post-total_cost)/prev*100) if prev>0 else 0
    return dict(general_units=general_units, housing=housing, shop=shop, post=post,
                construct=construct, base_cost=base_cost, finance=finance, total_cost=total_cost,
                biryul=biryul, profit=post-total_cost-prev, eff_units=eff_units)

# ── 법정요건 (소규모정비 4유형 세분화) · 내부 한글키 유지 ──
def calc_req(pt, area, year, diag, oldr, lot, agree, stype, total_units):
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
        oo = oldr>=66.7
        if stype=="가로주택정비":
            ar = area<10000
            reqs=[("면적1만㎡미만",ar),("노후2/3",oo)]; okv=ar and oo
        elif stype=="자율주택정비":
            uo = total_units<20
            reqs=[("20세대미만",uo),("노후2/3",oo)]; okv=uo and oo
        elif stype=="소규모재건축":
            ar = area<10000; uo = total_units<200
            reqs=[("면적1만㎡미만",ar),("200세대미만",uo),("노후2/3",oo)]; okv=ar and uo and oo
        else:
            ar = area<5000
            reqs=[("면적5천㎡미만",ar),("노후2/3",oo)]; okv=ar and oo
        sd="적합" if okv else "미달"
    return reqs, okv, sd, score

def verdict(b, okv):
    if b>=110 and okv: return "success","✅", T("v_excellent"), T("v_excellent_d")
    if b>=100 and okv: return "info","🔵", T("v_good"), T("v_good_d")
    return "warning","⚠️", T("v_weak"), T("v_weak_d")

# ── 사이드바 ──────────────────────────────────────────
with st.sidebar:
    # 언어 토글 (최상단)
    st.markdown(f'<div class="side-h">{T("side_lang")}</div>', unsafe_allow_html=True)
    lang_sel = st.radio("lang", ["ko","en"],
                        format_func=lambda x:"🇰🇷 한국어" if x=="ko" else "🇺🇸 English",
                        index=0 if not EN else 1, horizontal=True, label_visibility="collapsed")
    if lang_sel != st.session_state.lang:
        st.session_state.lang = lang_sel
        st.rerun()

    st.markdown(f'<div class="side-h">{T("side_mode")}</div>', unsafe_allow_html=True)
    mode_sel = st.radio("mode", ["basic","advanced"],
                        format_func=lambda x: T("mode_basic_opt") if x=="basic" else T("mode_adv_opt"),
                        index=0 if not ADV else 1, label_visibility="collapsed")
    if mode_sel != st.session_state.mode:
        st.session_state.mode = mode_sel
        st.rerun()

    st.markdown(f'<div class="side-h">{T("side_region")}</div>', unsafe_allow_html=True)
    region_name = st.text_input(T("in_region"), st.session_state.get("v_region","○○3 후보구역"), key="v_region", label_visibility="collapsed")
    pt = st.radio(T("in_pt"), ["rebuild","redevelop","small"], format_func=PT, key="v_pt")

    st.markdown(f'<div class="side-h">{T("side_cond")}</div>', unsafe_allow_html=True)
    area = st.number_input(T("in_area"), 0, value=st.session_state.get("v_area",35000), step=1000, key="v_area")
    year, diag, oldr, lot, stype = 1992, "통과(D/E)", 75.0, 30.0, "가로주택정비"
    if pt=="rebuild":
        _diag_opts = DIAG_EN if EN else DIAG_KO
        _diag_disp = st.radio(T("in_diag"), _diag_opts, horizontal=True, key="v_diag")
        diag = diag_to_ko(_diag_disp)
        year = st.number_input(T("in_year"), 1960, 2025, st.session_state.get("v_year",1992), key="v_year")
        st.caption(T("cap_age", n=dt.date.today().year-year))
    elif pt=="redevelop":
        oldr = st.slider(T("in_oldr"), 50.0, 100.0, st.session_state.get("v_oldr",75.0), key="v_oldr")
        lot = st.slider(T("in_lot"), 0.0, 60.0, st.session_state.get("v_lot",30.0), key="v_lot")
    else:
        _stype_opts = STYPE_EN if EN else STYPE_KO
        _stype_disp = st.radio(T("in_subtype"), _stype_opts, key="v_stype")
        stype = stype_to_ko(_stype_disp)
        oldr = st.slider(T("in_oldr"), 50.0, 100.0, st.session_state.get("v_oldr",70.0), key="v_oldr2")
        _hint_ko = {
            "가로주택정비":"가로주택: 1만㎡ 미만 · 노후 2/3 이상 · 안전진단 면제",
            "자율주택정비":"자율주택: 단독·다세대 밀집 · 20세대 미만 소규모",
            "소규모재건축":"소규모재건축: 1만㎡·200세대 미만 · 안전진단",
            "소규모재개발":"소규모재개발: 역세권·준공업 5천㎡ 미만",
        }
        _hint_en = {
            "가로주택정비":"Street-block: <10,000㎡ · aging ≥2/3 · diagnosis exempt",
            "자율주택정비":"Self-managed: detached/multiplex cluster · <20 units",
            "소규모재건축":"Small reconstruction: <10,000㎡ & <200 units · diagnosis",
            "소규모재개발":"Small redevelopment: station-area/semi-industrial <5,000㎡",
        }
        st.caption((_hint_en if EN else _hint_ko)[stype])
    agree = st.slider(T("in_agree"), 50.0, 100.0, st.session_state.get("v_agree",75.0), key="v_agree")

    st.markdown(f'<div class="side-h">{T("side_sale")}</div>', unsafe_allow_html=True)
    total_units = st.number_input(T("in_total"), 1, value=st.session_state.get("v_total",600), step=10, key="v_total")
    member_units = st.number_input(T("in_member"), 0, value=st.session_state.get("v_member",350), step=10, help=T("help_member"), key="v_member")
    avg_m2 = st.number_input(T("in_avgm2"), 30, 200, st.session_state.get("v_avgm2",85), help=T("help_avgm2"), key="v_avgm2")

    st.markdown(f'<div class="side-h">{T("side_fin")}</div>', unsafe_allow_html=True)
    prev = st.number_input(T("in_prev"), 0, value=st.session_state.get("v_prev",2000), step=100, help=T("help_prev"), key="v_prev")
    g_price = st.number_input(T("in_gprice"), 0, value=st.session_state.get("v_gprice",850), step=10, key="v_gprice")
    m_price = st.number_input(T("in_mprice"), 0, value=st.session_state.get("v_mprice",760), step=10, key="v_mprice")
    cc = st.number_input(T("in_cc"), 0, value=st.session_state.get("v_cc",200), step=5, key="v_cc")
    other_rate = st.slider(T("in_other"), 20, 50, st.session_state.get("v_other",28 if pt=="small" else 35),
                           help=T("help_other"), key="v_other")/100

    if ADV:
        st.markdown(f'<div class="side-h">{T("side_inc")}</div>', unsafe_allow_html=True)
        donation_rate = st.slider(T("in_donation"), 0, 20, st.session_state.get("v_donation",10), help=T("help_donation"), key="v_donation")
        shop_area = st.number_input(T("in_shoparea"), 0, value=st.session_state.get("v_shoparea",1650), step=50, key="v_shoparea")
        shop_price = st.number_input(T("in_shopprice"), 0, value=st.session_state.get("v_shopprice",1200), step=50, key="v_shopprice")
        pf_rate = st.number_input(T("in_pfrate"), 0.0, value=st.session_state.get("v_pfrate",8.0), step=0.1, key="v_pfrate")
        delay_months = st.slider(T("in_delay"), 0, 36, st.session_state.get("v_delay",0), key="v_delay")

# ── 계산 (로직 보존) ──────────────────────────────────
if ADV:
    biz = calc_advanced_business(total_units, member_units, avg_m2, m_price, g_price, cc, other_rate, prev,
                                 donation_rate, shop_area, shop_price, pf_rate, delay_months)
else:
    biz = calc_business(total_units, member_units, avg_m2, m_price, g_price, cc, other_rate, prev)
reqs, okv, sd, score = calc_req(pt, area, year, diag, oldr, lot, agree, stype, total_units)
vk, vi, vt, vd = verdict(biz["biryul"], okv)
law_ko = "빈집·소규모주택 정비 특례법" if pt=="small" else "도시 및 주거환경정비법"
law_en = "Small Housing Act" if pt=="small" else "Urban Renewal Act"
law = law_en if EN else law_ko

# ── 결과 기반 동적 테마 결정 ───────────────────────────
FIT = (biz["biryul"] >= 100) and okv
if FIT:
    ACCENT  = "#1B64DA"; ACCENT2 = "#0F2A4A"; SOFT_BG = "#E8F1FF"; HEAD_BG = "#1B64DA"
else:
    ACCENT  = "#E8590C"; ACCENT2 = "#9A3412"; SOFT_BG = "#FDF1E7"; HEAD_BG = "#C2410C"

# ── CSS (동적 테마 주입) ──────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
html, body, .stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3,
.stApp h4, .stApp label, .stApp input, .stApp button, .stApp td, .stApp th,
.stApp li, .stApp a {{
    font-family:'Inter','Noto Sans KR',sans-serif;
}}
.stApp {{ background:#F4F6F9 !important; color:#1A1A1A !important; }}
[data-testid="stIconMaterial"], .material-icons, .material-symbols-outlined,
[data-testid="stIconMaterial"] * {{
    font-family:'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
    font-feature-settings:'liga' !important;
}}
[data-testid="stSidebarCollapseButton"] span:not([data-testid="stIconMaterial"]),
[data-testid="collapsedControl"] span:not([data-testid="stIconMaterial"]) {{
    font-size:0 !important;
}}
#MainMenu, footer {{ display:none !important; }}
.main .block-container {{ padding:0 2rem 3rem !important; max-width:1600px !important; }}
.top-header {{ background:{HEAD_BG}; margin:0 -2rem 0; padding:14px 2rem; display:flex; align-items:center; gap:16px; }}
.top-header .brand {{ font-size:18px; font-weight:900; color:#fff; display:flex; align-items:center; gap:8px; letter-spacing:-0.02em; }}
.top-header .brand-sub {{ font-size:11px; font-weight:500; color:rgba(255,255,255,.85); padding:2px 9px; background:rgba(255,255,255,.18); border-radius:100px; }}
.top-header .spacer {{ flex:1; }}
.top-header .head-link {{ font-size:13px; color:rgba(255,255,255,.92); font-weight:500; }}
.rtag {{ font-size:12px; font-weight:500; padding:3px 10px; border-radius:6px; display:inline-block; }}
.rtag.sample {{ background:{SOFT_BG}; color:{ACCENT2}; }}
.rtag.law {{ background:#F2F4F6; color:#4E5968; }}
.rtag.mode {{ background:{SOFT_BG}; color:{ACCENT2}; font-weight:700; }}
.rname {{ font-size:17px; font-weight:700; color:#191F28; }}
.region-strip {{ background:#fff; border-bottom:1px solid #E5E8EB; margin:0 -2rem 18px; padding:10px 2rem; }}
[data-testid="stImage"] img {{ border-radius:16px; }}
.save-slot button {{ background:#fff !important; color:{ACCENT} !important; border:1.5px solid {ACCENT} !important; font-weight:700 !important; }}
.save-slot button:hover {{ background:{SOFT_BG} !important; color:{ACCENT2} !important; filter:none !important; }}
.save-slot button:disabled {{ background:#fff !important; color:#B0B8C1 !important; border-color:#D1D6DB !important; }}
.kpi-grid {{ display:grid; grid-template-columns:repeat(2,1fr); gap:12px; margin-bottom:16px; }}
.kpi-card {{ background:#fff; border:1px solid #E5E8EB; border-radius:12px; padding:16px 18px; text-align:center; transition:border-color .15s,box-shadow .15s; }}
.kpi-card:hover {{ border-color:{ACCENT}; box-shadow:0 2px 12px {ACCENT}22; }}
.kpi-card .kl {{ font-size:12px; color:#8B95A1; font-weight:500; margin-bottom:8px; text-align:center; }}
.kpi-card .kv {{ font-size:1.7rem; font-weight:900; color:#191F28; line-height:1; letter-spacing:-0.02em; text-align:center; }}
.kpi-card .kv small {{ font-size:13px; font-weight:500; color:#8B95A1; margin-left:3px; }}
.kpi-card .kd {{ font-size:11px; margin-top:7px; font-weight:500; text-align:center; }}
[data-testid="stSidebar"] {{ background:#FAFBFC !important; border-right:1px solid #E5E8EB !important; }}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] div:not([data-testid="stIconMaterial"]) {{
    font-family:'Inter','Noto Sans KR',sans-serif;
}}
.side-h {{ font-size:13px; font-weight:700; color:#191F28; margin:6px 0 2px; }}
input[type="text"], input[type="number"],
.stTextInput input, .stNumberInput input,
[data-testid="stSidebar"] input {{
    background:#F2F4F6 !important; color:#191F28 !important;
    border:1.5px solid #D1D6DB !important; border-radius:8px !important;
    font-size:14px !important; -webkit-text-fill-color:#191F28 !important;
}}
.stTextInput input:focus, .stNumberInput input:focus {{
    border-color:{ACCENT} !important; box-shadow:0 0 0 3px {ACCENT}22 !important;
}}
[data-testid="stNumberInput"] button {{ background:#F2F4F6 !important; color:#191F28 !important; border:1px solid #D1D6DB !important; }}
[data-testid="stSidebar"] label, [data-testid="stWidgetLabel"] label {{ color:#4E5968 !important; font-weight:500 !important; }}
[data-testid="stSidebar"] label p, [data-testid="stSidebar"] label div,
[data-testid="stSidebar"] [role="radiogroup"] label,
[data-testid="stSidebar"] [data-baseweb="radio"] div {{ color:#191F28 !important; -webkit-text-fill-color:#191F28 !important; }}
[data-testid="stSidebar"] [data-testid="stTickBar"] div,
[data-testid="stSidebar"] [data-testid="stThumbValue"] {{ color:#4E5968 !important; -webkit-text-fill-color:#4E5968 !important; }}
.stCaption, [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color:#8B95A1 !important; -webkit-text-fill-color:#8B95A1 !important; }}
.stButton>button {{ background:{ACCENT} !important; color:#fff !important; border:none !important; border-radius:8px !important; font-weight:700 !important; font-size:14px !important; padding:10px 20px !important; transition:.15s !important; }}
.stButton>button:hover {{ filter:brightness(1.12); transform:translateY(-1px); }}
.stButton>button:disabled {{ background:#D1D6DB !important; color:#fff !important; }}
.chips {{ display:flex; flex-wrap:wrap; gap:6px; margin-top:10px; }}
.chip {{ font-size:11px; font-weight:500; padding:4px 11px; border-radius:100px; display:inline-flex; align-items:center; gap:4px; }}
.chip.ok {{ background:{SOFT_BG}; color:{ACCENT2}; }} .chip.no {{ background:#FFF4E6; color:#E8590C; }}
.struct {{ background:#fff; border:1px solid #E5E8EB; border-radius:12px; padding:18px 20px; }}
.bar-line {{ display:flex; align-items:center; gap:10px; margin-bottom:10px; }}
.bar-line .bl {{ font-size:13px; color:#4E5968; flex:0 0 90px; font-weight:500; }}
.bar-track {{ flex:1; height:10px; background:#F2F4F6; border-radius:100px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:100px; }}
.bar-line .bv {{ font-size:13px; font-weight:700; color:#191F28; flex:0 0 90px; text-align:right; }}
.verdict {{ border-radius:12px; padding:16px 20px; margin-bottom:18px; display:flex; align-items:center; gap:14px; }}
.verdict .vi {{ font-size:26px; }}
.verdict .vt h4 {{ margin:0; font-size:15px; font-weight:700; }}
.verdict .vt p {{ margin:3px 0 0; font-size:13px; }}
.v-success {{ background:{SOFT_BG}; }} .v-success h4,.v-success p {{ color:{ACCENT2}; }}
.v-info {{ background:#E8F1FF; }} .v-info h4,.v-info p {{ color:#1B64DA; }}
.v-warning {{ background:#FDF1E7; }} .v-warning h4,.v-warning p {{ color:#9A3412; }}
.sec-title {{ font-size:15px; font-weight:700; color:#191F28; margin:18px 0 12px; display:flex; align-items:center; gap:8px; }}
.sec-title::before {{ content:''; width:3px; height:15px; background:{ACCENT}; border-radius:2px; }}
.info-box {{ background:#fff; border:1px solid #E5E8EB; border-radius:12px; padding:14px 18px; }}
</style>
""", unsafe_allow_html=True)

mode_label = T("mode_adv") if ADV else T("mode_basic")
st.markdown(f"""
<div class="top-header">
  <div class="brand">🏗️ {T('app_title')}<span class="brand-sub">{T('app_badge')}</span></div>
  <div class="spacer"></div>
  <div class="head-link">{mode_label}</div>
</div>
""", unsafe_allow_html=True)

# ── 구역 정보 바 (저장 버튼은 우측 패널로 이동) ──
st.markdown('<div class="region-strip">', unsafe_allow_html=True)
st.markdown(f"""
<div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding-top:4px;">
  <span class="rtag sample">{T('tag_sample')}</span>
  <span class="rname">{region_name}</span>
  <span class="rtag law">{PT(pt)} · {law}</span>
  <span class="rtag mode">{'ADVANCED' if ADV else 'BASIC'}</span>
</div>
""", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

# ── 저장 처리 함수 (버튼은 우측 사업지 설정 위에서 호출) ──
def do_save():
    note = None
    if ADV:
        note = f"ADV|기부{donation_rate}%|상가{shop_area}㎡|PF{pf_rate}%|지연{delay_months}M|금융{biz['finance']:.0f}억"
    inputs = dict(mode=st.session_state.mode, region=region_name, pt=pt, area=area,
                  year=year, diag=diag, oldr=oldr, lot=lot, stype=stype, agree=agree,
                  total=total_units, member=member_units, avgm2=avg_m2, prev=prev,
                  gprice=g_price, mprice=m_price, cc=cc, other=int(other_rate*100),
                  radius=st.session_state.get("biz_radius",500), addr=st.session_state.get("addr_q",""))
    if ADV:
        inputs.update(donation=donation_rate, shoparea=shop_area, shopprice=shop_price,
                      pfrate=pf_rate, delay=delay_months)
    inputs["ai_results"] = st.session_state.get("ai_results", {})
    row = dict(region_name=region_name, project_type=pt,
               small_type=stype if pt=="small" else None,
               area_sqm=area, built_year=year if pt=="rebuild" else None,
               diagnosis=diag if pt=="rebuild" else None, old_ratio=oldr,
               small_lot=lot, agree_ratio=agree, units=biz["eff_units"], prev_asset=prev,
               sale_price=g_price, construct_cost=cc,
               gen_ratio=round(biz["general_units"]/max(biz["eff_units"],1)*100,1),
               biryul=round(biz["biryul"],2), total_cost=round(biz["total_cost"],1),
               profit=round(biz["profit"],1),
               jeongbi_score=round(score,1) if score is not None else None,
               verdict=vt, req_pass=okv, note=note, inputs=json.dumps(inputs, ensure_ascii=False))
    try:
        r = supabase.table("analysis_regions").insert(row).execute()
        st.success(T("save_ok", id=r.data[0]['id']))
    except Exception as e:
        st.error(T("save_fail", e=e))

# ── Split-screen ──────────────────────────────────────
left, right = st.columns([4.5, 5.5], gap="large")

with left:
    bcolor = ACCENT2 if biz["biryul"]>=100 else "#E8590C"
    pcolor = ACCENT2 if biz["profit"]>=0 else "#E8590C"
    _ou = T("unit_oku")
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card"><div class="kl">{T('kpi_index')}</div><div class="kv">{sd_label(sd)}</div><div class="kd" style="color:#8B95A1;">{T('kpi_index_d')}</div></div>
      <div class="kpi-card"><div class="kl">{T('kpi_biryul')}</div><div class="kv" style="color:{bcolor};">{biz['biryul']:.1f}<small>%</small></div><div class="kd" style="color:{bcolor};">{T('kpi_biryul_d')}</div></div>
      <div class="kpi-card"><div class="kl">{T('kpi_cost')}</div><div class="kv">{biz['total_cost']:,.0f}<small>{_ou}</small></div><div class="kd" style="color:#8B95A1;">{T('kpi_cost_adv') if ADV else T('kpi_cost_bas')}</div></div>
      <div class="kpi-card"><div class="kl">{T('kpi_profit')}</div><div class="kv" style="color:{pcolor};">{biz['profit']:,.0f}<small>{_ou}</small></div><div class="kd" style="color:{pcolor};">{T('kpi_profit_d')}</div></div>
    </div>
    """, unsafe_allow_html=True)

    chips = "".join(f'<span class="chip {"ok" if o else "no"}">{"✓" if o else "✗"} {req_label(n)}</span>' for n,o in reqs)
    st.markdown(f"""
    <div class="verdict v-{vk}">
      <span class="vi">{vi}</span>
      <div class="vt"><h4>{vt}</h4><p>{vd}</p><div class="chips">{chips}</div></div>
    </div>
    """, unsafe_allow_html=True)

    unit_note = T("struct_eff", e=biz['eff_units'], g=biz['general_units']) if ADV else T("struct_gen", g=biz['general_units'])
    st.markdown(f'<div class="sec-title">{T("struct_title")} · {unit_note}</div>', unsafe_allow_html=True)
    if ADV:
        items = [(T("bar_housing"),biz["housing"],ACCENT),(T("bar_shop"),biz["shop"],"#2E86C1"),
                 (T("bar_base"),biz["base_cost"],"#5B7A9D"),(T("bar_finance"),biz["finance"],"#C0392B"),
                 (T("bar_prev"),prev,"#8B95A1"),(T("bar_profit"),max(biz["profit"],0),ACCENT2)]
    else:
        items = [(T("bar_post"),biz["post"],ACCENT),(T("bar_cost"),biz["total_cost"],"#5B7A9D"),
                 (T("bar_prev"),prev,"#8B95A1"),(T("bar_profit"),max(biz["profit"],0),ACCENT2)]
    mx = max([v for _,v,_ in items]+[1])
    bars = "".join(f'<div class="bar-line"><span class="bl">{n}</span><div class="bar-track"><div class="bar-fill" style="width:{min(v/mx*100,100):.0f}%;background:{c};"></div></div><span class="bv">{v:,.0f}{_ou}</span></div>' for n,v,c in items)
    st.markdown(f'<div class="struct">{bars}</div>', unsafe_allow_html=True)
    st.caption(T("biryul_form") + (T("biryul_form_adv") if ADV else ""))

    # 누적 데이터
    st.markdown(f'<div class="sec-title">{T("data_title")}</div>', unsafe_allow_html=True)
    st.caption(T("data_on") if SB_ON else T("data_off"))
    if SB_ON:
        try:
            r = supabase.table("analysis_regions").select(
                "id,created_at,region_name,project_type,biryul,total_cost,profit,verdict,inputs"
            ).order("created_at", desc=True).limit(100).execute()
            if r.data:
                raw = r.data
                df = pd.DataFrame(raw)[["created_at","region_name","project_type","biryul","total_cost","profit","verdict"]]
                df["project_type"] = df["project_type"].map(PT_LABEL_EN if EN else PT_LABEL_KO).fillna(df["project_type"])
                df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d")
                df.columns = [T("col_date"),T("col_region"),T("col_type"),T("col_biryul"),T("col_cost"),T("col_profit"),T("col_verdict")]
                st.dataframe(df, use_container_width=True, height=340, hide_index=True)

                st.markdown(f'<div style="font-size:13px;font-weight:700;color:#191F28;margin:6px 0;">{T("restore_lbl")}</div>', unsafe_allow_html=True)
                _pr = "Prop.Rate" if EN else "비례율"
                opts = {f"{pd.to_datetime(x['created_at']).strftime('%m-%d %H:%M')} · {x['region_name']} ({_pr} {x['biryul']}%)": x
                        for x in raw if x.get("inputs")}
                if opts:
                    sel = st.selectbox(T("restore_sel"), list(opts.keys()), label_visibility="collapsed", key="restore_sel")
                    if st.button(T("restore_do"), use_container_width=True, key="restore_btn"):
                        try:
                            st.session_state["_restore"] = json.loads(opts[sel]["inputs"])
                            st.rerun()
                        except Exception as e:
                            st.error(T("restore_fail", e=e))
                else:
                    st.caption(T("restore_none"))
            else:
                st.info(T("data_empty"))
        except Exception as e:
            st.error(T("query_fail", e=e))
    else:
        st.info(T("data_off_info"))

with right:
        AR = st.session_state.ai_results

        # AI 공통 입력 데이터 (영문/국문 분기)
        if EN:
            ai_input = f"""Project type: {PT(pt)}
Area name: {region_name}
Proportion rate: {biz['biryul']:.1f}%
Total project cost: {biz['total_cost']:.0f} (100M KRW)
Project profit: {biz['profit']:.0f} (100M KRW)
Pre-project asset: {prev:.0f} (100M KRW)
Post-project asset: {biz['post']:.0f} (100M KRW)
Statutory requirements met: {'Yes' if okv else 'No'}
Bid verdict: {'Suitable' if FIT else 'Not suitable'}"""
        else:
            ai_input = f"""사업 유형: {PT(pt)}
구역명: {region_name}
비례율: {biz['biryul']:.1f}%
총사업비: {biz['total_cost']:.0f}억원
사업이익: {biz['profit']:.0f}억원
종전자산: {prev:.0f}억원
종후자산: {biz['post']:.0f}억원
법정요건 충족: {'예' if okv else '아니오'}
사업 판정: {'수주 적합' if FIT else '수주 부적합'}"""

        # ════════ 1) 저장 버튼 → 사업지 설정 (지도) ════════
        st.markdown('<div class="save-slot">', unsafe_allow_html=True)
        if st.button(T("save_btn"), use_container_width=True, disabled=not SB_ON, key="save_left"):
            do_save()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="sec-title">{T("site_title")}</div>', unsafe_allow_html=True)

        addr_q = st.text_input(T("site_search"), value=st.session_state.get("addr_q",""),
            placeholder=T("site_ph"), key="addr_q")

        map_lat, map_lon, place_label = 37.5665, 126.9780, T("site_default")
        if addr_q.strip():
            geo = geocode(addr_q.strip())
            if geo == "NOKEY":
                st.warning(T("site_nokey"))
            elif geo:
                map_lat, map_lon, place_label = geo
                st.success(T("site_found", place=place_label[:55]))
            else:
                st.warning(T("site_notfound"))

        radius = st.slider(T("site_radius"), 100, 1500,
                           st.session_state.get("biz_radius",500), step=50, key="biz_radius")

        # 카카오맵 JS SDK (한국 지도 정확) — JS 키 필요
        # autoload=false + kakao.maps.load() 콜백으로 로딩 타이밍 문제 해결
        kakao_js_key = st.secrets.get("KAKAO_JS_KEY", "")
        with st.expander("🔧 지도 진단 (임시)", expanded=True):
            st.write("JS 키 존재:", bool(kakao_js_key), "· 길이:", len(kakao_js_key))
            st.write("좌표:", map_lat, map_lon, "· 반경:", radius)
        if kakao_js_key:
            _safe_label = place_label[:40].replace("'", " ").replace('"', " ")
            map_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>html,body{{margin:0;padding:0;font-family:sans-serif;}}
#map{{width:100%;height:340px;border-radius:12px;background:#eef;}}
#dbg{{font-size:12px;color:#06c;padding:6px;white-space:pre-wrap;}}</style>
</head><body>
<div id="map"></div>
<div id="dbg">⏳ 진단 시작...</div>
<script>
  var dbgEl = document.getElementById('dbg');
  function dbg(m){{ dbgEl.innerText = m; }}
  var SDK = "https://dapi.kakao.com/v2/maps/sdk.js?appkey={kakao_js_key}&autoload=false";

  // 1단계: SDK URL을 fetch로 직접 호출해 응답 확인
  fetch(SDK).then(function(r){{
    dbg('SDK fetch 상태: ' + r.status + ' (200이면 키/도메인 정상)');
    return r.text();
  }}).then(function(t){{
    // 2단계: 정상이면 실제 script 주입
    var sc = document.createElement('script');
    sc.src = SDK;
    sc.onload = function(){{
      if (typeof kakao === 'undefined' || !kakao.maps){{ dbg('❌ kakao 객체 없음'); return; }}
      kakao.maps.load(function(){{
        try {{
          var c = new kakao.maps.LatLng({map_lat}, {map_lon});
          var map = new kakao.maps.Map(document.getElementById('map'), {{center:c, level:5}});
          new kakao.maps.Marker({{position:c}}).setMap(map);
          new kakao.maps.Circle({{center:c, radius:{radius}, strokeWeight:3,
            strokeColor:'#1B64DA', strokeOpacity:0.8, fillColor:'#1B64DA', fillOpacity:0.15}}).setMap(map);
          dbg('✅ 지도 렌더링 완료');
        }} catch(e){{ dbg('❌ 렌더 오류: ' + e.message); }}
      }});
    }};
    sc.onerror = function(){{ dbg('❌ script 주입 실패'); }};
    document.head.appendChild(sc);
  }}).catch(function(e){{
    dbg('❌ SDK fetch 실패: ' + e.message + '\\n→ 카카오 콘솔 플랫폼>Web 도메인 등록 확인 필요');
  }});
</script>
</body></html>"""
            components.html(map_html, height=400, scrolling=False)
        else:
            st.warning(T("site_nojskey"))
        st.caption(T("site_tip", r=radius))

        # ════════ 2) AI 어시스턴트 ════════
        st.markdown(f'<div class="sec-title">{T("ai_title")}</div>', unsafe_allow_html=True)

        # 2-1) AI 컨설턴트
        if st.button(T("ai_consult_btn"), use_container_width=True, key="ai_consult"):
            if EN:
                prompt = f"""You are a Korean urban-redevelopment (reconstruction/redevelopment) consulting expert.
Analyze the project data and give an expert opinion.

[Project Data]
{ai_input}

Answer concisely in English:
1. Feasibility grade: one of S/A/B/C/D + one-line basis
2. Recommendation: Strongly proceed / Conditional / Hold / Re-review + reason
3. Strengths: 2 key strengths
4. Weaknesses: 2 main risk factors
5. Recommended strategy: 2-3 sentences
6. Final opinion: overall judgment from the bidder's view in 2 sentences"""
            else:
                prompt = f"""당신은 한국 정비사업(재건축·재개발) 전문 컨설턴트입니다.
다음 사업 데이터를 분석하고 전문가 의견을 제시해주세요.

[사업 데이터]
{ai_input}

다음 6가지를 한국어로 간결하게 답해주세요:
1. 사업성 등급: S/A/B/C/D 중 하나 + 근거 한 줄
2. 추진 권고 여부: 적극 추진 / 조건부 추진 / 보류 / 재검토 필요 중 하나 + 이유
3. 강점: 이 사업의 핵심 강점 2가지
4. 약점: 주요 리스크 요인 2가지
5. 추천 전략: 사업 추진 시 핵심 전략 2~3문장
6. 최종 의견: 수주사 입장에서의 종합 판단 2문장"""
            with st.spinner(T("ai_consult_sp")):
                AR["consult"] = call_gemini(prompt, 2048)
        if AR.get("consult"):
            st.markdown(f"""<div style="background:#F5F8FF;border:1.5px solid #1B64DA;border-radius:12px;
                padding:16px;margin-top:8px;white-space:pre-wrap;font-size:13px;line-height:1.7;color:#191F28;">
                <b style="color:#1B64DA;">{T('ai_consult_h')}</b><br><br>{AR['consult']}</div>""",
                unsafe_allow_html=True)

        # 2-2) AI 리스크
        if st.button(T("ai_risk_btn"), use_container_width=True, key="ai_risk"):
            if EN:
                prompt = f"""You are a Korean redevelopment project risk-analysis expert.
Analyze the risks of this project.

[Project Data]
{ai_input}

Answer in English:
1. Failure probability: Low/Medium/High + 2-sentence reason
2. Key risk factors: top 3 risks, each with a one-line explanation
3. Sensitivity: impact of changes in proportion rate / sale price / construction cost (2-3 sentences)
4. Mitigation: response strategy per risk (2-3 sentences)"""
            else:
                prompt = f"""당신은 한국 정비사업 리스크 분석 전문가입니다.
다음 사업의 리스크를 분석해주세요.

[사업 데이터]
{ai_input}

다음 4가지를 한국어로 분석해주세요:
1. 사업 실패 가능성: 낮음/중간/높음 + 주요 이유 2문장
2. 핵심 위험요소: 가장 중요한 리스크 3가지와 각 설명 한 줄
3. 민감도 분석: 비례율·분양가·공사비 변동 시 사업성 영향 2~3문장
4. 대응 전략: 각 리스크별 대응 방안 2~3문장"""
            with st.spinner(T("ai_risk_sp")):
                AR["risk"] = call_gemini(prompt, 2048)
        if AR.get("risk"):
            st.markdown(f"""<div style="background:#FFF8F0;border:1.5px solid #E8590C;border-radius:12px;
                padding:16px;margin-top:8px;white-space:pre-wrap;font-size:13px;line-height:1.7;color:#191F28;">
                <b style="color:#E8590C;">{T('ai_risk_h')}</b><br><br>{AR['risk']}</div>""",
                unsafe_allow_html=True)

        # 2-3) AI 보고서
        if st.button(T("ai_report_btn"), use_container_width=True, key="ai_report"):
            if EN:
                prompt = f"""You are a Korean redevelopment feasibility report writer.
Write a concise feasibility review report based on the project data.

[Project Data]
{ai_input}

Write the report in English markdown with this structure:
## 1. Project Overview
(area name, project type, key metrics, 3-4 sentences)
## 2. Market Analysis
(redevelopment market context & positioning, 3-4 sentences)
## 3. Feasibility Assessment
(proportion-rate/profitability analysis & statutory compliance, 4-5 sentences)
## 4. Risk Analysis
(3 key risks and mitigation)
## 5. Execution Strategy
(core strategy from the bidder's view, 3-4 sentences)
## 6. Final Recommendation
(final bid recommendation and conditions, 2-3 sentences)"""
            else:
                prompt = f"""당신은 한국 정비사업 전문 보고서 작성자입니다.
다음 사업 데이터를 바탕으로 간략한 사업성 검토 보고서를 작성해주세요.

[사업 데이터]
{ai_input}

다음 구조로 마크다운 형식의 보고서를 작성해주세요:
## 1. 사업 개요
(구역명, 사업 유형, 핵심 지표 요약 3~4문장)
## 2. 시장 분석
(정비사업 시장 현황과 본 사업의 시장 포지셔닝 3~4문장)
## 3. 사업성 평가
(비례율·수익성 분석 및 법정요건 충족 여부 4~5문장)
## 4. 리스크 분석
(주요 위험요소 3가지와 대응방안)
## 5. 추진 전략
(수주사 입장에서의 핵심 추진 전략 3~4문장)
## 6. 최종 권고안
(수주 여부 최종 권고 및 조건 2~3문장)"""
            with st.spinner(T("ai_report_sp")):
                AR["report"] = call_gemini(prompt, 2048)
        if AR.get("report"):
            st.markdown(f"""<div style="background:#F8FFF8;border:1.5px solid #2ecc71;border-radius:12px;
                padding:16px;margin-top:8px;font-size:13px;line-height:1.7;color:#191F28;">
                <b style="color:#27ae60;">{T('ai_report_h')}</b><br><br>{AR['report']}</div>""",
                unsafe_allow_html=True)
            st.download_button(T("ai_report_dl"), data=AR["report"],
                file_name=T("ai_report_fn", region=region_name),
                mime="text/plain", key="dl_report")

        # ════════ 3) AI 종합평가 (입지·수주) ════════
        st.markdown(f'<div class="sec-title">{T("ai_eval_title")}</div>', unsafe_allow_html=True)
        if not addr_q.strip():
            st.info(T("ai_loc_info"))
        if st.button(T("ai_loc_btn"), use_container_width=True, key="ai_location",
                     disabled=not addr_q.strip()):
            if EN:
                loc_prompt = f"""You are a Korean real-estate location & redevelopment bid analyst.
Analyze the location using your knowledge of the area (state that it is an estimate).

[Target]
- Location: {place_label}
- Coordinates: lat {map_lat:.4f}, lon {map_lon:.4f}
- Project radius: {radius}m (analyze conditions within this range)
- Project: {ai_input}

Analyze in English with structure:
## 1. Location Score (out of 100)
- Transit (__/35): subway/bus access
- Living infra (__/30): schools, hospitals, malls, parks
- Development catalysts (__/20): new rail, urban development, redevelopment
- Risk factors (__/15): aging commerce, oversupply
- **Total: __**
## 2. Station-Area Rating
- Nearest subway station (est.) & distance, grade (prime <250m / station-area <500m / semi <1km / none)
- Expected price premium
## 3. Competing Redevelopment
- Estimated competing projects within 3km and supply burden
## 4. AI Bid-Win Probability (0-100%)
- Combined probability from feasibility, location, resident acceptance, market, competition
- Sub-scores and rationale
## 5. Overall (3-4 sentences)
- Bid recommendation and differentiation strategy"""
            else:
                loc_prompt = f"""당신은 한국 부동산 입지·정비사업 수주 분석 전문가입니다.
다음 위치와 사업 정보를 바탕으로 입지를 분석해주세요. 실제 해당 지역에 대한 지식을 활용하되, 추정임을 전제로 하세요.

[분석 대상]
- 위치: {place_label}
- 좌표: 위도 {map_lat:.4f}, 경도 {map_lon:.4f}
- 사업단지 반경: {radius}m (이 범위 내 입지 여건 중심으로 분석)
- 사업: {ai_input}

다음을 한국어로 구조적으로 분석해주세요:

## 1. 입지 점수 (100점 만점)
- 교통 (__/35): 지하철·버스 접근성 추정
- 생활인프라 (__/30): 학교·병원·마트·공원
- 개발호재 (__/20): 신규 철도·도시개발·정비사업
- 위험요인 (__/15): 노후상권·공급과잉 등 감점요소
- **총점: __점**

## 2. 역세권 판정
- 가장 가까운 지하철역(추정)과 거리, 등급(초역세권 250m↓/역세권 500m↓/준역세권 1km↓/비역세권)
- 예상 분양가 프리미엄

## 3. 경쟁 정비사업
- 인근 3km 내 추진 중인 정비사업 추정과 공급 부담

## 4. AI 수주 성공 확률 (0~100%)
- 사업성·입지성·주민수용성·시장성·경쟁도를 종합한 수주 성공 확률 %
- 세부 점수와 근거

## 5. 종합 총평 (3~4문장)
- 수주 추천 여부와 차별화 전략"""
            with st.spinner(T("ai_loc_sp")):
                AR["location"] = call_gemini(loc_prompt, 2048)
                AR["location_place"] = place_label[:45]
        if AR.get("location"):
            st.markdown(f"""<div style="background:#F0F6FF;border:1.5px solid {ACCENT};border-radius:12px;
                padding:16px;margin-top:8px;font-size:13px;line-height:1.7;color:#191F28;">
                <b style="color:{ACCENT};">{T('ai_loc_h')}</b><br>
                <span style="font-size:12px;color:#888;">📍 {AR.get('location_place','')}</span><br><br>{AR['location']}</div>""",
                unsafe_allow_html=True)
            st.caption(T("ai_loc_note"))

st.caption(T("footer"))
