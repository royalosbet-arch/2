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

# --- 3. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ (БРИГАДА ПЕРША) ---
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

# --- 4. ВІДОБРАЖЕННЯ ТА ОЧИСТКА ---
try:
    # Завантаження даних
    df = conn.read(worksheet=selected_tab, ttl=300).dropna(how='all', axis=0).fillna("")
    
    # Очистка від Unnamed
    df.columns = ["" if "Unnamed" in str(c) else c for c in df.columns]

    st.markdown(f"<h2 style='text-align:center; color:white;'>📊 {selected_tab}</h2>", unsafe_allow_html=True)

    # --- СПЕЦІАЛЬНИЙ ГРАФІК ДЛЯ БРИГАДНОГО ЗГ (СТОВПЧИКИ) ---
    if selected_tab == "Бригадний ЗГ":
        try:
            # Обробка структури: Дані починаються з 2-го рядка
            brig_data = df.iloc[1:].copy()
            brig_data.columns = df.iloc[0] # Дата, 1 аемб, 2 аемб...
            
            # Фільтруємо порожні рядки та беремо 1-4 батальйони
            brig_data = brig_data[brig_data.iloc[:, 0].astype(str).str.strip() != ""]
            
            fig = go.Figure()
            # Кольори для батальйонів
            colors = {'1 аемб': '#92D050', '2 аемб': '#A5A5A5', '3 аемб': '#4472C4', '4 аемб': '#ED7D31'}
            
            for unit in ['1 аемб', '2 аемб', '3 аемб', '4 аемб']:
                if unit in brig_data.columns:
                    vals = pd.to_numeric(brig_data[unit], errors='coerce').fillna(0)
                    fig.add_trace(go.Bar(
                        x=brig_data.iloc[:, 0], 
                        y=vals,
                        name=unit,
                        marker_color=colors.get(unit, None),
                        text=vals,
                        textposition='outside'
                    ))

            fig.update_layout(
                barmode='group',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="white"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                height=550,
                xaxis=dict(tickangle=-45)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("#### 📋 Детальна таблиця")
            st.dataframe(df, use_container_width=True)
            
        except Exception as e:
            st.info("Перевірте структуру вкладки 'Бригадний ЗГ'.")
            st.dataframe(df, use_container_width=True)

    # --- ГРАФІК ДЛЯ Е-БАЛІВ ---
    elif selected_tab == "Е-Бали":
        try:
            dates = df.iloc[:, 0]
            fig = go.Figure()
            fig.add_trace(go.Bar(x=dates, y=df.iloc[:, 1], name='Попередній', marker_color='#A5A5A5', text=df.iloc[:, 1], textposition='outside'))
            fig.add_trace(go.Bar(x=dates, y=df.iloc[:, 2], name='Поточний', marker_color='#92D050', text=df.iloc[:, 2], textposition='outside'))
            fig.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), height=550)
            st.plotly_chart(fig, use_container_width=True)
            
            df_t = df.T
            df_t.index = ["" if "Unnamed" in str(i) else i for i in df_t.index]
            st.dataframe(df_t, use_container_width=True)
        except:
            st.dataframe(df, use_container_width=True)

    else:
        st.write("---")
        with st.expander("📂 ВІДКРИТИ ТАБЛИЦЮ", expanded=True):
            st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка: {e}")
