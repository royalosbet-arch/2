import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import base64

# --- 1. CONFIG & AUTH ---
st.set_page_config(page_title="SITUATION CENTER 1.0", layout="wide", page_icon="⚡")

USER_PASSWORD = "1234" # Ваш пароль

def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)
        st.write("<br><br><br>", unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown("""
                <div style='background:rgba(255,255,255,0.03); padding:40px; border-radius:20px; border:1px solid #333; text-align:center;'>
                    <h1 style='color:white; letter-spacing: 5px;'>SITUATION CENTER</h1>
                    <p style='color:#555;'>1st AIRBORNE ASSAULT BATTALION</p>
                </div>
            """, unsafe_allow_html=True)
            pwd = st.text_input("ENTER ACCESS CODE:", type="password")
            if st.button("AUTHORIZE"):
                if pwd == USER_PASSWORD:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("ACCESS DENIED")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. ADVANCED CSS (MILITARY TECH STYLE) ---
def set_design(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except: bg_css = 'background-color: #0E1117;'

    st.markdown(f'''
    <style>
    .stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }}
    /* Стиль карток показників */
    [data-testid="stMetric"] {{
        background: rgba(10, 15, 20, 0.8) !important;
        border-left: 5px solid #ff4b4b !important;
        border-radius: 5px !important;
        padding: 20px !important;
    }}
    /* Стиль кастомних карток подій */
    .event-card {{
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 20px; }}
    .stTabs [data-baseweb="tab"] {{
        background-color: rgba(255,255,255,0.05);
        border-radius: 5px;
        padding: 10px 20px;
        color: white;
    }}
    </style>
    ''', unsafe_allow_html=True)

set_design('background.jpg')

# --- 3. DATA LOADING ---
conn = st.connection("gsheets", type=GSheetsConnection)
tabs_to_show = ["Ураження 04.2026", "Ураження 03.2026", "Ураження 02.2026", "Ураження 01.2026", "Ураження 12.2025", "Ураження 11.2025", "ЗГ", "Розрахунки", "Е-Бали", "НРК", "Мінування"]

# Sidebar
st.sidebar.markdown("### 🗂️ РЕЗЕРВ ДАНИХ")
selected_tab = st.sidebar.selectbox("Оберіть сектор:", tabs_to_show)
if st.sidebar.button('🔄 СИНХРОНІЗУВАТИ'):
    st.cache_data.clear()
    st.rerun()

try:
    df = conn.read(worksheet=selected_tab, ttl=300).dropna(how='all', axis=0).fillna("")

    # --- 4. DASHBOARD LAYOUT ---
    st.markdown(f"<h1 style='color:white;'>📡 СЕКТОР: {selected_tab}</h1>", unsafe_allow_html=True)
    
    # TOP METRICS
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("ОПЕРАЦІЙ", len(df[df.iloc[:,0]!=""]))
    
    # Пошук колонок для логіки
    res_col = [c for c in df.columns if 'результат' in c.lower() or 'статус' in c.lower()]
    val_col = [c for c in df.columns if 'разом' in c.lower() or 'сума' in c.lower()]
    
    if res_col:
        hits = df[df[res_col[0]].astype(str).str.contains("уражен", case=False, na=False)].shape[0]
        with m2: st.metric("УСПІШНО", hits)
    
    if val_col:
        total = pd.to_numeric(df[val_col[0]], errors='coerce').sum()
        with m3: st.metric("БАЛИ", f"{total:.1f}")

    st.write("---")

    # MAIN VISUALS
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("#### 📈 АНАЛІТИЧНИЙ ГРАФІК")
        if "Е-Бали" in selected_tab and val_col:
            # Спеціальний чарт для рейтингу
            df_p = df.copy()
            df_p[val_col[0]] = pd.to_numeric(df_p[val_col[0]], errors='coerce').fillna(0)
            df_p = df_p[df_p[val_col[0]] > 0].sort_values(by=val_col[0], ascending=True)
            fig = px.bar(df_p, x=val_col[0], y=df.columns[0], orientation='h', text=val_col[0],
                         color=val_col[0], color_continuous_scale='Reds')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Кругова діаграма для інших розділів
            target_col = [c for c in df.columns if 'цілі' in c.lower() or 'тип' in c.lower()]
            if target_col:
                fig = px.pie(df[df[target_col[0]]!=""], names=target_col[0], hole=0.5)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white")
                st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("#### 🔔 ОСТАННІ ПОДІЇ")
        # Виводимо останні 5 записів як картки, а не таблицю
        recent_data = df[df.iloc[:,0] != ""].tail(5).iloc[::-1]
        for _, row in recent_data.iterrows():
            color = "#2ecc71" if "уражен" in str(row).lower() else "#555"
            st.markdown(f"""
                <div class="event-card" style="border-left: 4px solid {color};">
                    <small style='color:#888;'>{row[0]}</small><br>
                    <strong>{row[1]}</strong><br>
                    <span style='color:{color}; font-size: 0.8em;'>● {row[res_col[0]] if res_col else ""}</span>
                </div>
            """, unsafe_allow_html=True)

    # DETAILED DATA (Сховано в екпандер)
    with st.expander("📂 ВІДКРИТИ ПОВНИЙ РЕЄСТР (ТАБЛИЦЯ)"):
        search = st.text_input("Пошук по базі:", placeholder="Введіть назву або прізвище...")
        if search:
            df_show = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
        else:
            df_show = df
        st.dataframe(df_show, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"SYSTEM ERROR: {e}")
