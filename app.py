import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64
import re

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 77 ОАЕМБр", layout="wide", page_icon="🇺🇦")

USER_PASSWORD = "2887" 
MONTHS_UKR = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень", 5: "Травень", 6: "Червень",
    7: "Липень", 8: "Серпень", 9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень"
}

# --- 2. ЕКРАН ВХОДУ (ОКУРАТНИЙ ДИЗАЙН) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)
        st.write("<br><br><br><br>", unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1.2, 1.5, 1.2])
        with col_c:
            st.markdown("""
                <div style='background:rgba(255,255,255,0.03); padding:30px; border-radius:15px; border:1px solid rgba(255,255,255,0.1); text-align:center;'>
                    <h2 style='color:white; margin-bottom: 0; font-weight: 300; letter-spacing: 1px;'>🛡️ СИТУАЦІЙНИЙ ЦЕНТР</h2>
                    <p style='color:#aaa; font-size: 14px; margin-top: 5px;'>77 ОАЕМБр • ДШВ ЗСУ 🇺🇦</p>
                    <div style='margin: 25px 0;'></div>
                </div>
            """, unsafe_allow_html=True)
            pwd = st.text_input("КОД ДОСТУПУ:", type="password", placeholder="****")
            if st.button("УВІЙТИ В СИСТЕМУ"):
                if pwd == USER_PASSWORD:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("Невірний код")
        return False
    return True

if not check_password(): st.stop()

# --- 3. ЗАГАЛЬНИЙ ДИЗАЙН ---
def set_design(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except: bg_css = 'background-color: #0E1117;'
    st.markdown(f'''
    <style>
    .stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }} 
    .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }} 
    [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}
    [data-testid="stMetricValue"] {{ font-size: 24px !important; color: #ffd700; }}
    </style>
    ''', unsafe_allow_html=True)

set_design('background.jpg')

# --- 4. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.markdown("### 🛠️ УПРАВЛІННЯ")
category = st.sidebar.radio("Напрямок:", ["⚔️ Бригадні звіти", "📈 Рейтинг та Бали", "🧨 Мінування", "🔥 Ураження", "📡 Спец. розділи"])

selected_tab = ""
if category == "⚔️ Бригадні звіти": selected_tab = st.sidebar.selectbox("Розділ:", ["Бригадний ЗГ", "Бригадний"])
elif category == "📈 Рейтинг та Бали": selected_tab = st.sidebar.selectbox("Розділ:", ["Е-Бали", "Розрахунки"])
elif category == "🧨 Мінування": selected_tab = "Мінування"
elif category == "🔥 Ураження":
    months = ["04.2026", "03.2026", "02.2026", "01.2026", "12.2025", "11.2025"]
    selected_tab = f"Ураження {st.sidebar.selectbox('Період:', months)}"
else: selected_tab = st.sidebar.selectbox("Розділ:", ["ЗГ", "НРК"])

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

# --- 5. ВІДОБРАЖЕННЯ ---
try:
    df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
    st.markdown(f"<h3 style='text-align:center; color:white; font-weight:300;'>📊 {selected_tab}</h3>", unsafe_allow_html=True)

    if selected_tab == "Мінування":
        data_list = df.values.tolist()
        rows = data_list[1:]
        clean_rows = []
        for r in rows:
            try: 
                dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                if pd.notnull(dt):
                    total = to_native(r[2])
                    v, u = get_verif_data(total, r[3])
                    clean_rows.append({
                        "Дата_dt": dt, "День": dt.day, "Місяць": dt.month, "Рік": dt.year,
                        "Місяць_Рік": MONTHS_UKR.get(dt.month, "M") + " " + str(dt.year),
                        "Сорт": dt.year * 100 + dt.month, "V": v, "U": u
                    })
            except: continue

        if clean_rows:
            m_options = sorted(list(set([(r["Місяць_Рік"], r["Сорт"]) for r in clean_rows])), key=lambda x: x[1], reverse=True)
            sel_m_label = st.selectbox("Період перегляду:", [x[0] for x in m_options])
            
            m_data = [r for r in clean_rows if r["Місяць_Рік"] == sel_m_label]
            y, m_num = m_data[0]["Рік"], m_data[0]["Місяць"]
            num_days = pd.Period(f"{y}-{m_num}").days_in_month
            labels = [f"{d}.{str(m_num).zfill(2)}" for d in range(1, num_days + 1)]
            v_vals = {l: 0.0 for l in labels}; u_vals = {l: 0.0 for l in labels}
            for r in m_data:
                l = f"{r['День']}.{str(m_num).zfill(2)}"
                v_vals[l] += r["V"]; u_vals[l] += r["U"]
            
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(x=labels, y=[v_vals[l] for l in labels], name='Верифіковано', marker_color='#444444'))
            fig1.add_trace(go.Bar(x=labels, y=[u_vals[l] for l in labels], name='Не верифіковано', marker_color='#CC0000'))
            fig1.add_trace(go.Scatter(
                x=labels, y=[v_vals[l] + u_vals[l] for l in labels],
                mode='text', text=[str(int(v_vals[l])) if v_vals[l]>0 else "" for l in labels],
                textposition='top center', showlegend=False, textfont=dict(color='white', size=12)
            ))
            fig1.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400, 
                              xaxis=dict(type='category', tickangle=-45, gridcolor='rgba(255,255,255,0.05)'), margin=dict(t=40))
            st.plotly_chart(fig1, use_container_width=True)

            st.markdown("#### 📈 Загальна динаміка")
            m_t, m_u, m_s = {}, {}, {}
            for r in clean_rows:
                mn = r["Місяць_Рік"]
                m_t[mn] = m_t.get(mn, 0) + r["V"]; m_u[mn] = m_u.get(mn, 0) + r["U"]; m_s[mn] = r["Сорт"]
            sorted_m = sorted(m_t.keys(), key=lambda x: m_s[x])
            
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=sorted_m, y=[m_t[mx] for mx in sorted_m], name="Верифіковано", marker_color='#444444'))
            fig2.add_trace(go.Bar(x=sorted_m, y=[m_u[mx] for mx in sorted_m], name="Не верифіковано", marker_color='#CC0000'))
            fig2.add_trace(go.Scatter(
                x=sorted_m, y=[m_t[mx] + m_u[mx] for mx in sorted_m],
                mode='text', text=[str(int(m_t[mx])) for mx in sorted_m],
                textposition='top center', showlegend=False, textfont=dict(color='white', size=14)
            ))
            fig2.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400, margin=dict(t=40))
            st.plotly_chart(fig2, use_container_width=True)

            with st.expander("📂 ДЕТАЛЬНИЙ ЖУРНАЛ"):
                st.dataframe(df.iloc[1:].astype(str), use_container_width=True, hide_index=True)

    elif selected_tab == "Бригадний ЗГ":
        sub = [str(x) for x in df.iloc[1].values]
        d_rows = df.iloc[2:].values.tolist()
        def bc(title, start_c):
            f = go.Figure()
            clrs = {'1 аемб': '#92D050', '2 аемб': '#A5A5A5', '3 аемб': '#4472C4', '4 аемб': '#ED7D31'}
            for u, c in clrs.items():
                idx = [i for i, x in enumerate(sub) if u in x and i >= start_c and i < start_c+6]
                if idx:
                    v = [float(to_native(r[idx[0]])) for r in d_rows if r[0] != ""]
                    f.add_trace(go.Bar(x=[str(r[0]) for r in d_rows if r[0] != ""], y=v, name=u, marker_color=c, text=[str(int(val)) for val in v], textposition='outside'))
            f.update_layout(title=title, barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            return f
        st.plotly_chart(bc("🏆 ЗАГАЛЬНИЙ РЕЗУЛЬТАТ", 0), use_container_width=True)
        st.plotly_chart(bc("🔥 УРАЖЕННЯ", 6), use_container_width=True)
        st.plotly_chart(bc("🧨 МІНУВАННЯ", 12), use_container_width=True)

    elif selected_tab == "Е-Бали":
        d_list = df.values.tolist()[1:]
        dates = [str(r[0]) for r in d_list]
        f = go.Figure()
        f.add_trace(go.Bar(x=dates, y=[float(to_native(r[1])) for r in d_list], name='Попередній', marker_color='#A5A5A5', text=[str(int(to_native(r[1]))) for r in d_list], textposition='outside'))
        f.add_trace(go.Bar(x=dates, y=[float(to_native(r[2])) for r in d_list], name='Поточний', marker_color='#92D050', text=[str(int(to_native(r[2]))) for r in d_list
