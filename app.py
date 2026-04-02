import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64

# --- 1. НАЛАШТУВАННЯ ТА ПАРОЛЬ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

USER_PASSWORD = "2887" 

def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)
        st.write("<br><br><br>", unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown("""
                <div style='background:rgba(255,255,255,0.05); padding:40px; border-radius:20px; border:1px solid rgba(255,255,255,0.1); text-align:center;'>
                    <h2 style='color:white; margin-bottom: 0;'>🛡️ СИТУАЦІЙНИЙ ЦЕНТР</h2>
                    <p style='color:#888;'>1 аемб. АВТОРИЗАЦІЯ</p>
                </div>
            """, unsafe_allow_html=True)
            pwd = st.text_input("ВВЕДІТЬ КОД ДОСТУПУ:", type="password")
            if st.button("УВІЙТИ В СИСТЕМУ"):
                if pwd == USER_PASSWORD:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("❌ Невірний код.")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. ДИЗАЙН ---
def set_design(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except: bg_css = 'background-color: #0E1117;'
    
    st.markdown(f'''
    <style>
    .stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }}
    [data-testid="stMetric"] {{
        background: rgba(0, 0, 0, 0.7) !important;
        border-left: 5px solid #ff4b4b !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }}
    .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }}
    [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}
    </style>
    ''', unsafe_allow_html=True)

set_design('background.jpg')

# --- 3. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.title("🛠️ НАВІГАЦІЯ")
category = st.sidebar.radio(
    "Оберіть напрямок:",
    ["⚔️ Бригадні звіти", "📈 Рейтинг та Бали", "🧨 Мінування", "🔥 Ураження", "📡 Спец. розділи"]
)

selected_tab = ""
if category == "⚔️ Бригадні звіти":
    selected_tab = st.sidebar.selectbox("Розділ:", ["Бригадний ЗГ", "Бригадний"])
elif category == "📈 Рейтинг та Бали": 
    selected_tab = st.sidebar.selectbox("Розділ:", ["Е-Бали", "Розрахунки"])
elif category == "🧨 Мінування": 
    selected_tab = "Мінування"
elif category == "🔥 Ураження":
    months = ["04.2026", "03.2026", "02.2026", "01.2026", "12.2025", "11.2025"]
    selected_month = st.sidebar.selectbox("Оберіть місяць:", months)
    selected_tab = f"Ураження {selected_month}"
elif category == "📡 Спец. розділи": 
    selected_tab = st.sidebar.selectbox("Розділ:", ["ЗГ", "НРК"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

# --- 4. ДОПОМІЖНІ ФУНКЦІЇ ---
def create_brigade_chart(data, title):
    """Створює стовпчиковий графік для 4-х батальйонів"""
    fig = go.Figure()
    colors = {'1 аемб': '#92D050', '2 аемб': '#A5A5A5', '3 аемб': '#4472C4', '4 аемб': '#ED7D31'}
    
    # Дата завжди в першій колонці блоку
    dates = data.iloc[:, 0]
    
    for unit, color in colors.items():
        # Шукаємо назву підрозділу в заголовках блоку
        matching_cols = [c for c in data.columns if unit in str(c)]
        if matching_cols:
            col_name = matching_cols[0]
            vals = pd.to_numeric(data[col_name], errors='coerce').fillna(0)
            fig.add_trace(go.Bar(
                x=dates, y=vals, name=unit,
                marker_color=color, text=vals, textposition='outside'
            ))

    fig.update_layout(
        title=title, barmode='group',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=450, margin=dict(t=80)
    )
    return fig

# --- 5. ВІДОБРАЖЕННЯ ДАНИХ ---
try:
    # Завантажуємо сирі дані
    raw_df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
    
    st.markdown(f"<h2 style='text-align:center; color:white;'>📊 {selected_tab}</h2>", unsafe_allow_html=True)

    if selected_tab == "Бригадний ЗГ":
        try:
            # Рядок 1 - заголовки батальйонів (1 аемб, 2 аемб...)
            # Дані починаються з рядка 2
            sub_headers = raw_df.iloc[1].values
            main_data = raw_df.iloc[2:].copy()
            
            # Фільтруємо порожні дати
            main_data = main_data[main_data.iloc[:, 0].astype(str).str.strip() != ""]

            # РОЗРІЗАЄМО ТАБЛИЦЮ НА 3 БЛОКИ ПО 6 КОЛОНОК
            # Блок 1: Ураження + Мінування (стовпчики 0-5)
            block_total = main_data.iloc[:, 0:6]
            block_total.columns = sub_headers[0:6]
            st.plotly_chart(create_brigade_chart(block_total, "🏆 ЗАГАЛЬНИЙ РЕЗУЛЬТАТ (Ураження + Мінування)"), use_container_width=True)

            # Блок 2: Ураження (стовпчики 6-11)
            block_strikes = main_data.iloc[:, 6:12]
            block_strikes.columns = sub_headers[6:12]
            st.plotly_chart(create_brigade_chart(block_strikes, "🔥 ТІЛЬКИ УРАЖЕННЯ"), use_container_width=True)

            # Блок 3: Мінування (стовпчики 12-17)
            block_mining = main_data.iloc[:, 12:18]
            block_mining.columns = sub_headers[12:18]
            st.plotly_chart(create_brigade_chart(block_mining, "🧨 ТІЛЬКИ МІНУВАННЯ"), use_container_width=True)

            st.write("---")
            with st.expander("📂 ПОВНА ТАБЛИЦЯ ЗГ"):
                st.dataframe(raw_df.iloc[1:], use_container_width=True)
                
        except Exception as e:
            st.error(f"Помилка аналізу блоків: {e}")
            st.dataframe(raw_df)

    elif selected_tab == "Е-Бали":
        # Залишаємо ваш графік Лютий/Березень
        try:
            dates = raw_df.iloc[1:, 0]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=dates, y=raw_df.iloc[1:, 1], name='Попередній', marker_color='#A5A5A5', text=raw_df.iloc[1:, 1], textposition='outside'))
            fig.add_trace(go.Bar(x=dates, y=raw_df.iloc[1:, 2], name='Поточний', marker_color='#92D050', text=raw_df.iloc[1:, 2], textposition='outside'))
            fig.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), height=550)
            st.plotly_chart(fig, use_container_width=True)
        except: st.dataframe(raw_df)

    else:
        st.write("---")
        with st.expander("📂 ВІДКРИТИ ТАБЛИЦЮ", expanded=True):
            st.dataframe(raw_df.iloc[1:], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка: {e}")
