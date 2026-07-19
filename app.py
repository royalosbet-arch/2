import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import base64
import re
import time
import calendar
from datetime import datetime

# =================================================================
# 1. НАЛАШТУВАННЯ ТА КОНСТАНТИ
# =================================================================
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

USER_PASSWORD = "2887"

# Виправлений словник — без дублікатів, з нормалізацією
POINTS_MAP = {
    "О/С-200": 12, "О/С-300": 8, "О/С 200": 12, "О/С 300": 8,
    "Молнія": 10, "Укриття": 1, "Фортифікація": 1,
    "Антена": 4, "FPV": 6, "Танк": 40, "FPV Бомбер": 6, "FPV бомбер": 6, "Бомбер": 6,
    "РЛС": 50, "САУ": 30, "Міномет": 5, "ЛАТ": 8, "Генератор": 4,
    "Електросамокат": 4, "Квадроцикл": 4, "Мотоцикл": 4, "РЕБ": 8,
    "Мавік": 6, "Мавк": 6,
    "Орлан": 40, "Шахед": 20, "Ждун": 10, "ждун": 10,
    "Автомобіль": 5, "Гаубиця": 40, "ББМ": 20, "Гармата": 20,
    "Гербера": 20, "Зала": 20, "Причіп": 2, "ПОЛОНЕНИЙ": 120,
    "Старлінк": 4, "Винос": 8, "Мавік нічний": 10, "Розвідка": 9,
    "Склад": 5, "Склад БК": 5, "Артилерія": 1, "ФПВ": 6,
    "НРК": 4, "Місія НРК": 70, "Місія НРК Л": 3.4,
    "Відеокамера": 4,
}

MONTHS_UKR = {1:"Січень", 2:"Лютий", 3:"Березень", 4:"Квітень", 5:"Травень", 6:"Червень", 7:"Липень", 8:"Серпень", 9:"Вересень", 10:"Жовтень", 11:"Листопад", 12:"Грудень"}
CLRS = {'1аемб': '#92D050', '2аемб': '#A5A5A5', '3аемб': '#4472C4', '4аемб': '#ED7D31'}

# Твій список місяців (рік 2026 відповідає даним у Google Sheets)
AVAILABLE_MONTHS = ["07.2026", "06.2026", "05.2026", "04.2026"]

# =================================================================
# 2. ДОПОМІЖНІ ФУНКЦІЇ
# =================================================================
def get_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

def to_native(val):
    try:
        s = str(val).replace(',', '.').strip()
        return float(s) if s not in ["", "-", ".", "•"] else 0.0
    except Exception:
        return 0.0

def get_urazh_data(qty, target, status):
    t_clean = str(target).strip()
    t_norm = t_clean.replace("  ", " ")
    unit_p = POINTS_MAP.get(t_norm, 0)
    if unit_p == 0:
        lower_map = {k.lower(): v for k, v in POINTS_MAP.items()}
        unit_p = lower_map.get(t_norm.lower(), 0)
    st_clean = str(status).lower().strip()
    if st_clean == "верифіковано":
        return qty * unit_p, qty
    return 0.0, 0.0

# =================================================================
# ЄДИНІ ФУНКЦІЇ ПАРСИНГУ ДАНИХ
# =================================================================
def parse_battalion_data(conn, unit_names, prefix, cur_m, cur_y):
    all_results = []
    validation_issues = []

    for b_name in unit_names:
        sheet_name = f"{prefix}.{b_name}"
        df_unit = None

        try:
            df_unit = conn.read(worksheet=sheet_name, ttl=300, header=None).fillna("")
        except Exception:
            try:
                df_unit = conn.read(worksheet=b_name, ttl=300, header=None).fillna("")
            except Exception:
                continue

        try:
            u_rows = df_unit.values.tolist()
            l_dt = None

            for r_idx, r in enumerate(u_rows[1:], start=2):
                if str(r[0]).strip() != "":
                    dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                    if pd.notnull(dt):
                        l_dt = dt
                if not l_dt:
                    continue

                target = str(r[1]).strip()
                if target in ["", "-", "•", ".", "Ціль"]:
                    continue

                qty = to_native(r[2])
                st_raw = str(r[3]).strip()
                st_clean = st_raw.lower().strip()
                reason = ""

                if target != "Мінування":
                    t_norm = target.replace("  ", " ")
                    known = t_norm in POINTS_MAP or t_norm.lower() in {k.lower() for k in POINTS_MAP}
                    if not known and qty > 0:
                        validation_issues.append({
                            "Підрозділ": b_name,
                            "Рядок": r_idx,
                            "Ціль": target,
                            "Дата": l_dt.strftime("%d.%m.%Y") if l_dt else "?",
                            "Проблема": "Невідомий тип цілі — 0 балів"
                        })

                if target == "Мінування":
                    if "не вериф" in st_clean:
                        match = re.search(r'(\d+)', st_clean)
                        qun_m = float(match.group(1)) if match else qty
                        qv_m = max(0.0, qty - qun_m)
                        qp_m = 0.0
                        if ":" in st_raw:
                            reason = st_raw.split(":", 1)[1].strip()
                        elif "(" in st_raw:
                            reason = st_raw.split("(", 1)[1].replace(")", "").strip()
                    elif st_clean == "верифіковано":
                        qv_m, qun_m, qp_m = qty, 0.0, 0.0
                    else:
                        qv_m, qun_m, qp_m = 0.0, 0.0, qty

                    all_results.append({
                        "D": l_dt, "B": b_name, "T": "Мінування", "PU": 0.0, "PM": qv_m,
                        "QT": qty, "QV": qv_m, "QUN": qun_m, "QPE": qp_m, "Reason": reason
                    })
                else:
                    vp, vq = get_urazh_data(qty, target, st_raw)
                    q_ver = vq

                    if q_ver > 0:
                        q_unver, q_pend = 0.0, 0.0
                    elif "не вериф" in st_clean:
                        q_unver, q_pend = qty, 0.0
                        if ":" in st_raw:
                            reason = st_raw.split(":", 1)[1].strip()
                        elif "(" in st_raw:
                            reason = st_raw.split("(", 1)[1].replace(")", "").strip()
                    else:
                        q_unver, q_pend = 0.0, qty

                    all_results.append({
                        "D": l_dt, "B": b_name, "T": target, "PU": vp, "PM": 0.0,
                        "QT": qty, "QV": q_ver, "QUN": q_unver, "QPE": q_pend, "Reason": reason
                    })

                if target != "Мінування" and len(r) > 4:
                    v_mine = to_native(r[4])
                    if v_mine > 0:
                        all_results.append({
                            "D": l_dt, "B": b_name, "T": "Мінування", "PU": 0.0, "PM": v_mine,
                            "QT": v_mine, "QV": v_mine, "QUN": 0.0, "QPE": 0.0, "Reason": ""
                        })
        except Exception as e:
            st.warning(f"⚠️ Помилка обробки даних підрозділу {b_name}: {e}")
            continue

    return all_results, validation_issues


def parse_urazh_data(conn, unit_names, prefix, cur_m, cur_y):
    urazh_all_units = []
    for b_name in unit_names:
        sheet_name = f"{prefix}.{b_name}"
        df_unit = None
        try:
            df_unit = conn.read(worksheet=sheet_name, ttl=300, header=None).fillna("")
        except Exception:
            try:
                df_unit = conn.read(worksheet=b_name, ttl=300, header=None).fillna("")
            except Exception:
                continue

        try:
            u_rows = df_unit.values.tolist()
            l_dt = None
            for r in u_rows[1:]:
                if str(r[0]).strip() != "":
                    dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                    if pd.notnull(dt):
                        l_dt = dt
                if not l_dt:
                    continue

                if l_dt.month != cur_m or l_dt.year != cur_y:
                    continue

                target = str(r[1]).strip()
                if target in ["", "-", "•", ".", "Ціль"]:
                    continue

                qty = to_native(r[2])
                st_raw = str(r[3]).strip()
                st_clean = st_raw.lower().strip()

                if target == "Мінування":
                    if "не вериф" in st_clean:
                        match = re.search(r'(\d+)', st_clean)
                        qun_m = float(match.group(1)) if match else qty
                        qv_m = max(0.0, qty - qun_m)
                    elif st_clean == "верифіковано":
                        qv_m = qty
                    else:
                        qv_m = 0.0

                    if len(r) > 4:
                        v_mine = to_native(r[4])
                        if v_mine > 0:
                            qv_m += v_mine

                    if qv_m > 0:
                        urazh_all_units.append({
                            "D": l_dt, "Battalion": b_name, "Target": "Мінування", "Qty": qv_m
                        })
                else:
                    if qty > 0:
                        urazh_all_units.append({
                            "D": l_dt, "Battalion": b_name, "Target": target, "Qty": qty
                        })
        except Exception as e:
            st.warning(f"⚠️ Помилка обробки уражень для {b_name}: {e}")
            continue

    return urazh_all_units


# =================================================================
# 3. АНІМАЦІЙНА ЗАСТАВКА ТА ЕКРАН ВХОДУ
# =================================================================
if "intro_shown" not in st.session_state:
    st.session_state["intro_shown"] = False

if not st.session_state["intro_shown"]:
    logo = get_base64("logo.png")
    st.markdown("""
        <style>
        .boot-screen-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background-color: #0E1117;
            z-index: 999999;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-family: "Inter", sans-serif;
            color: #ffd700;
            text-align: center;
        }
        .radar-pulse {
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background: rgba(255, 215, 0, 0.03);
            border: 2px solid #ffd700;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 30px;
            animation: pulseRadar 6s infinite ease-in-out;
        }
        @keyframes pulseRadar {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.4); opacity: 0.7; }
            70% { transform: scale(1.05); box-shadow: 0 0 0 25px rgba(255, 215, 0, 0); opacity: 1; }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 215, 0, 0); opacity: 0.7; }
        }
        .boot-text {
            font-size: 13px;
            font-weight: 800;
            letter-spacing: 4px;
            text-transform: uppercase;
            animation: blinkText 2s infinite;
            margin: 0;
            padding: 0 20px;
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
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 4. НАВІГАЦІЯ ТА ДАНІ
# =================================================================
conn = st.connection("gsheets", type=GSheetsConnection)

category = st.sidebar.radio("НАПРЯМОК РОБОТИ:", [
    "⚔️ Бригадні звіти",
    "🔥 Ураження",
    "─" * 10,
    "📊 Дашборд",
    "📈 Графіки",
    "🔍 Валідація даних"
])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

unit_names = ["1аемб", "2аемб", "3аемб", "4аемб"]

try:
    if category == "⚔️ Бригадні звіти":
        sel_report_month = st.selectbox("ОБЕРІТЬ МІСЯЦЬ ДЛЯ ПЕРЕГЛЯДУ ЗВІТУ:", AVAILABLE_MONTHS)
        prefix = sel_report_month.split(".")[0]
        cur_m = int(prefix)
        cur_y = int(sel_report_month.split(".")[1])

        st.markdown(f"<h2 style='text-align:center; color:#ffd700; text-shadow: 2px 2px 8px rgba(0,0,0,0.95); font-weight: 800; letter-spacing: 1px;'>⚔️ ЗАГАЛЬНОБРИГАДНИЙ МОНІТОРИНГ {sel_report_month} </h2>", unsafe_allow_html=True)

        now_str = datetime.now().strftime("%d.%m.%Y о %H:%M")
        st.markdown(f"<p style='text-align:center; color:#00E676; font-size: 15px; margin-top: -10px; margin-bottom: 25px; font-weight: 700;'>🕒 Дані оновлені на: {now_str}</p>", unsafe_allow_html=True)

        all_results, _ = parse_battalion_data(conn, unit_names, prefix, cur_m, cur_y)

        if all_results:
            filtered = [r for r in all_results if r["D"].month == cur_m and r["D"].year == cur_y]

            st.markdown("---")
            sel_b = st.selectbox("ДЕТАЛІЗАЦІЯ ПІДРОЗДІЛУ:", unit_names)
            u_res = [r for r in filtered if r["B"] == sel_b]

            u_total_pts = int(sum(r["PU"] + r["PM"] for r in u_res))
            u_pending_pts = sum(r["QPE"] for r in u_res)

            now = datetime.now()
            current_day = now.day
            days_in_month = calendar.monthrange(cur_y, cur_m)[1]

            if current_day > days_in_month:
                current_day = days_in_month
            if current_day == 0:
                current_day = 1

            total_for_forecast = u_total_pts + u_pending_pts
            daily_avg = total_for_forecast / current_day if current_day > 0 else 0
            forecast = int(daily_avg * days_in_month)
            remaining_to_forecast = forecast - u_total_pts

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="💰 Поточні бали", value=u_total_pts)
            with col2:
                st.metric(
                    label="📈 Прогноз на кінець місяця",
                    value=forecast,
                    delta=f"+{remaining_to_forecast} до прогнозу",
                    delta_color="normal"
                )
            with col3:
                st.metric(
                    label="📅 Днів пройдено",
                    value=current_day,
                    delta=f"всього {days_in_month}",
                    delta_color="off"
                )
            st.markdown("<br>", unsafe_allow_html=True)

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

                def style_report_cells(val, column_name):
                    if isinstance(val, (int, float)) and val == 0:
                        return 'color: #555555; font-weight: normal;'
                    if column_name == "Верифіковано (шт)": return 'color: #2ECC71; font-weight: bold;'
                    elif column_name == "Не верифіковано (шт)": return 'color: #E74C3C; font-weight: bold;'
                    elif column_name == "На верифікації (шт)": return 'color: #95A5A6; font-weight: bold;'
                    return 'color: white;'

                styled_df = df_report.style.map(
                    lambda v: style_report_cells(v, "Верифіковано (шт)"), subset=["Верифіковано (шт)"]
                ).map(
                    lambda v: style_report_cells(v, "Не верифіковано (шт)"), subset=["Не верифіковано (шт)"]
                ).map(
                    lambda v: style_report_cells(v, "На верифікації (шт)"), subset=["На верифікації (шт)"]
                ).map(
                    lambda v: 'color: #555555;' if (isinstance(v, (int, float)) and v == 0) else 'color: white;',
                    subset=["Всього (шт)", "Бали"]
                )

                st.dataframe(styled_df, use_container_width=True, hide_index=True)

                csv_data = df_report.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Експортувати звіт (CSV)",
                    csv_data,
                    file_name=f"звіт_{sel_b}_{sel_report_month}.csv",
                    mime="text/csv"
                )

            unverified_records = [r for r in u_res if r["QUN"] > 0]

            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("🔍 Переглянути деталі та причини щодо не верифікованих об'єктів"):
                if unverified_records:
                    has_reasons = False
                    for item in unverified_records:
                        date_str = item["D"].strftime("%d.%m.%Y")
                        if item["Reason"]:
                            has_reasons = True
                            st.markdown(f"• **{date_str}** — *{item['T']}* ({int(item['QUN'])} шт) — <span style='color:#E74C3C; font-weight:600;'>Причина: {item['Reason']}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"• **{date_str}** — *{item['T']}* ({int(item['QUN'])} шт) — <span style='color:#95A5A6;'>Причину не вказано в Google Sheets</span>", unsafe_allow_html=True)

                    if not has_reasons:
                        st.info("ℹ️ У таблиці знайдено не верифіковані об'єкти, але жодного опису чи причини для них не додано.")
                else:
                    st.success("✅ У цього підрозділу за обраний період немає жодного не верифікованого об'єкта.")

    elif category == "🔥 Ураження":
        sel_ur = st.selectbox("ОБЕРІТЬ ПЕРІОД ДЛЯ АНАЛІТИКИ:", AVAILABLE_MONTHS)
        prefix = sel_ur.split(".")[0]
        cur_m = int(prefix)
        cur_y = int(sel_ur.split(".")[1])

        st.markdown(f"<h2 style='text-align:center; color:#ffd700; text-shadow: 2px 2px 8px rgba(0,0,0,0.95); font-weight: 800; letter-spacing: 1px;'>🔥 МОНІТОРИНГ УРАЖЕНЬ ЗА {sel_ur} </h2>", unsafe_allow_html=True)

        urazh_all_units = parse_urazh_data(conn, unit_names, prefix, cur_m, cur_y)

        if urazh_all_units:
            df_urazh = pd.DataFrame(urazh_all_units)
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("#### 📋 Порівняльна таблиця об'єктів ураження та мінувань за підрозділами:")

            pivot_df = df_urazh.pivot_table(index="Target", columns="Battalion", values="Qty", aggfunc="sum")

            for b in unit_names:
                if b not in pivot_df.columns:
                    pivot_df[b] = 0.0

            pivot_df = pivot_df[unit_names].fillna(0).astype(int)
            pivot_df.index.name = "Об'єкт ураження / Мінування"
            pivot_df_final = pivot_df.reset_index()

            def highlight_max_battalion(row):
                styles = [''] * len(row)
                bat_values = row[unit_names]
                max_val = bat_values.max()
                if max_val <= 0:
                    return styles
                for col_name in unit_names:
                    if row[col_name] == max_val:
                        idx = row.index.get_loc(col_name)
                        styles[idx] = 'background-color: #2E7D32; color: #FFFFFF; font-weight: bold; border-radius: 4px;'
                return styles

            styled_pivot = pivot_df_final.style.apply(highlight_max_battalion, axis=1)
            st.dataframe(styled_pivot, use_container_width=True, hide_index=True)

            csv_pivot = pivot_df_final.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Експортувати таблицю (CSV)",
                csv_pivot,
                file_name=f"ураження_{sel_ur}.csv",
                mime="text/csv"
            )
        else:
            st.info(f"ℹ️ Немає знайдених даних про ураження або мінування за період {sel_ur}.")

    elif category == "📊 Дашборд":
        sel_month = st.selectbox("ОБЕРІТЬ МІСЯЦЬ:", AVAILABLE_MONTHS)
        prefix = sel_month.split(".")[0]
        cur_m = int(prefix)
        cur_y = int(sel_month.split(".")[1])

        st.markdown(f"<h2 style='text-align:center; color:#ffd700; text-shadow: 2px 2px 8px rgba(0,0,0,0.95); font-weight: 800; letter-spacing: 1px;'>📊 ЗАГАЛЬНИЙ ДАШБОРД — {sel_month}</h2>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        all_results, _ = parse_battalion_data(conn, unit_names, prefix, cur_m, cur_y)

        if all_results:
            filtered = [r for r in all_results if r["D"].month == cur_m and r["D"].year == cur_y]

            total_pts_all = int(sum(r["PU"] + r["PM"] for r in filtered))
            total_verified = int(sum(r["QV"] for r in filtered))
            total_unverified = int(sum(r["QUN"] for r in filtered))
            total_pending = int(sum(r["QPE"] for r in filtered))
            total_targets = int(sum(r["QT"] for r in filtered))
            verif_pct = round((total_verified / total_targets * 100), 1) if total_targets > 0 else 0

            best_battalion = ""
            best_pts = 0
            for b in unit_names:
                b_pts = int(sum(r["PU"] + r["PM"] for r in filtered if r["B"] == b))
                if b_pts > best_pts:
                    best_pts = b_pts
                    best_battalion = b

            k1, k2, k3, k4 = st.columns(4)
            with k1:
                st.metric("💰 Загальні бали", total_pts_all)
            with k2:
                st.metric("🎯 Всього об'єктів", total_targets, delta=f"{verif_pct}% верифіковано")
            with k3:
                st.metric("✅ Верифіковано", total_verified, delta=f"❌ {total_unverified} не вериф.")
            with k4:
                st.metric("🏆 Найкращий підрозділ", best_battalion, delta=f"{best_pts} балів")

            st.markdown("---")

            st.markdown("#### 🏅 Рейтинг підрозділів")
            rating_data = []
            for b in unit_names:
                b_res = [r for r in filtered if r["B"] == b]
                b_pts = int(sum(r["PU"] + r["PM"] for r in b_res))
                b_targets = int(sum(r["QT"] for r in b_res))
                b_verif = int(sum(r["QV"] for r in b_res))
                b_unverif = int(sum(r["QUN"] for r in b_res))
                rating_data.append({
                    "Підрозділ": b,
                    "Бали": b_pts,
                    "Об'єктів всього": b_targets,
                    "Верифіковано": b_verif,
                    "Не верифіковано": b_unverif,
                    "% верифікації": round((b_verif / b_targets * 100), 1) if b_targets > 0 else 0
                })

            df_rating = pd.DataFrame(rating_data).sort_values(by="Бали", ascending=False)

            def style_rating(df):
                styled = df.style.bar(subset=["Бали"], color='#ffd700')
                styled = styled.format({"% верифікації": "{:.1f}%"})
                return styled

            st.dataframe(style_rating(df_rating), use_container_width=True, hide_index=True)

            st.markdown("#### 📊 Порівняння балів між підрозділами")
            fig_bar = go.Figure(data=[
                go.Bar(
                    x=df_rating["Підрозділ"],
                    y=df_rating["Бали"],
                    marker_color=[CLRS.get(b, '#ffd700') for b in df_rating["Підрозділ"]],
                    text=df_rating["Бали"],
                    textposition='outside',
                    textfont=dict(color='#ffd700', size=14, family='Inter'),
                )
            ])
            fig_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white', family='Inter', size=13),
                xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                height=400,
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                st.markdown("#### 🥧 Розподіл за типами цілей")
                target_totals = {}
                for r in filtered:
                    t = r["T"]
                    pts = r["PU"] + r["PM"]
                    if t not in target_totals:
                        target_totals[t] = {"pts": 0, "qty": 0}
                    target_totals[t]["pts"] += pts
                    target_totals[t]["qty"] += r["QT"]

                if target_totals:
                    df_pie = pd.DataFrame([
                        {"Ціль": k, "Бали": v["pts"], "Кількість": v["qty"]}
                        for k, v in sorted(target_totals.items(), key=lambda x: -x[1]["pts"])
                    ]).head(12)

                    fig_pie = go.Figure(data=[go.Pie(
                        labels=df_pie["Ціль"],
                        values=df_pie["Бали"],
                        hole=0.4,
                        textinfo='label+percent',
                        textfont=dict(color='white', size=12, family='Inter'),
                        marker=dict(colors=px.colors.qualitative.Set3)
                    )])
                    fig_pie.update_layout(
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white', family='Inter'),
                        height=400,
                        margin=dict(l=10, r=10, t=10, b=10),
                        showlegend=True,
                        legend=dict(font=dict(color='white'))
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

            with col_chart2:
                st.markdown("#### 📈 Динаміка балів по днях")
                daily_data = {}
                for r in filtered:
                    day = r["D"].day
                    b = r["B"]
                    key = (day, b)
                    if key not in daily_data:
                        daily_data[key] = 0
                    daily_data[key] += r["PU"] + r["PM"]

                fig_timeline = go.Figure()
                for b in unit_names:
                    days = sorted(set(day for day, bat in daily_data.keys() if bat == b))
                    pts_list = [daily_data.get((d, b), 0) for d in days]
                    fig_timeline.add_trace(go.Scatter(
                        x=days,
                        y=pts_list,
                        mode='lines+markers',
                        name=b,
                        line=dict(color=CLRS.get(b, '#ffd700'), width=2),
                        marker=dict(size=6)
                    ))

                fig_timeline.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', family='Inter', size=13),
                    xaxis=dict(title="День місяця", gridcolor='rgba(255,255,255,0.1)'),
                    yaxis=dict(title="Бали", gridcolor='rgba(255,255,255,0.1)'),
                    height=400,
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(font=dict(color='white')),
                    hovermode='x unified'
                )
                st.plotly_chart(fig_timeline, use_container_width=True)

            st.markdown("#### 🔥 Теплова карта: інтенсивність балів по днях та підрозділах")
            all_days = sorted(set(r["D"].day for r in filtered))
            heatmap_z = []
            for b in unit_names:
                row_data = []
                for d in all_days:
                    pts = sum(r["PU"] + r["PM"] for r in filtered if r["D"].day == d and r["B"] == b)
                    row_data.append(pts)
                heatmap_z.append(row_data)

            fig_heat = go.Figure(data=go.Heatmap(
                z=heatmap_z,
                x=all_days,
                y=unit_names,
                colorscale='YlOrRd',
                text=heatmap_z,
                texttemplate="%{text}",
                textfont=dict(size=11),
                hovertemplate="День: %{x}<br>Підрозділ: %{y}<br>Бали: %{z}<extra></extra>"
            ))
            fig_heat.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white', family='Inter', size=13),
                xaxis=dict(title="День місяця", gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(title="Підрозділ", gridcolor='rgba(255,255,255,0.1)'),
                height=350,
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig_heat, use_container_width=True)
        else:
            st.warning(f"⚠️ Немає даних за період {sel_month}.")

    elif category == "📈 Графіки":
        sel_month = st.selectbox("ОБЕРІТЬ МІСЯЦЬ:", AVAILABLE_MONTHS)
        prefix = sel_month.split(".")[0]
        cur_m = int(prefix)
        cur_y = int(sel_month.split(".")[1])

        st.markdown(f"<h2 style='text-align:center; color:#ffd700; text-shadow: 2px 2px 8px rgba(0,0,0,0.95); font-weight: 800; letter-spacing: 1px;'>📈 ГРАФІКИ ТА АНАЛІТИКА — {sel_month}</h2>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        all_results, _ = parse_battalion_data(conn, unit_names, prefix, cur_m, cur_y)

        if all_results:
            filtered = [r for r in all_results if r["D"].month == cur_m and r["D"].year == cur_y]

            all_targets = sorted(list(set(r["T"] for r in filtered)))
            sel_targets = st.multiselect(
                "ФІЛЬТР ПО ТИПАХ ЦІЛЕЙ (оберіть потрібні або залиште порожнім для всіх):",
                all_targets,
                default=[]
            )

            if sel_targets:
                filtered = [r for r in filtered if r["T"] in sel_targets]

            st.markdown(f"<p style='color:#00E676;'>Відфільтровано: {len(filtered)} записів</p>", unsafe_allow_html=True)
            st.markdown("---")

            st.markdown("#### 📊 Ураження за статусом верифікації (по підрозділах)")
            verif_data = {}
            for b in unit_names:
                b_res = [r for r in filtered if r["B"] == b]
                verif_data[b] = {
                    "Верифіковано": int(sum(r["QV"] for r in b_res)),
                    "Не верифіковано": int(sum(r["QUN"] for r in b_res)),
                    "На верифікації": int(sum(r["QPE"] for r in b_res))
                }

            fig_stacked = go.Figure()
            statuses = ["Верифіковано", "Не верифіковано", "На верифікації"]
            status_colors = {"Верифіковано": "#2ECC71", "Не верифіковано": "#E74C3C", "На верифікації": "#95A5A6"}

            for s in statuses:
                fig_stacked.add_trace(go.Bar(
                    name=s,
                    x=unit_names,
                    y=[verif_data[b][s] for b in unit_names],
                    marker_color=status_colors[s],
                    text=[verif_data[b][s] for b in unit_names],
                    textposition='inside',
                    textfont=dict(color='white', size=12, family='Inter')
                ))

            fig_stacked.update_layout(
                barmode='stack',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white', family='Inter', size=13),
                xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                height=450,
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(font=dict(color='white'))
            )
            st.plotly_chart(fig_stacked, use_container_width=True)

            st.markdown("---")

            st.markdown("#### 🎯 Топ цілей за балами")
            target_pts = {}
            for r in filtered:
                t = r["T"]
                if t not in target_pts:
                    target_pts[t] = 0
                target_pts[t] += r["PU"] + r["PM"]

            df_top = pd.DataFrame(list(target_pts.items()), columns=["Ціль", "Бали"])
            df_top = df_top.sort_values(by="Бали", ascending=True).tail(15)

            fig_top = go.Figure(go.Bar(
                y=df_top["Ціль"],
                x=df_top["Бали"],
                orientation='h',
                marker_color='#ffd700',
                text=df_top["Бали"],
                textposition='outside',
                textfont=dict(color='#ffd700', size=13, family='Inter')
            ))
            fig_top.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white', family='Inter', size=13),
                xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                height=500,
                margin=dict(l=20, r=20, t=20, b=20),
            )
            st.plotly_chart(fig_top, use_container_width=True)

            st.markdown("---")

            st.markdown("#### 📈 Накопичувальна динаміка балів")
            cdf_data = {}
            for b in unit_names:
                b_res = sorted([r for r in filtered if r["B"] == b], key=lambda x: x["D"])
                cumulative = 0
                days_list = []
                pts_list = []
                for r in b_res:
                    cumulative += r["PU"] + r["PM"]
                    if r["D"].day not in days_list:
                        days_list.append(r["D"].day)
                    pts_list.append(cumulative)
                unique_days = []
                unique_pts = []
                seen_days = set()
                for d, p in zip(days_list, pts_list):
                    if d not in seen_days:
                        unique_days.append(d)
                        unique_pts.append(p)
                    else:
                        unique_pts[-1] = p
                cdf_data[b] = (unique_days, unique_pts)

            fig_cdf = go.Figure()
            for b in unit_names:
                days, pts = cdf_data[b]
                if days:
                    fig_cdf.add_trace(go.Scatter(
                        x=days,
                        y=pts,
                        mode='lines+markers',
                        name=b,
                        line=dict(color=CLRS.get(b, '#ffd700'), width=2),
                        marker=dict(size=5),
                        fill='tozeroy' if b == list(unit_names)[0] else None,
                        fillcolor='rgba(255, 215, 0, 0.05)'
                    ))

            fig_cdf.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white', family='Inter', size=13),
                xaxis=dict(title="День місяця", gridcolor='rgba(255,255,255,0.1)'),
                yaxis=dict(title="Накопичувальні бали", gridcolor='rgba(255,255,255,0.1)'),
                height=450,
                margin=dict(l=20, r=20, t=20, b=20),
                legend=dict(font=dict(color='white')),
                hovermode='x unified'
            )
            st.plotly_chart(fig_cdf, use_container_width=True)

            st.markdown("---")
            st.markdown("#### 📅 Щоденна активність (кількість уражених об'єктів)")
            daily_qty = {}
            for r in filtered:
                day = r["D"].day
                if day not in daily_qty:
                    daily_qty[day] = 0
                daily_qty[day] += r["QT"]

            if daily_qty:
                df_daily = pd.DataFrame(list(daily_qty.items()), columns=["День", "Кількість"])
                df_daily = df_daily.sort_values("День")

                fig_daily = go.Figure(go.Bar(
                    x=df_daily["День"],
                    y=df_daily["Кількість"],
                    marker_color='#00E676',
                    text=df_daily["Кількість"],
                    textposition='outside',
                    textfont=dict(color='#00E676', size=11, family='Inter')
                ))
                fig_daily.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white', family='Inter', size=13),
                    xaxis=dict(title="День місяця", gridcolor='rgba(255,255,255,0.1)', dtick=1),
                    yaxis=dict(title="Кількість об'єктів", gridcolor='rgba(255,255,255,0.1)'),
                    height=400,
                    margin=dict(l=20, r=20, t=20, b=20),
                )
                st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.warning(f"⚠️ Немає даних за період {sel_month}.")

    elif category == "🔍 Валідація даних":
        sel_month = st.selectbox("ОБЕРІТЬ МІСЯЦЬ ДЛЯ ПЕРЕВІРКИ:", AVAILABLE_MONTHS)
        prefix = sel_month.split(".")[0]
        cur_m = int(prefix)
        cur_y = int(sel_month.split(".")[1])

        st.markdown(f"<h2 style='text-align:center; color:#ffd700; text-shadow: 2px 2px 8px rgba(0,0,0,0.95); font-weight: 800; letter-spacing: 1px;'>🔍 ВАЛІДАЦІЯ ДАНИХ — {sel_month}</h2>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        all_results, validation_issues = parse_battalion_data(conn, unit_names, prefix, cur_m, cur_y)

        if validation_issues:
            st.warning(f"⚠️ Знайдено {len(validation_issues)} потенційних проблем з даними:")

            df_issues = pd.DataFrame(validation_issues)
            st.dataframe(
                df_issues.style.map(
                    lambda v: 'color: #E74C3C; font-weight: bold;' if isinstance(v, str) and "Невідом" in str(v) else 'color: white;',
                    subset=["Проблема"]
                ),
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")
            st.markdown("#### 💡 Рекомендації:")
            unknown_targets = df_issues["Ціль"].unique()
            if len(unknown_targets) > 0:
                st.markdown("**Невідомі типи цілей не знайдені в POINTS_MAP:**")
                for t in unknown_targets:
                    st.markdown(f"- `{t}` — додайте цей тип у словник `POINTS_MAP` або виправте опечатку в Google Sheets")

            csv_issues = df_issues.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Експортувати проблеми (CSV)",
                csv_issues,
                file_name=f"валідація_{sel_month}.csv",
                mime="text/csv"
            )
        else:
            st.success("✅ Дані за обраний період не містять помилок! Всі типи цілей розпізнано.")

        st.markdown("---")
        st.markdown("#### 🔎 Стан словника POINTS_MAP")
        lower_map = {}
        duplicates_found = []
        for k, v in POINTS_MAP.items():
            kl = k.lower().strip()
            if kl in lower_map:
                if lower_map[kl] != v:
                    duplicates_found.append((k, v, lower_map[kl]))
            else:
                lower_map[kl] = v

        if duplicates_found:
            st.warning(f"⚠️ Знайдено {len(duplicates_found)} конфліктів у POINTS_MAP:")
            for name, val1, val2 in duplicates_found:
                st.markdown(f"- `{name}`: значення {val1} конфліктує з {val2}")
        else:
            st.success("✅ У POINTS_MAP немає конфліктів дубльованих ключів.")

except Exception as e:
    st.error(f"СИСТЕМНА ПОМИЛКА: {e}")

# =================================================================
# 5. БЛОК ТЕХНІЧНОЇ ПІДТРИМКИ
# =================================================================
st.markdown("""
    <style>
    .support-card {
        position: fixed;
        bottom: 15px;
        left: 15px;
        background-color: rgba(14, 17, 23, 0.90);
        padding: 8px 12px;
        border-radius: 8px;
        border: 1px solid rgba(255, 215, 0, 0.2);
        z-index: 999999;
        font-family: "Inter", sans-serif;
        text-align: left;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.6);
        backdrop-filter: blur(5px);
        transition: all 0.3s ease;
    }
    .support-card:hover {
        border-color: rgba(255, 215, 0, 0.5);
        background-color: rgba(14, 17, 23, 0.98);
    }
    .support-title {
        margin: 0 0 4px 0;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 0.5px;
        color: #ffd700;
        text-transform: uppercase;
    }
    .support-text {
        margin: 1px 0;
        font-size: 11px;
        color: #e0e0e0;
    }
    .support-label {
        color: #888888;
        font-size: 10px;
        font-weight: 600;
    }
    </style>
    <div class="support-card">
        <p class="support-title">⚙️ ТЕХ. ДОПОМОГА</p>
        <p class="support-text"><span class="support-label">WhatsApp:</span> +380 67 485 95 90</p>
        <p class="support-text"><span class="support-label">Delta:</span> Usignolo</p>
    </div>
""", unsafe_allow_html=True)
