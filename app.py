import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
import base64

# --- 1. НАЛАШТУВАННЯ ТА ПАРОЛЬ ---
st.set_page_config(page_title="Ситуаційний Центр 1 аемб", layout="wide", page_icon="🛡️")

USER_PASSWORD = "1234" # ВАШ ПАРОЛЬ

def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)
        st.write("<br><br><br>", unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown("<div style='padding:40px; background:rgba(255,255,255,0.05); border-radius:20px; border:1px solid rgba(255,255,255,0.1); text-align:center;'><h2 style='color:white;'>🛡️ СИТУАЦІЙНИЙ ЦЕНТР</h2><p style='color:#888;'>Авторизація користувача</p></div>", unsafe_allow_html=True)
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

# --- 2. ФОН ---
def set_bg(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        bin_str = base64.b64encode(data).decode()
        st.markdown(f'''
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{bin_str}");
            background-size: cover; background-position: center; background-attachment: fixed;
        }}
        /* Картки показників */
        [data-testid="stMetric"] {{
            background: rgba(0, 0, 0, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 10px;
            padding: 15px !important;
        }}
        .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; padding: 10px; }}
        [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.9); }}
        </style>
        ''', unsafe_allow_html=True)
    except:
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)

set_bg('background.jpg')

# --- 3. ПІДКЛЮЧЕННЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)

tabs_to_show = [
    "Ураження 04.2026", "Ураження 03.2026", "Ураження 02.2026", 
    "Ураження 01.2026", "Ураження 12.2025", "Ураження 11.2025",
    "ЗГ", "Розрахунки", "Е-Бали", "НРК", "Мінування"
]

st.sidebar.title("🛠️ Керування")
selected_tab = st.sidebar.selectbox("Оберіть розділ:", tabs_to_show)

if st.sidebar.button('🔄 Оновити дані'):
    st.cache_data.clear()
    st.rerun()

# --- 4. ГОЛОВНА ЛОГІКА ПАНЕЛІ ---
try:
    df = conn.read(worksheet=selected_tab, ttl=300).dropna(how='all', axis=0).dropna(how='all', axis=1).fillna("")
    
    # Заголовок розділу
    st.markdown(f"### 📡 {selected_tab}")

    # --- БЛОК KPI (ВЕЛИКІ ЦИФРИ) ---
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    with kpi1:
        st.metric("Всього записів", len(df[df.iloc[:,0] != ""]))
    
    # Динамічні метрики залежно від контенту
    if "Ураження" in selected_tab:
        res_col = [c for c in df.columns if 'результат' in c.lower()]
        if res_col:
            hits = df[df[res_col[0]].astype(str).str.contains("уражен", case=False, na=False)].shape[0]
            with kpi2: st.metric("Успішних уражень", hits)
    
    if "Е-Бали" in selected_tab:
        sum_col = [c for c in df.columns if 'разом' in c.lower() or 'сума' in c.lower()]
        if sum_col:
            total_score = pd.to_numeric(df[sum_col[0]], errors='coerce').sum()
            with kpi3: st.metric("Загальний бал підрозділу", round(total_score, 1))

    st.write("<br>", unsafe_allow_html=True)

    # --- СЕРЕДНЯ ЧАСТИНА (ГРАФІК + ФІЛЬТР) ---
    col_chart, col_info = st.columns([2, 1])

    with col_chart:
        # Логіка для Е-Балів (Графік)
        if selected_tab == "Е-Бали":
            try:
                name_col, val_col = df.columns[0], [c for c in df.columns if 'разом' in c.lower()][0]
                df_p = df.copy()
                df_p[val_col] = pd.to_numeric(df_p[val_col], errors='coerce').fillna(0)
                df_p = df_p[df_p[val_col] > 0].sort_values(by=val_col, ascending=True)
                fig = px.bar(df_p, x=val_col, y=name_col, orientation='h', text=val_col, 
                             color=val_col, color_continuous_scale='Greens', title="Рейтинг особового складу")
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
                st.plotly_chart(fig, use_container_width=True)
            except: st.info("Графік очікує на дані...")
        
        # Логіка для Уражень (Графік)
        elif "Ураження" in selected_tab:
            target_col = [c for c in df.columns if 'цілі' in c.lower() or 'тип' in c.lower()]
            if target_col:
                fig = px.pie(df[df[target_col[0]] != ""], names=target_col[0], hole=0.4, title="Типи цілей",
                             color_discrete_sequence=px.colors.sequential.Reds_r)
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
                st.plotly_chart(fig, use_container_width=True)

    with col_info:
        st.markdown("#### 🔍 Швидкий пошук")
        search_query = st.text_input("Введіть прізвище, техніку або дату:", placeholder="Наприклад: БМП або Іванов")
        st.info("Почніть писати, і таблиця знизу автоматично відфільтрується.")

    # --- НИЖНЯ ЧАСТИНА (ТАБЛИЦЯ) ---
    st.write("#### 📑 Детальні дані")
    
    # Фільтрація таблиці за пошуком
    if search_query:
        df_display = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]
    else:
        df_display = df

    # Налаштування вигляду колонок (Progress bar для балів)
    column_config = {}
    score_cols = [c for c in df.columns if 'бал' in c.lower() or 'разом' in c.lower()]
    for sc in score_cols:
        column_config[sc] = st.column_config.ProgressColumn(sc, format="%.1f", min_value=0, max_value=float(df[sc].max()) if not df.empty and df[sc].max() != "" else 100)

    st.dataframe(
        df_display, 
        use_container_width=True, 
        hide_index=True,
        column_config=column_config
    )

except Exception as e:
    st.error(f"Помилка завантаження розділу '{selected_tab}'")
    st.write(f"Деталі: {e}")
