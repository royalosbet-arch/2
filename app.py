import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64

# --- 1. НАЛАШТУВАННЯ ТА ПАРОЛЬ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

USER_PASSWORD = "2887" # ВАШ ТИМЧАСОВИЙ ПАРОЛЬ

def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)
        st.write("<br><br><br>", unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown("""
                <div style='background:rgba(255,255,255,0.05); padding:30px; border-radius:20px; border:1px solid rgba(255,255,255,0.1); text-align:center;'>
                    <h2 style='color:white; margin-bottom: 0; font-size: 1.5rem;'>🛡️ СИТУАЦІЙНИЙ ЦЕНТР</h2>
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

# --- 2. ДИЗАЙН (АДАПТИВНИЙ) ---
def set_design(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except: bg_css = 'background-color: #0E1117;'
    
    st.markdown(f'''
    <style>
    .stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }}
    
    /* Оптимізація для мобільних пристроїв */
    @media (max-width: 640px) {{
        .main .block-container {{ padding: 10px !important; }}
        h2 {{ font-size: 1.2rem !important; }}
        [data-testid="stMetricValue"] {{ font-size: 1.5rem !important; }}
    }}
    
    [data-testid="stMetric"] {{
        background: rgba(0, 0, 0, 0.7) !important;
        border-left: 5px solid #ff4b4b !important;
        border-radius: 10px !important;
        padding: 15px !important;
    }}
    .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }}
    [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.98); }}
    </style>
    ''', unsafe_allow_html=True)

set_design('background.jpg')

# --- 3. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.title("🛠️ НАВІГАЦІЯ")
category = st.sidebar.radio("Напрямок:", ["📈 Рейтинг та Бали", "🧨 Мінування", "🔥 Ураження", "📡 Спец. розділи"])

selected_tab = ""
if category == "📈 Рейтинг та Бали": selected_tab = st.sidebar.selectbox("Розділ:", ["Е-Бали", "Розрахунки"])
elif category == "🧨 Мінування": selected_tab = "Мінування"
elif category == "🔥 Ураження":
    months = ["04.2026", "03.2026", "02.2026", "01.2026", "12.2025", "11.2025"]
    selected_month = st.sidebar.selectbox("Оберіть місяць:", months)
    selected_tab = f"Ураження {selected_month}"
elif category == "📡 Спец. розділи": selected_tab = st.sidebar.selectbox("Розділ:", ["ЗГ", "НРК"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

# --- 4. ВІДОБРАЖЕННЯ ---
try:
    df = conn.read(worksheet=selected_tab, ttl=300).dropna(how='all', axis=0).fillna("")

    st.markdown(f"<h2 style='text-align:center; color:white;'>📊 {selected_tab}</h2>", unsafe_allow_html=True)

    if selected_tab == "Е-Бали":
        try:
            dates = df.iloc[:, 0]
            fig = go.Figure()

            # Лютий (Сірий)
            fig.add_trace(go.Bar(
                x=dates, y=df.iloc[:, 1],
                name='Лют', marker_color='#A5A5A5',
                text=df.iloc[:, 1], textposition='auto',
                textfont=dict(size=9)
            ))
            # Березень (Зелений)
            fig.add_trace(go.Bar(
                x=dates, y=df.iloc[:, 2],
                name='Бер', marker_color='#92D050',
                text=df.iloc[:, 2], textposition='auto',
                textfont=dict(size=9)
            ))

            fig.update_layout(
                barmode='group',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="white", size=10),
                # Налаштування легенди для мобільних
                legend=dict(
                    orientation="h",
                    yanchor="bottom", y=1.02,
                    xanchor="center", x=0.5,
                    font=dict(size=12)
                ),
                # Прибираємо величезні поля навколо графіка
                margin=dict(l=5, r=5, t=40, b=20),
                height=450,
                xaxis=dict(tickangle=-90, tickfont=dict(size=9)),
                yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("#### 📋 Показники")
            # Виводимо таблицю з прокруткою для мобільних
            st.dataframe(df.T, use_container_width=True)

        except Exception as e:
            st.info("Очікування даних...")
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    else:
        # Для інших розділів - стандартна таблиця
        st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка завантаження: {e}")
