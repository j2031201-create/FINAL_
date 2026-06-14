"""
정비사업 수주 타당성 분석 플랫폼
시행사 사업개발팀용 · Basic / Advanced 2-모드 · 결과기반 동적 테마(Dynamic Theming)
"""
import streamlit as st
import pandas as pd
import datetime as dt
import requests, json
import folium
from streamlit_folium import st_folium

# ── Gemini API 공통 호출 함수 ──────────────────────────
def call_gemini(prompt: str, max_tokens: int = 2048) -> str:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        return "⚠️ Gemini API 키가 설정되지 않았습니다. Streamlit secrets에 GEMINI_API_KEY를 입력하세요."
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
        return text.strip() if text.strip() else "⚠️ AI 응답이 비어 있습니다. 다시 시도해주세요."
    except Exception as e:
        return f"⚠️ AI 응답 오류: {str(e)[:80]}"

@st.cache_data(ttl=3600, show_spinner=False)
def geocode(query: str):
    """주소·지명 → 위경도 (Nominatim, 무료·키 불필요). 실패 시 None"""
    try:
        r = requests.get("https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "kr"},
            headers={"User-Agent": "jeongbi-feasibility-app"}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"]), data[0].get("display_name", query)
    except Exception:
        pass
    return None

st.set_page_config(page_title="정비사업 수주 타당성 분석", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="expanded")

if "mode" not in st.session_state:
    st.session_state.mode = "advanced" if False else "basic"
if "ai_results" not in st.session_state:
    st.session_state.ai_results = {}  # {consult, risk, report, location} 캐싱·저장용

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
        if k in _map and v is not None:
            st.session_state[_map[k]] = v
    # small 유형의 oldr은 별도 key(v_oldr2)
    if rd.get("pt")=="small" and rd.get("oldr") is not None:
        st.session_state["v_oldr2"] = rd["oldr"]
    # 저장된 AI 분석 결과 복원 (재호출 없이 바로 표시 → API 절약)
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

PT_LABEL = {"rebuild":"재건축","redevelop":"재개발","small":"소규모정비"}



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

# ── 법정요건 (소규모정비 4유형 세분화) ─────────────────
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
    else:  # 소규모정비 (빈집 및 소규모주택 정비에 관한 특례법)
        oo = oldr>=66.7
        if stype=="가로주택정비":
            ar = area<10000
            reqs=[("면적1만㎡미만",ar),("노후2/3",oo)]; okv=ar and oo
        elif stype=="자율주택정비":
            uo = total_units<20  # 단독·다세대 밀집, 소규모 세대 기준
            reqs=[("20세대미만",uo),("노후2/3",oo)]; okv=uo and oo
        elif stype=="소규모재건축":
            ar = area<10000; uo = total_units<200
            reqs=[("면적1만㎡미만",ar),("200세대미만",uo),("노후2/3",oo)]; okv=ar and uo and oo
        else:  # 소규모재개발
            ar = area<5000  # 역세권·준공업 5천㎡ 미만
            reqs=[("면적5천㎡미만",ar),("노후2/3",oo)]; okv=ar and oo
        sd="적합" if okv else "미달"
    return reqs, okv, sd, score

def verdict(b, okv):
    if b>=110 and okv: return "success","✅","사업성 우수 · 수주 우선 검토","비례율·법정요건 모두 충족"
    if b>=100 and okv: return "info","🔵","사업성 양호 · 조건부 검토","추가 변수 점검 후 추진 가능"
    return "warning","⚠️","사업성 부족 · 재검토 필요","비례율 100% 미만 또는 요건 미달"

# ── 사이드바 ──────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="side-h">⚙️ 분석 모드</div>', unsafe_allow_html=True)
    mode_sel = st.radio("모드", ["basic","advanced"],
                        format_func=lambda x:"Basic (초기 스크리닝)" if x=="basic" else "Advanced (상세 수지)",
                        index=0 if not ADV else 1, label_visibility="collapsed")
    if mode_sel != st.session_state.mode:
        st.session_state.mode = mode_sel
        st.rerun()

    st.markdown('<div class="side-h">📍 구역 정보</div>', unsafe_allow_html=True)
    region_name = st.text_input("구역명", st.session_state.get("v_region","○○3 후보구역"), key="v_region", label_visibility="collapsed")
    pt = st.radio("사업 유형", ["rebuild","redevelop","small"], format_func=lambda x:PT_LABEL[x], key="v_pt")

    st.markdown('<div class="side-h">🏘️ 구역 요건</div>', unsafe_allow_html=True)
    area = st.number_input("구역면적 (㎡)", 0, value=st.session_state.get("v_area",35000), step=1000, key="v_area")
    year, diag, oldr, lot, stype = 1992, "통과(D/E)", 75.0, 30.0, "가로주택정비"
    if pt=="rebuild":
        diag = st.radio("안전진단", ["통과(D/E)","미통과"], horizontal=True, key="v_diag")
        year = st.number_input("준공연도", 1960, 2025, st.session_state.get("v_year",1992), key="v_year")
        st.caption(f"경과 {dt.date.today().year-year}년 (법정 30년 이상)")
    elif pt=="redevelop":
        oldr = st.slider("노후 동수 비율 (%)", 50.0, 100.0, st.session_state.get("v_oldr",75.0), key="v_oldr")
        lot = st.slider("과소필지율 (%)", 0.0, 60.0, st.session_state.get("v_lot",30.0), key="v_lot")
    else:
        stype = st.radio("세부유형", ["가로주택정비","자율주택정비","소규모재건축","소규모재개발"], key="v_stype")
        oldr = st.slider("노후 동수 비율 (%)", 50.0, 100.0, st.session_state.get("v_oldr",70.0), key="v_oldr2")
        _hint = {
            "가로주택정비":"가로주택: 1만㎡ 미만 · 노후 2/3 이상 · 안전진단 면제",
            "자율주택정비":"자율주택: 단독·다세대 밀집 · 20세대 미만 소규모",
            "소규모재건축":"소규모재건축: 1만㎡·200세대 미만 · 안전진단",
            "소규모재개발":"소규모재개발: 역세권·준공업 5천㎡ 미만",
        }
        st.caption(_hint[stype])
    agree = st.slider("주민동의율 (%)", 50.0, 100.0, st.session_state.get("v_agree",75.0), key="v_agree")

    st.markdown('<div class="side-h">🏢 분양 계획</div>', unsafe_allow_html=True)
    total_units = st.number_input("신축 총세대", 1, value=st.session_state.get("v_total",600), step=10, key="v_total")
    member_units = st.number_input("조합원 분양세대", 0, value=st.session_state.get("v_member",350), step=10, help="나머지가 일반분양분", key="v_member")
    avg_m2 = st.number_input("세대당 분양면적 (㎡)", 30, 200, st.session_state.get("v_avgm2",85), help="전용 84㎡ ≈ 국민주택규모", key="v_avgm2")

    st.markdown('<div class="side-h">💰 사업성 입력</div>', unsafe_allow_html=True)
    prev = st.number_input("종전자산 총액 (억)", 0, value=st.session_state.get("v_prev",2000), step=100, help="조합원 보유 토지·건물 감정가 합계", key="v_prev")
    g_price = st.number_input("일반분양가 (만원/㎡)", 0, value=st.session_state.get("v_gprice",850), step=10, key="v_gprice")
    m_price = st.number_input("조합원분양가 (만원/㎡)", 0, value=st.session_state.get("v_mprice",760), step=10, key="v_mprice")
    cc = st.number_input("공사비 (만원/㎡)", 0, value=st.session_state.get("v_cc",200), step=5, key="v_cc")
    other_rate = st.slider("기타사업비율 (공사비 대비 %)", 20, 50, st.session_state.get("v_other",28 if pt=="small" else 35),
                           help="설계·감리비, 각종 부담금, 신탁보수, 예비비 등 공사비 외 부대비용을 하나의 비율로 묶어 추정합니다 (사전타당성 단계의 표준 방식 · 세부 항목은 본 타당성에서 산정). PF 금융비용은 Advanced에서 별도 계산.", key="v_other")/100

    if ADV:
        st.markdown('<div class="side-h">🎯 인센티브 · 상가 · 금융 (Advanced)</div>', unsafe_allow_html=True)
        donation_rate = st.slider("기부채납률 (%)", 0, 20, st.session_state.get("v_donation",10), help="높을수록 용적률 인센티브로 세대수 증가", key="v_donation")
        shop_area = st.number_input("상가 연면적 (㎡)", 0, value=st.session_state.get("v_shoparea",1650), step=50, key="v_shoparea")
        shop_price = st.number_input("상가 분양가 (만원/㎡)", 0, value=st.session_state.get("v_shopprice",1200), step=50, key="v_shopprice")
        pf_rate = st.number_input("예상 PF 금리 (%)", 0.0, value=st.session_state.get("v_pfrate",8.0), step=0.1, key="v_pfrate")
        delay_months = st.slider("사업 지연 기간 (개월)", 0, 36, st.session_state.get("v_delay",0), key="v_delay")


# ── 계산 (로직 보존) ──────────────────────────────────
if ADV:
    biz = calc_advanced_business(total_units, member_units, avg_m2, m_price, g_price, cc, other_rate, prev,
                                 donation_rate, shop_area, shop_price, pf_rate, delay_months)
else:
    biz = calc_business(total_units, member_units, avg_m2, m_price, g_price, cc, other_rate, prev)
reqs, okv, sd, score = calc_req(pt, area, year, diag, oldr, lot, agree, stype, total_units)
vk, vi, vt, vd = verdict(biz["biryul"], okv)
law = "빈집·소규모주택 정비 특례법" if pt=="small" else "도시 및 주거환경정비법"


# ── 결과 기반 동적 테마 결정 ───────────────────────────
FIT = (biz["biryul"] >= 100) and okv          # 수주 적합 여부
if FIT:
    ACCENT  = "#1B64DA"   # 메인 블루
    ACCENT2 = "#0F2A4A"   # 보조 네이비
    SOFT_BG = "#E8F1FF"
    HEAD_BG = "#1B64DA"
else:
    ACCENT  = "#E8590C"   # 메인 앰버
    ACCENT2 = "#9A3412"   # 보조 다크오렌지
    SOFT_BG = "#FDF1E7"
    HEAD_BG = "#C2410C"

# ── CSS (동적 테마 주입) ──────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
html, body, .stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3,
.stApp h4, .stApp label, .stApp input, .stApp button, .stApp td, .stApp th,
.stApp li, .stApp a {{
    font-family:'Noto Sans KR',sans-serif;
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
    font-family:'Noto Sans KR',sans-serif;
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

mode_label = "Advanced · 상세 수지분석" if ADV else "Basic · 초기 스크리닝"
st.markdown(f"""
<div class="top-header">
  <div class="brand">🏗️ 정비사업 수주 타당성 분석<span class="brand-sub">시행사 사업개발팀용</span></div>
  <div class="spacer"></div>
  <div class="head-link">{mode_label}</div>
</div>
""", unsafe_allow_html=True)

# ── 구역 정보 바 (헤더에 붙는 풀폭 흰 바) + 저장 버튼 ──
st.markdown('<div class="region-strip">', unsafe_allow_html=True)
rb1, rb2 = st.columns([7, 3], vertical_alignment="center")
with rb1:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding-top:4px;">
      <span class="rtag sample">예시 데이터</span>
      <span class="rname">{region_name}</span>
      <span class="rtag law">{PT_LABEL[pt]} · {law}</span>
      <span class="rtag mode">{'ADVANCED' if ADV else 'BASIC'}</span>
    </div>
    """, unsafe_allow_html=True)
with rb2:
    st.markdown('<div class="save-slot">', unsafe_allow_html=True)
    save_clicked = st.button("💾 이 분석 저장", use_container_width=True, disabled=not SB_ON)
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

if save_clicked:
    note = None
    if ADV:
        note = f"ADV|기부{donation_rate}%|상가{shop_area}㎡|PF{pf_rate}%|지연{delay_months}M|금융{biz['finance']:.0f}억"
    # 전체 입력값을 JSON으로 묶어 복원용으로 저장
    inputs = dict(mode=st.session_state.mode, region=region_name, pt=pt, area=area,
                  year=year, diag=diag, oldr=oldr, lot=lot, stype=stype, agree=agree,
                  total=total_units, member=member_units, avgm2=avg_m2, prev=prev,
                  gprice=g_price, mprice=m_price, cc=cc, other=int(other_rate*100),
                  radius=st.session_state.get("biz_radius",500), addr=st.session_state.get("addr_q",""))
    if ADV:
        inputs.update(donation=donation_rate, shoparea=shop_area, shopprice=shop_price,
                      pfrate=pf_rate, delay=delay_months)
    # AI 분석 결과도 함께 저장 → 불러올 때 재호출 없이 복원 (API 절약)
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
        st.success(f"저장 완료 (id: {r.data[0]['id']})")
    except Exception as e:
        st.error(f"저장 실패: {e}")

st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)


# ── Split-screen ──────────────────────────────────────
left, right = st.columns([4.5, 5.5], gap="large")

with left:
    bcolor = ACCENT2 if biz["biryul"]>=100 else "#E8590C"
    pcolor = ACCENT2 if biz["profit"]>=0 else "#E8590C"
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card"><div class="kl">정비지수 / 요건</div><div class="kv">{sd}</div><div class="kd" style="color:#8B95A1;">법정 요건 평가</div></div>
      <div class="kpi-card"><div class="kl">비례율</div><div class="kv" style="color:{bcolor};">{biz['biryul']:.1f}<small>%</small></div><div class="kd" style="color:{bcolor};">100% 이상 사업성</div></div>
      <div class="kpi-card"><div class="kl">총사업비</div><div class="kv">{biz['total_cost']:,.0f}<small>억</small></div><div class="kd" style="color:#8B95A1;">{'공사비+기타+금융' if ADV else '공사비+기타사업비'}</div></div>
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

    unit_note = f"유효 {biz['eff_units']}세대 · 일반분양 {biz['general_units']}세대" if ADV else f"일반분양 {biz['general_units']}세대"
    st.markdown(f'<div class="sec-title">사업성 구조 · {unit_note}</div>', unsafe_allow_html=True)
    if ADV:
        items = [("주택분양",biz["housing"],ACCENT),("상가수입",biz["shop"],"#2E86C1"),
                 ("공사+기타",biz["base_cost"],"#5B7A9D"),("금융비용",biz["finance"],"#C0392B"),
                 ("종전자산",prev,"#8B95A1"),("사업이익",max(biz["profit"],0),ACCENT2)]
    else:
        items = [("종후자산",biz["post"],ACCENT),("총사업비",biz["total_cost"],"#5B7A9D"),
                 ("종전자산",prev,"#8B95A1"),("사업이익",max(biz["profit"],0),ACCENT2)]
    mx = max([v for _,v,_ in items]+[1])
    bars = "".join(f'<div class="bar-line"><span class="bl">{n}</span><div class="bar-track"><div class="bar-fill" style="width:{min(v/mx*100,100):.0f}%;background:{c};"></div></div><span class="bv">{v:,.0f}억</span></div>' for n,v,c in items)
    st.markdown(f'<div class="struct">{bars}</div>', unsafe_allow_html=True)
    st.caption("비례율 = (종후자산 − 총사업비) ÷ 종전자산 × 100 · 실무 표준 공식" + (" · 총사업비에 PF 금융비용 포함" if ADV else ""))

    # 누적 데이터 (좌측 패널 하단 · 항상 펼침)
    st.markdown('<div class="sec-title">누적 분석 데이터</div>', unsafe_allow_html=True)
    st.caption("☁️ Supabase 연결됨 · 행을 선택해 그때 분석을 다시 불러올 수 있습니다" if SB_ON else "💾 로컬 모드 · 연결 설정(secrets) 시 영구 저장 활성화")
    if SB_ON:
        try:
            r = supabase.table("analysis_regions").select(
                "id,created_at,region_name,project_type,biryul,total_cost,profit,verdict,inputs"
            ).order("created_at", desc=True).limit(100).execute()
            if r.data:
                raw = r.data
                df = pd.DataFrame(raw)[["created_at","region_name","project_type","biryul","total_cost","profit","verdict"]]
                df["project_type"] = df["project_type"].map(PT_LABEL).fillna(df["project_type"])
                df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d")
                df.columns = ["분석일자","구역명","유형","비례율(%)","총사업비(억)","사업이익(억)","판정"]
                st.dataframe(df, use_container_width=True, height=340, hide_index=True)

                # ── 분석 복원 (그때 입력값으로 사이드바 되돌리기) ──
                st.markdown('<div style="font-size:13px;font-weight:700;color:#191F28;margin:6px 0;">🔄 저장된 분석 불러오기</div>', unsafe_allow_html=True)
                opts = {f"{pd.to_datetime(x['created_at']).strftime('%m-%d %H:%M')} · {x['region_name']} (비례율 {x['biryul']}%)": x
                        for x in raw if x.get("inputs")}
                if opts:
                    sel = st.selectbox("불러올 분석 선택", list(opts.keys()), label_visibility="collapsed", key="restore_sel")
                    if st.button("📂 이 분석 다시 보기", use_container_width=True, key="restore_btn"):
                        try:
                            st.session_state["_restore"] = json.loads(opts[sel]["inputs"])
                            st.rerun()
                        except Exception as e:
                            st.error(f"복원 실패: {e}")
                else:
                    st.caption("복원 가능한 저장 항목이 아직 없습니다. (이후 저장분부터 불러오기 지원)")
            else:
                st.info("저장된 데이터가 없습니다.")
        except Exception as e:
            st.error(f"조회 실패: {e}")
    else:
        st.info("연결 설정 시 누적 데이터가 표시됩니다.")

with right:
        AR = st.session_state.ai_results  # AI 결과 캐시

        # 공통 입력 데이터 (계산 결과 기반)
        ai_input = f"""사업 유형: {PT_LABEL.get(pt, pt)}
구역명: {region_name}
비례율: {biz['biryul']:.1f}%
총사업비: {biz['total_cost']:.0f}억원
사업이익: {biz['profit']:.0f}억원
종전자산: {prev:.0f}억원
종후자산: {biz['post']:.0f}억원
법정요건 충족: {'예' if okv else '아니오'}
사업 판정: {'수주 적합' if FIT else '수주 부적합'}"""

        # ════════ 1) 사업지 설정 (지도) ════════
        st.markdown('<div class="sec-title">📍 사업지 설정</div>', unsafe_allow_html=True)
        addr_q = st.text_input("📍 구역명·단지명·주소 검색", value=st.session_state.get("addr_q",""),
            placeholder="예: 한남더힐, 성수전략정비구역, 잠실 자이, 왕십리역", key="addr_q")

        map_lat, map_lon, place_label = 37.5665, 126.9780, "서울시청 (기본 위치)"
        if addr_q.strip():
            geo = geocode(addr_q.strip())
            if geo:
                map_lat, map_lon, place_label = geo
                st.success(f"📍 {place_label[:55]}")
            else:
                st.warning("위치를 찾지 못했습니다. 단지명이 안 되면 '동 이름'이나 '가까운 역'으로 검색해보세요.")

        radius = st.slider("📐 사업단지 반경 (m)", 100, 1500,
                           st.session_state.get("biz_radius",500), step=50, key="biz_radius")

        fmap = folium.Map(location=[map_lat, map_lon], zoom_start=15, tiles="OpenStreetMap")
        folium.Marker([map_lat, map_lon], tooltip=place_label[:40],
                      icon=folium.Icon(color="blue", icon="building", prefix="fa")).add_to(fmap)
        folium.Circle(location=[map_lat, map_lon], radius=radius,
                      color="#1B64DA", weight=2, fill=True, fill_color="#1B64DA",
                      fill_opacity=0.18, tooltip=f"사업단지 반경 {radius}m").add_to(fmap)
        st_folium(fmap, width=None, height=380, returned_objects=[], key="biz_map")
        st.caption(f"📐 파란 원 = 사업단지 반경 {radius}m · 이 범위를 기준으로 AI가 분석합니다.")

        # ════════ 2) AI 어시스턴트 ════════
        st.markdown('<div class="sec-title">🤖 AI 어시스턴트</div>', unsafe_allow_html=True)

        # 2-1) AI 컨설턴트 분석
        if st.button("🤖 AI 컨설턴트 분석", use_container_width=True, key="ai_consult"):
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
            with st.spinner("🤖 AI 컨설턴트 분석 중..."):
                AR["consult"] = call_gemini(prompt, 2048)
        if AR.get("consult"):
            st.markdown(f"""<div style="background:#F5F8FF;border:1.5px solid #1B64DA;border-radius:12px;
                padding:16px;margin-top:8px;white-space:pre-wrap;font-size:13px;line-height:1.7;color:#191F28;">
                <b style="color:#1B64DA;">🤖 AI 사업성 컨설턴트 의견</b><br><br>{AR['consult']}</div>""",
                unsafe_allow_html=True)

        # 2-2) AI 리스크 분석
        if st.button("⚠️ 주요 리스크 분석", use_container_width=True, key="ai_risk"):
            prompt = f"""당신은 한국 정비사업 리스크 분석 전문가입니다.
다음 사업의 리스크를 분석해주세요.

[사업 데이터]
{ai_input}

다음 4가지를 한국어로 분석해주세요:
1. 사업 실패 가능성: 낮음/중간/높음 + 주요 이유 2문장
2. 핵심 위험요소: 가장 중요한 리스크 3가지와 각 설명 한 줄
3. 민감도 분석: 비례율·분양가·공사비 변동 시 사업성 영향 2~3문장
4. 대응 전략: 각 리스크별 대응 방안 2~3문장"""
            with st.spinner("⚠️ 리스크 분석 중..."):
                AR["risk"] = call_gemini(prompt, 2048)
        if AR.get("risk"):
            st.markdown(f"""<div style="background:#FFF8F0;border:1.5px solid #E8590C;border-radius:12px;
                padding:16px;margin-top:8px;white-space:pre-wrap;font-size:13px;line-height:1.7;color:#191F28;">
                <b style="color:#E8590C;">⚠️ AI 리스크 분석 결과</b><br><br>{AR['risk']}</div>""",
                unsafe_allow_html=True)

        # 2-3) AI 보고서 생성
        if st.button("📄 AI 보고서 생성", use_container_width=True, key="ai_report"):
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
            with st.spinner("📄 AI 보고서 생성 중..."):
                AR["report"] = call_gemini(prompt, 2048)
        if AR.get("report"):
            st.markdown(f"""<div style="background:#F8FFF8;border:1.5px solid #2ecc71;border-radius:12px;
                padding:16px;margin-top:8px;font-size:13px;line-height:1.7;color:#191F28;">
                <b style="color:#27ae60;">📄 AI 생성 사업성 검토 보고서</b><br><br>{AR['report']}</div>""",
                unsafe_allow_html=True)
            st.download_button("⬇️ 보고서 텍스트 다운로드", data=AR["report"],
                file_name=f"{region_name}_AI사업성보고서.txt",
                mime="text/plain", key="dl_report")

        # ════════ 3) AI 종합평가 (입지·수주) ════════
        st.markdown('<div class="sec-title">🎯 AI 종합평가</div>', unsafe_allow_html=True)
        if not addr_q.strip():
            st.info("📍 위 **사업지 설정**에서 주소를 입력하면 입지·수주 분석이 활성화됩니다.")
        if st.button("🤖 입지·수주 성공률 분석", use_container_width=True, key="ai_location",
                     disabled=not addr_q.strip()):
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
            with st.spinner("🤖 입지·수주 분석 중... (지도 + AI)"):
                AR["location"] = call_gemini(loc_prompt, 2048)
                AR["location_place"] = place_label[:45]
        if AR.get("location"):
            st.markdown(f"""<div style="background:#F0F6FF;border:1.5px solid {ACCENT};border-radius:12px;
                padding:16px;margin-top:8px;font-size:13px;line-height:1.7;color:#191F28;">
                <b style="color:{ACCENT};">🎯 AI 입지·수주 종합평가</b><br>
                <span style="font-size:12px;color:#888;">📍 {AR.get('location_place','')}</span><br><br>{AR['location']}</div>""",
                unsafe_allow_html=True)
            st.caption("※ AI 추정 분석입니다. 실제 사업 판단 시 현장 실사와 공공데이터 확인이 필요합니다.")

st.caption("⚠️ 예시 데이터 기반 간이 시뮬레이션 · 실제 사업 판단 시 정식 감정평가·정비계획 수립 필요")
