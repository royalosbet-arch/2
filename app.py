import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
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
POINTS_MAP = {
    "О/С-200": 12, "О/С-300": 8, "Молнія": 10, "Укриття": 1, "Фортифікація": 1,
    "Антена": 4, "FPV": 6, "Танк": 40, "FPV Бомбер": 6, "РЛС": 50, "САУ": 30,
    "Міномет": 5, "ЛАТ": 8, "Генератор": 4, "Електросамокат": 4, "Квадроцикл": 4,
    "Мотоцикл": 4, "РЕБ": 8, "Мавік": 6, "Орлан": 40, "Шахед": 20, "ждун": 10,
    "Автомобіль": 5, "Гаубиця": 40, "ББМ": 20, "Гармата": 20, "Гербера": 20, "Зала": 20,
    "Причіп": 2, "ПОЛОНЕНИЙ": 120, "Старлінк": 4, "Винос": 8, "Мавік нічний": 10, "Розвідка": 1,
    "Склад": 5, "Артилерія": 1, "ФПВ": 6, "О/С 200": 12, "О/С 300": 8,"FPV бомбер": 6,"Бомбер": 6,
    "НРК": 4, "Ждун": 10, "ФПВ бомбер": 6, "Місія НРК": 70, "Місія НРК Л": 3.4, "Розвідка": 9,
    "Склад БК": 5, "Відеокамера": 4
}

MONTHS_UKR = {1:"Січень", 2:"Лютий", 3:"Березень", 4:"Квітень", 5:"Травень", 6:"Червень", 7:"Липень", 8:"Серпень", 9:"Вересень", 10:"Жовтень", 11:"Листопад", 12:"Грудень"}
CLRS = {'1аемб': '#92D050', '2аемб': '#A5A5A5', '3аемб': '#4472C4', '4аемб': '#ED7D31'}
MINE_CLR = "#7030A0"

# =================================================================
# 2. ДОПОМІЖНІ ФУНКЦІЇ
# =================================================================
def get_base64(path):
    try:
        with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return None

def to_native(val):
    try:
        s = str(val).replace(',', '.').strip()
        return float(s) if s not in ["", "-", ".", "•"] else 0.0
    except: return 0.0

def get_urazh_data(qty, target, status):
    t_clean = str(target).strip()
    unit_p = POINTS_MAP.get(t_clean, 0)
    st_clean = str(status).lower().strip()
    if st_clean == "верифіковано":
        return qty * unit_p, qty
    return 0.0, 0.0

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

category = st.sidebar.radio("НАПРЯМОК РОБОТИ:", ["⚔️ Бригадні звіти", "🔥 Ураження"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

try:
    if category == "⚔️ Бригадні звіти":
        sel_report_month = st.selectbox("ОБЕРІТЬ МІСЯЦЬ ДЛЯ ПЕРЕГЛЯДУ ЗВІТУ:", ["07.2026", "06.2026", "05.2026", "04.2026"])
        prefix = sel_report_month.split(".")[0]
        cur_m = int(prefix)
        cur_y = int(sel_report_month.split(".")[1])

        st.markdown(f"<h2 style='text-align:center; color:#ffd700; text-shadow: 2px 2px 8px rgba(0,0,0,0.95); font-weight: 800; letter-spacing: 1px;'>⚔️ ЗАГАЛЬНОБРИГАДНИЙ МОНІТОРИНГ {sel_report_month} </h2>", unsafe_allow_html=True)
        
        # Яскраво-зелений колір (#00E676) для кращої видимості
        now_str = datetime.now().strftime("%d.%m.%Y о %H:%M")
        st.markdown(f"<p style='text-align:center; color:#00E676; font-size: 15px; margin-top: -10px; margin-bottom: 25px; font-weight: 700;'>🕒 Дані оновлені на: {now_str}</p>", unsafe_allow_html=True)
        
        unit_names = ["1аемб", "2аемб", "3аемб", "4аемб"]
        all_results = []

        for b_name in unit_names:
            sheet_name = f"{prefix}.{b_name}"
            try:
                df_unit = conn.read(worksheet=sheet_name, ttl=300, header=None).fillna("")
            except:
                try:
                    df_unit = conn.read(worksheet=b_name, ttl=300, header=None).fillna("")
                except:
                    continue
            
            try:
                u_rows = df_unit.values.tolist()
                l_dt = None
                for r in u_rows[1:]:
                    if str(r[0]).strip() != "":
                        dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                        if pd.notnull(dt): l_dt = dt
                    if not l_dt: continue
                    target = str(r[1]).strip()
                    if target not in ["", "-", "•", ".", "Ціль"]:
                        qty = to_native(r[2])
                        st_raw = str(r[3]).strip()
                        st_clean = st_raw.lower()
                        reason = ""
                        
                        if target == "Мінування":
                            if "не вериф" in st_clean:
                                match = re.search(r'(\d+)', st_clean)
                                qun_m = float(match.group(1)) if match else qty
                                qv_m = max(0.0, qty - qun_m)
                                qp_m = 0.0
                                if ":" in st_raw: reason = st_raw.split(":", 1)[1].strip()
                                elif "(" in st_raw: reason = st_raw.split("(", 1)[1].replace(")", "").strip()
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
                                if ":" in st_raw: reason = st_raw.split(":", 1)[1].strip()
                                elif "(" in st_raw: reason = st_raw.split("(", 1)[1].replace(")", "").strip()
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
            except: continue

        if all_results:
            filtered = [r for r in all_results if r["D"].month == cur_m and r["D"].year == cur_y]
            
            st.markdown("---")
            sel_b = st.selectbox("ДЕТАЛІЗАЦІЯ ПІДРОЗДІЛУ:", unit_names)
            u_res = [r for r in filtered if r["B"] == sel_b]
            
            # Поточні верифіковані бали
            u_total_pts = int(sum(r["PU"] + r["PM"] for r in u_res))
            
            # =================================================================
            # ПРОГНОЗ ТА МЕТРИКИ (Варіант А: враховуємо верифіковані + на верифікації)
            # =================================================================
            u_pending_pts = sum(r["QPE"] for r in u_res) # Бали, які чекають на верифікацію
            
            now = datetime.now()
            current_day = now.day
            days_in_month = calendar.monthrange(cur_y, cur_m)[1]
            
            if current_day > days_in_month:
                current_day = days_in_month
            if current_day == 0:
                current_day = 1
                
            # Логіка: (верифіковано + на верифікації) / поточний день * днів у місяці
            total_for_forecast = u_total_pts + u_pending_pts
            daily_avg = total_for_forecast / current_day
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
            # =================================================================

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
        sel_ur = st.selectbox("ОБЕРІТЬ ПЕРІОД ДЛЯ АНАЛІТИКИ:", ["07.2026", "06.2026", "05.2026", "04.2026"])
        prefix = sel_ur.split(".")[0]
        cur_m = int(prefix)
        cur_y = int(sel_ur.split(".")[1])

        st.markdown(f"<h2 style='text-align:center; color:#ffd700; text-shadow: 2px 2px 8px rgba(0,0,0,0.95); font-weight: 800; letter-spacing: 1px;'>🔥 МОНІТОРИНГ УРАЖЕНЬ ЗА {sel_ur} </h2>", unsafe_allow_html=True)
        
        unit_names = ["1аемб", "2аемб", "3аемб", "4аемб"]
        urazh_all_units = []

        for b_name in unit_names:
            sheet_name = f"{prefix}.{b_name}"
            try:
                df_unit = conn.read(worksheet=sheet_name, ttl=300, header=None).fillna("")
                u_rows = df_unit.values.tolist()
                l_dt = None
                for r in u_rows[1:]:
                    if str(r[0]).strip() != "":
                        dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                        if pd.notnull(dt): l_dt = dt
                    if not l_dt: continue
                    
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
            except:
                continue

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
                if max_val <= 0: return styles
                for col_name in unit_names:
                    if row[col_name] == max_val:
                        idx = row.index.get_loc(col_name)
                        styles[idx] = 'background-color: #2E7D32; color: #FFFFFF; font-weight: bold; border-radius: 4px;'
                return styles

            styled_pivot = pivot_df_final.style.apply(highlight_max_battalion, axis=1)
            st.dataframe(styled_pivot, use_container_width=True, hide_index=True)
        else:
            st.info(f"ℹ️ Немає знайдених даних про ураження або мінування за період {sel_ur}.")

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

