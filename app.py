import streamlit as st
import math
import random
import time

# 페이지 레이아웃 설정
st.set_page_config(page_title="란체스터 제대별 작전 시뮬레이터", layout="wide")

st.title("⚔️ 란체스터 전술 시뮬레이터 (교리적 제대 편제 v3.0)")
st.write("사용자가 병력을 일일이 입력하지 않습니다. 제대의 종류와 규모를 선택하면 군사 교리에 기반한 장비/인원 통계가 자동 산출되어 전투에 반영됩니다.")

# 1. 제대 규모(체급) 정의 및 기본 인원/장비 가중치
UNIT_SCALES = {
    "소대 (Platoon) [●●]": {"weight_mod": 1, "icon_text": "●●"},
    "중대 (Company) [I]": {"weight_mod": 4, "icon_text": "I"},
    "대대 (Battalion) [II]": {"weight_mod": 16, "icon_text": "II"},
    "연대 (Regiment) [III]": {"weight_mod": 48, "icon_text": "III"},
    "여단 (Brigade) [X]": {"weight_mod": 100, "icon_text": "X"},
    "사단 (Division) [XX]": {"weight_mod": 350, "icon_text": "XX"},
}

# 2. 🌟 제대 종류(성격) 정의 및 소대(기준점)당 표준 편제 통계
# - 여기서 정해진 비율이 제대 규모(weight_mod)와 곱해져서 자동 통계가 나옵니다.
UNIT_TYPES = {
    "보병제대 (Infantry Unit)": {
        "icon_type": "보병",
        "men_per_plt": 30, "tank_per_plt": 0, "ifv_per_plt": 0, "art_per_plt": 0,
        "base_power": 30, # 화력 지수
        "desc": "순수 알보병 위주 편제. 방어와 야지/시가지 전투에 유리합니다."
    },
    "기갑제대 (Armored Unit)": {
        "icon_type": "기갑",
        "men_per_plt": 15, "tank_per_plt": 3, "ifv_per_plt": 0, "art_per_plt": 0,
        "base_power": 90, 
        "desc": "전차 중심의 강력한 충격 군세. 평지 돌격에 특화되어 있습니다."
    },
    "기계화보병제대 (Mechanized Infantry)": {
        "icon_type": "기갑", # 외관 기호는 기갑/장갑 기호 사용
        "men_per_plt": 25, "tank_per_plt": 0, "ifv_per_plt": 3, "art_per_plt": 0,
        "base_power": 65,
        "desc": "장갑차에 탑승한 보병. 기동력과 전투 지속력이 균형을 이룹니다."
    },
    "공수/특전제대 (Airborne / Special Forces)": {
        "icon_type": "항공",
        "men_per_plt": 20, "tank_per_plt": 0, "ifv_per_plt": 0, "art_per_plt": 0,
        "base_power": 45, # 정예병 버프 반영
        "desc": "경량화된 정예 보병. 우수한 사기와 특수 전술(포위 등)에 강합니다."
    },
    "포병제대 (Artillery Unit)": {
        "icon_type": "포병",
        "men_per_plt": 20, "tank_per_plt": 0, "ifv_per_plt": 0, "art_per_plt": 3,
        "base_power": 180,
        "desc": "강력한 화력 지원 부대. 직접 교전 시 방어력 페널티가 큽니다."
    }
}

# 3. 핵심 군사 전술 작전 교리
TACTICAL_OPTIONS = {
    "정면 공격 (Frontal Assault)": {"atk_mod": 1.0, "def_mod": 1.0, "law": "제곱"},
    "포위 / 이중 포위 (Encirclement)": {"atk_mod": 1.4, "def_mod": 1.0, "law": "제곱"},
    "전격전 / 기갑 돌격 (Blitzkrieg)": {"atk_mod": 1.3, "def_mod": 0.8, "law": "제곱"},
    "종심 방어 (Defense in Depth)": {"atk_mod": 0.8, "def_mod": 1.5, "law": "선형"}
}

# 전장의 안개 돌발 이벤트
RANDOM_EVENTS = [
    {"title": "정상 교전", "blue": 1.0, "red": 1.0, "desc": "특이사항 없음."},
    {"title": "지휘관 저격당함!", "blue": 0.7, "red": 1.0, "desc": "자유진영 지휘 마비 (화력 -30%)"},
    {"title": "적 탄약고 대폭발!", "blue": 1.0, "red": 0.65, "desc": "공산진영 군수 마비 (화력 -35%)"},
    {"title": "야간 기습 감행", "blue": 1.3, "red": 0.9, "desc": "야간 장비가 우수한 자유진영의 야습 (+30%)"},
    {"title": "공산군 결사 항전", "blue": 0.9, "red": 1.3, "desc": "배수의 진을 친 공산군의 반격 (+30%)"}
]

# 🎨 NATO 표준 전술 기호 SVG 렌더링 함수
def render_nato_symbol(affiliation, branch, scale_text):
    if affiliation == "blue":
        box_color = "#4A90E2"
        bg_color = "rgba(74, 144, 226, 0.15)"
        frame_svg = '<rect x="25" y="25" width="50" height="50" rx="3" fill="{bg}" stroke="{stroke}" stroke-width="3"/>'
    else:
        box_color = "#E24A4A"
        bg_color = "rgba(226, 74, 74, 0.15)"
        frame_svg = '<polygon points="50,20 80,50 50,80 20,50" fill="{bg}" stroke="{stroke}" stroke-width="3"/>'
    
    frame_svg = frame_svg.format(bg=bg_color, stroke=box_color)

    inner_symbol = ""
    if "보병" in branch:
        inner_symbol = f'<line x1="30" y1="30" x2="70" y2="70" stroke="{box_color}" stroke-width="2.5"/><line x1="70" y1="30" x2="30" y2="70" stroke="{box_color}" stroke-width="2.5"/>'
    elif "기갑" in branch:
        inner_symbol = f'<ellipse cx="50" cy="50" rx="18" ry="8" fill="none" stroke="{box_color}" stroke-width="2.5"/>'
    elif "포병" in branch:
        inner_symbol = f'<circle cx="50" cy="50" r="6" fill="{box_color}"/>'
    elif "항공" in branch:
        inner_symbol = f'<path d="M32,60 Q50,30 68,60" fill="none" stroke="{box_color}" stroke-width="2.5"/>'

    return f"""
    <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <text x="50" y="15" font-family="Arial, sans-serif" font-size="12" font-weight="bold" fill="{box_color}" text-anchor="middle">{scale_text}</text>
        {frame_svg} {inner_symbol}
    </svg>
    """

# [글로벌 환경 설정]
st.subheader("🌐 글로벌 전장 환경 설정")
c_env1, c_env2 = st.columns(2)
with c_env1: terrain = st.selectbox("⛰️ 전장 지형 선택", ["평지", "야지 (산악)", "시가지"])
with c_env2: tactics_relation = st.selectbox("⚔️ 초기 배치 상태", ["공평한 조우전", "자유진영 진지방어", "공산진영 진지방어"])

st.markdown("---")

# [진영별 입력 영역]
col1, col2 = st.columns(2)

with col1:
    st.header("🔵 자유진영 (Free World)")
    blue_tactics = st.selectbox("작전 교리", list(TACTICAL_OPTIONS.keys()), key="b_tac")
    
    # 제대 종류 및 규모 선택
    b_type = st.selectbox("🔰 제대 종류 선택 (아군)", list(UNIT_TYPES.keys()), index=0, key="b_type")
    b_scale = st.selectbox("📏 제대 규모 선택 (아군)", list(UNIT_SCALES.keys()), index=2, key="b_scale")
    blue_count = st.number_input("참전 제대 개수 (부대 수)", min_value=1, value=1, key="b_count")
    blue_morale = st.slider("지휘관 역량 및 사기", 0.5, 2.0, 1.0, 0.1, key="b_m")
    
    # 📊 선택에 따른 자동 통계 산출
    b_type_data = UNIT_TYPES[b_type]
    b_mod = UNIT_SCALES[b_scale]["weight_mod"]
    
    b_stat_men = b_type_data["men_per_plt"] * b_mod * blue_count
    b_stat_tank = b_type_data["tank_per_plt"] * b_mod * blue_count
    b_stat_ifv = b_type_data["ifv_per_plt"] * b_mod * blue_count
    b_stat_art = b_type_data["art_per_plt"] * b_mod * blue_count
    
    # 통계 표기 화면
    st.markdown("##### 📈 인프라 및 편제 자동 산출 통계")
    st.info(f"ℹ️ **특성:** {b_type_data['desc']}")
    st.code(f"• 총 원 (병력): {b_stat_men} 명\n• 주력 전차: {b_stat_tank} 대\n• 보병장갑차: {b_stat_ifv} 대\n• 견인/자주포: {b_stat_art} 문")

with col2:
    st.header("🔴 공산진영 (Communist Bloc)")
    red_tactics = st.selectbox("작전 교리", list(TACTICAL_OPTIONS.keys()), key="r_tac")
    
    # 제대 종류 및 규모 선택
    r_type = st.selectbox("🔰 제대 종류 선택 (적군)", list(UNIT_TYPES.keys()), index=1, key="r_type")
    r_scale = st.selectbox("📏 제대 규모 선택 (적군)", list(UNIT_SCALES.keys()), index=2, key="r_scale")
    red_count = st.number_input("참전 제대 개수 (부대 수)", min_value=1, value=1, key="r_count")
    red_morale = st.slider("지휘관 역량 및 사기", 0.5, 2.0, 1.0, 0.1, key="r_m")
    
    # 📊 선택에 따른 자동 통계 산출
    r_type_data = UNIT_TYPES[r_type]
    r_mod = UNIT_SCALES[r_scale]["weight_mod"]
    
    r_stat_men = r_type_data["men_per_plt"] * r_mod * red_count
    r_stat_tank = r_type_data["tank_per_plt"] * r_mod * red_count
    r_stat_ifv = r_type_data["ifv_per_plt"] * r_mod * red_count
    r_stat_art = r_type_data["art_per_plt"] * r_mod * red_count
    
    # 통계 표기 화면
    st.markdown("##### 📈 인프라 및 편제 자동 산출 통계")
    st.info(f"ℹ️ **특성:** {r_type_data['desc']}")
    st.code(f"• 총 원 (병력): {r_stat_men} 명\n• 주력 전차: {r_stat_tank} 대\n• 보병장갑차: {r_stat_ifv} 대\n• 견인/자주포: {r_stat_art} 문")

st.markdown("---")

# [시뮬레이션 구동 ENGINE]
if st.button("⚔️ NATO 군사 심볼 작전 시뮬레이션 개시", type="primary", use_container_width=True):
    
    # 1. 초기 전력 수치(HP) 설정 -> 자동 계산된 총 병력수 기준
    blue_start_HP = float(b_stat_men)
    red_start_HP = float(r_stat_men)
    
    # 부대 소멸 방지 하한값
    if blue_start_HP <= 0: blue_start_HP = 10.0
    if red_start_HP <= 0: red_start_HP = 10.0
    
    # 2. 제대 종류별 기초 화력 계산 (기본화력지수 * 규모 모디파이어 * 부대 수)
    blue_base_dmg = b_type_data["base_power"] * b_mod * blue_count
    red_base_dmg = r_type_data["base_power"] * r_mod * red_count
    
    # 지형 페널티/버프 연산
    if terrain == "야지 (산악)":
        if "기갑" in b_type or "기계화" in b_type: blue_base_dmg *= 0.7
        if "기갑" in r_type or "기계화" in r_type: red_base_dmg *= 0.7
    elif terrain == "시가지":
        if "기갑" in b_type: blue_base_dmg *= 0.5
        if "기갑" in r_type: red_base_dmg *= 0.5
        if "보병" in b_type: blue_base_dmg *= 1.3
        if "보병" in r_type: red_base_dmg *= 1.3

    b_tac = TACTICAL_OPTIONS[blue_tactics]
    r_tac = TACTICAL_OPTIONS[red_tactics]
    is_linear = (b_tac["law"] == "선형" or r_tac["law"] == "선형")
    
    blue_def_mod = 2.0 if "자유진영 진지방어" in tactics_relation else 1.0
    red_def_mod = 2.0 if "공산진영 진지방어" in tactics_relation else 1.0

    B_HP, R_HP = blue_start_HP, red_start_HP
    
    st.subheader("🎬 지휘통제소 작전 상황판 (COP)")
    symbol_zone = st.empty()
    log_placeholder = st.empty()
    
    turn = 1
    max_turns = 12
    
    while B_HP > 0 and R_HP > 0 and turn <= max_turns:
        evt = random.choice(RANDOM_EVENTS)
        
        # 란체스터 계산
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
        
        # 📊 NATO 심볼 실시간 렌더링 (제대 종류별 아이콘 연결)
        blue_svg = render_nato_symbol("blue", b_type_data["icon_type"], UNIT_SCALES[b_scale]["icon_text"])
        red_svg = render_nato_symbol("red", r_type_data["icon_type"], UNIT_SCALES[r_scale]["icon_text"])
        
        with symbol_zone.container():
            sz_col1, sz_vs, sz_col2 = st.columns([4, 2, 4])
            with sz_col1:
                st.markdown(f"<div style='text-align: center;'>{blue_svg}<br><b>자유군 {b_type.split(' ')[0]}</b></div>", unsafe_allow_html=True)
            with sz_vs:
                st.markdown("<h2 style='text-align: center; line-height: 100px; color: #777;'>VS</h2>", unsafe_allow_html=True)
            with sz_col2:
                st.markdown(f"<div style='text-align: center;'>{red_svg}<br><b>공산군 {r_type.split(' ')[0]}</b></div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

        with log_placeholder.container():
            st.markdown(f"### ⚔️ **제 {turn} 턴 교전 상황** (전장의 안개: `{evt['title']}`)")
            st.caption(f"💬 *지휘소 보고: {evt['desc']}*")
            
            b_per = (B_HP / blue_start_HP) * 100
            r_per = (R_HP / red_start_HP) * 100
            
            col_b, col_r = st.columns(2)
            with col_b:
                st.write(f"🔵 **자유군 전력 잔존율:** {round(b_per, 1)}% ({int(B_HP)} / {int(blue_start_HP)} 명)")
                st.progress(B_HP / blue_start_HP)
            with col_r:
                st.write(f"🔴 **공산군 전력 잔존율:** {round(r_per, 1)}% ({int(R_HP)} / {int(red_start_HP)} 명)")
                st.progress(R_HP / red_start_HP)
                
            st.markdown(f"**💥 교전 피해 산출:** 아군이 적에게 {int(b_inflict)} 타격 ⚔️ 적군이 아군에게 {int(r_inflict)} 타격")
            st.markdown("---")
            
        turn += 1
        time.sleep(1.0)

    # 최종 결과
    st.header("🏁 작전통제실 최종 전과 분석")
    if B_HP > 0 and R_HP == 0:
        st.success(f"🏆 **작전 성공!** 아군 {b_type.split(' ')[0]}가 {turn-1}턴 만에 적을 완전 소탕했습니다.")
    elif R_HP > 0 and B_HP == 0:
        st.error(f"💀 **작전 실패...** 적 {r_type.split(' ')[0]}의 전력을 이기지 못하고 전선이 붕괴되었습니다.")
    else:
        st.warning("🤝 **상호 파멸:** 치명적인 소모전 끝에 양측 모두 전투력을 상실했습니다.")

import streamlit as st

# [디자인 커스텀 CSS]
st.markdown("""
    <style>
    /* 전체 배경을 전술 모니터 느낌의 어두운 색으로 설정 */
    .stApp {
        background-color: #0a0e0a;
        color: #00ff41; /* 군용 모니터의 상징인 형광 녹색 텍스트 */
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* 헤더 스타일링 */
    h1, h2, h3 {
        color: #00ff41 !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 1px solid #00ff41;
    }
    
    /* 버튼 디자인: 투박한 군용 버튼 느낌 */
    div.stButton > button {
        background-color: #1a2a1a !important;
        color: #00ff41 !important;
        border: 2px solid #00ff41 !important;
        border-radius: 0px !important;
        font-weight: bold;
    }
    
    /* 경고/성공 메시지 박스 스타일 */
    .stAlert {
        background-color: #1a2a1a !important;
        border: 1px solid #00ff41 !important;
    }
    
    /* 프로그레스 바 스타일 */
    .stProgress > div > div > div {
        background-color: #00ff41 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 이후 기존의 시뮬레이션 코드들이 이어집니다...
