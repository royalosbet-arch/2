import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64
import re

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

# АКТУАЛЬНИЙ СЛОВНИК БАЛІВ
POINTS_MAP = {
    "О/С 200": 12, "О/С 300": 8, "Молнія": 10, "Укриття": 1, "Фортифікація": 1,
    "Антена": 4, "ФПВ": 6, "Танк": 40, "Бомбер": 6, "РЛС": 50, "САУ": 30,
    "Міномет": 5, "ЛАТ": 8, "Генератор": 4, "Електросамокат": 4, "Квадроцикл": 4,
    "Мотоцикл": 4, "РЕБ": 8, "Мавік": 6, "Орлан": 40, "Шахед": 20, "Ждун": 10,
    "Автомобіль": 5, "Гаубиця": 40, "ББМ": 20, "Гармата": 20
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

# --- 3. ДИЗАЙН САЙТУ ---
def set_design(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except: bg_css = 'background-color: #0E1117;'
    st.markdown(f'<style>.stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }} .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }} [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }} [data-testid="stMetricValue"] {{ color: #ffd700 !important; font-size: 36px !important; }}</style>', unsafe_allow_html=True)

set_design('background.jpg')

# --- 4. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("### 🛠️ УПРАВЛІННЯ")
category = st.sidebar.radio("Напрямок:", ["⚔️ Бригадні звіти", "🧨 Мінування", "🔥 Ураження", "📡 Спец. розділи"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

def to_native(val):
    try: return float(str(val).replace(',', '.'))
    except: return 0.0

def calculate_verif_data(qty, target, status):
    t_clean = str(target).strip()
    unit_p = POINTS_MAP.get(t_clean, 0)
    st_clean = str(status).lower().strip()
    if "не верифіковано" in st_clean:
        match = re.search(r'(\d+)', st_clean)
        unv_q = float(match.group(1)) if match else qty
        v_q = max(0.0, qty - unv_q)
    else: v_q = qty
    return v_q * unit_p, v_q

# --- 5. ВІДОБРАЖЕННЯ ДАНИХ ---
try:
    # --- КАТЕГОРІЯ: БРИГАДНІ ЗВІТИ (ОДИН РОЗДІЛ БЕЗ ВИБОРУ) ---
    if category == "⚔️ Бригадні звіти":
        selected_tab = "Бригадний1" 
        df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
        st.markdown(f"<h3 style='text-align:center; color:white; font-weight:300;'>⚔️ ЗАГАЛЬНОБРИГАДНИЙ ЗВІТ</h3>", unsafe_allow_html=True)
        
        data = df.values.tolist()
        units_cols = {"1аемб": [0,1,2,3], "2аемб": [4,5,6,7], "3аемб": [8,9,10,11], "4аемб": [12,13,14,15], "ЗРДН": [16,17,18,19]}
        clrs = {'1аемб': '#92D050', '2аемб': '#A5A5A5', '3аемб': '#4472C4', '4аемб': '#ED7D31', 'ЗРДН': '#FFC000'}
        
        clean_results = []
        for u_name, cols in units_cols.items():
            last_dt = None
            for row in data[2:]:
                d_raw, target, qty_raw, verif_status = str(row[cols[0]]), str(row[cols[1]]), row[cols[2]], row[cols[3]]
                if d_raw.strip() != "":
                    dt = pd.to_datetime(d_raw, dayfirst=True, errors='coerce')
                    if pd.notnull(dt): last_dt = dt
                if last_dt and target.strip() != "":
                    q_total = to_native(qty_raw)
                    v_pts, v_qty = calculate_verif_data(q_total, target, verif_status)
                    clean_results.append({
                        "Дата": last_dt, "Бат": u_name, "Ціль": target.strip(), 
                        "Бали": v_pts, "Шт_всього": q_total, "Шт_вериф": v_qty
                    })

        if clean_results:
            all_dates = sorted(list(set([r["Дата"] for r in clean_results])))
            x_labs = [d.strftime('%d.%m') for d in all_dates]
            
            tab_cum, tab_daily = st.tabs(["📈 Прогрес за місяць (накопичувально)", "📊 Статистика по днях"])
            
            with tab_cum:
                fig_cum = go.Figure()
                for b in units_cols.keys():
                    y_cum = []; total_acc = 0.0
                    for d in all_dates:
                        total_acc += sum(r["Бали"] for r in clean_results if r["Дата"] == d and r["Бат"] == b)
                        y_cum.append(total_acc)
                    if sum(y_cum) > 0:
                        fig_cum.add_trace(go.Bar(x=x_labs, y=y_cum, name=b, marker_color=clrs.get(b), text=[str(int(v)) if v > 0 else "" for v in y_cum], textposition='outside', textfont=dict(color='white')))
                fig_cum.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=450, legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_cum, use_container_width=True)

            with tab_daily:
                fig_daily = go.Figure()
                for b in units_cols.keys():
                    y_v = [sum(r["Бали"] for r in clean_results if r["Дата"] == d and r["Бат"] == b) for d in all_dates]
                    if sum(y_v) > 0:
                        fig_daily.add_trace(go.Bar(x=x_labs, y=y_v, name=b, marker_color=clrs.get(b), text=[str(int(v)) if v > 0 else "" for v in y_v], textposition='outside', textfont=dict(color='white')))
                fig_daily.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=450, legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_daily, use_container_width=True)

            st.markdown("---")
            st.markdown("#### 🎯 Детальна класифікація уражень")
            sel_unit = st.selectbox("Оберіть підрозділ для деталізації:", list(units_cols.keys()))
            u_data = [r for r in clean_results if r["Бат"] == sel_unit]
            u_summary = []
            for t in sorted(list(set([r["Ціль"] for r in u_data]))):
                q_t = sum(r["Шт_всього"] for r in u_data if r["Ціль"] == t)
                q_v = sum(r["Шт_вериф"] for r in u_data if r["Ціль"] == t)
                p_v = sum(r["Бали"] for r in u_data if r["Ціль"] == t)
                u_summary.append({"Тип цілі": t, "Всього (шт)": int(q_t), "Верифіковано (шт)": int(q_v), "Бали": int(p_v)})
            st.table(pd.DataFrame(u_summary).sort_values(by="Бали", ascending=False))

    # --- КАТЕГОРІЯ: МІНУВАННЯ ---
    elif category == "🧨 Мінування":
        df = conn.read(worksheet="Мінування", ttl=300, header=None).fillna("")
        data_list = df.values.tolist()[1:]
        clean_rows = []
        for r in data_list:
            dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
            if pd.notnull(dt):
                st_cl = str(r[3]).lower()
                qty = to_native(r[2])
                if "не верифіковано" in st_cl:
                    match = re.search(r'(\d+)', st_cl)
                    unv_q = float(match.group(1)) if match else qty
                    v_q = max(0, qty - unv_q); u_q = unv_q
                else: v_q = qty; u_q = 0
                clean_rows.append({"Дата": dt, "День": dt.day, "Місяць": dt.month, "Рік": dt.year, "Місяць_Рік": MONTHS_UKR.get(dt.month, "M") + " " + str(dt.year), "S": dt.year*100+dt.month, "V": v_q, "U": u_q})
        
        if clean_rows:
            m_opts = sorted(list(set([(r["Місяць_Рік"], r["S"]) for r in clean_rows])), key=lambda x: x[1], reverse=True)
            sel_m = st.selectbox("Період перегляду:", [x[0] for x in m_opts])
            m_d = [r for r in clean_rows if r["Місяць_Рік"] == sel_m]
            y, m = m_d[0]["Рік"], m_d[0]["Місяць"]
            labs = [f"{d}.{str(m).zfill(2)}" for d in range(1, pd.Period(f"{y}-{m}").days_in_month + 1)]
            v_v, u_v = {l: 0.0 for l in labs}, {l: 0.0 for l in labs}
            for r in m_d:
                l = f"{r['День']}.{str(m).zfill(2)}"
                v_v[l] += r["V"]; u_v[l] += r["U"]
            
            st.metric("ЗАГАЛЬНА КІЛЬКІСТЬ ВЕРИФІКОВАНИХ МІН:", f"{int(sum(v_v.values()))}")
            f_m = go.Figure()
            f_m.add_trace(go.Bar(x=labs, y=[v_v[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            f_m.add_trace(go.Bar(x=labs, y=[u_v[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            f_m.add_trace(go.Scatter(x=labs, y=[v_v[l]+u_v[l] for l in labs], mode='text', text=[str(int(v_v[l])) if v_v[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white', size=12)))
            f_m.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400, xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(f_m, use_container_width=True)

    # --- КАТЕГОРІЯ: УРАЖЕННЯ ---
    elif category == "🔥 Ураження":
        urazh_tabs = ["Ураження 04.2026", "Ураження 03.2026", "Ураження 02.2026"]
        selected_tab = st.selectbox("Період уражень:", urazh_tabs)
        df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
        
        data_list = df.values.tolist()[1:]
        clean_rows, last_dt = [], None
        for r in data_list:
            target_name = str(r[1]).strip()
            if str(r[0]).strip() != "":
                dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                if pd.notnull(dt): last_dt = dt
            if last_dt and target_name != "":
                q = to_native(r[2])
                v_pts, v_qty = calculate_verif_data(q, target_name, r[3])
                total_possible = q * POINTS_MAP.get(target_name, 0)
                clean_rows.append({"Дата": last_dt, "V": v_pts, "U": total_possible - v_pts, "Ціль": target_name, "Q": q, "QV": v_qty})
        
        if clean_rows:
            st.metric("ЗАГАЛЬНІ ВЕРИФІКОВАНІ БАЛИ БАТАЛЬЙОНУ:", f"{int(sum(r['V'] for r in clean_rows))}")
            y, m = clean_rows[0]["Дата"].year, clean_rows[0]["Дата"].month
            labs = [f"{d}.{str(m).zfill(2)}" for d in range(1, pd.Period(f"{y}-{m}").days_in_month + 1)]
            v_v, u_v, obj_stats = {l: 0.0 for l in labs}, {l: 0.0 for l in labs}, {}
            for r in clean_rows:
                l = f"{r['Дата'].day}.{str(m).zfill(2)}"
                v_v[l] += r["V"]; u_v[l] += r["U"]
                name = r["Ціль"]
                if name not in obj_stats: obj_stats[name] = [0, 0, 0]
                obj_stats[name][0] += r["Q"]; obj_stats[name][1] += r["QV"]; obj_stats[name][2] += r["V"]
            
            f_u = go.Figure()
            f_u.add_trace(go.Bar(x=labs, y=[v_v[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            f_u.add_trace(go.Bar(x=labs, y=[u_v[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            f_u.add_trace(go.Scatter(x=labs, y=[v_v[l]+u_v[l] for l in labs], mode='text', text=[str(int(v_v[l])) if v_v[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white')))
            f_u.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400, xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(f_u, use_container_width=True)
            
            st.markdown("#### 🎯 Статистика уражень за типами цілей")
            st.table(pd.DataFrame([{"Тип цілі": k, "Всього (шт)": int(v[0]), "Верифіковано (шт)": int(v[1]), "Бали": int(v[2])} for k, v in sorted(obj_stats.items(), key=lambda x: x[1][2], reverse=True)]))

except Exception as e:
    st.error(f"Помилка: {e}")
