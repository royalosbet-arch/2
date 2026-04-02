import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import base64

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

# --- 2. ПЕРЕВІРКА ПАРОЛЯ (УКРАЇНСЬКОЮ) ---
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
                    <p style='color:#888;'>1 ОЛЕМБ. АВТОРИЗАЦІЯ</p>
                </div>
            """, unsafe_allow_html=True)
            pwd = st.text_input("ВВЕДІТЬ КОД ДОСТУПУ:", type="password")
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

# --- 3. ДИЗАЙН (ФОН ТА СТИЛІ) ---
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
    .stApp {{
        {bg_css}
        background-size: cover; background-position: center; background-attachment: fixed;
    }}
    /* Картки метрик */
    [data-testid="stMetric"] {{
        background: rgba(0, 0, 0, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-left: 5px solid #ff4b4b !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }}
    /* Картки останніх подій */
    .event-card {{
        background: rgba(0, 0, 0, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }}
    .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }}
    [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}
    </style>
    ''', unsafe_allow_html=True)

set_design('background.jpg')

# --- 4. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)
tabs_to_show = [
    "Ураження 04.2026", "Ураження 03.2026", "Ураження 02.2026", 
    "Ураження 01.2026", "Ураження 12.2025", "Ураження 11.2025",
    "ЗГ", "Розрахунки", "Е-Бали", "НРК", "Мінування"
]

st.sidebar.title("🛠️ НАВІГАЦІЯ")
selected_tab = st.sidebar.selectbox("Оберіть розділ:", tabs_to_show)

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

# --- 5. ОСНОВНА ПАНЕЛЬ ---
try:
    # Завантаження та очистка від None
    df = conn.read(worksheet=selected_tab, ttl=300).dropna(how='all', axis=0).fillna("")

    st.markdown(f"<h2 style='color:white;'>📡 СЕКТОР: {selected_tab}</h2>", unsafe_allow_html=True)

    # ВЕРХНІ ПОКАЗНИКИ (KPI)
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("ВСЬОГО ЗАПИСІВ", len(df[df.iloc[:, 0] != ""]))
    
    # Авто-пошук успіхів (якщо є колонка результат)
    res_col = [c for c in df.columns if 'результат' in c.lower()]
    if res_col:
        hits = df[df[res_col[0]].astype(str).str.contains("уражен", case=False, na=False)].shape[0]
        with m2: st.metric("УСПІШНО", hits)
    
    # Авто-пошук балів
    val_col = [c for c in df.columns if 'разом' in c.lower() or 'сума' in c.lower()]
    if val_col:
        total_val = pd.to_numeric(df[val_col[0]], errors='coerce').sum()
        with m3: st.metric("ЗАГАЛЬНИЙ БАЛ", f"{total_val:.1f}")

    st.write("---")

    # ЦЕНТРАЛЬНА ЧАСТИНА (ГРАФІК ТА ОСТАННІ ПОДІЇ)
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("#### 📈 АНАЛІТИКА ТА ГРАФІКИ")
        if "Е-Бали" in selected_tab and val_col:
            # Графік рейтингу
            df_p = df.copy()
            df_p[val_col[0]] = pd.to_numeric(df_p[val_col[0]], errors='coerce').fillna(0)
            df_p = df_p[df_p[val_col[0]] > 0].sort_values(by=val_col[0], ascending=True)
            fig = px.bar(df_p, x=val_col[0], y=df.columns[0], orientation='h', text=val_col[0],
                         color=val_col[0], color_continuous_scale='Reds')
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=450)
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Графік типів цілей (для уражень)
            target_col = [c for c in df.columns if 'цілі' in c.lower() or 'тип' in c.lower()]
            if target_col:
                fig = px.pie(df[df[target_col[0]] != ""], names=target_col[0], hole=0.4)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=450)
                st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown("#### 🔔 ОСТАННІ ЗАПИСИ")
        # Відображення останніх 5 рядків як карток
        recent = df[df.iloc[:, 0] != ""].tail(5).iloc[::-1]
        for _, row in recent.iterrows():
            st.markdown(f"""
                <div class="event-card">
                    <small style='color:#888;'>{row[0]}</small><br>
                    <strong>{row[1]}</strong><br>
                    <span style='color:#ff4b4b; font-size:0.9em;'>{row[res_col[0]] if res_col else ""}</span>
                </div>
            """, unsafe_allow_html=True)

    # ТАБЛИЦЯ (ПРИХОВАНА В ЕКСПАНДЕР)
    with st.expander("📂 ВІДКРИТИ ПОВНУ ТАБЛИЦЮ (АРХІВ ДАНИХ)"):
        search = st.text_input("Швидкий пошук по списку:", placeholder="Введіть текст для фільтрації...")
        if search:
            df_display = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]
        else:
            df_display = df
        st.dataframe(df_display, use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка завантаження розділу: {e}")
