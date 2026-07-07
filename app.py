import streamlit as st
import math
import random
import time

# 페이지 레이아웃 설정
st.set_page_config(page_title="란체스터 턴제 작전 시뮬레이터", layout="wide")

st.title("⚔️ 란체스터 작전 시뮬레이터 (NATO 군사 기호 v2.5)")
st.write("양측의 군세를 설정하고 작전을 개시하면, 표준 NATO 군사 기호(Mil-Std-2525)와 잔존 병력 게이지가 실시간으로 매 턴 업데이트됩니다.")

# 1. 부대 규모(제대) 정의 및 NATO 표준 기호 표시용 식별자
UNIT_SCALES = {
    "분대 (Squad - 약 10명) [●]": {"weight": 10, "icon_text": "●"},
    "소대 (Platoon - 약 30명) [●●]": {"weight": 30, "icon_text": "●●"},
    "중대 (Company - 약 120명) [I]": {"weight": 120, "icon_text": "I"},
    "대대 (Battalion - 약 500명) [II]": {"weight": 500, "icon_text": "II"},
    "연대 (Regiment - 약 1,500명) [III]": {"weight": 1500, "icon_text": "III"},
    "여단 (Brigade - 약 3,500명) [X]": {"weight": 3500, "icon_text": "X"},
    "사단 (Division - 약 12,000명) [XX]": {"weight": 12000, "icon_text": "XX"},
}

# 2. 핵심 군사 전술 정의
TACTICAL_OPTIONS = {
    "정면 공격 (Frontal Assault)": {"atk_mod": 1.0, "def_mod": 1.0, "law": "제곱", "desc": "정직한 정면 승부."},
    "포위 / 이중 포위 (Encirclement)": {"atk_mod": 1.4, "def_mod": 1.0, "law": "제곱", "desc": "적의 측후방 차단, 화력 +40%"},
    "전격전 / 기갑 돌격 (Blitzkrieg)": {"atk_mod": 1.3, "def_mod": 0.8, "law": "제곱", "desc": "기갑/항공 중심 종심 타격"},
    "종심 방어 (Defense in Depth)": {"atk_mod": 0.8, "def_mod": 1.5, "law": "선형", "desc": "방어선 중첩, 선형 법칙 강제 적용"},
    "소모전 / 파상공세 (Attrition Warfare)": {"atk_mod": 1.2, "def_mod": 0.9, "law": "선형", "desc": "참호전 유도, 일대일 갉아먹기"}
}

# 3. 정규병과 및 기본 전투력 지수
BRANCH_POWER = {
    "보병 (정규 보병)": 1.0,
    "기갑 (전차/장갑차)": 25.0,
    "포병 (자주포/다연장)": 60.0,
    "정보/드론 (UAV)": 15.0,
    "항공 (공격헬기)": 120.0
}

# 매 턴 터질 수 있는 전장의 안개 돌발 이벤트
RANDOM_EVENTS = [
    {"title": "정상 교전", "blue": 1.0, "red": 1.0, "desc": "특이사항 없음."},
    {"title": "지휘관 저격당함!", "blue": 0.7, "red": 1.0, "desc": "자유진영 지휘 마비 (화력 -30%)"},
    {"title": "적 탄약고 대폭발!", "blue": 1.0, "red": 0.65, "desc": "공산진영 군수 마비 (화력 -35%)"},
    {"title": "악천후 대공습", "blue": 0.8, "red": 0.8, "desc": "양측 기동 및 시야 제한 (화력 -20%)"},
    {"title": "야간 기습 감행", "blue": 1.3, "red": 0.9, "desc": "야간 장비가 우수한 자유진영의 야습 (+30%)"},
    {"title": "공산군 결사 항전", "blue": 0.9, "red": 1.3, "desc": "배수의 진을 친 공산군의 반격 (+30%)"}
]

# 🎨 NATO 표준 전술 기호(APP-6/Mil-Std-2525)를 실시간 렌더링하는 함수 (SVG 기반)
def render_nato_symbol(affiliation, branch, scale_text):
    """
    affiliation: 'blue' (아군: 사각형 프레임) 또는 'red' (적군: 다이아몬드 프레임)
    branch: 보병, 기갑, 포병, 정보/드론, 항공
    scale_text: ●●, I, II, X 등 제대 표시 마커
    """
    # 진영별 색상 및 프레임(테두리 사각형 vs 다이아몬드) 크기 설정
    if affiliation == "blue":
        box_color = "#4A90E2"  # 우군 청색
        bg_color = "rgba(74, 144, 226, 0.15)"
        frame_svg = '<rect x="25" y="25" width="50" height="50" rx="3" fill="{bg}" stroke="{stroke}" stroke-width="3"/>'
    else:
        box_color = "#E24A4A"  # 적군 적색
        bg_color = "rgba(226, 74, 74, 0.15)"
        # 다이아몬드(마름모) 형태
        frame_svg = '<polygon points="50,20 80,50 50,80 20,50" fill="{bg}" stroke="{stroke}" stroke-width="3"/>'
    
    frame_svg = frame_svg.format(bg=bg_color, stroke=box_color)

    # 병과 기호 내부 심볼 디자인 지정
    inner_symbol = ""
    if "보병" in branch:
        # 보병: 교차하는 X선 (참호전 엑스반도 유래)
        inner_symbol = f'<line x1="30" y1="30" x2="70" y2="70" stroke="{box_color}" stroke-width="2.5"/><line x1="70" y1="30" x2="30" y2="70" stroke="{box_color}" stroke-width="2.5"/>'
    elif "기갑" in branch:
        # 기갑: 궤도를 뜻하는 타원형 원
        inner_symbol = f'<ellipse cx="50" cy="50" rx="18" ry="8" fill="none" stroke="{box_color}" stroke-width="2.5"/>'
    elif "포병" in branch:
        # 포병: 포탄을 뜻하는 중앙에 꽉 찬 검은 점/원
        inner_symbol = f'<circle cx="50" cy="50" r="6" fill="{box_color}"/>'
    elif "드론" in branch or "정보" in branch:
        # 정보/UAV: 레이더 스캔 형태의 번개선 기호처럼 표현
        inner_symbol = f'<polyline points="40,35 60,35 45,52 60,52 45,68" fill="none" stroke="{box_color}" stroke-width="2.5"/>'
    elif "항공" in branch:
        # 항공(회전익/고정익): 프로펠러 모양의 하단 곡선 아치 형태
        inner_symbol = f'<path d="M32,60 Q50,30 68,60" fill="none" stroke="{box_color}" stroke-width="2.5"/>'

    # 완성된 SVG 코드 조립 (상단에 크기별 제대 표시 기호 가산)
    svg_code = f"""
    <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <text x="50" y="15" font-family="Arial, sans-serif" font-size="12" font-weight="bold" fill="{box_color}" text-anchor="middle">{scale_text}</text>
        {frame_svg}
        {inner_symbol}
    </svg>
    """
    return svg_code

st.markdown("---")

# [상단 종합 전장 변수 영역] ----------------------------------------------------
st.subheader("🌐 글로벌 전장 인프라 설정")
c_env1, c_env2, c_env3 = st.columns(3)

with c_env1:
    selected_scale = st.selectbox("📏 작전 부대 체급 (제대 규모)", options=list(UNIT_SCALES.keys()), index=3)
    scale_weight = UNIT_SCALES[selected_scale]["weight"]
    scale_icon = UNIT_SCALES[selected_scale]["icon_text"]
with c_env2:
    terrain = st.selectbox("⛰️ 전장 지형 선택", ["평지", "야지 (산악)", "시가지"])
with c_env3:
    tactics_relation = st.selectbox("⚔️ 초기 배치 상태", ["공평한 조우전", "자유진영 진지방어", "공산진영 진지방어"])

st.markdown("---")

# [진영별 입력 영역] ----------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    st.header("🔵 자유진영 (Free World)")
    blue_tactics = st.selectbox("자유진영 작전 교리", list(TACTICAL_OPTIONS.keys()), key="b_tac")
    blue_unit_count = st.number_input("참전 제대 개수 (부대 수)", min_value=1, value=1, key="b_uc")
    
    st.write("**[제대 편제 및 주력 병과 기호 설정]**")
    blue_main_branch = st.selectbox("대표 군사 기호 선택 (아군)", list(BRANCH_POWER.keys()), index=0, key="b_mb")
    
    blue_regular = {}
    for branch in BRANCH_POWER.keys():
        blue_regular[branch] = st.number_input(f"자유 {branch} 수량", min_value=0, value=10 if "보병" in branch else 0, key=f"b_{branch}")
    blue_guerrilla = st.number_input("자유 민병대/게릴라 (명)", min_value=0, value=0, key="b_g")
    blue_morale = st.slider("지휘관 역량 및 사기", 0.5, 2.0, 1.0, 0.1, key="b_m")

with col2:
    st.header("🔴 공산진영 (Communist Bloc)")
    red_tactics = st.selectbox("공산진영 작전 교리", list(TACTICAL_OPTIONS.keys()), key="r_tac")
    red_unit_count = st.number_input("참전 제대 개수 (부대 수)", min_value=1, value=1, key="r_uc")
    
    st.write("**[제대 편제 및 주력 병과 기호 설정]**")
    red_main_branch = st.selectbox("대표 군사 기호 선택 (적군)", list(BRANCH_POWER.keys()), index=1, key="r_mb")
    
    red_regular = {}
    for branch in BRANCH_POWER.keys():
        red_regular[branch] = st.number_input(f"공산 {branch} 수량", min_value=0, value=10 if "보병" in branch else 0, key=f"r_{branch}")
    red_guerrilla = st.number_input("공산 파르티잔/반군 (명)", min_value=0, value=0, key="r_g")
    red_morale = st.slider("지휘관 역량 및 사기", 0.5, 2.0, 1.0, 0.1, key="r_m")

st.markdown("---")

# [턴제 시뮬레이션 구동 엔진] ----------------------------------------------------
if st.button("⚔️ NATO 군사 심볼 작전 시뮬레이션 개시", type="primary", use_container_width=True):
    
    # 1. 초기 총 원 계산
    blue_single_total = sum(blue_regular.values())
    red_single_total = sum(red_regular.values())
    
    blue_start_HP = (blue_single_total * blue_unit_count * scale_weight) + blue_guerrilla
    red_start_HP = (red_single_total * red_unit_count * scale_weight) + red_guerrilla
    
    # 2. 기초 화력 계산 가중치 맵 구성
    blue_power_map = BRANCH_POWER.copy()
    red_power_map = BRANCH_POWER.copy()
    
    b_g_pow, r_g_pow = 0.5, 0.5
    if terrain == "야지 (산악)":
        blue_power_map["기갑 (전차/장갑차)"] *= 0.7; red_power_map["기갑 (전차/장갑차)"] *= 0.7
        b_g_pow, r_g_pow = 0.8, 0.8
    elif terrain == "시가지":
        blue_power_map["기갑 (전차/장갑차)"] *= 0.5; red_power_map["기갑 (전차/장갑차)"] *= 0.5
        blue_power_map["보병 (정규 보병)"] *= 1.3; red_power_map["보병 (정규 보병)"] *= 1.3
        b_g_pow, r_g_pow = 1.5, 1.5
        
    blue_base_dmg = sum(blue_regular[br] * blue_unit_count * blue_power_map[br] for br in BRANCH_POWER.keys()) + (blue_guerrilla * b_g_pow)
    red_base_dmg = sum(red_regular[br] * red_unit_count * red_power_map[br] for br in BRANCH_POWER.keys()) + (red_guerrilla * r_g_pow)
    
    b_tac = TACTICAL_OPTIONS[blue_tactics]
    r_tac = TACTICAL_OPTIONS[red_tactics]
    is_linear = (b_tac["law"] == "선형" or r_tac["law"] == "선형")
    
    blue_def_mod = 2.0 if "자유진영 진지방어" in tactics_relation else 1.0
    red_def_mod = 2.0 if "공산진영 진지방어" in tactics_relation else 1.0

    B_HP = float(blue_start_HP)
    R_HP = float(red_start_HP)
    
    st.subheader("🎬 지휘통제소 작전 상황판 (COP)")
    
    # 상단에 NATO 심볼 고정 전개 배치를 위한 레이아웃 공간 마련
    symbol_zone = st.empty()
    log_placeholder = st.empty()
    
    turn = 1
    max_turns = 12
    
    # 실시간 비주얼 갱신용 루프 코드
    while B_HP > 0 and R_HP > 0 and turn <= max_turns:
        evt = random.choice(RANDOM_EVENTS)
        
        if not is_linear:
            b_ratio = (B_HP / blue_start_HP)
            r_ratio = (R_HP / red_start_HP)
            b_current_dmg = blue_base_dmg * b_ratio * b_tac["atk_mod"] * blue_morale * evt["blue"]
            r_current_dmg = red_base_dmg * r_ratio * r_tac["atk_mod"] * red_morale * evt["red"]
        else:
            b_current_dmg = blue_base_dmg * b_tac["atk_mod"] * blue_morale * evt["blue"] * 0.4
            r_current_dmg = red_base_dmg * r_tac["atk_mod"] * red_morale * evt["red"] * 0.4
            
        b_inflict = max(1.0, b_current_dmg / red_def_mod)
        r_inflict = max(1.0, r_current_dmg / blue_def_mod)
        
        B_HP = max(0.0, B_HP - r_inflict)
        R_HP = max(0.0, R_HP - b_inflict)
        
        # 📊 1. 상단 NATO 전술 부대 심볼 배치 전개 (SVG 실시간 주입)
        blue_svg = render_nato_symbol("blue", blue_main_branch, scale_icon)
        red_svg = render_nato_symbol("red", red_main_branch, scale_icon)
        
        with symbol_zone.container():
            sz_col1, sz_vs, sz_col2 = st.columns([4, 2, 4])
            with sz_col1:
                st.markdown(f"<div style='text-align: center;'>{blue_svg}<br><b>자유군 주력부대</b></div>", unsafe_allow_html=True)
            with sz_vs:
                st.markdown("<h2 style='text-align: center; line-height: 100px; color: #777;'>VS</h2>", unsafe_allow_html=True)
            with sz_col2:
                st.markdown(f"<div style='text-align: center;'>{red_svg}<br><b>공산군 주력부대</b></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        # 📊 2. 하단 잔존 지수 및 대미지 로그 출력
        with log_placeholder.container():
            st.markdown(f"### ⚔️ **제 {turn} 턴 교전 상황** (전장의 안개: `{evt['title']}`)")
            st.caption(f"💬 *지휘소 보고: {evt['desc']}*")
            
            b_per = (B_HP / blue_start_HP) * 100
            r_per = (R_HP / red_start_HP) * 100
            
            col_b, col_r = st.columns(2)
            with col_b:
                st.write(f"🔵 **자유진영 전력 수준:** {round(b_per, 1)}% ({int(B_HP)} / {int(blue_start_HP)})")
                st.progress(B_HP / blue_start_HP)
            with col_r:
                st.write(f"🔴 **공산진영 전력 수준:** {round(r_per, 1)}% ({int(R_HP)} / {int(red_start_HP)})")
                st.progress(R_HP / red_start_HP)
                
            st.markdown(f"**💥 교전 피해 산출:** 아군이 적에게 {int(b_inflict)} 타격 ⚔️ 적군이 아군에게 {int(r_inflict)} 타격")
            st.markdown("---")
            
        turn += 1
        time.sleep(1.0) # 1초마다 시각적 로그와 NATO 기호 정보 갱신

    # 🏁 최종 결과
    st.header("🏁 작전통제실 최종 전과 분석")
    if B_HP > 0 and R_HP == 0:
        st.success(f"🏆 **작전 성공!** {turn-1}턴 만에 적 진영을 격멸하고 전선을 수복하였습니다.")
    elif R_HP > 0 and B_HP == 0:
        st.error(f"💀 **작전 실패...** 전열이 격파당해 철수 명령이 하달되었습니다.")
    else:
        st.warning("🤝 **상호 파멸:** 치명적인 소모전 끝에 양측 부대 모두 전투 불능 상태(무승부)에 빠졌습니다.")
