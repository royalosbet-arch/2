import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64

# --- 1. НАЛАШТУВАННЯ ТА ПАРОЛЬ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

USER_PASSWORD = "2887" 

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
                else: st.error("❌ Невірний код.")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. ДИЗАЙН ---
def set_design(bin_file):
    try:
        with open(bin_file, 'rb') as f: data = f.read()
        bin_str = base64.b64encode(data).decode()
        bg_css = f'background-image: url("data:image/png;base64,{bin_str}");'
    except: bg_css = 'background-color: #0E1117;'
    
    st.markdown(f'''
    <style>
    .stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }}
    [data-testid="stMetric"] {{
        background: rgba(0, 0, 0, 0.7) !important;
        border-left: 5px solid #ff4b4b !important;
        border-radius: 10px !important;
        padding: 20px !important;
    }}
    .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }}
    [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}
    </style>
    ''', unsafe_allow_html=True)

set_design('background.jpg')

# --- 3. ПІДКЛЮЧЕННЯ ТА НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)

st.sidebar.title("🛠️ НАВІГАЦІЯ")
category = st.sidebar.radio(
    "Оберіть напрямок:",
    ["⚔️ Бригадні звіти", "📈 Рейтинг та Бали", "🧨 Мінування", "🔥 Ураження", "📡 Спец. розділи"]
)

selected_tab = ""
if category == "⚔️ Бригадні звіти":
    selected_tab = st.sidebar.selectbox("Розділ:", ["Бригадний ЗГ", "Бригадний"])
elif category == "📈 Рейтинг та Бали": 
    selected_tab = st.sidebar.selectbox("Розділ:", ["Е-Бали", "Розрахунки"])
elif category == "🧨 Мінування": 
    selected_tab = "Мінування"
elif category == "🔥 Ураження":
    months = ["04.2026", "03.2026", "02.2026", "01.2026", "12.2025", "11.2025"]
    selected_month = st.sidebar.selectbox("Оберіть місяць:", months)
    selected_tab = f"Ураження {selected_month}"
elif category == "📡 Спец. розділи": 
    selected_tab = st.sidebar.selectbox("Розділ:", ["ЗГ", "НРК"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

# --- 4. ВІДОБРАЖЕННЯ ДАНИХ ---
try:
    raw_df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
    st.markdown(f"<h2 style='text-align:center; color:white;'>📊 {selected_tab}</h2>", unsafe_allow_html=True)

    if selected_tab == "Мінування":
        try:
            # Обробка даних мінування
            df_m = raw_df.copy()
            df_m.columns = df_m.iloc[0]
            df_m = df_m.iloc[1:]
            
            # Конвертація дат та кількості
            df_m['Дата_dt'] = pd.to_datetime(df_m['Дата'], dayfirst=True, errors='coerce')
            df_m['Кількість'] = pd.to_numeric(df_m['Кількість'], errors='coerce').fillna(0)
            df_m = df_m.dropna(subset=['Дата_dt'])
            
            # Додаємо назви місяців для фільтрації
            df_m['Місяць_Рік'] = df_m['Дата_dt'].dt.strftime('%Y-%m')
            df_m['Місяць_Назва'] = df_m['Дата_dt'].dt.strftime('%B %Y')

            # --- ГРАФІК 1: ДЕТАЛЬНО ЗА МІСЯЦЬ ---
            st.markdown("### 📅 Детальна інтенсивність за місяць")
            available_months = sorted(df_m['Місяць_Рік'].unique(), reverse=True)
            sel_month = st.selectbox("Оберіть місяць для перегляду:", available_months, format_func=lambda x: pd.to_datetime(x).strftime('%B %Y'))
            
            monthly_data = df_m[df_m['Місяць_Рік'] == sel_month]
            daily_sum = monthly_data.groupby('Дата')['Кількість'].sum().reset_index()

            fig1 = go.Figure()
            fig1.add_trace(go.Bar(
                x=daily_sum['Дата'], y=daily_sum['Кількість'],
                marker_color='#ED7D31', text=daily_sum['Кількість'], textposition='outside'
            ))
            fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            st.plotly_chart(fig1, use_container_width=True)

            # --- ГРАФІК 2: ЗАГАЛЬНИЙ ПІДСУМОК ПО МІСЯЦЯХ ---
            st.write("---")
            st.markdown("### 📈 Загальний підсумок (з жовтня 2025)")
            
            # Групуємо по місяцях для всього періоду
            overall_monthly = df_m.groupby('Місяць_Рік')['Кількість'].sum().reset_index()
            overall_monthly = overall_monthly.sort_values('Місяць_Рік') # Сортуємо хронологічно

            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=overall_monthly['Місяць_Рік'].apply(lambda x: pd.to_datetime(x).strftime('%B %Y')), 
                y=overall_monthly['Кількість'],
                marker_color='#FF8C00', text=overall_monthly['Кількість'], textposition='outside'
            ))
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            st.plotly_chart(fig2, use_container_width=True)

            st.write("---")
            with st.expander("📂 АРХІВ ЗАПИСІВ МІНУВАННЯ"):
                st.dataframe(df_m.drop(columns=['Дата_dt', 'Місяць_Рік', 'Місяць_Назва']), use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Помилка аналізу мінування: {e}")
            st.dataframe(raw_df.iloc[1:])

    # --- ІНШІ РОЗДІЛИ (Бригадний ЗГ, Е-Бали) ЗАЛИШАЮТЬСЯ БЕЗ ЗМІН ---
    elif selected_tab == "Бригадний ЗГ":
        # (Тут залишається код для 3-х графіків бригади, як був раніше)
        sub_headers = raw_df.iloc[1].values
        main_data = raw_df.iloc[2:]
        main_data = main_data[main_data.iloc[:, 0].astype(str).str.strip() != ""]
        
        def create_bc(data, title):
            fig = go.Figure()
            colors = {'1 аемб': '#92D050', '2 аемб': '#A5A5A5', '3 аемб': '#4472C4', '4 аемб': '#ED7D31'}
            for unit, color in colors.items():
                matching = [c for c in data.columns if unit in str(c)]
                if matching:
                    v = pd.to_numeric(data[matching[0]], errors='coerce').fillna(0)
                    fig.add_trace(go.Bar(x=data.iloc[:, 0], y=v, name=unit, marker_color=color, text=v, textposition='outside'))
            fig.update_layout(title=title, barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            return fig

        st.plotly_chart(create_bc(main_data.iloc[:, 0:6].set_axis(sub_headers[0:6], axis=1), "🏆 ЗАГАЛЬНИЙ РЕЗУЛЬТАТ"), use_container_width=True)
        st.plotly_chart(create_bc(main_data.iloc[:, 6:12].set_axis(sub_headers[6:12], axis=1), "🔥 УРАЖЕННЯ"), use_container_width=True)
        st.plotly_chart(create_bc(main_data.iloc[:, 12:18].set_axis(sub_headers[12:18], axis=1), "🧨 МІНУВАННЯ"), use_container_width=True)

    elif selected_tab == "Е-Бали":
        dates = raw_df.iloc[1:, 0]
        fig = go.Figure()
        fig.add_trace(go.Bar(x=dates, y=raw_df.iloc[1:, 1], name='Лютий', marker_color='#A5A5A5', text=raw_df.iloc[1:, 1], textposition='outside'))
        fig.add_trace(go.Bar(x=dates, y=raw_df.iloc[1:, 2], name='Березень', marker_color='#92D050', text=raw_df.iloc[1:, 2], textposition='outside'))
        fig.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color="white"), height=500)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(raw_df.iloc[1:].T, use_container_width=True)

    else:
        st.write("---")
        with st.expander("📂 ВІДКРИТИ ТАБЛИЦЮ", expanded=True):
            st.dataframe(raw_df.iloc[1:], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Системна помилка: {e}")
