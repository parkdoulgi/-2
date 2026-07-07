import streamlit as st
import math
import random
import time

# 페이지 레이아웃 설정
st.set_page_config(page_title="란체스터 턴제 작전 시뮬레이터", layout="wide")

st.title("🎮 란체스터 턴제 작전 시뮬레이터 (Tactical Turn-Based Game)")
st.write("양측의 군세를 설정하고 [전투 작전 개시]를 누르면, 매 턴마다 화력을 주고받으며 전황이 실시간으로 시각화됩니다.")

# 1. 부대 규모(제대) 정의
UNIT_SCALES = {
    "팀 (Team - 약 3~5명)": 1,
    "반 (Section - 약 10명 내외)": 2,
    "분대 (Squad - 약 10명)": 10,
    "소대 (Platoon - 약 30명)": 30,
    "중대 (Company - 약 120명)": 120,
    "대대 (Battalion - 약 500명)": 500,
    "연대 (Regiment - 약 1,500명)": 1500,
    "여단 (Brigade - 약 3,500명)": 3500,
    "사단 (Division - 약 12,000명)": 12000,
    "군단 (Corps - 약 50,000명)": 50000,
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

st.markdown("---")

# [상단 종합 전장 변수 영역] ----------------------------------------------------
st.subheader("🌐 글로벌 전장 인프라 설정")
c_env1, c_env2, c_env3 = st.columns(3)

with c_env1:
    selected_scale = st.selectbox("📏 작전 부대 체급 (제대 규모)", options=list(UNIT_SCALES.keys()), index=4)
    scale_weight = UNIT_SCALES[selected_scale]
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
    
    st.write("**[제대 1개당 평균 편제]**")
    blue_regular = {}
    for branch in BRANCH_POWER.keys():
        blue_regular[branch] = st.number_input(f"자유 {branch} 수량", min_value=0, value=10 if "보병" in branch else 0, key=f"b_{branch}")
    blue_guerrilla = st.number_input("자유 민병대/게릴라 (명)", min_value=0, value=0, key="b_g")
    blue_morale = st.slider("지휘관 역량 및 사기", 0.5, 2.0, 1.0, 0.1, key="b_m")

with col2:
    st.header("🔴 공산진영 (Communist Bloc)")
    red_tactics = st.selectbox("공산진영 작전 교리", list(TACTICAL_OPTIONS.keys()), key="r_tac")
    red_unit_count = st.number_input("참전 제대 개수 (부대 수)", min_value=1, value=1, key="r_uc")
    
    st.write("**[제대 1개당 평균 편제]**")
    red_regular = {}
    for branch in BRANCH_POWER.keys():
        red_regular[branch] = st.number_input(f"공산 {branch} 수량", min_value=0, value=10 if "보병" in branch else 0, key=f"r_{branch}")
    red_guerrilla = st.number_input("공산 파르티잔/반군 (명)", min_value=0, value=0, key="r_g")
    red_morale = st.slider("지휘관 역량 및 사기", 0.5, 2.0, 1.0, 0.1, key="r_m")

st.markdown("---")

# [턴제 시뮬레이션 구동 엔진] ----------------------------------------------------
if st.button("⚔️ 턴제 작전 시뮬레이션 개시 (전투 시작)", type="primary", use_container_width=True):
    
    # 1. 초기 총 원 계산
    blue_single_total = sum(blue_regular.values())
    red_single_total = sum(red_regular.values())
    
    # 실제 전장에 진입하는 총 인원수 (규모 가중치 적용)
    blue_start_HP = (blue_single_total * blue_unit_count * scale_weight) + blue_guerrilla
    red_start_HP = (red_single_total * red_unit_count * scale_weight) + red_guerrilla
    
    # 2. 기초 화력 계산 가중치 맵 구성
    blue_power_map = BRANCH_POWER.copy()
    red_power_map = BRANCH_POWER.copy()
    
    # 지형 보너스 처리
    b_g_pow, r_g_pow = 0.5, 0.5
    if terrain == "야지 (산악)":
        blue_power_map["기갑 (전차/장갑차)"] *= 0.7; red_power_map["기갑 (전차/장갑차)"] *= 0.7
        b_g_pow, r_g_pow = 0.8, 0.8
    elif terrain == "시가지":
        blue_power_map["기갑 (전차/장갑차)"] *= 0.5; red_power_map["기갑 (전차/장갑차)"] *= 0.5
        blue_power_map["보병 (정규 보병)"] *= 1.3; red_power_map["보병 (정규 보병)"] *= 1.3
        b_g_pow, r_g_pow = 1.5, 1.5
        
    # 기본 단일 제대 총 화력 합산
    blue_base_dmg = sum(blue_regular[br] * blue_unit_count * blue_power_map[br] for br in BRANCH_POWER.keys()) + (blue_guerrilla * b_g_pow)
    red_base_dmg = sum(red_regular[br] * red_unit_count * red_power_map[br] for br in BRANCH_POWER.keys()) + (red_guerrilla * r_g_pow)
    
    # 기본 전술 계수 및 법칙 추출
    b_tac = TACTICAL_OPTIONS[blue_tactics]
    r_tac = TACTICAL_OPTIONS[red_tactics]
    is_linear = (b_tac["law"] == "선형" or r_tac["law"] == "선형")
    
    # 초기 배치 방어력 버프
    blue_def_mod = 2.0 if "자유진영 진지방어" in tactics_relation else 1.0
    red_def_mod = 2.0 if "공산진영 진지방어" in tactics_relation else 1.0

    # 턴제 루프 구동을 위한 변수 복사
    B_HP = float(blue_start_HP)
    R_HP = float(red_start_HP)
    
    st.subheader("🎬 실시간 전장 브리핑 및 교전 로그")
    log_placeholder = st.empty()
    status_container = st.container()
    
    turn = 1
    max_turns = 12 # 무한루프 방지 최대 턴 제한
    
    # 시각적 변화를 실시간으로 보여주기 위한 턴 루프
    while B_HP > 0 and R_HP > 0 and turn <= max_turns:
        # 🎲 매 턴 다른 전장의 안개 이벤트 발생
        evt = random.choice(RANDOM_EVENTS)
        
        # 란체스터 법칙에 따른 실시간 화력 연산
        # 제곱 법칙이면 (현재 인원 비례 가중치)^2 혹은 현재원 기반 화력 집중 효과 반영
        if not is_linear:
            # 제곱 법칙: 현재 남은 인원 비율만큼 화력 유지
            b_ratio = (B_HP / blue_start_HP)
            r_ratio = (R_HP / red_start_HP)
            b_current_dmg = blue_base_dmg * b_ratio * b_tac["atk_mod"] * blue_morale * evt["blue"]
            r_current_dmg = red_base_dmg * r_ratio * r_tac["atk_mod"] * red_morale * evt["red"]
        else:
            # 선형 법칙: 인원이 줄어도 화력이 선형적으로만 분산됨
            b_current_dmg = blue_base_dmg * b_tac["atk_mod"] * blue_morale * evt["blue"] * 0.4
            r_current_dmg = red_base_dmg * r_tac["atk_mod"] * red_morale * evt["red"] * 0.4
            
        # 서로에게 가해지는 최종 피해 (방어력 모디파이어 나누기)
        b_inflict = max(1.0, b_current_dmg / red_def_mod)
        r_inflict = max(1.0, r_current_dmg / blue_def_mod)
        
        # 데미지 적용
        B_HP -= r_inflict
        R_HP -= b_inflict
        
        # HP 하한선 차단
        if B_HP < 0: B_HP = 0
        if R_HP < 0: R_HP = 0
        
        # 📊 실시간 화면 갱신 (시각적 턴제 연출)
        with log_placeholder.container():
            st.markdown(f"### ⚔️ **제 {turn} 턴 교전 상황** (전장의 안개: `{evt['title']}`)")
            st.caption(f"💬 *이벤트 효과: {evt['desc']}*")
            
            # 게이지 바 시각화 (HTML/CSS 활용)
            b_per = (B_HP / blue_start_HP) * 100
            r_per = (R_HP / red_start_HP) * 100
            
            col_b, col_r = st.columns(2)
            with col_b:
                st.write(f"🔵 **자유진영 군세 잔존율:** {round(b_per, 1)}% ({int(B_HP)} / {int(blue_start_HP)})")
                st.progress(min(1.0, max(0.0, B_HP / blue_start_HP)))
            with col_r:
                st.write(f"🔴 **공산진영 군세 잔존율:** {round(r_per, 1)}% ({int(R_HP)} / {int(red_start_HP)})")
                st.progress(min(1.0, max(0.0, R_HP / red_start_HP)))
                
            st.markdown(f"**💥 이번 턴 타격 로그:** 자유진영이 {int(b_inflict)}의 대미지 타격 ⚔️ 공산진영이 {int(r_inflict)}의 대미지 타격")
            st.markdown("---")
            
        turn += 1
        time.sleep(0.8) # 0.8초 딜레이를 주어 턴이 실제로 흘러가는 듯한 시각 효과 부여

    # 🏁 최종 전과 보고서
    st.header("🏁 참모본부 최종 전과 분석 보고서")
    if B_HP > 0 and R_HP == 0:
        st.success(f"🏆 **자유진영 승리!** {turn-1}턴 만에 작전 지역 내 공산진영을 완전 격멸 및 소탕하였습니다.")
    elif R_HP > 0 and B_HP == 0:
        st.error(f"💀 **공산진영 승리...** 자유진영 전선이 무너지며 {turn-1}턴 만에 작전 지역에서 철수했습니다.")
    else:
        st.warning("🤝 **교착 상태 / 동귀어진:** 양측 모두 치명적인 피해를 입고 전열이 붕괴되어 무승부로 끝났습니다.")
