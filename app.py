import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

# --- 2. ПЕРЕВІРКА ПАРОЛЯ ---
USER_PASSWORD = "2887" 

MONTHS_UKR = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень", 5: "Травень", 6: "Червень",
    7: "Липень", 8: "Серпень", 9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень"
}

def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)
        st.write("<br><br><br>", unsafe_allow_html=True)
        col_l, col_c, col_r = st.columns([1, 2, 1])
        with col_c:
            st.markdown("""<div style='background:rgba(255,255,255,0.05); padding:40px; border-radius:20px; border:1px solid rgba(255,255,255,0.1); text-align:center;'><h2 style='color:white; margin-bottom: 0;'>🛡️ СИТУАЦІЙНИЙ ЦЕНТР</h2><p style='color:#888;'>1 аемб. АВТОРИЗАЦІЯ</p></div>""", unsafe_allow_html=True)
            pwd = st.text_input("ВВЕДІТЬ КОД ДОСТУПУ:", type="password")
            if st.button("УВІЙТИ В СИСТЕМУ"):
                if pwd == USER_PASSWORD:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else: st.error("❌ Невірний код.")
        return False
    return True

if not check_password(): st.stop()

# --- 3. ДИЗАЙН ---
def set_design(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except: bg_css = 'background-color: #0E1117;'
    st.markdown(f'<style>.stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }} [data-testid="stMetric"] {{ background: rgba(0, 0, 0, 0.7) !important; border-left: 5px solid #ff4b4b !important; border-radius: 10px !important; padding: 20px !important; }} .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }} [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}</style>', unsafe_allow_html=True)

set_design('background.jpg')

# --- 4. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.title("🛠️ НАВІГАЦІЯ")
category = st.sidebar.radio("Оберіть напрямок:", ["⚔️ Бригадні звіти", "📈 Рейтинг та Бали", "🧨 Мінування", "🔥 Ураження", "📡 Спец. розділи"])

selected_tab = ""
if category == "⚔️ Бригадні звіти": selected_tab = st.sidebar.selectbox("Розділ:", ["Бригадний ЗГ", "Бригадний"])
elif category == "📈 Рейтинг та Бали": selected_tab = st.sidebar.selectbox("Розділ:", ["Е-Бали", "Розрахунки"])
elif category == "🧨 Мінування": selected_tab = "Мінування"
elif category == "🔥 Ураження":
    months = ["04.2026", "03.2026", "02.2026", "01.2026", "12.2025", "11.2025"]
    m_sel = st.sidebar.selectbox("Місяць:", months)
    selected_tab = f"Ураження {m_sel}"
elif category == "📡 Спец. розділи": selected_tab = st.sidebar.selectbox("Розділ:", ["ЗГ", "НРК"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

# --- 5. ВІДОБРАЖЕННЯ ДАНИХ ---
try:
    raw_df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
    st.markdown(f"<h2 style='text-align:center; color:white;'>📊 {selected_tab}</h2>", unsafe_allow_html=True)

    if selected_tab == "Мінування":
        df_m = raw_df.copy()
        df_m.columns = [str(c).strip() for c in df_m.iloc[0]]
        df_m = df_m.iloc[1:].reset_index(drop=True)
        
        # Перетворення дат та кількості
        df_m['Дата_dt'] = pd.to_datetime(df_m['Дата'], dayfirst=True, errors='coerce')
        df_m['Кількість_val'] = pd.to_numeric(df_m['Кількість'], errors='coerce').fillna(0)
        
        # Відсікаємо порожні або підсумкові рядки
        df_clean = df_m[df_m['Дата_dt'].notnull()].copy()
        
        if not df_clean.empty:
            df_clean['Year'] = df_clean['Дата_dt'].dt.year
            df_clean['Month'] = df_clean['Дата_dt'].dt.month
            df_clean['Day_Label'] = df_clean['Дата_dt'].dt.strftime('%d.%m')
            df_clean['Month_Label'] = df_clean['Month'].map(MONTHS_UKR) + " " + df_clean['Year'].astype(str)
            df_clean['Sort_Key'] = df_clean['Year'] * 100 + df_clean['Month']

            # ГРАФІК 1
            st.markdown("### 📅 Щоденна робота")
            m_opts = df_clean[['Month_Label', 'Sort_Key']].drop_duplicates().sort_values('Sort_Key', ascending=False)
            sel_m = st.selectbox("Оберіть місяць:", m_opts['Month_Label'].tolist())
            
            p_df = df_clean[df_clean['Month_Label'] == sel_m].sort_values('Дата_dt')
            daily = p_df.groupby('Day_Label')['Кількість_val'].sum().reset_index()

            fig1 = go.Figure(go.Bar(
                x=daily['Day_Label'].tolist(), 
                y=[float(x) for x in daily['Кількість_val']], 
                marker_color='#ED7D31', 
                text=[str(int(x)) if x == int(x) else str(x) for x in daily['Кількість_val']], 
                textposition='outside'
            ))
            fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            st.plotly_chart(fig1, use_container_width=True)

            # ГРАФІК 2
            st.markdown("### 📈 Всього за місяць")
            overall = df_clean.groupby(['Sort_Key', 'Month_Label'])['Кількість_val'].sum().reset_index().sort_values('Sort_Key')
            fig2 = go.Figure(go.Bar(
                x=overall['Month_Label'].tolist(), 
                y=[float(x) for x in overall['Кількість_val']], 
                marker_color='#FF8C00', 
                text=[str(int(x)) for x in overall['Кількість_val']], 
                textposition='outside'
            ))
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            st.plotly_chart(fig2, use_container_width=True)
            
            with st.expander("📂 ПЕРЕГЛЯНУТИ ТАБЛИЦЮ"):
                target_cols = ['Дата', 'БК', 'Кількість', 'Верифікація']
                valid_cols = [c for c in target_cols if c in df_m.columns]
                # Максимально безпечний вивід таблиці (все як текст)
                st.dataframe(df_m[valid_cols].applymap(str), use_container_width=True, hide_index=True)
        else:
            st.warning("Дані для аналізу не знайдені. Перевірте формат дат у колонці 'Дата'.")

    elif selected_tab == "Бригадний ЗГ":
        sub = [str(x) for x in raw_df.iloc[1].values]
        data = raw_df.iloc[2:][raw_df.iloc[2:, 0] != ""]
        def bc(d, t, s_col):
            f = go.Figure()
            clrs = {'1 аемб': '#92D050', '2 аемб': '#A5A5A5', '3 аемб': '#4472C4', '4 аемб': '#ED7D31'}
            for u, c in clrs.items():
                idx = [i for i, x in enumerate(sub) if u in x and i >= s_col and i < s_col+6]
                if idx:
                    vals = pd.to_numeric(d.iloc[:, idx[0]], errors='coerce').fillna(0).tolist()
                    f.add_trace(go.Bar(x=d.iloc[:, 0].tolist(), y=[float(v) for v in vals], name=u, marker_color=c, text=[str(v) for v in vals], textposition='outside'))
            f.update_layout(title=t, barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            return f
        st.plotly_chart(bc(data, "🏆 ЗАГАЛЬНИЙ РЕЗУЛЬТАТ", 0), use_container_width=True)
        st.plotly_chart(bc(data, "🔥 УРАЖЕННЯ", 6), use_container_width=True)
        st.plotly_chart(bc(data, "🧨 МІНУВАННЯ", 12), use_container_width=True)

    elif selected_tab == "Е-Бали":
        dates = raw_df.iloc[1:, 0].tolist()
        v1 = pd.to_numeric(raw_df.iloc[1:, 1], errors='coerce').fillna(0).tolist()
        v2 = pd.to_numeric(raw_df.iloc[1:, 2], errors='coerce').fillna(0).tolist()
        f = go.Figure()
        f.add_trace(go.Bar(x=dates, y=[float(x) for x in v1], name='Попередній', marker_color='#A5A5A5', text=[str(x) for x in v1], textposition='outside'))
        f.add_trace(go.Bar(x=dates, y=[float(x) for x in v2], name='Поточний', marker_color='#92D050', text=[str(x) for x in v2], textposition='outside'))
        f.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=500)
        st.plotly_chart(f, use_container_width=True)
        st.dataframe(raw_df.iloc[1:].T.applymap(str), use_container_width=True)

    else:
        st.dataframe(raw_df.iloc[1:].applymap(str), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка системи: {e}")
