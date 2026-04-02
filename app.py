import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import base64

# --- 1. НАЛАШТУВАННЯ ТА ПАРОЛЬ ---
# Встановіть свій пароль тут
USER_PASSWORD = "1234" 

def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔐 Вхід у систему 1 аемб</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Введіть пароль для доступу:", type="password")
        if st.button("Увійти"):
            if pwd == USER_PASSWORD:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Невірний пароль")
        return False
    return True

# Налаштування сторінки (має бути на самому початку)
st.set_page_config(page_title="Ситуаційний Центр 1 аемб", layout="wide", page_icon="🛡️")

if not check_password():
    st.stop()

# --- 2. ФУНКЦІЯ ДЛЯ ФОНУ (background.jpg з вашого GitHub) ---
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
        [data-testid="stHeader"] {{ background: rgba(0,0,0,0); }}
        .stMetric {{ background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.1); }}
        .stDataFrame {{ background: rgba(0,0,0,0.7); border-radius: 10px; }}
        </style>
        '''
        st.markdown(page_bg_img, unsafe_allow_html=True)
    except:
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)

# Шукаємо файл background.jpg у вашому репозиторії
set_bg('background.jpg')

# --- 3. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
st.title("🛡️ СИТУАЦІЙНИЙ ЦЕНТР: 1 аемб")
conn = st.connection("gsheets", type=GSheetsConnection)

# Список ваших вкладок (перевірте, щоб назви були 1-в-1 як у таблиці)
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

# --- 4. ОСНОВНА ЛОГІКА ВІДОБРАЖЕННЯ ---
try:
    # Завантаження даних (кеш на 5 хв)
    df = conn.read(worksheet=selected_tab, ttl=300).dropna(how='all', axis=0)
    
    st.subheader(f"📂 Поточний розділ: {selected_tab}")

    # --- СПЕЦІАЛЬНИЙ ГРАФІК ДЛЯ Е-БАЛИ ---
    if selected_tab == "Е-Бали":
        try:
            name_col = df.columns[0] # Прізвище/Позивний
            # Шукаємо колонку з підсумком (РАЗОМ або Сума)
            val_col = [c for c in df.columns if 'разом' in c.lower() or 'сума' in c.lower()][0]
            
            df[val_col] = pd.to_numeric(df[val_col], errors='coerce').fillna(0)
            df_plot = df[df[val_col] > 0].sort_values(by=val_col, ascending=True)

            fig = px.bar(df_plot, x=val_col, y=name_col, orientation='h', 
                         text=val_col, color=val_col, color_continuous_scale='Reds')
            
            fig.update_traces(texttemplate='%{text}', textposition='outside')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', 
                              font_color="white", showlegend=False, height=500)
            
            st.write("### 🏆 Рейтинг ефективності (Автоматичний графік)")
            st.plotly_chart(fig, use_container_width=True)
        except:
            st.info("Для побудови графіка рейтингу потрібні колонки з прізвищем та підсумковою сумою.")

    # --- АНАЛІТИКА ДЛЯ УРАЖЕНЬ ---
    elif "Ураження" in selected_tab:
        target_col = [c for c in df.columns if 'цілі' in c.lower() or 'тип' in c.lower()]
        if target_col:
            st.write("### 📈 Розподіл уражених цілей")
            chart_data = df[target_col[0]].value_counts()
            st.bar_chart(chart_data)

    # --- ВИВІД МЕТРИК І ТАБЛИЦІ ---
    st.divider()
    c1, c2 = st.columns(2)
    c1.metric("Всього записів у розділі", len(df))
    
    st.write("### 📄 Детальна таблиця")
    st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка завантаження розділу '{selected_tab}'")
    st.info("Перевірте, чи не змінили ви назву вкладки в самій Google Таблиці.")
