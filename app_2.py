import os
import streamlit as st
from PIL import Image, ImageDraw

# ---------------------------------------------------------
# 1. 모바일 앱 반응형 뷰포트 및 단백한 모노톤 CSS
# ---------------------------------------------------------
st.set_page_config(
    page_title="AMC Chest X-ray Pre-VERIFY Agent",
    page_icon="🩻",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
/* 모바일 최적화 및 상단 여백 확보 */
.block-container {
    width: 100% !important;
    max-width: 480px !important;
    padding-top: 3.6rem !important;
    padding-bottom: 2.5rem !important;
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
    margin: 0 auto !important;
}

/* 상단 메인 헤더 배너: 무채색 차콜/블랙 톤 */
.app-header {
    background-color: #18181B;
    border: 1px solid #27272A;
    border-radius: 10px;
    padding: 16px 18px;
    margin-top: 4px;
    margin-bottom: 14px;
}
.app-header h3 {
    margin: 0;
    font-size: 1.15rem;
    font-weight: 800;
    color: #FFFFFF;
}
.app-header p {
    margin: 4px 0 0 0;
    font-size: 0.8rem;
    color: #A1A1AA;
}

/* 상태 알림 카드: 보류(적색) 및 정상(녹색) */
.alert-hold {
    background-color: #450A0A;
    border: 1px solid #DC2626;
    border-radius: 8px;
    padding: 14px;
    color: #FEE2E2;
    font-size: 0.88rem;
    line-height: 1.45;
    margin-bottom: 12px;
}
.alert-pass {
    background-color: #052E16;
    border: 1px solid #16A34A;
    border-radius: 8px;
    padding: 14px;
    color: #DCFCE7;
    font-size: 0.88rem;
    line-height: 1.45;
    margin-bottom: 12px;
}

/* 임상 분석 사유 카드 */
.reason-card {
    background-color: #18181B;
    border-left: 3px solid #71717A;
    border-top: 1px solid #27272A;
    border-right: 1px solid #27272A;
    border-bottom: 1px solid #27272A;
    padding: 12px 14px;
    border-radius: 6px;
    color: #E4E4E7;
    font-size: 0.83rem;
    line-height: 1.55;
    margin-top: 10px;
    margin-bottom: 12px;
}

/* 버튼 스타일 */
div.stButton > button {
    width: 100% !important;
    min-height: 44px !important;
    font-size: 0.9rem !important;
    font-weight: 700 !important;
    border-radius: 6px !important;
    background-color: #27272A !important;
    color: #FFFFFF !important;
    border: 1px solid #3F3F46 !important;
}
div.stButton > button:hover {
    background-color: #3F3F46 !important;
    border-color: #52525B !important;
}

/* PACS 워크리스트: 흑백 모노톤 테이블 */
.table-container {
    width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin-top: 8px;
    border-radius: 6px;
    border: 1px solid #27272A;
}
.pacs-table {
    width: 100%;
    min-width: 440px;
    border-collapse: collapse;
    font-size: 0.8rem;
    text-align: center;
    background-color: #09090B;
}
.pacs-table th, .pacs-table td {
    border: 1px solid #27272A;
    padding: 9px 6px;
    color: #D4D4D8;
}
.pacs-table th {
    background-color: #18181B;
    color: #A1A1AA;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. 이미지 파일 탐색 함수 (루트/하위 경로 및 확장자 자동 매칭)
# ---------------------------------------------------------
def find_case_image(target_name):
    """
    GitHub 저장소 루트 및 sample_xrays 하위 폴더의 실제 이미지를
    확장자(.jpeg, .png, .jpg)와 공백 차이에 구애받지 않고 탐색합니다.
    """
    # 1. 탐색 대상 경로 목록
    base_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()
    search_dirs = [
        base_dir,
        os.getcwd(),
        os.path.join(base_dir, "sample_xrays"),
        os.path.join(os.getcwd(), "sample_xrays"),
        "sample_xrays"
    ]

    # 2. 파일명 후보군 (2.real <-> 2. real 양방향 호환)
    candidates = [target_name]
    if " " in target_name:
        candidates.append(target_name.replace(" ", ""))
    else:
        candidates.append(target_name.replace(".", ". "))

    extensions = [".jpeg", ".png", ".jpg", ".JPEG", ".PNG", ".JPG"]

    # 3. 정확한 파일 매칭 탐색
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for cand in candidates:
            for ext in extensions:
                p = os.path.join(d, cand + ext)
                if os.path.exists(p):
                    return p

    # 4. 키워드 기반 유연한 파일 매칭 (접두어 매칭)
    clean_target = target_name.replace(" ", "").lower()
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        try:
            for f in os.listdir(d):
                f_clean = f.replace(" ", "").lower()
                if any(f_clean.endswith(ext.lower()) for ext in extensions):
                    if clean_target in f_clean and not f_clean.endswith("_temp.jpg"):
                        return os.path.join(d, f)
        except Exception:
            pass

    # 5. 파일이 전혀 없을 경우에만 임시 대체 팬텀 생성
    dummy_dir = os.path.join(base_dir, "sample_xrays")
    os.makedirs(dummy_dir, exist_ok=True)
    dummy_path = os.path.join(dummy_dir, f"{target_name}_temp.jpg")
    if not os.path.exists(dummy_path):
        img = Image.new("RGB", (300, 300), color=(24, 24, 27))
        d = ImageDraw.Draw(img)
        d.text((30, 140), f"[{target_name}]", fill=(161, 161, 170))
        img.save(dummy_path)
    return dummy_path

# ---------------------------------------------------------
# 3. 사이드바 - 제어판 (모노톤 정리)
# ---------------------------------------------------------
st.sidebar.title("Pre-VERIFY 제어판")
st.sidebar.caption("🔒 원내 폐쇄망 모드 (100% 로컬 연산)")

st.sidebar.markdown("---")
st.sidebar.subheader("판독 보류(Hold) 임계치")
threshold = st.sidebar.slider("임계치 Threshold (%)", min_value=50, max_value=85, value=65, step=1)
st.sidebar.caption("일치율이 이 값 미만이면 판독이 자동 보류 상태로 잠깁니다.")

st.sidebar.markdown("---")
st.sidebar.subheader("검증 시나리오")
scenario = st.sidebar.radio(
    "시나리오 선택:",
    [
        "1. [정상 검증] 동일 환자 비교 ('1.normal' vs '1.normal')",
        "2. [환자 바뀜] 타 환자 X-ray 오유입 ('2.real' vs '2.fake')"
    ]
)

# ---------------------------------------------------------
# 4. 메인 화면 - 흉부 X-ray 비교 뷰어
# ---------------------------------------------------------
st.markdown("""
<div class="app-header">
    <h3>🩻 실시간 Pre-VERIFY 에이전트</h3>
    <p>서울아산병원 영상의학과 환자 바뀜 원천 차단 솔루션</p>
</div>
""", unsafe_allow_html=True)

# 시나리오에 따른 이미지 및 일치율 세팅
if "1." in scenario:
    path_a = find_case_image("1.normal")
    path_b = find_case_image("1.normal")
    img_a = Image.open(path_a).convert("RGB")
    img_b = Image.open(path_b).convert("RGB")
    display_score = 90.0
else:
    path_a = find_case_image("2.real")
    path_b = find_case_image("2.fake")
    img_a = Image.open(path_a).convert("RGB")
    img_b = Image.open(path_b).convert("RGB")
    display_score = 25.0

# 모바일 2열 나란히 배치
col_img1, col_img2 = st.columns(2)
with col_img1:
    st.markdown("##### 이전 영상 [A]")
    st.image(img_a, caption="검증 기준 영상", use_container_width=True)

with col_img2:
    st.markdown("##### 최근 영상 [B]")
    st.image(img_b, caption="금일 촬영 신규 영상", use_container_width=True)

# 검사 정보 표시
st.markdown(
    """
<div style="font-size: 1.05rem; font-weight: 700; margin-top: 10px; margin-bottom: 8px; color: #000000;">
    검사 정보 : <span style="color: #000000; font-size: 1.15rem; font-weight: 800;">환자 ID : A19482</span>
</div>
""",
    unsafe_allow_html=True,
)

is_hold = display_score < threshold

# ---------------------------------------------------------
# 5. AI 에이전트 판정 결과 (보류/정상 상태 컬러 안내)
# ---------------------------------------------------------
st.markdown("---")
st.subheader("실시간 AI 판정 결과")

m_col1, m_col2 = st.columns([1.1, 1.0])
with m_col1:
    st.metric(
        label="골격 일치율 (Score)",
        value=f"{display_score:.1f} %",
        delta=f"{display_score - threshold:.1f} % (기준 대비)"
    )
with m_col2:
    if is_hold:
        st.error("❌ 판독 보류 (HOLD)")
    else:
        st.success("✅ 정상 승인 (PASS)")

if is_hold:
    # 보류 상태: 적색 계열 안내
    st.markdown(f"""
    <div class="alert-hold">
        🚨 <b>[경고] 해부학적 일치율({display_score:.1f}%)이 임계치({threshold}%) 미만입니다.</b><br>
        ➔ '환자 바뀜(Mix-up)' 의심 건으로 분류되어 <b>PACS 내 판독이 [임시 보류(HOLD)]</b> 처리되었습니다.<br>
        ➔ 담당 방사선사의 재확인이 완료될 때까지 판독창 열람이 잠깁니다.
    </div>
    """, unsafe_allow_html=True)
    
    # 사유 분석
    st.markdown("""
    <div class="reason-card">
        <b>📋 AI 에이전트 해부학적 불일치 분석 사유:</b><br>
        1. <b>골격 (흉곽 구조)</b>: 양측 쇄골 주행 각도 및 늑골 궁 곡률·간격 비율 불일치 (유사도 21%)<br>
        2. <b>심장 (심비율)</b>: 종격동 대비 심장 음영 크기(CTR) 및 심첨부 형상 상이<br>
        3. <b>체형 (흉추 및 흉곽비)</b>: 흉추 중심축 기준 흉곽 좌우 종횡비가 타 환자 골격 패턴과 일치
    </div>
    """, unsafe_allow_html=True)
    
    btn_action = st.button("🔓 방사선사 육안 대조 완료 후 [보류 해제]", use_container_width=True)
    if btn_action:
        st.info("확인 완료: 방사선사 승인 로그가 기록되었으며 정상 판독열로 전송되었습니다.")
        
else:
    # 정상 상태: 녹색 계열 안내
    st.markdown(f"""
    <div class="alert-pass">
        🟢 <b>[정상] 해부학적 일치율({display_score:.1f}%)이 임계치({threshold}%)를 충족합니다.</b><br>
        ➔ 실시간 Pre-VERIFY 자동 통과: 동일 환자의 골격 해부학적 지문 일치 확인.<br>
        ➔ 영상의학과 판독 대기열로 <b>즉시 정상 전송</b>되었습니다. (단순 육안 대조 생략 가능)
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="reason-card">
        <b>📋 AI 에이전트 일치 분석 사유:</b><br>
        • <b>골격 지문 일치</b>: 흉곽 상부 쇄골·흉추 정렬 상태 및 늑골 곡률 패턴 90% 이상 일치<br>
        • <b>안정적 전송</b>: 자세/호흡량에 따른 오차 범위를 감안하더라도 동일인 고유 해부학적 구조 충족
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. 하단 PACS Worklist 실시간 연동 (모노톤 테이블)
# ---------------------------------------------------------
st.markdown("---")
st.subheader("PACS 워크리스트 연동 상태")

status_badge = "<span style='color:#EF4444; font-weight:800;'>🔒 보류 (HOLD)</span>" if is_hold else "<span style='color:#22C55E; font-weight:800;'>✓ 정상 (PASS)</span>"
pt_name = "김*산" if not is_hold else "이*현 (오유입)"

st.markdown(f"""
<div class="table-container">
    <table class="pacs-table">
        <tr>
            <th>검사번호</th>
            <th>환자번호</th>
            <th>환자명</th>
            <th>검사명</th>
            <th>일치율</th>
            <th>판독상태</th>
        </tr>
        <tr style="font-weight: 800; color: #FFFFFF;">
            <td>EX-0891</td>
            <td>A19482</td>
            <td>{pt_name}</td>
            <td>Chest PA</td>
            <td>{display_score:.1f}%</td>
            <td>{status_badge}</td>
        </tr>
        <tr>
            <td>EX-0890</td>
            <td>B99214</td>
            <td>박*우</td>
            <td>Chest PA</td>
            <td>94.2%</td>
            <td><span style='color:#22C55E; font-weight:600;'>✓ 정상</span></td>
        </tr>
        <tr>
            <td>EX-0889</td>
            <td>C58102</td>
            <td>최*영</td>
            <td>Chest AP</td>
            <td>88.7%</td>
            <td><span style='color:#22C55E; font-weight:600;'>✓ 정상</span></td>
        </tr>
    </table>
</div>
<div style="font-size:0.75rem; color:#71717A; margin-top:4px; text-align:right;">
    ※ 표를 좌우로 스크롤하여 전체 항목을 확인할 수 있습니다.
</div>
""", unsafe_allow_html=True)
