import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64

# --- 1. НАЛАШТУВАННЯ ТА ПАРОЛЬ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

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

# --- 2. ДИЗАЙН ---
def set_design(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except: bg_css = 'background-color: #0E1117;'
    st.markdown(f'<style>.stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }} [data-testid="stMetric"] {{ background: rgba(0, 0, 0, 0.7) !important; border-left: 5px solid #ff4b4b !important; border-radius: 10px !important; padding: 20px !important; }} .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }} [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}</style>', unsafe_allow_html=True)

set_design('background.jpg')

# --- 3. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.title("🛠️ НАВІГАЦІЯ")
category = st.sidebar.radio("Оберіть напрямок:", ["⚔️ Бригадні звіти", "📈 Рейтинг та Бали", "🧨 Мінування", "🔥 Ураження", "📡 Спец. розділи"])

selected_tab = ""
if category == "⚔️ Бригадні звіти": selected_tab = st.sidebar.selectbox("Розділ:", ["Бригадний ЗГ", "Бригадний"])
elif category == "📈 Рейтинг та Бали": selected_tab = st.sidebar.selectbox("Розділ:", ["Е-Бали", "Розрахунки"])
elif category == "🧨 Мінування": selected_tab = "Мінування"
elif category == "🔥 Ураження":
    months = ["04.2026", "03.2026", "02.2026", "01.2026", "12.2025", "11.2025"]
    selected_tab = f"Ураження {st.sidebar.selectbox('Місяць:', months)}"
elif category == "📡 Спец. розділи": selected_tab = st.sidebar.selectbox("Розділ:", ["ЗГ", "НРК"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

# --- 4. ВІДОБРАЖЕННЯ ---
try:
    raw_df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
    st.markdown(f"<h2 style='text-align:center; color:white;'>📊 {selected_tab}</h2>", unsafe_allow_html=True)

    if selected_tab == "Мінування":
        df_m = raw_df.copy()
        df_m.columns = df_m.iloc[0]
        df_m = df_m.iloc[1:].reset_index(drop=True)
        
        # Перетворення дат
        df_m['Дата_чиста'] = pd.to_datetime(df_m['Дата'], dayfirst=True, errors='coerce')
        df_m['Кількість'] = pd.to_numeric(df_m['Кількість'], errors='coerce').fillna(0)
        df_m = df_m[df_m['Дата_чиста'].notnull()]
        
        if not df_m.empty:
            df_m['Year'] = df_m['Дата_чиста'].dt.year
            df_m['Month'] = df_m['Дата_чиста'].dt.month
            df_m['Day_Label'] = df_m['Дата_чиста'].dt.strftime('%d.%m')
            df_m['Month_Label'] = df_m['Month'].map(MONTHS_UKR) + " " + df_m['Year'].astype(str)
            df_m['Sort_Key'] = df_m['Year'] * 100 + df_m['Month']

            # ГРАФІК 1: ПО ДНЯХ
            st.markdown("### 📅 Щоденна робота")
            month_list = df_m[['Month_Label', 'Sort_Key']].drop_duplicates().sort_values('Sort_Key', ascending=False)
            sel_month = st.selectbox("Оберіть місяць:", month_list['Month_Label'])
            
            plot_df = df_m[df_m['Month_Label'] == sel_month].sort_values('Дата_чиста')
            daily_res = plot_df.groupby('Day_Label')['Кількість'].sum().reset_index()

            fig1 = go.Figure(go.Bar(x=daily_res['Day_Label'], y=daily_res['Кількість'], marker_color='#ED7D31', text=daily_res['Кількість'], textposition='outside'))
            fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            st.plotly_chart(fig1, use_container_width=True)

            # ГРАФІК 2: ПІДСУМОК
            st.markdown("### 📈 Всього за місяць")
            overall = df_m.groupby(['Sort_Key', 'Month_Label'])['Кількість'].sum().reset_index().sort_values('Sort_Key')
            fig2 = go.Figure(go.Bar(x=overall['Month_Label'], y=overall['Кількість'], marker_color='#FF8C00', text=overall['Кількість'], textposition='outside'))
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            st.plotly_chart(fig2, use_container_width=True)
            
            with st.expander("📂 ПЕРЕГЛЯНУТИ ТАБЛИЦЮ"):
                # Автоматично приховуємо технічні колонки, які ми створили для розрахунків
                tech_cols = ['Дата_чиста', 'Year', 'Month', 'Day_Label', 'Month_Label', 'Sort_Key']
                display_cols = [c for c in df_m.columns if c not in tech_cols]
                st.dataframe(df_m[display_cols], use_container_width=True, hide_index=True)
        else:
            st.warning("Дані не знайдено. Перевірте формат дат.")

    elif selected_tab == "Бригадний ЗГ":
        sub = raw_df.iloc[1].values
        data = raw_df.iloc[2:][raw_df.iloc[2:, 0] != ""]
        def bc(d, t, start_col):
            f = go.Figure()
            clrs = {'1 аемб': '#92D050', '2 аемб': '#A5A5A5', '3 аемб': '#4472C4', '4 аемб': '#ED7D31'}
            for u, c in clrs.items():
                col_idx = [i for i, x in enumerate(sub) if u in str(x) and i >= start_col and i < start_col+6]
                if col_idx:
                    v = pd.to_numeric(d.iloc[:, col_idx[0]], errors='coerce').fillna(0)
                    f.add_trace(go.Bar(x=d.iloc[:, 0], y=v, name=u, marker_color=c, text=v, textposition='outside'))
            f.update_layout(title=t, barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            return f
        st.plotly_chart(bc(data, "🏆 ЗАГАЛЬНИЙ РЕЗУЛЬТАТ", 0), use_container_width=True)
        st.plotly_chart(bc(data, "🔥 УРАЖЕННЯ", 6), use_container_width=True)
        st.plotly_chart(bc(data, "🧨 МІНУВАННЯ", 12), use_container_width=True)

    elif selected_tab == "Е-Бали":
        dates = raw_df.iloc[1:, 0]
        f = go.Figure()
        f.add_trace(go.Bar(x=dates, y=raw_df.iloc[1:, 1], name='Лютий', marker_color='#A5A5A5', text=raw_df.iloc[1:, 1], textposition='outside'))
        f.add_trace(go.Bar(x=dates, y=raw_df.iloc[1:, 2], name='Березень', marker_color='#92D050', text=raw_df.iloc[1:, 2], textposition='outside'))
        f.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=500)
        st.plotly_chart(f, use_container_width=True)
        st.dataframe(raw_df.iloc[1:].T, use_container_width=True)

    else:
        st.dataframe(raw_df.iloc[1:], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Помилка завантаження: {e}")
