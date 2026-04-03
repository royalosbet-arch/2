import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64
import re

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

# --- СЛОВНИК БАЛІВ ДЛЯ УРАЖЕНЬ ---
POINTS_MAP = {
    "Антена": 4, "О/С 200": 9, "О/С 300": 9, "Молнія": 20, "ФПВ": 7, "Мавік": 7,
    "Бомбер": 7, "РЛС": 15, "Міномет": 10, "ЛАТ": 10, "Генератор": 4, "РЕБ": 4,
    "Фортифікація": 1, "Укриття": 1, "Електросамокат": 4, "Квадроцикл": 4, "Мотоцикл": 4,
    "Танк": 50, "САУ": 30, "ББМ": 20, "Гармата": 20
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

# --- 4. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("### 🛠️ УПРАВЛІННЯ")
category = st.sidebar.radio("Оберіть напрямок:", ["⚔️ Бригадні звіти", "📈 Рейтинг та Бали", "🧨 Мінування", "🔥 Ураження", "📡 Спец. розділи"])

selected_tab = ""

# Логіка вибору вкладки
if category == "⚔️ Бригадні звіти":
    selected_tab = st.sidebar.selectbox("Оберіть розділ:", ["Бригадний ЗГ", "Бригадний"])
elif category == "📈 Рейтинг та Бали":
    selected_tab = st.sidebar.selectbox("Оберіть розділ:", ["Е-Бали", "Розрахунки"])
elif category == "🧨 Мінування":
    selected_tab = "Мінування"
elif category == "🔥 Ураження":
    # Список місяців (вкладок у Google Sheets)
    urazh_months = ["03.2026", "04.2026", "02.2026", "01.2026", "12.2025"]
    selected_month = st.sidebar.selectbox("Оберіть місяць уражень:", urazh_months)
    selected_tab = f"Ураження {selected_month}"
else:
    selected_tab = st.sidebar.selectbox("Оберіть розділ:", ["ЗГ", "НРК"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

def to_native(val):
    try: return float(str(val).replace(',', '.'))
    except: return 0.0

def get_verif_data(total, text):
    txt = str(text).lower().strip()
    if "не верифіковано" in txt:
        match = re.search(r'(\d+)', txt)
        unverif = float(match.group(1)) if match else 0.0
        return max(0.0, total - unverif), unverif
    elif "верифіковано" in txt or txt == "так": return total, 0.0
    return 0.0, total

# --- 5. ВІДОБРАЖЕННЯ ДАНИХ ---
try:
    df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
    st.markdown(f"<h3 style='text-align:center; color:white; font-weight:300;'>📊 {selected_tab}</h3>", unsafe_allow_html=True)

    # --- УРАЖЕННЯ ---
    if "Ураження" in selected_tab:
        data_list = df.values.tolist()[1:]
        clean_rows = []
        last_date = None
        for r in data_list:
            raw_date, target_name, qty, status = str(r[0]).strip(), str(r[1]).strip(), to_native(r[2]), str(r[3])
            if raw_date != "":
                dt = pd.to_datetime(raw_date, dayfirst=True, errors='coerce')
                if pd.notnull(dt): last_date = dt
            if last_date and target_name != "" and qty > 0:
                unit_price = POINTS_MAP.get(target_name, 0)
                total_pts = qty * unit_price
                
                # Логіка верифікації балів
                v_p, u_p = 0.0, 0.0
                if "не верифіковано" in status.lower():
                    match = re.search(r'(\d+)', status)
                    unv_qty = float(match.group(1)) if match else qty
                    u_p = unv_qty * unit_price
                    v_p = max(0.0, total_pts - u_p)
                else:
                    v_p, u_p = get_verif_data(total_pts, status)
                
                clean_rows.append({"Дата_dt": last_date, "День": last_date.day, "Місяць": last_date.month, "Рік": last_date.year, "V": v_p, "U": u_p})

        if clean_rows:
            y, m = clean_rows[0]["Рік"], clean_rows[0]["Місяць"]
            num_days = pd.Period(f"{y}-{m}").days_in_month
            labels = [f"{d}.{str(m).zfill(2)}" for d in range(1, num_days + 1)]
            v_vals = {l: 0.0 for l in labels}; u_vals = {l: 0.0 for l in labels}
            for r in clean_rows:
                l = f"{r['День']}.{str(m).zfill(2)}"
                v_vals[l] += r["V"]; u_vals[l] += r["U"]
            
            total_sum = sum(v_vals.values())
            st.metric("ЗАГАЛЬНА КІЛЬКІСТЬ ВЕРИФІКОВАНИХ БАЛІВ:", f"{int(total_sum)}")

            fig = go.Figure()
            fig.add_trace(go.Bar(x=labels, y=[v_vals[l] for l in labels], name='Верифіковано', marker_color='#444444'))
            fig.add_trace(go.Bar(x=labels, y=[u_vals[l] for l in labels], name='Не верифіковано', marker_color='#CC0000'))
            fig.add_trace(go.Scatter(x=labels, y=[v_vals[l]+u_vals[l] for l in labels], mode='text', text=[str(int(v_vals[l])) if v_vals[l]>0 else "" for l in labels], textposition='top center', showlegend=False, textfont=dict(color='white', size=13)))
            fig.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("📂 ЖУРНАЛ УРАЖЕНЬ"):
                st.dataframe(df.iloc[1:, :4], use_container_width=True, hide_index=True)

    # --- МІНУВАННЯ ---
    elif selected_tab == "Мінування":
        data_list = df.values.tolist()[1:]
        clean_rows = []
        for r in data_list:
            try:
                dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                if pd.notnull(dt):
                    total = to_native(r[2])
                    v, u = get_verif_data(total, r[3])
                    clean_rows.append({"Дата_dt": dt, "День": dt.day, "Місяць": dt.month, "Рік": dt.year, "Місяць_Рік": MONTHS_UKR.get(dt.month, "M") + " " + str(dt.year), "S": dt.year*100+dt.month, "V": v, "U": u})
            except: continue
        if clean_rows:
            m_opts = sorted(list(set([(r["Місяць_Рік"], r["S"]) for r in clean_rows])), key=lambda x: x[1], reverse=True)
            sel_m = st.selectbox("Період перегляду:", [x[0] for x in m_opts])
            m_data = [r for r in clean_rows if r["Місяць_Рік"] == sel_m]
            y, m = m_data[0]["Рік"], m_data[0]["Місяць"]
            num_days = pd.Period(f"{y}-{m}").days_in_month
            labels = [f"{d}.{str(m).zfill(2)}" for d in range(1, num_days + 1)]
            v_v, u_v = {l: 0.0 for l in labels}, {l: 0.0 for l in labels}
            for r in m_data:
                l = f"{r['День']}.{str(m).zfill(2)}"
                v_v[l] += r["V"]; u_v[l] += r["U"]
            
            total_mines = sum(v_v.values())
            st.metric("ЗАГАЛЬНА КІЛЬКІСТЬ ВЕРИФІКОВАНИХ МІН:", f"{int(total_mines)}")

            fig1 = go.Figure()
            fig1.add_trace(go.Bar(x=labels, y=[v_v[l] for l in labels], name='Верифіковано', marker_color='#444444'))
            fig1.add_trace(go.Bar(x=labels, y=[u_v[l] for l in labels], name='Не верифіковано', marker_color='#CC0000'))
            fig1.add_trace(go.Scatter(x=labels, y=[v_v[l]+u_v[l] for l in labels], mode='text', text=[str(int(v_v[l])) if v_v[l]>0 else "" for l in labels], textposition='top center', showlegend=False, textfont=dict(color='white', size=13)))
            fig1.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(fig1, use_container_width=True)
            with st.expander("📂 АРХІВ МІНУВАННЯ"):
                st.dataframe(df.iloc[1:, :4], use_container_width=True, hide_index=True)

    # --- БРИГАДНИЙ ЗГ ---
    elif selected_tab == "Бригадний ЗГ":
        sub, d_rows = [str(x) for x in df.iloc[1].values], df.iloc[2:].values.tolist()
        x_dates = []
        for r in d_rows:
            dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
            x_dates.append(dt.strftime('%d.%m') if pd.notnull(dt) else str(r[0]))
        def bc(title, start_c):
            f = go.Figure()
            clrs = {'1 аемб': '#92D050', '2 аемб': '#A5A5A5', '3 аемб': '#4472C4', '4 аемб': '#ED7D31'}
            for u, c in clrs.items():
                idx = [i for i, x in enumerate(sub) if u in x and i >= start_c and i < start_c+6]
                if idx:
                    v = [to_native(r[idx[0]]) for r in d_rows if r[0] != ""]
                    text_l = [f"{int(val)}<br><span style='font-size:10px;'>{u}</span>" if val > 0 else "" for val in v]
                    f.add_trace(go.Bar(x=x_dates, y=[float(val) for val in v], name=u, marker_color=c, text=text_l, textposition='outside', textfont=dict(color='white')))
            f.update_layout(title=dict(text=title, font=dict(color='white')), barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", showlegend=False, xaxis=dict(type='category', tickangle=-45))
            return f
        st.plotly_chart(bc("🏆 ЗАГАЛЬНИЙ РЕЗУЛЬТАТ", 0), use_container_width=True)

    # --- Е-БАЛИ ---
    elif selected_tab == "Е-Бали":
        d_list = df.values.tolist()[1:]
        f = go.Figure()
        f.add_trace(go.Bar(x=[str(r[0]) for r in d_list], y=[to_native(r[2]) for r in d_list], name='Поточний', marker_color='#92D050', text=[str(int(to_native(r[2]))) for r in d_list], textposition='outside', textfont=dict(color='white')))
        f.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
        st.plotly_chart(f, use_container_width=True)

    else:
        st.dataframe(df.iloc[1:].astype(str), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка: {e}. Перевірте, чи правильно вказана назва вкладки в Google Sheets.")
