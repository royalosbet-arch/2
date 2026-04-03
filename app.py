import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64

# --- 1. НАЛАШТУВАННЯ ---
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
            st.markdown(" <div style='background:rgba(255,255,255,0.05); padding:40px; border-radius:20px; border:1px solid rgba(255,255,255,0.1); text-align:center;'><h2 style='color:white; margin-bottom: 0;'>🛡️ СИТУАЦІЙНИЙ ЦЕНТР</h2><p style='color:#888;'>1 аемб. АВТОРИЗАЦІЯ</p></div>", unsafe_allow_html=True)
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
    st.markdown(f'<style>.stApp {{ {bg_css} background-size: cover; background-position: center; background-attachment: fixed; }} .stDataFrame {{ background: rgba(0,0,0,0.8); border-radius: 10px; }} [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}</style>', unsafe_allow_html=True)

set_design('background.jpg')

# --- 3. ПІДКЛЮЧЕННЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)
st.sidebar.title("🛠️ НАВІГАЦІЯ")
category = st.sidebar.radio("Оберіть напрямок:", ["⚔️ Бригадні звіти", "📈 Рейтинг та Бали", "🧨 Мінування", "🔥 Ураження", "📡 Спец. розділи"])

# Навігація
selected_tab = ""
if category == "⚔️ Бригадні звіти": selected_tab = st.sidebar.selectbox("Розділ:", ["Бригадний ЗГ", "Бригадний"])
elif category == "📈 Рейтинг та Бали": selected_tab = st.sidebar.selectbox("Розділ:", ["Е-Бали", "Розрахунки"])
elif category == "🧨 Мінування": selected_tab = "Мінування"
elif category == "🔥 Ураження":
    months = ["04.2026", "03.2026", "02.2026", "01.2026", "12.2025", "11.2025"]
    selected_tab = f"Ураження {st.sidebar.selectbox('Місяць:', months)}"
else: selected_tab = st.sidebar.selectbox("Розділ:", ["ЗГ", "НРК"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

# --- 4. ФУНКЦІЯ ОЧИСТКИ ЧИСЕЛ ---
def to_native(val):
    """Перетворює будь-яке число в чистий Python float/int"""
    try:
        f_val = float(val)
        return int(f_val) if f_val == int(f_val) else f_val
    except: return 0

# --- 5. ВІДОБРАЖЕННЯ ---
try:
    df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
    st.markdown(f"<h2 style='text-align:center; color:white;'>📊 {selected_tab}</h2>", unsafe_allow_html=True)

    if selected_tab == "Мінування":
        # Перетворюємо в список списків (PURE PYTHON)
        data_list = df.values.tolist()
        headers = data_list[0]
        rows = data_list[1:]
        
        # Ручна фільтрація та перетворення
        clean_rows = []
        for r in rows:
            date_raw = str(r[0])
            # Спроба розпізнати дату
            try: 
                dt = pd.to_datetime(date_raw, dayfirst=True, errors='coerce')
                if pd.notnull(dt):
                    # Створюємо словник рядка з чистими типами
                    clean_rows.append({
                        "Дата_dt": dt,
                        "Дата_str": dt.strftime('%d.%m'),
                        "Місяць_Рік": MONTHS_UKR.get(dt.month, "Невідомо") + " " + str(dt.year),
                        "Сорт": dt.year * 100 + dt.month,
                        "Кількість": to_native(r[2]),
                        "БК": str(r[1]),
                        "Верифікація": str(r[3])
                    })
            except: continue

        if clean_rows:
            # Графік 1: По днях
            all_months = sorted(list(set([r["Місяць_Рік"] for r in clean_rows])), reverse=True)
            sel_m = st.selectbox("Оберіть місяць:", all_months)
            
            m_data = [r for r in clean_rows if r["Місяць_Рік"] == sel_m]
            m_data.sort(key=lambda x: x["Дата_dt"])
            
            # Групуємо по днях вручну
            days = {}
            for r in m_data:
                d = r["Дата_str"]
                days[d] = days.get(d, 0) + r["Кількість"]
            
            fig1 = go.Figure(go.Bar(
                x=list(days.keys()), 
                y=[float(v) for v in days.values()], 
                marker_color='#ED7D31', text=[str(v) for v in days.values()], textposition='outside'
            ))
            fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig1, use_container_width=True)

            # Графік 2: По місяцях
            month_totals = {}
            sort_map = {}
            for r in clean_rows:
                m = r["Місяць_Рік"]
                month_totals[m] = month_totals.get(m, 0) + r["Кількість"]
                sort_map[m] = r["Сорт"]
            
            sorted_m = sorted(month_totals.keys(), key=lambda x: sort_map[x])
            
            fig2 = go.Figure(go.Bar(
                x=sorted_m, 
                y=[float(month_totals[m]) for m in sorted_m], 
                marker_color='#FF8C00', text=[str(month_totals[m]) for m in sorted_m], textposition='outside'
            ))
            fig2.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig2, use_container_width=True)

            with st.expander("📂 ПЕРЕГЛЯНУТИ ТАБЛИЦЮ"):
                # Створюємо просту таблицю без індексів Pandas
                simple_df = pd.DataFrame([{ "Дата": r["Дата_str"], "БК": r["БК"], "Кількість": r["Кількість"], "Верифікація": r["Верифікація"] } for r in clean_rows])
                st.write(simple_df.astype(str))
        else:
            st.warning("Перевірте формат дат у стовпчику 'Дата'.")

    elif selected_tab == "Бригадний ЗГ":
        sub = [str(x) for x in df.iloc[1].values]
        d_rows = df.iloc[2:].values.tolist()
        def bc(title, start_c):
            f = go.Figure()
            clrs = {'1 аемб': '#92D050', '2 аемб': '#A5A5A5', '3 аемб': '#4472C4', '4 аемб': '#ED7D31'}
            for u, c in clrs.items():
                idx = [i for i, x in enumerate(sub) if u in x and i >= start_c and i < start_c+6]
                if idx:
                    v = [to_native(r[idx[0]]) for r in d_rows if r[0] != ""]
                    x_axis = [str(r[0]) for r in d_rows if r[0] != ""]
                    f.add_trace(go.Bar(x=x_axis, y=[float(val) for val in v], name=u, marker_color=c, text=[str(val) for val in v], textposition='outside'))
            f.update_layout(title=title, barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            return f
        st.plotly_chart(bc("🏆 ЗАГАЛЬНИЙ РЕЗУЛЬТАТ", 0), use_container_width=True)
        st.plotly_chart(bc("🔥 УРАЖЕННЯ", 6), use_container_width=True)
        st.plotly_chart(bc("🧨 МІНУВАННЯ", 12), use_container_width=True)

    elif selected_tab == "Е-Бали":
        d_list = df.values.tolist()[1:]
        dates = [str(r[0]) for r in d_list]
        v1 = [to_native(r[1]) for r in d_list]
        v2 = [to_native(r[2]) for r in d_list]
        f = go.Figure()
        f.add_trace(go.Bar(x=dates, y=[float(x) for x in v1], name='Попередній', marker_color='#A5A5A5', text=[str(x) for x in v1], textposition='outside'))
        f.add_trace(go.Bar(x=dates, y=[float(x) for x in v2], name='Поточний', marker_color='#92D050', text=[str(x) for x in v2], textposition='outside'))
        f.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=500)
        st.plotly_chart(f, use_container_width=True)
        st.write(df.iloc[1:].T.astype(str))

    else:
        st.write(df.iloc[1:].astype(str))

except Exception as e:
    st.error(f"Помилка завантаження: {e}")
