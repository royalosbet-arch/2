import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import base64

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="Ситуаційний Центр 1 аемб", layout="wide", page_icon="🛡️")

# --- 2. ПЕРЕВІРКА ПАРОЛЯ ---
USER_PASSWORD = "1234" # ВАШ ПАРОЛЬ

def check_password():
    if "password_correct" not in st.session_state:
        # Стиль для чистого екрана входу (без картинки)
        st.markdown("""
            <style>
            .stApp { background-color: #0E1117; }
            .login-box {
                max-width: 400px;
                margin: 0 auto;
                padding: 40px;
                background: rgba(255,255,255,0.05);
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.1);
                text-align: center;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.write("<br><br><br>", unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1, 2, 1])
        
        with col_c:
            st.markdown("""
                <div class="login-box">
                    <h2 style='color: white;'>🛡️ СИТУАЦІЙНИЙ ЦЕНТР</h2>
                    <p style='color: #888;'>Авторизація користувача</p>
                </div>
            """, unsafe_allow_html=True)
            
            pwd = st.text_input("Код доступу:", type="password")
            if st.button("УВІЙТИ"):
                if pwd == USER_PASSWORD:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("Невірний код.")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. ФУНКЦІЯ ФОНУ (Тільки для авторизованих) ---
def set_bg(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        # background-size: cover - заповнює екран
        # background-position: center - центрує, щоб не було перекосів
        page_bg_img = f'''
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
        .stMetric {{ background: rgba(0, 0, 0, 0.6); padding: 15px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); }}
        .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }}
        /* Стиль для бічної панелі, щоб вона була читабельною */
        [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.85); }}
        </style>
        '''
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except:
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)

set_bg('background.jpg')

# --- 4. ПІДКЛЮЧЕННЯ ТА ДАНІ ---
st.title("🛡️ СИТУАЦІЙНИЙ ЦЕНТР: 1 аемб")
conn = st.connection("gsheets", type=GSheetsConnection)

tabs_to_show = [
    "Ураження 04.2026", "Ураження 03.2026", "Ураження 02.2026", 
    "Ураження 01.2026", "Ураження 12.2025", "Ураження 11.2025",
    "ЗГ", "Розрахунки", "Е-Бали", "НРК", "Мінування"
]

st.sidebar.title("Навігація")
selected_tab = st.sidebar.selectbox("Оберіть розділ:", tabs_to_show)

if st.sidebar.button('🔄 Оновити дані'):
    st.cache_data.clear()
    st.rerun()

try:
    df = conn.read(worksheet=selected_tab, ttl=300).dropna(how='all', axis=0).dropna(how='all', axis=1).fillna("")
    
    st.subheader(f"📂 Розділ: {selected_tab}")

    # Спеціальний графік для Е-Балів
    if selected_tab == "Е-Бали":
        try:
            name_col = df.columns[0]
            val_col = [c for c in df.columns if 'разом' in c.lower() or 'сума' in c.lower()][0]
            df_plot = df.copy()
            df_plot[val_col] = pd.to_numeric(df_plot[val_col], errors='coerce').fillna(0)
            df_plot = df_plot[df_plot[val_col] > 0].sort_values(by=val_col, ascending=True)
            
            fig = px.bar(df_plot, x=val_col, y=name_col, orientation='h', text=val_col, color_continuous_scale='Reds')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig, use_container_width=True)
        except: st.info("Дані для графіка відсутні.")

    st.divider()
    st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка розділу '{selected_tab}'")
