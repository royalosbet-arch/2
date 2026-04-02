import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 1. НАЛАШТУВАННЯ ТА ПАРОЛЬ ---
# Змініть цей пароль на свій
USER_PASSWORD = "1234" 

def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Доступ обмежено")
        pwd = st.text_input("Введіть пароль для перегляду звіту:", type="password")
        if st.button("Увійти"):
            if pwd == USER_PASSWORD:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Невірний пароль")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. ВАША НОВА НАЗВА ТУТ ---
st.set_page_config(page_title="Статистика 1 аемб", layout="wide", page_icon="📈")
st.title("📈 Аналітична система: 1 аемб") # Змінюйте цей текст на будь-який інший

# --- 3. ПІДКЛЮЧЕННЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)

tabs_to_show = [
    "Ураження 04.2026", "Ураження 03.2026", "Ураження 02.2026", 
    "Ураження 01.2026", "Ураження 12.2025", "Ураження 11.2025",
    "ЗГ", "Розрахунки", "Е-Бали", "НРК", "Мінування"
]

selected_tab = st.sidebar.selectbox("Оберіть розділ:", tabs_to_show)

if st.sidebar.button('🔄 Оновити дані'):
    st.cache_data.clear()
    st.rerun()

try:
    df = conn.read(worksheet=selected_tab, ttl=300)
    df = df.dropna(how='all').dropna(axis=1, how='all')

    # --- 4. ГОЛОВНІ МЕТРИКИ (ВЕЛИКІ ЦИФРИ) ---
    st.subheader(f"📊 Статистика: {selected_tab}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Загальна к-сть записів", len(df))
    
    # Спроба знайти колонку з результатом (якщо вона є)
    res_col = [c for c in df.columns if 'результат' in c.lower()]
    if res_col:
        hits = df[df[res_col[0]].astype(str).str.contains("уражен", case=False, na=False)].shape[0]
        with col2:
            st.metric("Уражено цілей", hits)

    st.divider()

    # --- 5. ГРАФІКИ ---
    # Якщо в таблиці є колонка "Тип цілі", "Об'єкт" або "Результат" - малюємо графік
    target_col = [c for c in df.columns if 'цілі' in c.lower() or 'об\'єкт' in c.lower() or 'тип' in c.lower()]
    
    if target_col:
        st.subheader("📉 Розподіл по типах цілей")
        chart_data = df[target_col[0]].value_counts()
        st.bar_chart(chart_data)
        st.divider()

    # --- 6. ТАБЛИЦЯ ---
    st.subheader("📝 Повний список")
    st.dataframe(df, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Не вдалося завантажити вкладку '{selected_tab}'")
    st.info("Перевірте, чи назва вкладки в Google Sheets збігається з кодом.")
