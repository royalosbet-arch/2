import streamlit as st
import pandas as pd

# Налаштування сторінки
st.set_page_config(page_title="Звіт по БК та Ураженнях", layout="wide")

st.title("📊 Оперативний звіт")
st.write("Дані оновлюються в режимі реального часу")

# Функція для завантаження даних (замініть посилання на ваше)
# Важливо: у Google Таблиці натисніть Файл -> Поділитися -> Опублікувати в інтернеті (як CSV)
SHEET_URL = "ТУТ_БУДЕ_ВАШЕ_ПОСИЛАННЯ_НА_CSV"

@st.cache_data(ttl=60) # Оновлювати дані кожну хвилину
def load_data():
    return pd.read_csv(SHEET_URL)

try:
    df = load_data()

    # Створюємо колонки для головних показників
    col1, col2, col3 = st.columns(3)
    
    total_bk = df['Кількість_БК'].sum()
    total_hits = df['Ураження'].sum()

    with col1:
        st.metric(label="Загальна к-сть БК", value=total_bk)
    
    with col2:
        st.metric(label="Всього уражень", value=total_hits, delta=int(total_hits * 0.1)) # Приклад дельти
    
    with col3:
        # Розрахунок ефективності
        eff = round((total_hits / total_bk) * 100, 1) if total_bk > 0 else 0
        st.metric(label="Ефективність", value=f"{eff}%")

    st.divider()

    # Візуалізація
    st.subheader("Статистика по об'єктах")
    st.bar_chart(data=df, x="Назва", y="Ураження")

    # Таблиця внизу для деталей
    with st.expander("Переглянути повну таблицю"):
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error("Будь ласка, перевірте підключення до таблиці або формат даних.")
    st.info("Переконайтеся, що ви опублікували Google Таблицю як CSV.")