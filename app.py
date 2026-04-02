import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import base64

# --- 1. НАЛАШТУВАННЯ ТА ФОН (ОБОВ'ЯЗКОВО ПЕРШИМИ) ---
st.set_page_config(page_title="Ситуаційний Центр 1 аемб", layout="wide", page_icon="🛡️")

def set_bg(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        page_bg_img = f'''
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-attachment: fixed;
        }}
        /* Стиль для вікна входу */
        .stTextInput {{
            max-width: 400px;
            margin: 0 auto;
            background: rgba(0,0,0,0.5);
            padding: 20px;
            border-radius: 15px;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
        .stMetric {{ background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); }}
        .stDataFrame {{ background: rgba(0,0,0,0.7); border-radius: 10px; }}
        </style>
        '''
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except:
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)

# Вмикаємо фон ОДРАЗУ, щоб він був і на паролі
set_bg('background.jpg')

# --- 2. ПЕРЕВІРКА ПАРОЛЯ ---
USER_PASSWORD = "1234" # Замініть на свій

def check_password():
    if "password_correct" not in st.session_state:
        # Робимо гарний відступ зверху
        st.write("<br><br><br>", unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1, 2, 1]) # Центруємо вікно
        
        with col_c:
            st.markdown("<h2 style='text-align: center; color: white; text-shadow: 2px 2px 4px #000;'>🛡️ СИТУАЦІЙНИЙ ЦЕНТР</h2>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #ccc;'>Вхід тільки для авторизованого персоналу</p>", unsafe_allow_html=True)
            
            pwd = st.text_input("Введіть код доступу:", type="password")
            
            if st.button("УВІЙТИ В СИСТЕМУ"):
                if pwd == USER_PASSWORD:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Доступ відхилено. Невірний код.")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
st.title("🛡️ СИТУАЦІЙНИЙ ЦЕНТР: 1 аемб")
conn = st.connection("gsheets", type=GSheetsConnection)

tabs_to_show = [
    "Ураження 04.2026", "Ураження 03.2026", "Ураження 02.2026", 
    "Ураження 01.2026", "Ураження 12.2025", "Ураження 11.2025",
    "ЗГ", "Розрахунки", "Е-Бали", "НРК", "Мінування"
]

st.sidebar.title("Навігація")
selected_tab = st.sidebar.selectbox("Оберіть розділ:", tabs_to_show)

st.sidebar.markdown("---")
if st.sidebar.button('🔄 Оновити дані з Google'):
    st.cache_data.clear()
    st.rerun()

# --- 4. ОСНОВНА ЛОГІКА ТА ОЧИСТКА ВІД NONE ---
try:
    raw_df = conn.read(worksheet=selected_tab, ttl=300)
    df = raw_df.dropna(how='all', axis=0).dropna(how='all', axis=1)
    df = df.fillna("") # Прибираємо None

    st.subheader(f"📂 Розділ: {selected_tab}")

    # --- СПЕЦІАЛЬНИЙ ГРАФІК ДЛЯ Е-БАЛИ ---
    if selected_tab == "Е-Бали":
        try:
            name_col = df.columns[0]
            val_col = [c for c in df.columns if 'разом' in c.lower() or 'сума' in c.lower()][0]
            
            df_plot_data = df.copy()
            df_plot_data[val_col] = pd.to_numeric(df_plot_data[val_col], errors='coerce').fillna(0)
            df_plot = df_plot_data[df_plot_data[val_col] > 0].sort_values(by=val_col, ascending=True)

            fig = px.bar(df_plot, x=val_col, y=name_col, orientation='h', 
                         text=val_col, color=val_col, color_continuous_scale='Reds')
            
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                              font_color="white", showlegend=False, height=500)
            
            st.write("### 🏆 Рейтинг ефективності")
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.info("Графік буде доступний після заповнення таблиці.")

    # --- ТАБЛИЦЯ ---
    st.divider()
    st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка завантаження розділу '{selected_tab}'")
