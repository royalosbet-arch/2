import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64
import re
import time  # Додано для затримки заставки
from datetime import datetime

# =================================================================
# 1. НАЛАШТУВАННЯ ТА КОНСТАНТИ
# =================================================================
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

USER_PASSWORD = "2887"
POINTS_MAP = {
    "О/С 200": 12, "О/С 300": 8, "Молнія": 10, "Укриття": 1, "Фортифікація": 1,
    "Антена": 4, "ФПВ": 6, "Танк": 40, "Бомбер": 6, "РЛС": 50, "САУ": 30,
    "Міномет": 5, "ЛАТ": 8, "Генератор": 4, "Електросамокат": 4, "Квадроцикл": 4,
    "Мотоцикл": 4, "РЕБ": 8, "Мавік": 6, "Орлан": 40, "Шахед": 20, "Ждун": 10,
    "Автомобіль": 5, "Гаубиця": 40, "ББМ": 20, "Гармата": 20, "Гербера": 20, "Зала": 20,
    "Причіп": 2, "ПОЛОНЕНИЙ": 60, "Старлінк": 4, "Винос": 8, "Мавік нічний": 10
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

def get_mine_data(qty, status):
    st_cl = str(status).lower().strip()
    if "не вериф" in st_cl:
        match = re.search(r'(\d+)', st_cl)
        unv_q = float(match.group(1)) if match else qty
        return max(0.0, qty - unv_q), unv_q
    elif st_cl == "верифіковано":
        return qty, 0.0
    return 0.0, qty

# =================================================================
# 3. АНІМАЦІЙНА ЗАСТАВКА ТА ЕКРАН ВХОДУ
# =================================================================
if "intro_shown" not in st.session_state:
    st.session_state["intro_shown"] = False

# Крок А: Показуємо заставку, якщо користувач тільки зайшов
if not st.session_state["intro_shown"]:
    logo = get_base64("logo.png")
    st.markdown("""
        <style>
        /* Повністю перекриваємо весь екран поверх Streamlit */
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
        
        /* Ховаємо елементи Streamlit під час заставки, щоб вони не стрибали */
        [data-testid="stHeader"], [data-testid="stSidebar"] { display: none !important; }
        </style>
    """, unsafe_allow_html=True)
    
    # Створюємо один суцільний контейнер, який зафіксовано по центру екрана
    html_content = '<div class="boot-screen-overlay">'
    if logo:
        html_content += f'<div class="radar-pulse"><img src="data:image/png;base64,{logo}" style="max-width:95px; border-radius:15px;"></div>'
    else:
        html_content += '<div class="radar-pulse" style="font-size:40px;">🛡️</div>'
    html_content += '<p class="boot-text">СИНХРОНІЗАЦІЯ З БАЗОЮ ДАНИХ... ЗАВАНТАЖЕННЯ СИСТЕМИ</p>'
    html_content += '</div>'
    
    st.markdown(html_content, unsafe_allow_html=True)
    
    time.sleep(2.5)  # Час показу заставки у секундах
    st.session_state["intro_shown"] = True
    st.rerun()

# Крок Б: Екран входу з плавною появою (Fade-in)
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
                <p style='color:#ffd700; font-size: 16px; font-weight: 600; margin-bottom: 20px;'>77 ОАЕМБр • ДШВ ЗСУ 🇺🇦</p>
                <hr style='border:0; border-top: 1px solid rgba(255,255,255,0.1);'>
                <p style='color:white; font-size: 13px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-top: 15px;'>СИТУАЦІЙНИЙ ЦЕНТР БАТАЛЬЙОНУ</p>
            </div>
        """, unsafe_allow_html=True)
        
        pwd = st.text_input("ВВЕДІТЬ КОД ДОСТУПУ:", type="password")
        if st.button("УВІЙТИ В СИСТЕМУ") and pwd == USER_PASSWORD:
            st.session_state["password_correct"] = True
            st.rerun()
    st.stop()

# НАЛАШТУВАННЯ ДИЗАЙНУ ОСНОВНОЇ СТОРІНКИ (після авторизації)
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
category = st.sidebar.radio("НАПРЯМОК РОБОТИ:", ["⚔️ Бригадні звіти", "🧨 Мінування", "🔥 Ураження"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

try:
    if category == "⚔️ Бригадні звіти":
        sel_report_month = st.selectbox("ОБЕРІТЬ МІСЯЦЬ ДЛЯ ПЕРЕГЛЯДУ ЗВІТУ:", ["05.2026", "04.2026"])
        prefix = sel_report_month.split(".")[0]
        cur_m = int(prefix)
        cur_y = int(sel_report_month.split(".")[1])

        st.markdown(f"<h3 style='text-align:center; color:white;'>⚔️ ЗАГАЛЬНОБРИГАДНИЙ МОНІТОРИНГ {sel_report_month} </h3>", unsafe_allow_html=True)
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
                        
                        vp, vq = get_urazh_data(qty, target, st_raw)
                        
                        q_ver = vq
                        reason = ""
                        
                        # Надійна логіка визначення статусів та витягування причин
                        if q_ver > 0:
                            q_unver, q_pend = 0.0, 0.0
                        elif "не вериф" in st_clean:
                            q_unver, q_pend = qty, 0.0
                            
                            # Намагаємось дістати причину за двокрапкою або дужками
                            if ":" in st_raw:
                                reason = st_raw.split(":", 1)[1].strip()
                            elif "(" in st_raw:
                                reason = st_raw.split("(", 1)[1].replace(")", "").strip()
                            else:
                                # Якщо двокрапки немає, але текст довший за "не верифіковано"
                                # Вирізаємо саме слово "не верифіковано" / "не вериф" і беремо залишок
                                rem = re.sub(r'(не верифіковано|не верифікований|не вериф)', '', st_raw, flags=re.IGNORECASE).strip()
                                if rem: reason = rem
                        else:
                            q_unver, q_pend = 0.0, qty
                            
                        all_results.append({
                            "D": l_dt, "B": b_name, "T": target, "PU": vp, "PM": 0.0, 
                            "QT": qty, "QV": q_ver, "QUN": q_unver, "QPE": q_pend,
                            "Reason": reason
                        })
                    if len(r) > 4:
                        v_mine = to_native(r[4])
                        if v_mine > 0:
                            all_results.append({
                                "D": l_dt, "B": b_name, "T": "Мінування", "PU": 0.0, "PM": v_mine, 
                                "QT": v_mine, "QV": v_mine, "QUN": 0.0, "QPE": 0.0, "Reason": ""
                            })
            except: continue

            if b_name == "1аемб":
                try:
                    df_m = conn.read(worksheet="Мінування", ttl=300, header=None).fillna("")
                    m_rows = df_m.values.tolist()
                    for r in m_rows[1:]:
                        dt_m = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                        if pd.notnull(dt_m) and dt_m.month == cur_m and dt_m.year == cur_y:
                            qty_m = to_native(r[2])
                            st_raw_m = str(r[3]).strip()
                            st_cl = st_raw_m.lower()
                            reason_m = ""
                            
                            if "не вериф" in st_cl:
                                match = re.search(r'(\d+)', st_cl)
                                qun_m = float(match.group(1)) if match else qty_m
                                qv_m = max(0.0, qty_m - qun_m)
                                qp_m = 0.0
                                
                                if ":" in st_raw_m: 
                                    reason_m = st_raw_m.split(":", 1)[1].strip()
                                elif "(" in st_raw_m:
                                    reason_m = st_raw_m.split("(", 1)[1].replace(")", "").strip()
                                else:
                                    rem_m = re.sub(r'(\d+|не верифіковано|не верифікований|не вериф)', '', st_raw_m, flags=re.IGNORECASE).strip()
                                    if rem_m: reason_m = rem_m
                            elif st_cl == "верифіковано":
                                qv_m, qun_m, qp_m = qty_m, 0.0, 0.0
                            else:
                                qv_m, qun_m, qp_m = 0.0, 0.0, qty_m
                                
                            if qty_m > 0:
                                all_results.append({
                                    "D": dt_m, "B": b_name, "T": "Мінування", "PU": 0.0, "PM": qv_m, 
                                    "QT": qty_m, "QV": qv_m, "QUN": qun_m, "QPE": qp_m, "Reason": reason_m
                                })
                except: pass

        if all_results:
            filtered = [r for r in all_results if r["D"].month == cur_m and r["D"].year == cur_y]
            
            st.markdown("---")
            sel_b = st.selectbox("ДЕТАЛІЗАЦІЯ ПІДРОЗДІЛУ:", unit_names)
            u_res = [r for r in filtered if r["B"] == sel_b]
            
            u_total_pts = int(sum(r["PU"] + r["PM"] for r in u_res))
            st.metric(f"ВСЬОГО БАЛІВ ({sel_b}):", u_total_pts)
            
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

            # --- ОНОВЛЕНИЙ І НАДІЙНІШИЙ БЛОК ПРИЧИН ---
            # Витягуємо всі записи поточного підрозділу, які мають хоча б ОДНУ неверифіковану одиницю
            unverified_records = [r for r in u_res if r["QUN"] > 0]
            
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("🔍 Переглянути деталі та причини щодо не верифікованих об'єктів"):
                if unverified_records:
                    has_reasons = False
                    for item in unverified_records:
                        date_str = item["D"].strftime("%d.%m.%Y")
                        # Якщо причина вказана
                        if item["Reason"]:
                            has_reasons = True
                            st.markdown(f"• **{date_str}** — *{item['T']}* ({int(item['QUN'])} шт) — <span style='color:#E74C3C; font-weight:600;'>Причина: {item['Reason']}</span>", unsafe_allow_html=True)
                        else:
                            # Якщо причину забули написати в таблиці
                            st.markdown(f"• **{date_str}** — *{item['T']}* ({int(item['QUN'])} шт) — <span style='color:#95A5A6;'>Причину не вказано в Google Sheets</span>", unsafe_allow_html=True)
                    
                    if not has_reasons:
                        st.info("ℹ️ У таблиці знайдено не верифіковані об'єкти, але жодного опису чи причини для них не додано.")
                else:
                    st.success("✅ У цього підрозділу за обраний період немає жодного не верифікованого об'єкта.")

    elif category == "🧨 Мінування":
        df = conn.read(worksheet="Мінування", ttl=300, header=None).fillna("")
        raw_m = df.values.tolist()[1:]; m_list = []
        for r in raw_m:
            dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
            if pd.notnull(dt):
                vq, uq = get_mine_data(to_native(r[2]), r[3])
                m_list.append({"D": dt, "Month": MONTHS_UKR.get(dt.month, "") + " " + str(dt.year), "V": vq, "U": uq})
        if m_list:
            sel_m = st.selectbox("ПЕРІОД:", sorted(list(set([x["Month"] for x in m_list if x["Month"] != ""])), reverse=True))
            m_data = [x for x in m_list if x["Month"] == sel_m]
            labs = [f"{d}.{str(m_data[0]['D'].month).zfill(2)}" for d in range(1, pd.Period(f"{m_data[0]['D'].year}-{m_data[0]['D'].month}").days_in_month + 1)]
            vv, uu = {l:0.0 for l in labs}, {l:0.0 for l in labs}
            for r in m_data:
                l = f"{r['D'].day}.{str(r['D'].month).zfill(2)}"
                if l in vv: vv[l] += r["V"]; uu[l] += r["U"]
            st.metric("ВЕРИФІКОВАНО МІН:", int(sum(vv.values())))
            fm = go.Figure()
            fm.add_trace(go.Bar(x=labs, y=[vv[l] for l in labs], name='Вериф', marker_color='#444444'))
            fm.add_trace(go.Bar(x=labs, y=[uu[l] for l in labs], name='Не вериф', marker_color='#CC0000'))
            fm.add_trace(go.Scatter(x=labs, y=[vv[l]+uu[l] for l in labs], mode='text', text=[str(int(vv[l])) if vv[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white')))
            fm.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(fm, use_container_width=True)

    elif category == "🔥 Ураження":
        sel_ur = st.selectbox("ОБЕРІТЬ ПЕРІОД:", ["04.2026", "03.2026", "02.2026", "01.2026"])
        df = conn.read(worksheet=f"Ураження {sel_ur}", ttl=300, header=None).fillna("")
        raw_u = df.values.tolist()[1:]; clean_u, last_dt, obs = [], None, {}
        for r_u in raw_u:
            if str(r_u[0]).strip() != "":
                dt = pd.to_datetime(str(r_u[0]), dayfirst=True, errors='coerce')
                if pd.notnull(dt): last_dt = dt
            if last_dt and str(r_u[1]).strip() not in ["", "-", "•", ".", "Ціль"]:
                target = str(r_u[1]).strip()
                qty = to_native(r_u[2])
                st_clean = str(r_u[3]).lower().strip()
                
                vp, vq = get_urazh_data(qty, target, str(r_u[3]))
                
                q_ver = vq
                if q_ver > 0:
                    q_unver, q_pend = 0.0, 0.0
                elif "не вериф" in st_clean:
                    q_unver, q_pend = qty, 0.0
                else:
                    q_unver, q_pend = 0.0, qty
                    
                clean_u.append({
                    "D": last_dt, "V": vp, "U": (qty * POINTS_MAP.get(target, 0)) - vp, "T": target, 
                    "QT": qty, "QV": q_ver, "QUN": q_unver, "QPE": q_pend
                })
        if clean_u:
            st.metric("ВЕРИФІКОВАНІ БАЛИ БАТАЛЬЙОНУ:", int(sum(rx["V"] for rx in clean_u)))
            labs = [f"{d}.{str(clean_u[0]['D'].month).zfill(2)}" for d in range(1, pd.Period(f"{clean_u[0]['D'].year}-{clean_u[0]['D'].month}").days_in_month + 1)]
            vv, uu = {l:0.0 for l in labs}, {l:0.0 for l in labs}
            for r_u in clean_u:
                l = f"{r_u['D'].day}.{str(r_u['D'].month).zfill(2)}"
                if l in vv: vv[l] += r_u["V"]; uu[l] += r_u["U"]
                n = r_u["T"]
                if n not in obs: 
                    obs[n] = {"QT": 0, "QV": 0, "QUN": 0, "QPE": 0, "V": 0}
                obs[n]["QT"] += r_u["QT"]
                obs[n]["QV"] += r_u["QV"]
                obs[n]["QUN"] += r_u["QUN"]
                obs[n]["QPE"] += r_u["QPE"]
                obs[n]["V"] += r_u["V"]
                
            fu = go.Figure()
            fu.add_trace(go.Bar(x=labs, y=[vv[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            fu.add_trace(go.Bar(x=labs, y=[uu[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            fu.add_trace(go.Scatter(x=labs, y=[vv[l]+uu[l] for l in labs], mode='text', text=[str(int(vv[l])) if vv[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white')))
            fu.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(fu, use_container_width=True)
            
            st.table(pd.DataFrame([{
                "Тип цілі": k, 
                "Всього (шт)": int(v["QT"]), 
                "Верифіковано (шт)": int(v["QV"]), 
                "Не верифіковано (шт)": int(v["QUN"]), 
                "На верифікації (шт)": int(v["QPE"]), 
                "Бали": int(v["V"])
            } for k, v in sorted(obs.items(), key=lambda x: x[1]["V"], reverse=True)]))

except Exception as e:
    st.error(f"СИСТЕМНА ПОМИЛКА: {e}")
