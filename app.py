import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. ПАРОЛЬ ТА КОНФІГУРАЦІЯ ---
USER_PASSWORD = "287087" # Змініть на свій

def check_password():
    if "password_correct" not in st.session_state:
        # Стилізація вікна входу
        st.markdown("<h2 style='text-align: center;'>🔐 Вхід у систему 1 аемб</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Пароль:", type="password")
        if st.button("Увійти"):
            if pwd == USER_PASSWORD:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Доступ заблоковано")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. ДИЗАЙН ТА ТЕМА ---
st.set_page_config(page_title="Ситуаційний Центр 1 аемб", layout="wide")

# CSS для фонової картинки та стилю карток
# Ви можете замінити URL картинки на свій (наприклад, камуфляж або карта)
bg_img_url = "https://img.freepik.com/free-photo/abstract-luxury-dark-grey-gradient-with-border-black-vignette-background_1258-108865.jpg"

st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("{bg_img_url}");
        background-attachment: fixed;
        background-size: cover;
    }}
    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0);
    }}
    .stMetric {{
        background: rgba(255, 255, 255, 0.05);
        padding: 20px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }}
    div[data-testid="stExpander"] {{
        background: rgba(0,0,0,0.4);
        border: none;
    }}
    .stDataFrame {{
        background: rgba(0,0,0,0.6);
        border-radius: 10px;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- 3. ПІДКЛЮЧЕННЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("🛡️ СИТУАЦІЙНИЙ ЦЕНТР: 1 аемб")
st.markdown("---")

# --- 4. НАВІГАЦІЯ ВЕРХНІМИ ВКЛАДКАМИ ---
# Групуємо ваші листи за категоріями
main_tabs = st.tabs(["🔥 Ураження", "🧨 Мінування & ЗГ", "🧮 Розрахунки & Бали"])

# --- ВКЛАДКА 1: УРАЖЕННЯ (АРХІВ ТА ПОТОЧНІ) ---
with main_tabs[0]:
    month = st.selectbox("Оберіть місяць уражень:", ["Ураження 04.2026", "Ураження 03.2026", "Ураження 02.2026", "Ураження 01.2026", "Ураження 12.2025"])
    try:
        df_u = conn.read(worksheet=month, ttl=300).dropna(how='all', axis=0)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Виїздів/Записів", len(df_u))
        
        # Шукаємо колонку з результатом для графіка
        res_col = [c for c in df_u.columns if 'результат' in c.lower() or 'ціль' in c.lower()]
        if res_col:
            st.subheader("📊 Аналітика цілей")
            st.bar_chart(df_u[res_col[0]].value_counts())
        
        st.dataframe(df_u, use_container_width=True)
    except: st.error("Не вдалося завантажити цей місяць")

# --- ВКЛАДКА 2: МІНУВАННЯ ТА ЗГ ---
with main_tabs[1]:
    sub_col1, sub_col2 = st.columns(2)
    with sub_col1:
        st.subheader("⛏️ Мінування")
        try:
            df_m = conn.read(worksheet="Мінування", ttl=300).dropna(how='all', axis=0)
            # Приклад: сумуємо кількість мін, якщо є така колонка
            count_col = [c for c in df_m.columns if 'кільк' in c.lower()]
            if count_col:
                st.metric("Всього встановлено", int(pd.to_numeric(df_m[count_col[0]], errors='coerce').sum()))
            st.dataframe(df_m, use_container_width=True)
        except: st.info("Вкладка 'Мінування' порожня або не знайдена")
        
    with sub_col2:
        st.subheader("📡 ЗГ (Загальні дані)")
        try:
            df_zg = conn.read(worksheet="ЗГ", ttl=300).dropna(how='all', axis=0)
            st.dataframe(df_zg, use_container_width=True)
        except: st.info("Вкладка 'ЗГ' не знайдена")

# --- ВКЛАДКА 3: РОЗРАХУНКИ ТА БАЛИ ---
with main_tabs[2]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏆 Е-Бали (Рейтинг)")
        try:
            df_b = conn.read(worksheet="Е-Бали", ttl=300).dropna(how='all', axis=0)
            st.table(df_b) # Таблиця без прокрутки для рейтингу
        except: st.info("Дані по балах відсутні")
    
    with c2:
        st.subheader("📈 Розрахунки / НРК")
        try:
            df_r = conn.read(worksheet="Розрахунки", ttl=300).dropna(how='all', axis=0)
            st.dataframe(df_r, use_container_width=True)
        except: st.info("Вкладка 'Розрахунки' не знайдена")

# Бокова панель для керування
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2592/2592201.png", width=100)
st.sidebar.write("### Керування")
if st.sidebar.button('🔄 Оновити всі дані'):
    st.cache_data.clear()
    st.rerun()

st.sidebar.info("Цей дашборд автоматично підтягує зміни з вашої Google Таблиці.")
