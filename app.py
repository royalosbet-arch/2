import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64
import re

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

# ПОВНИЙ СЛОВНИК БАЛІВ
POINTS_MAP = {
    "Антена": 4, "О/С 200": 9, "О/С 300": 9, "Молнія": 20, "ФПВ": 7, "Мавік": 7,
    "Бомбер": 7, "РЛС": 15, "Міномет": 10, "ЛАТ": 10, "Генератор": 4, "РЕБ": 4,
    "Фортифікація": 1, "Укриття": 1, "Електросамокат": 4, "Квадроцикл": 4, "Мотоцикл": 4,
    "Танк": 50, "САУ": 30, "ББМ": 20, "Гармата": 20, "Гаубиця": 40, "Автомобіль": 10, "Ждун": 5
}

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except: return None

USER_PASSWORD = "2887" 
MONTHS_UKR = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень", 5: "Травень", 6: "Червень",
    7: "Липень", 8: "Серпень", 9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень"
}

# --- 2. ЕКРАН ВХОДУ ---
def check_password():
    if "password_correct" not in st.session_state:
        logo_base64 = get_base64_image("logo.png") 
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)
        st.write("<br><br>", unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1.2, 1.5, 1.2])
        with col_c:
            if logo_base64:
                st.markdown(f"<div style='text-align: center; margin-bottom: -20px;'><img src='data:image/png;base64,{logo_base64}' style='max-width: 220px; border-radius: 15px;'></div>", unsafe_allow_html=True)
            st.markdown(f"""
                <div style='background:rgba(255,255,255,0.04); padding: 40px 30px 30px 30px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.15); text-align: center;'>
                    <h2 style='color:white; margin-bottom: 0; font-weight: 700; font-size: 34px;'>1 аемб</h2>
                    <p style='color:#ffd700; font-size: 16px; margin-top: 5px; font-weight: 600;'>77 ОАЕМБр • ДШВ ЗСУ 🇺🇦</p>
                    <hr style='border: 0; border-top: 1px solid rgba(255,255,255,0.1); margin: 25px 0;'>
                    <p style='color:#ffffff; font-size: 13px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase;'>СИТУАЦІЙНИЙ ЦЕНТР БАТАЛЬЙОНУ</p>
                </div>
            """, unsafe_allow_html=True)
            pwd = st.text_input("КОД ДОСТУПУ:", type="password", placeholder="Введіть пароль...")
            if st.button("УВІЙТИ В СИСТЕМУ"):
                if pwd == USER_PASSWORD:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("Невірний код")
        return False
    return True

if not check_password(): st.stop()

# --- 3. ДИЗАЙН ---
def set_design(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except: bg_css = 'background-color: #0E1117;'
    st.markdown(f'<style>.stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }} .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }} [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }} [data-testid="stMetricValue"] {{ color: #ffd700 !important; font-size: 36px !important; }}</style>', unsafe_allow_html=True)

set_design('background.jpg')

# --- 4. НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("### 🛠️ УПРАВЛІННЯ")
category = st.sidebar.radio("Напрямок:", ["⚔️ Бригадні звіти", "🧨 Мінування", "🔥 Ураження", "📡 Спец. розділи"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

def to_native(val):
    try: return float(str(val).replace(',', '.'))
    except: return 0.0

def get_pts(qty, target, status):
    target_clean = str(target).strip()
    unit_p = POINTS_MAP.get(target_clean, 0)
    total_p = qty * unit_p
    status_clean = str(status).lower().strip()
    if "не верифіковано" in status_clean:
        match = re.search(r'(\d+)', status_clean)
        unv_q = float(match.group(1)) if match else qty
        return max(0.0, total_p - (unv_q * unit_p))
    return total_p

# --- 5. ВІДОБРАЖЕННЯ ДАНИХ ---
try:
    # --- БРИГАДНІ ЗВІТИ ---
    if category == "⚔️ Бригадні звіти":
        brig_tabs = ["Бригадний1", "Бригадний ЗГ"]
        selected_tab = st.selectbox("Оберіть розділ звіту:", brig_tabs)
        df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
        
        if selected_tab == "Бригадний1":
            data = df.values.tolist()
            units_cols = {"1аемб": [0,1,2,3], "2аемб": [4,5,6,7], "3аемб": [8,9,10,11], "4аемб": [12,13,14,15], "ЗРДН": [16,17,18,19]}
            clrs = {'1аемб': '#92D050', '2аемб': '#A5A5A5', '3аемб': '#4472C4', '4аемб': '#ED7D31', 'ЗРДН': '#FFC000'}
            
            clean_results = []
            for u_name, cols in units_cols.items():
                last_dt = None
                for row in data[2:]:
                    d_raw, target, qty_raw, verif = str(row[cols[0]]), str(row[cols[1]]), row[cols[2]], row[cols[3]]
                    if d_raw.strip() != "":
                        dt = pd.to_datetime(d_raw, dayfirst=True, errors='coerce')
                        if pd.notnull(dt): last_dt = dt
                    if last_dt and target.strip() != "":
                        q = to_native(qty_raw)
                        p = get_pts(q, target, verif)
                        clean_results.append({"Дата": last_dt, "Бат": u_name, "Ціль": target.strip(), "Бали": p, "Шт": q})

            if clean_results:
                all_dates = sorted(list(set([r["Дата"] for r in clean_results])))
                x_labs = [d.strftime('%d.%m') for d in all_dates]
                fig = go.Figure()
                for b in units_cols.keys():
                    y_v = [sum(r["Бали"] for r in clean_results if r["Дата"] == d and r["Бат"] == b) for d in all_dates]
                    if sum(y_v) > 0:
                        fig.add_trace(go.Bar(x=x_labs, y=y_v, name=b, marker_color=clrs.get(b), text=[str(int(v)) if v>0 else "" for v in y_v], textposition='outside', textfont=dict(color='white')))
                fig.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=450, legend=dict(orientation="h", y=1.1), showlegend=True)
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("#### 🎯 Класифікація по підрозділах")
                sel_unit = st.selectbox("Оберіть батальйон для деталізації:", list(units_cols.keys()))
                u_table = []
                u_data = [r for r in clean_results if r["Бат"] == sel_unit]
                for t in sorted(list(set([r["Ціль"] for r in u_data]))):
                    t_q = sum(r["Шт"] for r in u_data if r["Ціль"] == t)
                    t_p = sum(r["Бали"] for r in u_data if r["Ціль"] == t)
                    u_table.append({"Тип цілі": t, "Кількість (шт)": int(t_q), "Бали": int(t_p)})
                st.table(pd.DataFrame(u_table).sort_values(by="Бали", ascending=False))

    # --- МІНУВАННЯ ---
    elif category == "🧨 Мінування":
        df = conn.read(worksheet="Мінування", ttl=300, header=None).fillna("")
        data_list = df.values.tolist()[1:]
        clean_rows = []
        for r in data_list:
            dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
            if pd.notnull(dt):
                v, u = get_pts(to_native(r[2]), "Міна", r[3]), 0 # Спрощена верифікація для мін
                # В мінуванні ми рахуємо штуки, тому поправимо:
                v_q, u_q = 0, 0
                st_cl = str(r[3]).lower()
                if "не верифіковано" in st_cl:
                    m = re.search(r'(\d+)', st_cl)
                    u_q = float(m.group(1)) if m else to_native(r[2])
                    v_q = max(0, to_native(r[2]) - u_q)
                else: v_q = to_native(r[2])
                
                clean_rows.append({"Дата_dt": dt, "День": dt.day, "Місяць": dt.month, "Рік": dt.year, "Місяць_Рік": MONTHS_UKR.get(dt.month, "M") + " " + str(dt.year), "S": dt.year*100+dt.month, "V": v_q, "U": u_q})
        if clean_rows:
            m_o = sorted(list(set([(r["Місяць_Рік"], r["S"]) for r in clean_rows])), key=lambda x: x[1], reverse=True)
            sel_m = st.selectbox("Період:", [x[0] for x in m_o])
            m_d = [r for r in clean_rows if r["Місяць_Рік"] == sel_m]
            y, m = m_d[0]["Рік"], m_d[0]["Місяць"]
            labs = [f"{d}.{str(m).zfill(2)}" for d in range(1, pd.Period(f"{y}-{m}").days_in_month + 1)]
            v_v, u_v = {l: 0.0 for l in labs}, {l: 0.0 for l in labs}
            for r in m_d:
                l = f"{r['День']}.{str(m).zfill(2)}"
                v_v[l] += r["V"]; u_v[l] += r["U"]
            st.metric("ЗАГАЛЬНА КІЛЬКІСТЬ МІН:", f"{int(sum(v_v.values()))}")
            f_m = go.Figure()
            f_m.add_trace(go.Bar(x=labs, y=[v_v[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            f_m.add_trace(go.Bar(x=labs, y=[u_v[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            f_m.add_trace(go.Scatter(x=labs, y=[v_v[l]+u_v[l] for l in labs], mode='text', text=[str(int(v_v[l])) if v_v[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white', size=12)))
            f_m.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(f_m, use_container_width=True)

    # --- УРАЖЕННЯ ---
    elif category == "🔥 Ураження":
        urazh_tabs = ["Ураження 03.2026", "Ураження 04.2026", "Ураження 02.2026"]
        selected_tab = st.selectbox("Оберіть період:", urazh_tabs)
        df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
        data_list = df.values.tolist()[1:]
        clean_rows, last_dt = [], None
        for r in data_list:
            if str(r[0]).strip() != "":
                dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                if pd.notnull(dt): last_dt = dt
            if last_dt and str(r[1]).strip() != "":
                q = to_native(r[2])
                target = str(r[1]).strip()
                v_p = get_pts(q, target, r[3])
                u_p = (q * POINTS_MAP.get(target, 0)) - v_p
                clean_rows.append({"Дата": last_dt, "V": v_p, "U": u_p, "День": last_dt.day, "Місяць": last_dt.month, "Рік": last_dt.year, "Ціль": target, "Q": q})
        if clean_rows:
            y, m = clean_rows[0]["Рік"], clean_rows[0]["Місяць"]
            labs = [f"{d}.{str(m).zfill(2)}" for d in range(1, pd.Period(f"{y}-{m}").days_in_month + 1)]
            v_v, u_v = {l: 0.0 for l in labs}, {l: 0.0 for l in labels if l in labs} # безпечний словник
            v_v = {l: 0.0 for l in labs}; u_v = {l: 0.0 for l in labs}
            for r in clean_rows:
                l = f"{r['День']}.{str(m).zfill(2)}"
                v_v[l] += r["V"]; u_v[l] += r["U"]
            st.metric("ЗАГАЛЬНІ БАЛИ:", f"{int(sum(v_v.values()))}")
            f_u = go.Figure()
            f_u.add_trace(go.Bar(x=labs, y=[v_v[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            f_u.add_trace(go.Bar(x=labs, y=[u_v[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            f_u.add_trace(go.Scatter(x=labs, y=[v_v[l]+u_v[l] for l in labs], mode='text', text=[str(int(v_v[l])) if v_v[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white')))
            f_u.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(f_u, use_container_width=True)

except Exception as e:
    st.error(f"Помилка: {e}")
