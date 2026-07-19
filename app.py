import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import re
import time
import io
from datetime import datetime, timedelta

# =================================================================
# 1. НАЛАШТУВАННЯ ТА КОНСТАНТИ
# =================================================================
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

USER_PASSWORD = "2887"  # 🔐TODO: перенести в secrets.toml

POINTS_MAP = {
    "О/С-200": 12, "О/С-300": 8, "Молнія": 10, "Укриття": 1, "Фортифікація": 1,
    "Антена": 4, "FPV": 6, "Танк": 40, "FPV Бомбер": 6, "РЛС": 50, "САУ": 30,
    "Міномет": 5, "ЛАТ": 8, "Генератор": 4, "Електросамокат": 4, "Квадроцикл": 4,
    "Мотоцикл": 4, "РЕБ": 8, "Мавік": 6, "Орлан": 40, "Шахед": 20, "ждун": 10,
    "Автомобіль": 5, "Гаубиця": 40, "ББМ": 20, "Гармата": 20, "Гербера": 20, "Зала": 20,
    "Причіп": 2, "ПОЛОНЕНИЙ": 120, "Старлінк": 4, "Винос": 8, "Мавік нічний": 10, "Розвідка": 1,
    "Склад": 5, "Артилерія": 1, "ФПВ": 6, "О/С 200": 12, "О/С 300": 8,
    "FPV бомбер": 6, "Бомбер": 6, "НРК": 4, "Ждун": 10, "Місія НРК": 70,
    "Місія НРК Л": 3.4, "Розвідка": 9, "Склад БК": 5, "Відеокамера": 4
}

MONTHS_UKR = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень"
}

CLRS = {'1аемб': '#92D050', '2аемб': '#A5A5A5', '3аемб': '#4472C4', '4аемб': '#ED7D31'}
MINE_CLR = "#7030A0"
UNIT_NAMES = ["1аемб", "2аемб", "3аемб", "4аемб"]
SKIP_TARGETS = ["", "-", "•", ".", "Ціль"]

# =================================================================
# 2. ДОПОМІЖНІ ФУНКЦІЇ
# =================================================================
def get_base64(path):
    """Конвертує файл у base64 рядок."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None


def to_native(val):
    """Безпечно конвертує значення у float."""
    try:
        s = str(val).replace(',', '.').strip()
        return float(s) if s not in ["", "-", ".", "•"] else 0.0
    except Exception:
        return 0.0


def get_urazh_data(qty, target, status):
    """Розраховує бали та верифіковану кількість для стандартної цілі."""
    t_clean = str(target).strip()
    unit_p = POINTS_MAP.get(t_clean, 0)
    st_clean = str(status).lower().strip()
    if st_clean == "верифіковано":
        return qty * unit_p, qty
    return 0.0, 0.0


def extract_reason(st_raw):
    """Витягує причину/опис із рядка статусу."""
    if ":" in st_raw:
        return st_raw.split(":", 1)[1].strip()
    elif "(" in st_raw:
        return st_raw.split("(", 1)[1].replace(")", "").strip()
    return ""


def parse_mining_row(qty, st_raw, b_name, l_dt):
    """Парсить рядок 'Мінування' → повертає dict з розрахованими полями."""
    reason = ""
    st_clean = st_raw.lower().strip()

    if "не вериф" in st_clean:
        match = re.search(r'(\d+)', st_clean)
        qun_m = float(match.group(1)) if match else qty
        qv_m = max(0.0, qty - qun_m)
        qp_m = 0.0
        reason = extract_reason(st_raw)
    elif st_clean == "верифіковано":
        qv_m, qun_m, qp_m = qty, 0.0, 0.0
    else:
        qv_m, qun_m, qp_m = 0.0, 0.0, qty

    return {
        "D": l_dt, "B": b_name, "T": "Мінування", "PU": 0.0, "PM": qv_m,
        "QT": qty, "QV": qv_m, "QUN": qun_m, "QPE": qp_m, "Reason": reason
    }


def parse_target_row(qty, target, st_raw, b_name, l_dt):
    """Парсить рядок стандартної цілі ураження → повертає dict."""
    st_clean = st_raw.lower().strip()
    reason = ""
    vp, vq = get_urazh_data(qty, target, st_raw)
    q_ver = vq

    if q_ver > 0:
        q_unver, q_pend = 0.0, 0.0
    elif "не вериф" in st_clean:
        q_unver, q_pend = qty, 0.0
        reason = extract_reason(st_raw)
    else:
        q_unver, q_pend = 0.0, qty

    return {
        "D": l_dt, "B": b_name, "T": target, "PU": vp, "PM": 0.0,
        "QT": qty, "QV": q_ver, "QUN": q_unver, "QPE": q_pend, "Reason": reason
    }


def generate_month_options(count=6):
    """Генерує список останніх N місяців у форматі 'MM.YYYY'."""
    now = datetime.now()
    months = []
    for i in range(count):
        d = now.replace(day=1) - pd.DateOffset(months=i)
        months.append(f"{d.month:02d}.{d.year}")
    return months


# =================================================================
# 3. ЦЕНТРАЛІЗОВАНЕ ЗЧИТУВАННЯ ДАНИХ (кешоване)
# =================================================================
@st.cache_data(ttl=300, show_spinner="📡 Завантаження даних з бази...")
def load_all_battalion_data(prefix, cur_m, cur_y):
    """
    Один виклик зчитування для всіх підрозділів за місяць.
    Повертає відфільтрований список записів.
    Використовується всіма 3 вкладками.
    """
    conn = st.connection("gsheets", type=GSheetsConnection)
    all_results = []

    for b_name in UNIT_NAMES:
        sheet_name = f"{prefix}.{b_name}"
        try:
            df_unit = conn.read(worksheet=sheet_name, ttl=300, header=None).fillna("")
        except Exception as e:
            try:
                df_unit = conn.read(worksheet=b_name, ttl=300, header=None).fillna("")
            except Exception as e2:
                st.warning(f"⚠️ Не вдалося зчитати аркуш '{sheet_name}': {e2}")
                continue

        try:
            u_rows = df_unit.values.tolist()
            l_dt = None

            for r in u_rows[1:]:
                # --- Відстеження дати (carry-forward) ---
                if str(r[0]).strip() != "":
                    dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                    if pd.notnull(dt):
                        l_dt = dt
                if not l_dt:
                    continue

                target = str(r[1]).strip()
                if target in SKIP_TARGETS:
                    continue

                qty = to_native(r[2])
                st_raw = str(r[3]).strip()

                # --- А. Мінування (окремий рядок) ---
                if target == "Мінування":
                    all_results.append(parse_mining_row(qty, st_raw, b_name, l_dt))

                # --- Б. Стандартні цілі ураження ---
                else:
                    all_results.append(parse_target_row(qty, target, st_raw, b_name, l_dt))

                # --- В. Старий формат: мін у 5-й колонці ---
                if target != "Мінування" and len(r) > 4:
                    v_mine = to_native(r[4])
                    if v_mine > 0:
                        all_results.append({
                            "D": l_dt, "B": b_name, "T": "Мінування", "PU": 0.0, "PM": v_mine,
                            "QT": v_mine, "QV": v_mine, "QUN": 0.0, "QPE": 0.0, "Reason": ""
                        })

        except Exception as e:
            st.warning(f"⚠️ Помилка обробки даних {b_name}: {e}")
            continue

    # Фільтрація по місяцю та році — один раз
    filtered = [r for r in all_results if r["D"].month == cur_m and r["D"].year == cur_y]
    return filtered


@st.cache_data(ttl=600, show_spinner="📡 Завантаження тренду за місяці...")
def load_trend_data(month_options):
    """Завантажує зведені дані за кілька місяців для графіків трендів."""
    trend = []
    for m_option in month_options:
        parts = m_option.split(".")
        prefix, cur_m, cur_y = parts[0], int(parts[0]), int(parts[1])
        data = load_all_battalion_data(prefix, cur_m, cur_y)
        if not data:
            continue

        for b_name in UNIT_NAMES:
            b_res = [r for r in data if r["B"] == b_name]
            trend.append({
                "Місяць": m_option,
                "Підрозділ": b_name,
                "Бали": int(sum(r["PU"] + r["PM"] for r in b_res)),
                "Міни (вер.)": int(sum(r["QV"] for r in b_res if r["T"] == "Мінування")),
                "Ураження (шт)": int(sum(r["QT"] for r in b_res if r["T"] != "Мінування")),
            })
    return pd.DataFrame(trend)


def style_report_cells(val, column_name):
    """Стилізує клітинки таблиці звіту залежно від колонки."""
    if isinstance(val, (int, float)) and val == 0:
        return 'color: #555555; font-weight: normal;'
    if column_name == "Верифіковано (шт)":
        return 'color: #2ECC71; font-weight: bold;'
    elif column_name == "Не верифіковано (шт)":
        return 'color: #E74C3C; font-weight: bold;'
    elif column_name == "На верифікації (шт)":
        return 'color: #95A5A6; font-weight: bold;'
    return 'color: white;'


def highlight_max_battalion(row):
    """Підсвічує максимальне значення в рядку pivot-таблиці."""
    styles = [''] * len(row)
    bat_values = row[UNIT_NAMES]
    max_val = bat_values.max()
    if max_val <= 0:
        return styles
    for col_name in UNIT_NAMES:
        if row[col_name] == max_val:
            idx = row.index.get_loc(col_name)
            styles[idx] = 'background-color: #2E7D32; color: #FFFFFF; font-weight: bold; border-radius: 4px;'
    return styles


# =================================================================
# 4. АНІМАЦІЙНА ЗАСТАВКА ТА ЕКРАН ВХОДУ
# =================================================================
if "intro_shown" not in st.session_state:
    st.session_state["intro_shown"] = False

if not st.session_state["intro_shown"]:
    logo = get_base64("logo.png")
    st.markdown("""
        <style>
        .boot-screen-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background-color: #0E1117; z-index: 999999;
            display: flex; flex-direction: column; align-items: center; justify-content: center;
            font-family: "Inter", sans-serif; color: #ffd700; text-align: center;
        }
        .radar-pulse {
            width: 150px; height: 150px; border-radius: 50%;
            background: rgba(255, 215, 0, 0.03); border: 2px solid #ffd700;
            display: flex; align-items: center; justify-content: center;
            margin-bottom: 30px; animation: pulseRadar 6s infinite ease-in-out;
        }
        @keyframes pulseRadar {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.4); opacity: 0.7; }
            70% { transform: scale(1.05); box-shadow: 0 0 0 25px rgba(255, 215, 0, 0); opacity: 1; }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 215, 0, 0); opacity: 0.7; }
        }
        .boot-text {
            font-size: 13px; font-weight: 800; letter-spacing: 4px; text-transform: uppercase;
            animation: blinkText 2s infinite; margin: 0; padding: 0 20px;
        }
        @keyframes blinkText { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
        [data-testid="stHeader"], [data-testid="stSidebar"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    html_content = '<div class="boot-screen-overlay">'
    if logo:
        html_content += f'<div class="radar-pulse"><img src="data:image/png;base64,{logo}" style="max-width:95px; border-radius:15px;"></div>'
    else:
        html_content += '<div class="radar-pulse" style="font-size:40px;">🛡️</div>'
    html_content += '<p class="boot-text">СИНХРОНІЗАЦІЯ З БАЗОЮ ДАНИХ... ЗАВАНТАЖЕННЯ СИСТЕМИ</p>'
    html_content += '</div>'
    st.markdown(html_content, unsafe_allow_html=True)

    time.sleep(2.5)
    st.session_state["intro_shown"] = True
    st.rerun()

if "password_correct" not in st.session_state:
    logo = get_base64("logo.png")
    st.markdown("""
        <style>
        .stApp { background-color: #0E1117; }
        .fade-in-element { animation: fadeInSmooth 2s ease-out forwards; }
        @keyframes fadeInSmooth {
            from { opacity: 0; transform: translateY(15px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
    """, unsafe_allow_html=True)

    _, col_c, _ = st.columns([1.2, 1.5, 1.2])
    with col_c:
        st.write("<br><br>", unsafe_allow_html=True)
        if logo:
            st.markdown(f"<div class='fade-in-element' style='text-align:center;'><img src='data:image/png;base64,{logo}' style='max-width:210px; border-radius:15px;'></div>", unsafe_allow_html=True)

        st.markdown("""
            <div class="fade-in-element" style='background:rgba(255,255,255,0.04); padding: 35px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.15); text-align: center; font-family: "Inter", sans-serif; margin-top: 15px;'>
                <h2 style='color:white; margin:0;'>1 аемб</h2>
                <p style='color:#ffd700; font-size: 16px; font-weight: 600; margin-bottom: 20px;'>77 ОАЕМБр • ДШВ ЗСУ </p>
                <hr style='border:0; border-top: 1px solid rgba(255,255,255,0.1);'>
                <p style='color:white; font-size: 13px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-top: 15px;'>СИТУАЦІЙНИЙ ЦЕНТР БАТАЛЬЙОНУ</p>
            </div>
        """, unsafe_allow_html=True)

        pwd = st.text_input("ВВЕДІТЬ КОД ДОСТУПУ:", type="password")
        if st.button("УВІЙТИ В СИСТЕМУ") and pwd == USER_PASSWORD:
            st.session_state["password_correct"] = True
            st.rerun()
    st.stop()

# =================================================================
# 5. ГЛОБАЛЬНЕ СТИЛІЗУВАННЯ (з мобільною адаптивністю)
# =================================================================
bg = get_base64("background.jpg")
bg_style = f'background-image: url("data:image/png;base64,{bg}");' if bg else 'background-color: #0E1117;'
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp {{ {bg_style} background-size: cover; background-position: center; background-attachment: fixed; font-family: "Inter", sans-serif; }}
    [data-testid="stTable"], .stDataFrame, [data-testid="stDataFrame"] {{ background-color: transparent !important; }}
    table {{ background-color: rgba(255,255,255,0.05) !important; color: white !important; border-radius: 10px; width: 100%; }}
    thead tr th {{ background-color: rgba(0,0,0,0.6) !important; color: #ffd700 !important; font-weight: 800 !important; border-bottom: 1px solid rgba(255,215,0,0.2) !important; }}
    tbody tr td {{ background-color: transparent !important; color: white !important; border-bottom: 1px solid rgba(255,255,255,0.05) !important; }}
    [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}
    [data-testid="stMetricValue"] {{ color: #ffd700 !important; font-size: 34px !important; font-weight: 800 !important; }}

    /* Мобільна адаптивність */
    @media (max-width: 768px) {{
        .stMetric {{ font-size: 0.85rem !important; }}
        [data-testid="stMetricValue"] {{ font-size: 24px !important; }}
        .support-card {{ font-size: 9px !important; bottom: 5px !important; left: 5px !important; }}
        h2 {{ font-size: 1.2rem !important; }}
        h3 {{ font-size: 1.0rem !important; }}
    }}
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 6. САЙДБАР: ВИБІР МІСЯЦЯ + ОНОВЛЕННЯ
# =================================================================
st.sidebar.markdown("### ⚙️ ПАНЕЛЬ КЕРУВАННЯ")

month_options = generate_month_options(6)
sel_month = st.sidebar.selectbox("📅 ОБЕРІТЬ МІСЯЦЬ:", month_options, index=0)
prefix = sel_month.split(".")[0]
cur_m = int(prefix)
cur_y = int(sel_month.split(".")[1])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# Завантаження даних (один виклик — кешується)
filtered_data = load_all_battalion_data(prefix, cur_m, cur_y)

# Розподіл за категоріями (один джерело даних)
mine_data = [r for r in filtered_data if r["T"] == "Мінування"]
urazh_data = [r for r in filtered_data if r["T"] != "Мінування"]

# =================================================================
# 7. ОСНОВНИЙ КОНТЕНТ — TABS
# =================================================================
st.markdown(f"<h2 style='text-align:center; color:#ffd700; text-shadow: 2px 2px 8px rgba(0,0,0,0.95); font-weight: 800; letter-spacing: 1px;'>⚔️ СИТУАЦІЙНИЙ ЦЕНТР БАТАЛЬЙОНУ — {sel_month} </h2>", unsafe_allow_html=True)

tab_reports, tab_mining, tab_urazh = st.tabs(["⚔️ Бригадні звіти", "🧨 Мінування", "🔥 Ураження"])

# =================================================================
# 7A. ВКЛАДКА 1: БРИГАДНІ ЗВІТИ
# =================================================================
with tab_reports:
    # --- Загальні метрики по всьому батальйону ---
    total_pts_all = int(sum(r["PU"] + r["PM"] for r in filtered_data))
    total_v_all = int(sum(r["QV"] for r in filtered_data))
    total_unv_all = int(sum(r["QUN"] for r in filtered_data))
    total_mines_all = int(sum(r["QV"] for r in mine_data))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🏆 ВСЬОГО БАЛІВ", total_pts_all)
    m2.metric("✅ ВЕРИФІКОВАНО", total_v_all)
    m3.metric("❌ НЕ ВЕРИФІКОВАНО", total_unv_all)
    m4.metric("🧨 МІН ПОСТАВЛЕНО", total_mines_all)

    st.markdown("---")

    # --- 🏆 Порівняльний рейтинг підрозділів ---
    st.markdown("### 🏆 Порівняльний рейтинг підрозділів")
    rating_data = []
    for b in UNIT_NAMES:
        b_res = [r for r in filtered_data if r["B"] == b]
        b_pts = int(sum(r["PU"] + r["PM"] for r in b_res))
        b_mines = int(sum(r["QV"] for r in b_res if r["T"] == "Мінування"))
        b_targets = int(sum(r["QV"] for r in b_res if r["T"] != "Мінування"))
        rating_data.append({
            "Підрозділ": b, "Бали": b_pts, "Міни (вер.)": b_mines, "Ураження (вер.)": b_targets
        })

    df_rating = pd.DataFrame(rating_data).sort_values("Бали", ascending=False)
    styled_rating = df_rating.style.bar(subset=["Бали"], color='#ffd700').hide(axis="index")
    st.dataframe(styled_rating, use_container_width=True)

    # --- 📊 Бали по підрозділах (стовпчикова діаграма) ---
    fig_rating = go.Figure(go.Bar(
        x=df_rating["Підрозділ"], y=df_rating["Бали"],
        marker_color=[CLRS.get(b, '#ffd700') for b in df_rating["Підрозділ"]],
        text=df_rating["Бали"], textposition='outside',
        textfont=dict(color='#ffd700', size=16, family="Inter")
    ))
    fig_rating.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color="white", showlegend=False, height=350,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig_rating, use_container_width=True)

    st.markdown("---")

    # --- Деталізація по підрозділу ---
    sel_b = st.selectbox("📋 ДЕТАЛІЗАЦІЯ ПІДРОЗДІЛУ:", UNIT_NAMES)
    u_res = [r for r in filtered_data if r["B"] == sel_b]
    u_total_pts = int(sum(r["PU"] + r["PM"] for r in u_res))

    # Метрики підрозділу
    u_v = int(sum(r["QV"] for r in u_res))
    u_unv = int(sum(r["QUN"] for r in u_res))
    u_pe = int(sum(r["QPE"] for r in u_res))

    um1, um2, um3, um4 = st.columns(4)
    um1.metric(f"Бали ({sel_b})", u_total_pts)
    um2.metric("Верифіковано", u_v)
    um3.metric("Не верифіковано", u_unv)
    um4.metric("На верифікації", u_pe)

    st.markdown("#### 📋 Детальна таблиця по типах цілей:")
    u_table = []
    for t in sorted(list(set([r["T"] for r in u_res]))):
        u_table.append({
            "Тип цілі": t,
            "Всього (шт)": int(sum(r["QT"] for r in u_res if r["T"] == t)),
            "Верифіковано (шт)": int(sum(r["QV"] for r in u_res if r["T"] == t)),
            "Не верифіковано (шт)": int(sum(r["QUN"] for r in u_res if r["T"] == t)),
            "На верифікації (шт)": int(sum(r["QPE"] for r in u_res if r["T"] == t)),
            "Бали": int(sum(r["PU"] + r["PM"] for r in u_res if r["T"] == t))
        })

    if u_table:
        df_report = pd.DataFrame(u_table).sort_values(by="Бали", ascending=False)

        styled_df = df_report.style.map(
            lambda v: style_report_cells(v, "Верифіковано (шт)"), subset=["Верифіковано (шт)"]
        ).map(
            lambda v: style_report_cells(v, "Не верифіковано (шт)"), subset=["Не верифіковано (шт)"]
        ).map(
            lambda v: style_report_cells(v, "На верифікації (шт)"), subset=["На верифікації (шт)"]
        ).map(
            lambda v: 'color: #555555;' if (isinstance(v, (int, float)) and v == 0) else 'color: white;',
            subset=["Всього (шт)", "Бали"]
        ).hide(axis="index")

        st.dataframe(styled_df, use_container_width=True)

        # --- 📥 Експорт CSV ---
        csv_buffer = io.StringIO()
        df_report.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 Експорт звіту (CSV)",
            data=csv_buffer.getvalue().encode('utf-8-sig'),
            file_name=f"звіт_{sel_b}_{sel_month}.csv",
            mime="text/csv"
        )

    # --- 📈 Динаміка балів по днях ---
    if u_res:
        df_daily = pd.DataFrame([
            {"Дата": r["D"], "Бали": r["PU"] + r["PM"]}
            for r in u_res
        ])
        df_daily = df_daily.groupby("Дата").sum().reset_index().sort_values("Дата")

        fig_daily = go.Figure(go.Scatter(
            x=df_daily["Дата"], y=df_daily["Бали"],
            fill='tozeroy', mode='lines+markers',
            line=dict(color=CLRS.get(sel_b, '#ffd700'), width=3),
            marker=dict(size=8),
            name='Бали по днях'
        ))
        fig_daily.update_layout(
            xaxis_title="Дата", yaxis_title="Бали",
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color="white", height=320,
            margin=dict(l=20, r=20, t=30, b=20)
        )
        fig_daily.update_xaxes(gridcolor='rgba(255,255,255,0.1)')
        fig_daily.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
        st.plotly_chart(fig_daily, use_container_width=True)

    # --- 🔍 Деталі не верифікованих об'єктів ---
    unverified_records = [r for r in u_res if r["QUN"] > 0]
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🔍 Переглянути деталі та причини щодо не верифікованих об'єктів"):
        if unverified_records:
            has_reasons = False
            for item in sorted(unverified_records, key=lambda x: x["D"]):
                date_str = item["D"].strftime("%d.%m.%Y")
                if item["Reason"]:
                    has_reasons = True
                    st.markdown(f"• **{date_str}** — _{item['T']}_ ({int(item['QUN'])} шт) — <span style='color:#E74C3C; font-weight:600;'>Причина: {item['Reason']}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(f"• **{date_str}** — _{item['T']}_ ({int(item['QUN'])} шт) — <span style='color:#95A5A6;'>Причину не вказано в Google Sheets</span>", unsafe_allow_html=True)
            if not has_reasons:
                st.info("ℹ️ У таблиці знайдено не верифіковані об'єкти, але жодного опису чи причини для них не додано.")
        else:
            st.success("✅ У цього підрозділу за обраний період немає жодного не верифікованого об'єкта.")

# =================================================================
# 7B. ВКЛАДКА 2: МІНУВАННЯ
# =================================================================
with tab_mining:
    st.markdown(f"<h3 style='text-align:center; color:#ffd700; text-shadow: 2px 2px 8px rgba(0,0,0,0.95);'>🧨 МОНІТОРИНГ МІНУВАНЬ ЗА {sel_month}</h3>", unsafe_allow_html=True)

    # --- Метрики ---
    mine_v_total = int(sum(r["QV"] for r in mine_data))
    mine_unv_total = int(sum(r["QUN"] for r in mine_data))
    mine_pe_total = int(sum(r["QPE"] for r in mine_data))

    mm1, mm2, mm3 = st.columns(3)
    mm1.metric("✅ ВЕРИФІКОВАНО (сумарно)", mine_v_total)
    mm2.metric("❌ НЕ ВЕРИФІКОВАНО", mine_unv_total)
    mm3.metric("⏳ НА ВЕРИФІКАЦІЇ", mine_pe_total)

    # --- Дані по підрозділах ---
    mine_chart_data = []
    for b_name in UNIT_NAMES:
        b_mine = [r for r in mine_data if r["B"] == b_name]
        v_sum = sum(r["QV"] for r in b_mine)
        unv_sum = sum(r["QUN"] for r in b_mine)
        mine_chart_data.append({"Підрозділ": b_name, "Верифіковано": v_sum, "Не верифіковано": unv_sum})

    df_g = pd.DataFrame(mine_chart_data)

    # --- Стовпчиковий графік ---
    fm = go.Figure()
    fm.add_trace(go.Bar(
        x=df_g["Підрозділ"], y=df_g["Верифіковано"],
        name='Верифіковано', marker_color='#2E7D32',
        text=df_g["Верифіковано"].astype(int), textposition='outside'
    ))
    fm.add_trace(go.Bar(
        x=df_g["Підрозділ"], y=df_g["Не верифіковано"],
        name='Не верифіковано', marker_color='#CC0000',
        text=df_g["Не верифіковано"].astype(int), textposition='outside'
    ))
    fm.update_layout(
        barmode='stack', paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)', font_color="white",
        height=400, margin=dict(l=20, r=20, t=20, b=20)
    )
    fm.update_xaxes(gridcolor='rgba(255,255,255,0.1)')
    fm.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
    st.plotly_chart(fm, use_container_width=True)

    # --- Детальна таблиця ---
    st.markdown("#### 📋 Детальна таблиця по підрозділах:")
    mine_table = []
    for b_name in UNIT_NAMES:
        b_mine = [r for r in mine_data if r["B"] == b_name]
        mine_table.append({
            "Підрозділ": b_name,
            "Верифіковано": int(sum(r["QV"] for r in b_mine)),
            "Не верифіковано": int(sum(r["QUN"] for r in b_mine)),
            "На верифікації": int(sum(r["QPE"] for r in b_mine)),
            "Всього": int(sum(r["QT"] for r in b_mine))
        })
    df_mine_tbl = pd.DataFrame(mine_table)
    st.dataframe(df_mine_tbl.style.hide(axis="index"), use_container_width=True)

    # --- 📈 Тренд по місяцях ---
    st.markdown("---")
    st.markdown("#### 📈 Тренд мінування по місяцях:")
    df_trend = load_trend_data(month_options)
    if not df_trend.empty:
        df_mine_trend = df_trend[df_trend["Місяць"].isin(month_options)]
        fig_trend = go.Figure()
        for b_name in UNIT_NAMES:
            b_trend = df_mine_trend[df_mine_trend["Підрозділ"] == b_name].sort_values("Місяць")
            fig_trend.add_trace(go.Scatter(
                x=b_trend["Місяць"], y=b_trend["Міни (вер.)"],
                mode='lines+markers+text', name=b_name,
                line=dict(color=CLRS.get(b_name, '#ffd700'), width=3),
                marker=dict(size=10),
                text=b_trend["Міни (вер.)"], textposition='top center'
            ))
        fig_trend.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color="white", height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_trend.update_xaxes(gridcolor='rgba(255,255,255,0.1)')
        fig_trend.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.info("ℹ️ Недостатньо даних для побудови тренду.")

# =================================================================
# 7C. ВКЛАДКА 3: УРАЖЕННЯ
# =================================================================
with tab_urazh:
    st.markdown(f"<h3 style='text-align:center; color:#ffd700; text-shadow: 2px 2px 8px rgba(0,0,0,0.95);'>🔥 МОНІТОРИНГ УРАЖЕНЬ ЗА {sel_month}</h3>", unsafe_allow_html=True)

    # --- Метрики ---
    urazh_total = int(sum(r["QT"] for r in urazh_data if r["QT"] > 0))
    urazh_pts = int(sum(r["PU"] for r in urazh_data))
    urazh_v = int(sum(r["QV"] for r in urazh_data))
    urazh_targets_count = len(set(r["T"] for r in urazh_data))

    um1, um2, um3, um4 = st.columns(4)
    um1.metric("🎯 ВСЬОГО УРАЖЕНЬ", urazh_total)
    um2.metric("🏆 БАЛІВ ЗА УРАЖЕННЯ", urazh_pts)
    um3.metric("✅ ВЕРИФІКОВАНО", urazh_v)
    um4.metric("📊 ТИПІВ ЦІЛЕЙ", urazh_targets_count)

    if urazh_data:
        df_urazh = pd.DataFrame(urazh_data)

        c_pie, c_pivot = st.columns([1, 2])

        # --- 📊 Кругова діаграма топ-10 цілей ---
        with c_pie:
            st.markdown("##### 📊 Топ-10 цілей за кількістю:")
            target_counts = df_urazh.groupby("Target")["Qty"].sum().sort_values(ascending=False).head(10)

            fig_pie = go.Figure(go.Pie(
                labels=target_counts.index, values=target_counts.values,
                hole=0.4,
                marker_colors=['#ffd700', '#92D050', '#4472C4', '#ED7D31', '#7030A0',
                               '#A5A5A5', '#FFC000', '#5B9BD5', '#FF6B6B', '#9B59B6']
            ))
            fig_pie.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                font_color="white", height=350,
                margin=dict(l=10, r=10, t=10, b=10),
                showlegend=True,
                legend=dict(font=dict(size=10), orientation="v")
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # --- Pivot-таблиця ---
        with c_pivot:
            st.markdown("##### 📋 Порівняльна таблиця по підрозділах:")
            pivot_df = df_urazh.pivot_table(index="Target", columns="Battalion", values="Qty", aggfunc="sum")
            for b in UNIT_NAMES:
                if b not in pivot_df.columns:
                    pivot_df[b] = 0.0
            pivot_df = pivot_df[UNIT_NAMES].fillna(0).astype(int)
            pivot_df.index.name = "Об'єкт ураження"
            pivot_df_final = pivot_df.reset_index()

            styled_pivot = pivot_df_final.style.apply(highlight_max_battalion, axis=1).hide(axis="index")
            st.dataframe(styled_pivot, use_container_width=True)

        st.markdown("---")

        # --- 📅 Активність по днях тижня ---
        st.markdown("##### 📅 Активність по днях тижня:")
        df_urazh["DayName"] = df_urazh["D"].dt.day_name()
        # ua day names mapping
        day_map = {
            "Monday": "Понеділок", "Tuesday": "Вівторок", "Wednesday": "Середа",
            "Thursday": "Четвер", "Friday": "П'ятниця", "Saturday": "Субота", "Sunday": "Неділя"
        }
        df_urazh["День"] = df_urazh["DayName"].map(day_map)
        day_order = ["Понеділок", "Вівторок", "Середа", "Четвер", "П'ятниця", "Субота", "Неділя"]

        # Heat-інтенсивність по підрозділах і днях
        heat_data = df_urazh.groupby(["День", "Battalion"])["Qty"].sum().reset_index()
        heat_pivot = heat_data.pivot(index="День", columns="Battalion", values="Qty").fillna(0).astype(int)
        for b in UNIT_NAMES:
            if b not in heat_pivot.columns:
                heat_pivot[b] = 0
        heat_pivot = heat_pivot[UNIT_NAMES].reindex(day_order)

        fig_heat = go.Figure(go.Heatmap(
            z=heat_pivot.values,
            x=heat_pivot.columns.tolist(),
            y=heat_pivot.index.tolist(),
            colorscale=[[0, '#0E1117'], [0.5, '#ED7D31'], [1, '#ffd700']],
            text=heat_pivot.values, texttemplate="%{text}",
            textfont=dict(color="white", size=14)
        ))
        fig_heat.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font_color="white", height=300,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        st.markdown("---")

        # --- 📈 Тренд уражень по місяцях ---
        st.markdown("##### 📈 Тренд уражень по місяцях:")
        df_trend = load_trend_data(month_options)
        if not df_trend.empty:
            df_ur_trend = df_trend[df_trend["Місяць"].isin(month_options)]
            fig_utrend = go.Figure()
            for b_name in UNIT_NAMES:
                b_trend = df_ur_trend[df_ur_trend["Підрозділ"] == b_name].sort_values("Місяць")
                fig_utrend.add_trace(go.Scatter(
                    x=b_trend["Місяць"], y=b_trend["Ураження (шт)"],
                    mode='lines+markers+text', name=b_name,
                    line=dict(color=CLRS.get(b_name, '#ffd700'), width=3),
                    marker=dict(size=10),
                    text=b_trend["Ураження (шт)"], textposition='top center'
                ))
            fig_utrend.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color="white", height=350,
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig_utrend.update_xaxes(gridcolor='rgba(255,255,255,0.1)')
            fig_utrend.update_yaxes(gridcolor='rgba(255,255,255,0.1)')
            st.plotly_chart(fig_utrend, use_container_width=True)
        else:
            st.info("ℹ️ Недостатньо даних для побудови тренду.")
    else:
        st.info(f"ℹ️ Немає знайдених даних про ураження за період {sel_month}.")

# =================================================================
# 8. БЛОК ТЕХНІЧНОЇ ПІДТРИМКИ
# =================================================================
st.markdown("""
    <style>
    .support-card {
        position: fixed; bottom: 15px; left: 15px;
        background-color: rgba(14, 17, 23, 0.90);
        padding: 8px 12px; border-radius: 8px;
        border: 1px solid rgba(255, 215, 0, 0.2);
        z-index: 999999; font-family: "Inter", sans-serif;
        text-align: left; box-shadow: 0px 4px 10px rgba(0,0,0,0.6);
        backdrop-filter: blur(5px); transition: all 0.3s ease;
    }
    .support-card:hover {
        border-color: rgba(255, 215, 0, 0.5);
        background-color: rgba(14, 17, 23, 0.98);
    }
    .support-title { margin: 0 0 4px 0; font-size: 10px; font-weight: 800; letter-spacing: 0.5px; color: #ffd700; text-transform: uppercase; }
    .support-text { margin: 1px 0; font-size: 11px; color: #e0e0e0; }
    .support-label { color: #888888; font-size: 10px; font-weight: 600; }
    </style>
    <div class="support-card">
        <p class="support-title">⚙️ ТЕХ. ДОПОМОГА</p>
        <p class="support-text"><span class="support-label">WhatsApp:</span> +380 67 485 95 90</p>
        <p class="support-text"><span class="support-label">Delta:</span> Usignolo</p>
    </div>
""", unsafe_allow_html=True)
