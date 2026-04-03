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
    "Автомобіль": 5, "Гаубиця": 40, "ББМ": 20, "Гармата": 20, "Мінування": 1
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
    if category == "⚔️ Бригадні звіти":
        df = conn.read(worksheet="Бригадний1", ttl=300, header=None).fillna("")
        st.markdown(f"<h3 style='text-align:center; color:white; font-weight:300;'>⚔️ ЗАГАЛЬНОБРИГАДНИЙ ЗВІТ</h3>", unsafe_allow_html=True)
        
        data = df.values.tolist()
        units_cols = {
            "1аемб": [0,1,2,3,4], "2аемб": [5,6,7,8,9],
            "3аемб": [10,11,12,13,14], "4аемб": [15,16,17,18,19],
            "ЗРДН": [20,21,22,23,24]
        }
        clrs = {'1аемб': '#92D050', '2аемб': '#A5A5A5', '3аемб': '#4472C4', '4аемб': '#ED7D31', 'ЗРДН': '#FFC000'}
        
        clean_results = []
        for u_name, cols in units_cols.items():
            last_dt = None
            for row in data[1:]:
                if len(row) <= max(cols): continue
                
                d_raw = str(row[cols[0]]).strip()
                target = str(row[cols[1]]).strip()
                
                if d_raw != "":
                    dt = pd.to_datetime(d_raw, dayfirst=True, errors='coerce')
                    if pd.notnull(dt): last_dt = dt
                
                if not last_dt: continue

                # Ураження
                if target != "" and target != "Ціль":
                    q_total = to_native(row[cols[2]])
                    v_pts, v_qty = calculate_verif_data(q_total, target, str(row[cols[3]]))
                    if q_total > 0:
                        clean_results.append({"Дата": last_dt, "Бат": u_name, "Ціль": target, "Бали": v_pts, "Шт_всього": q_total, "Шт_вериф": v_qty})
                
                # Мінування
                m_qty = to_native(row[cols[4]])
                if m_qty > 0:
                    clean_results.append({"Дата": last_dt, "Бат": u_name, "Ціль": "Мінування", "Бали": m_qty, "Шт_всього": m_qty, "Шт_вериф": m_qty})

        if clean_results:
            all_dates = sorted(list(set([r["Дата"] for r in clean_results])))
            x_labs = [d.strftime('%d.%m') for d in all_dates]
            
            st.metric("ЗАГАЛЬНИЙ РЕЗУЛЬТАТ БРИГАДИ (УРАЖЕННЯ + МІНУВАННЯ):", f"{int(sum(r['Бали'] for r in clean_results))}")

            tab_cum, tab_daily = st.tabs(["📈 Прогрес за місяць (накопичувально)", "📊 Статистика по днях"])
            
            with tab_cum:
                fig_cum = go.Figure()
                for b in units_cols.keys():
                    y_cum = []; acc = 0.0
                    for d in all_dates:
                        acc += sum(r["Бали"] for r in clean_results if r["Дата"] == d and r["Бат"] == b)
                        y_cum.append(acc)
                    if sum(y_cum) > 0:
                        txt = [f"{int(v)}<br><span style='font-size:10px;'>{b}</span>" if v > 0 else "" for v in y_cum]
                        fig_cum.add_trace(go.Bar(x=x_labs, y=y_cum, name=b, marker_color=clrs.get(b), text=txt, textposition='outside', textfont=dict(color='white')))
                fig_cum.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=500, legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_cum, use_container_width=True)

            with tab_daily:
                fig_daily = go.Figure()
                for b in units_cols.keys():
                    y_v = [sum(r["Бали"] for r in clean_results if r["Дата"] == d and r["Бат"] == b) for d in all_dates]
                    if sum(y_v) > 0:
                        txt = [f"{int(v)}<br><span style='font-size:10px;'>{b}</span>" if v > 0 else "" for v in y_v]
                        fig_daily.add_trace(go.Bar(x=x_labs, y=y_v, name=b, marker_color=clrs.get(b), text=txt, textposition='outside', textfont=dict(color='white')))
                fig_daily.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=500, legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_daily, use_container_width=True)

            st.markdown("---")
            sel_unit = st.selectbox("Оберіть підрозділ для деталізації:", list(units_cols.keys()))
            u_data = [r for r in clean_results if r["Бат"] == sel_unit]
            u_summary = []
            for t in sorted(list(set([r["Ціль"] for r in u_data]))):
                q_t = sum(r["Шт_всього"] for r in u_data if r["Ціль"] == t)
                q_v = sum(r["Шт_вериф"] for r in u_data if r["Ціль"] == t)
                p_v = sum(r["Бали"] for r in u_data if r["Ціль"] == t)
                u_summary.append({"Тип цілі": t, "Всього (шт)": int(q_t), "Верифіковано (шт)": int(q_v), "Бали": int(p_v)})
            st.table(pd.DataFrame(u_summary).sort_values(by="Бали", ascending=False))

    elif category == "🧨 Мінування":
        df = conn.read(worksheet="Мінування", ttl=300, header=None).fillna("")
        data_list = df.values.tolist()[1:]; clean_rows = []
        for r in data_list:
            dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
            if pd.notnull(dt):
                qty = to_native(r[2]); st_cl = str(r[3]).lower()
                if "не верифіковано" in st_cl:
                    m = re.search(r'(\d+)', st_cl)
                    u_q = float(m.group(1)) if m else qty
                    v_q = max(0, qty - u_q); u_q = u_q
                else: v_q = qty; u_q = 0
                clean_rows.append({"Дата": dt, "День": dt.day, "Місяць_Рік": MONTHS_UKR.get(dt.month, "M") + " " + str(dt.year), "S": dt.year*100+dt.month, "V": v_q, "U": u_q})
        if clean_rows:
            m_o = sorted(list(set([(r["Місяць_Рік"], r["S"]) for r in clean_rows])), key=lambda x: x[1], reverse=True)
            sel_m = st.selectbox("Період:", [x[0] for x in m_o])
            m_d = [r for r in clean_rows if r["Місяць_Рік"] == sel_m]
            y, m = m_d[0]["Дата"].year, m_d[0]["Дата"].month
            labs = [f"{d}.{str(m).zfill(2)}" for d in range(1, pd.Period(f"{y}-{m}").days_in_month + 1)]
            v_v, u_v = {l: 0.0 for l in labs}, {l: 0.0 for l in labs}
            for r in m_d:
                l = f"{r['Дата'].day}.{str(m).zfill(2)}"
                v_v[l] += r["V"]; u_v[l] += r["U"]
            st.metric("ЗАГАЛЬНА КІЛЬКІСТЬ МІН:", f"{int(sum(v_v.values()))}")
            f_m = go.Figure()
            f_m.add_trace(go.Bar(x=labs, y=[v_v[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            f_m.add_trace(go.Bar(x=labs, y=[u_v[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            f_m.add_trace(go.Scatter(x=labs, y=[v_v[l]+u_v[l] for l in labs], mode='text', text=[str(int(v_v[l])) if v_v[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white', size=12)))
            f_m.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=400, xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(f_m, use_container_width=True)

    elif category == "🔥 Ураження":
        urazh_tabs = ["Ураження 04.2026", "Ураження 03.2026"]
        selected_tab = st.selectbox("Період:", urazh_tabs)
        df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
        data_list = df.values.tolist()[1:]; clean_rows, last_dt = [], None
        for r in data_list:
            if str(r[0]).strip() != "":
                dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                if pd.notnull(dt): last_dt = dt
            if last_dt and str(r[1]).strip() != "":
                q = to_native(r[2]); v_p, v_q = calculate_verif_data(q, r[1], r[3])
                clean_rows.append({"Дата": last_dt, "V": v_p, "U": (q * POINTS_MAP.get(str(r[1]).strip(), 0)) - v_p, "Ціль": str(r[1]).strip(), "Q": q, "QV": v_q})
        if clean_rows:
            st.metric("ВЕРИФІКОВАНІ БАЛИ БАТАЛЬЙОНУ:", f"{int(sum(r['V'] for r in clean_rows))}")
            y, m = clean_rows[0]["Дата"].year, clean_rows[0]["Дата"].month
            labs = [f"{d}.{str(m).zfill(2)}" for d in range(1, pd.Period(f"{y}-{m}").days_in_month + 1)]
            v_v, u_v, obj_stats = {l: 0.0 for l in labs}, {l: 0.0 for l in labs}, {}
            for r in clean_rows:
                l = f"{r['Дата'].day}.{str(m).zfill(2)}"
                v_v[l] += r["V"]; u_v[l] += r["U"]
                n = r["Ціль"]
                if n not in obj_stats: obj_stats[n] = [0, 0, 0]
                obj_stats[n][0] += r["Q"]; obj_stats[n][1] += r["QV"]; obj_stats[n][2] += r["V"]
            f_u = go.Figure()
            f_u.add_trace(go.Bar(x=labs, y=[v_v[l] for l in labs], name='Вериф', marker_color='#444444'))
            f_u.add_trace(go.Bar(x=labs, y=[u_v[l] for l in labs], name='Не вериф', marker_color='#CC0000'))
            f_u.add_trace(go.Scatter(x=labs, y=[v_v[l]+u_v[l] for l in labs], mode='text', text=[str(int(v_v[l])) if v_v[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white')))
            f_u.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=400, xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(f_u, use_container_width=True)
            st.table(pd.DataFrame([{"Тип цілі": k, "Всього (шт)": int(v[0]), "Верифіковано (шт)": int(v[1]), "Бали": int(v[2])} for k, v in sorted(obj_stats.items(), key=lambda x: x[1][2], reverse=True)]))

except Exception as e:
    st.error(f"Помилка: {e}")
