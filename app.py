import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64
import re
from datetime import datetime, date

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

# --- 4. ДОПОМІЖНІ ФУНКЦІЇ ---
def to_native(val):
    try:
        f_val = float(str(val).replace(',', '.'))
        return int(f_val) if f_val == int(f_val) else f_val
    except: return 0

def calc_verified(total, text):
    """Логіка верифікації за правилами користувача"""
    txt = str(text).lower().strip()
    if "не верифіковано" in txt:
        match = re.search(r'(\d+)', txt)
        unverified = int(match.group(1)) if match else 0
        return max(0, total - unverified)
    elif "верифіковано" in txt or txt == "так":
        return total
    return 0

# --- 5. ВІДОБРАЖЕННЯ ---
try:
    df = conn.read(worksheet=selected_tab, ttl=300, header=None).fillna("")
    st.markdown(f"<h2 style='text-align:center; color:white;'>📊 {selected_tab}</h2>", unsafe_allow_html=True)

    if selected_tab == "Мінування":
        data_list = df.values.tolist()
        rows = data_list[1:]
        
        clean_rows = []
        for r in rows:
            try: 
                dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                if pd.notnull(dt):
                    total = to_native(r[2])
                    verif_txt = str(r[3])
                    clean_rows.append({
                        "Дата_dt": dt,
                        "Рік": dt.year, "Місяць": dt.month, "День": dt.day,
                        "Місяць_Рік": MONTHS_UKR.get(dt.month, "M") + " " + str(dt.year),
                        "Сорт": dt.year * 100 + dt.month,
                        "Всього": total,
                        "Верифіковано": calc_verified(total, verif_txt),
                        "БК": str(r[1]),
                        "Верифікація_Текст": verif_txt
                    })
            except: continue

        if clean_rows:
            st.markdown("### 📅 Детальна робота по днях")
            all_m_labels = sorted(list(set([r["Місяць_Рік"] for r in clean_rows])), reverse=True)
            sel_m = st.selectbox("Оберіть місяць:", all_m_labels)
            
            # Фільтруємо дані
            m_data = [r for r in clean_rows if r["Місяць_Рік"] == sel_m]
            target_year = m_data[0]["Рік"]
            target_month = m_data[0]["Місяць"]
            
            # Генеруємо повний календар місяця
            num_days = pd.Period(f"{target_year}-{target_month}").days_in_month
            full_days_labels = [f"{d}.{str(target_month).zfill(2)}" for d in range(1, num_days + 1)]
            
            # Підсумовуємо дані по днях
            daily_total = {d: 0 for d in full_days_labels}
            daily_verif = {d: 0 for d in full_days_labels}
            
            for r in m_data:
                d_lab = f"{r['День']}.{str(target_month).zfill(2)}"
                daily_total[d_lab] += r["Всього"]
                daily_verif[d_lab] += r["Верифіковано"]
            
            fig1 = go.Figure()
            # Стовпчик Всього
            fig1.add_trace(go.Bar(
                x=full_days_labels, y=[float(daily_total[d]) for d in full_days_labels],
                name='Всього', marker_color='#ED7D31', text=[str(daily_total[d]) if daily_total[d]>0 else "" for d in full_days_labels],
                textposition='outside'
            ))
            # Стовпчик Верифіковано
            fig1.add_trace(go.Bar(
                x=full_days_labels, y=[float(daily_verif[d]) for d in full_days_labels],
                name='Верифіковано', marker_color='#92D050', text=[str(daily_verif[d]) if daily_verif[d]>0 else "" for d in full_days_labels],
                textposition='outside'
            ))
            
            fig1.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig1, use_container_width=True)

            # Загальний підсумок (без змін, але з додаванням верифікації)
            st.markdown("### 📈 Підсумок по місяцях")
            month_totals = {}
            month_verif = {}
            sort_map = {}
            for r in clean_rows:
                m = r["Місяць_Рік"]
                month_totals[m] = month_totals.get(m, 0) + r["Всього"]
                month_verif[m] = month_verif.get(m, 0) + r["Верифіковано"]
                sort_map[m] = r["Сорт"]
            
            sorted_m = sorted(month_totals.keys(), key=lambda x: sort_map[x])
            
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=sorted_m, y=[float(month_totals[m]) for m in sorted_m], name="Всього", marker_color='#FF8C00', text=[str(month_totals[m]) for m in sorted_m], textposition='outside'))
            fig2.add_trace(go.Bar(x=sorted_m, y=[float(month_verif[m]) for m in sorted_m], name="Верифіковано", marker_color='#00B050', text=[str(month_verif[m]) for m in sorted_m], textposition='outside'))
            fig2.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white")
            st.plotly_chart(fig2, use_container_width=True)

            with st.expander("📂 АРХІВ ТАБЛИЦІ"):
                simple_df = pd.DataFrame([{ 
                    "Дата": r["Дата_dt"].strftime('%d.%m.%Y'), 
                    "БК": r["БК"], 
                    "Всього": r["Всього"], 
                    "Верифіковано": r["Верифіковано"],
                    "Статус": r["Верифікація_Текст"] 
                } for r in clean_rows])
                st.write(simple_df.astype(str))
        else: st.warning("Дані не знайдено.")

    # Решта розділів без змін (залишаю логіку bc та Е-Бали з минулого повідомлення)
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
                    f.add_trace(go.Bar(x=[str(r[0]) for r in d_rows if r[0] != ""], y=[float(val) for val in v], name=u, marker_color=c, text=[str(val) for val in v], textposition='outside'))
            f.update_layout(title=title, barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=400)
            return f
        st.plotly_chart(bc("🏆 ЗАГАЛЬНИЙ РЕЗУЛЬТАТ", 0), use_container_width=True)
        st.plotly_chart(bc("🔥 УРАЖЕННЯ", 6), use_container_width=True)
        st.plotly_chart(bc("🧨 МІНУВАННЯ", 12), use_container_width=True)

    elif selected_tab == "Е-Бали":
        d_list = df.values.tolist()[1:]
        dates = [str(r[0]) for r in d_list]
        f = go.Figure()
        f.add_trace(go.Bar(x=dates, y=[float(to_native(r[1])) for r in d_list], name='Попередній', marker_color='#A5A5A5', text=[str(to_native(r[1])) for r in d_list], textposition='outside'))
        f.add_trace(go.Bar(x=dates, y=[float(to_native(r[2])) for r in d_list], name='Поточний', marker_color='#92D050', text=[str(to_native(r[2])) for r in d_list], textposition='outside'))
        f.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', font_color="white", height=500)
        st.plotly_chart(f, use_container_width=True)
        st.write(df.iloc[1:].T.astype(str))

    else:
        st.write(df.iloc[1:].astype(str))

except Exception as e:
    st.error(f"Помилка завантаження: {e}")
