import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import base64

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

# --- 2. ПЕРЕВІРКА ПАРОЛЯ ---
USER_PASSWORD = "1234" # ВАШ ПАРОЛЬ

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
                else:
                    st.error("❌ Доступ відхилено.")
        return False
    return True

if not check_password():
    st.stop()

# --- 3. ДИЗАЙН ---
def set_design(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except:
        bg_css = 'background-color: #0E1117;'

    st.markdown(f'''
    <style>
    .stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }}
    [data-testid="stMetric"] {{
        background: rgba(0, 0, 0, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-left: 5px solid #ff4b4b !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }}
    .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }}
    [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}
    </style>
    ''', unsafe_allow_html=True)

set_design('background.jpg')

# --- 4. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.title("🛠️ НАВІГАЦІЯ")

category = st.sidebar.radio(
    "Оберіть напрямок:",
    ["🧨 Мінування", "🔥 Ураження", "📈 Рейтинг та Бали", "📡 Спец. розділи"]
)

selected_tab = ""

if category == "🧨 Мінування":
    selected_tab = "Мінування"
elif category == "🔥 Ураження":
    months = ["04.2026", "03.2026", "02.2026", "01.2026", "12.2025", "11.2025"]
    selected_month = st.sidebar.selectbox("Оберіть місяць:", months)
    selected_tab = f"Ураження {selected_month}"
elif category == "📈 Рейтинг та Бали":
    selected_tab = st.sidebar.selectbox("Оберіть розділ:", ["Е-Бали", "Розрахунки"])
elif category == "📡 Спец. розділи":
    selected_tab = st.sidebar.selectbox("Оберіть розділ:", ["ЗГ", "НРК"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

# --- 5. ВІДОБРАЖЕННЯ ДАНИХ ---
try:
    # Завантаження даних
    df = conn.read(worksheet=selected_tab, ttl=300).dropna(how='all', axis=0).fillna("")

    st.markdown(f"<h2 style='color:white;'>📡 СЕКТОР: {selected_tab}</h2>", unsafe_allow_html=True)

    # ПОКАЗНИКИ
    m1, m2, m3 = st.columns(3)
    # Рахуємо записи тільки там, де перший стовпчик не порожній
    valid_rows = df[df.iloc[:, 0].astype(str).str.strip() != ""]
    with m1: st.metric("ЗАПИСІВ У СЕКТОРІ", len(valid_rows))
    
    # Шукаємо колонки для статистики
    res_col = [c for c in df.columns if 'результат' in c.lower() or 'статус' in c.lower()]
    val_col = [c for c in df.columns if 'разом' in c.lower() or 'сума' in c.lower() or 'бал' in c.lower()]
    target_col = [c for c in df.columns if 'цілі' in c.lower() or 'тип' in c.lower() or 'об\'єкт' in c.lower()]

    if res_col:
        hits = df[df[res_col[0]].astype(str).str.contains("уражен", case=False, na=False)].shape[0]
        with m2: st.metric("УСПІШНО", hits)
    
    if val_col:
        try:
            total_val = pd.to_numeric(df[val_col[0]], errors='coerce').sum()
            with m3: st.metric("ПІДСУМКОВИЙ ПОКАЗНИК", f"{total_val:.1f}")
        except: pass

    st.write("---")

    # ГРАФІКИ НА ВСЮ ШИРИНУ (БЕЗ ОСТАННІХ ПОДІЙ)
    if selected_tab == "Е-Бали" and val_col:
        df_p = df.copy()
        df_p[val_col[0]] = pd.to_numeric(df_p[val_col[0]], errors='coerce').fillna(0)
        df_p = df_p[df_p[val_col[0]] > 0].sort_values(by=val_col[0], ascending=True)
        fig = px.bar(df_p, x=val_col[0], y=df.columns[0], orientation='h', text=val_col[0], color_continuous_scale='Reds')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=500)
        st.plotly_chart(fig, use_container_width=True)
    elif target_col and not df[target_col[0]].empty:
        # Перевіряємо, чи є дані для кругової діаграми
        pie_data = df[df[target_col[0]].astype(str).str.strip() != ""]
        if not pie_data.empty:
            fig = px.pie(pie_data, names=target_col[0], hole=0.4, title="Розподіл за типами")
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=450)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Аналітика буде доступна після заповнення даних у таблиці.")

    # ПОВНА ТАБЛИЦЯ
    st.write("---")
    with st.expander("📂 ВІДКРИТИ ПОВНУ ТАБЛИЦЮ (АРХІВ ДАНИХ)", expanded=False):
        search = st.text_input("Швидкий пошук:", placeholder="Введіть текст...")
        if search:
            df_display = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
        else:
            df_display = df
        st.dataframe(df_display, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка завантаження розділу '{selected_tab}'. Перевірте наявність вкладки в Google Таблиці.")
    st.info("Технічна деталя: " + str(e))
