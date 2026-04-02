import streamlit as st
from streamlit_gsheets import GSheetsConnection

# --- НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="Звіт 1 аемб", layout="wide", page_icon="📊")

# --- СТИЛІЗАЦІЯ (Optional) ---
st.markdown("""
    <style>
    .main {
        background-color: #f5f5f5;
    }
    stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 Оперативний дашборд 1 аемб")

# --- ПІДКЛЮЧЕННЯ ДО ТАБЛИЦІ ---
# Використовує дані з Secrets (connections.gsheets)
conn = st.connection("gsheets", type=GSheetsConnection)

# --- СПИСОК ВСІХ ВАШИХ ВКЛАДОК ---
tabs_to_show = [
    "ЗГ",
    "Ураження 11.2025",
    "Ураження 12.2025",
    "Ураження 01.2026",
    "Ураження 02.2026",
    "Ураження 03.2026",
    "Ураження 04.2026",
    "Розрахунки",
    "Е-Бали",
    "НРК",
    "Мінування"
]

# Вибір розділу в боковій панелі
st.sidebar.header("Навігація")
selected_tab = st.sidebar.selectbox("Оберіть розділ для перегляду:", tabs_to_show)

# Кнопка оновлення в боковій панелі
if st.sidebar.button('🔄 Оновити дані з таблиці'):
    st.cache_data.clear()
    st.rerun()

try:
    # Читання даних з обраного листа
    # ttl=300 означає, що дані кешуються на 5 хвилин
    df = conn.read(worksheet=selected_tab, ttl=300)
    
    # Очистка: видаляємо повністю порожні рядки та колонки
    df = df.dropna(how='all').dropna(axis=1, how='all')

    # ВІДОБРАЖЕННЯ ДАНИХ
    st.subheader(f"📂 Розділ: {selected_tab}")
    
    # Виводимо таблицю
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Додаткова статистика (якщо це вкладка з Ураженнями)
    if "Ураження" in selected_tab:
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"Всього записів у цьому місяці: **{len(df)}**")
        
        # Якщо в таблиці є колонка 'Тип цілі' або подібна, можна вивести графік
        # Наприклад:
        # if 'Тип цілі' in df.columns:
        #    st.bar_chart(df['Тип цілі'].value_counts())

except Exception as e:
    st.error(f"Помилка завантаження листа '{selected_tab}'")
    st.warning("Переконайтеся, що назва вкладки в Google Таблиці в точності збігається з назвою в меню.")
    st.expander("Технічні деталі помилки").write(e)

# Підпис внизу
st.sidebar.markdown("---")
st.sidebar.caption("Дані захищені та підтягуються з приватної таблиці через Google API.")
