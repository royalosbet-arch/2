import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64
import re
from datetime import datetime

# =================================================================
# 1. НАЛАШТУВАННЯ ТА КОНСТАНТИ
# =================================================================
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

USER_PASSWORD = "2887"
POINTS_MAP = {
    "О/С 200": 12, "О/С 300": 8, "Молнія": 10, "Укриття": 1, "Фортифікація": 1,
    "Антена": 4, "ФПВ": 6, "Танк": 40, "Бомбер": 6, "РЛС": 50, "САУ": 30,
    "Міномет": 5, "ЛАТ": 8, "Генератор": 4, "Електросамокат": 4, "Квадроцикл": 4,
    "Мотоцикл": 4, "РЕБ": 8, "Мавік": 6, "Орлан": 40, "Шахед": 20, "Ждун": 10,
    "Автомобіль": 5, "Гаубиця": 40, "ББМ": 20, "Гармата": 20
}

MONTHS_UKR = {1:"Січень", 2:"Лютий", 3:"Березень", 4:"Квітень", 5:"Травень", 6:"Червень", 7:"Липень", 8:"Серпень", 9:"Вересень", 10:"Жовтень", 11:"Листопад", 12:"Грудень"}
CLRS = {'1аемб': '#92D050', '2аемб': '#A5A5A5', '3аемб': '#4472C4', '4аемб': '#ED7D31', 'ЗРДН': '#FFC000'}
MINE_CLR = "#7030A0"

# =================================================================
# 2. ДОПОМІЖНІ ФУНКЦІЇ
# =================================================================
def get_base64(path):
    try:
        with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return None

def to_native(val):
    try:
        s = str(val).replace(',', '.').strip()
        return float(s) if s not in ["", "-", ".", "•"] else 0.0
    except: return 0.0

def get_urazh_data(qty, target, status):
    t_clean = str(target).strip()
    unit_p = POINTS_MAP.get(t_clean, 0)
    st_clean = str(status).lower().strip()
    if st_clean == "верифіковано":
        return qty * unit_p, qty
    return 0.0, 0.0

def get_mine_data(qty, status):
    st_cl = str(status).lower().strip()
    if "не верифіковано" in st_cl:
        match = re.search(r'(\d+)', st_cl)
        unv_q = float(match.group(1)) if match else qty
        return max(0.0, qty - unv_q), unv_q
    elif st_cl == "верифіковано":
        return qty, 0.0
    return 0.0, qty

# =================================================================
# 3. ЕКРАН ВХОДУ ТА ДИЗАЙН (ЗОЛОТИЙ СТАНДАРТ)
# =================================================================
if "password_correct" not in st.session_state:
    logo = get_base64("logo.png")
    st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1.2, 1.5, 1.2])
    with col_c:
        st.write("<br><br>", unsafe_allow_html=True)
        if logo: st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{logo}' style='max-width:210px; border-radius:15px;'></div>", unsafe_allow_html=True)
        st.markdown("""
            <div style='background:rgba(255,255,255,0.04); padding: 35px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.15); text-align: center; font-family: "Inter", sans-serif;'>
                <h2 style='color:white; margin:0;'>1 аемб</h2>
                <p style='color:#ffd700; font-size: 16px; font-weight: 600; margin-bottom: 20px;'>77 ОАЕМБр • ДШВ ЗСУ 🇺🇦</p>
                <hr style='border:0; border-top: 1px solid rgba(255,255,255,0.1);'>
                <p style='color:white; font-size: 13px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-top: 15px;'>СИТУАЦІЙНИЙ ЦЕНТР БАТАЛЬЙОНУ</p>
            </div>
        """, unsafe_allow_html=True)
        pwd = st.text_input("КОД ДОСТУПУ:", type="password")
        if st.button("УВІЙТИ В СИСТЕМУ") and pwd == USER_PASSWORD:
            st.session_state["password_correct"] = True
            st.rerun()
    st.stop()

bg = get_base64("background.jpg")
bg_style = f'background-image: url("data:image/png;base64,{bg}");' if bg else 'background-color: #0E1117;'
st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp {{ {bg_style} background-size: cover; background-position: center; background-attachment: fixed; font-family: "Inter", sans-serif; }}
    [data-testid="stTable"], .stDataFrame, [data-testid="stDataFrame"] {{ background-color: transparent !important; }}
    table {{ background-color: rgba(255,255,255,0.05) !important; color: white !important; border-radius: 10px; width: 100%; }}
    thead tr th {{ background-color: rgba(0,0,0,0.6) !important; color: #ffd700 !important; font-weight: 800 !important; border-bottom: 1px solid rgba(255,215,0,0.2) !important; }}
    tbody tr td {{ background-color: transparent !important; color: white !important; border-bottom: 1px solid rgba(255,255,255,0.05) !important; }}
    [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}
    [data-testid="stMetricValue"] {{ color: #ffd700 !important; font-size: 34px !important; font-weight: 800 !important; }}
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 4. НАВІГАЦІЯ ТА ДАНІ
# =================================================================
conn = st.connection("gsheets", type=GSheetsConnection)
category = st.sidebar.radio("НАПРЯМОК РОБОТИ:", ["⚔️ Бригадні звіти", "🧨 Мінування", "🔥 Ураження"])

if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

try:
    if category == "⚔️ Бригадні звіти":
        st.markdown("<h3 style='text-align:center; color:white;'>⚔️ ЗАГАЛЬНОБРИГАДНИЙ МОНІТОРИНГ</h3>", unsafe_allow_html=True)
        unit_names = ["1аемб", "2аемб", "3аемб", "4аемб", "ЗРДН"]
        all_results = []
        cur_m, cur_y = 4, 2026

        for b_name in unit_names:
            try:
                if b_name == "1аемб":
                    df_u = conn.read(worksheet="Ураження 04.2026", ttl=300, header=None).fillna("")
                    u_rows = df_u.values.tolist()
                    l_dt = None
                    for r in u_rows[1:]:
                        if str(r[0]).strip() != "":
                            dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                            if pd.notnull(dt): l_dt = dt
                        if l_dt and str(r[1]).strip() not in ["", "-", "•", ".", "Ціль"]:
                            vp, vq = get_urazh_data(to_native(r[2]), str(r[1]), str(r[3]))
                            all_results.append({"D": l_dt, "B": b_name, "T": str(r[1]), "PU": vp, "PM": 0.0, "QT": to_native(r[2]), "QV": vq})
                    df_m = conn.read(worksheet="Мінування", ttl=300, header=None).fillna("")
                    m_rows = df_m.values.tolist()
                    for r in m_rows[1:]:
                        dt_m = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                        if pd.notnull(dt_m):
                            vq_m, _ = get_mine_data(to_native(r[2]), str(r[3]))
                            if vq_m > 0:
                                all_results.append({"D": dt_m, "B": b_name, "T": "Мінування", "PU": 0.0, "PM": vq_m, "QT": vq_m, "QV": vq_m})
                else:
                    df_unit = conn.read(worksheet=b_name, ttl=300, header=None).fillna("")
                    u_rows = df_unit.values.tolist()
                    l_dt = None
                    for r in u_rows[1:]:
                        if str(r[0]).strip() != "":
                            dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                            if pd.notnull(dt): l_dt = dt
                        if not l_dt: continue
                        target = str(r[1]).strip()
                        if target not in ["", "-", "•", ".", "Ціль"]:
                            vp, vq = get_urazh_data(to_native(r[2]), target, str(r[3]))
                            all_results.append({"D": l_dt, "B": b_name, "T": target, "PU": vp, "PM": 0.0, "QT": to_native(r[2]), "QV": vq})
                        if len(r) > 4:
                            v_mine, _ = get_mine_data(to_native(r[4]), "Верифіковано")
                            if v_mine > 0:
                                all_results.append({"D": l_dt, "B": b_name, "T": "Мінування", "PU": 0.0, "PM": v_mine, "QT": v_mine, "QV": v_mine})
            except: continue

        if all_results:
            filtered = [r for r in all_results if r["D"].month == cur_m and r["D"].year == cur_y]
            if not filtered: filtered = all_results
            
            # --- БЛОК 1: ДЕТАЛІЗАЦІЯ ПІДРОЗДІЛУ ---
            st.markdown("---")
            sel_b = st.selectbox("ДЕТАЛІЗАЦІЯ ПІДРОЗДІЛУ:", unit_names)
            u_res = [r for r in filtered if r["B"] == sel_b]
            
            # Додано: Сумарний бал по батальйону
            u_total_pts = int(sum(r["PU"] + r["PM"] for r in u_res))
            st.metric(f"ВСЬОГО БАЛІВ ({sel_b}):", u_total_pts)
            
            u_table = []
            for t in sorted(list(set([r["T"] for r in u_res]))):
                u_table.append({
                    "Тип цілі": t, "Всього (шт)": int(sum(r["QT"] for r in u_res if r["T"] == t)),
                    "Верифіковано (шт)": int(sum(r["QV"] for r in u_res if r["T"] == t)),
                    "Бали": int(sum(r["PU"] + r["PM"] for r in u_res if r["T"] == t))
                })
            st.table(pd.DataFrame(u_table).sort_values(by="Бали", ascending=False))

            # --- БЛОК 2: ГРАФІКИ ТА ЗАГАЛЬНА МЕТРИКА ---
            st.markdown("---")
            # Додано: Загальна метрика бригади біля графіка
            st.metric("БРИГАДА (ВЕРИФІКОВАНО ЗА КВІТЕНЬ):", int(sum(r["PU"] + r["PM"] for r in filtered)))
            
            all_dates = sorted(list(set([r["D"] for r in filtered])))
            x_labs = [d.strftime('%d.%m') for d in all_dates]
            
            t1, t2 = st.tabs(["📈 Прогрес за місяць", "📊 Статистика за день"])
            def draw_chart(mode):
                fig = go.Figure()
                for b in unit_names:
                    yu, ym = [], []
                    acc_u, acc_m = 0.0, 0.0
                    for d in all_dates:
                        du = sum(r["PU"] for r in filtered if r["D"] == d and r["B"] == b)
                        dm = sum(r["PM"] for r in filtered if r["D"] == d and r["B"] == b)
                        if mode == "cum":
                            acc_u += du; acc_m += dm
                            yu.append(acc_u); ym.append(acc_m)
                        else:
                            yu.append(du); ym.append(dm)
                    if (sum(yu) + sum(ym)) > 0:
                        lbls = [f"<b>{int(u+m)}</b><br>{b}" if (u+m) > 0 else "" for u, m in zip(yu, ym)]
                        fig.add_trace(go.Bar(x=x_labs, y=yu, marker_color=CLRS[b], offsetgroup=b, showlegend=False))
                        fig.add_trace(go.Bar(x=x_labs, y=ym, marker_color=MINE_CLR, offsetgroup=b, base=yu, showlegend=False, text=lbls, textposition='outside', cliponaxis=False, textfont=dict(color='white', size=11)))
                fig.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=500, xaxis=dict(type='category'), margin=dict(t=80))
                return fig
            with t1: st.plotly_chart(draw_chart("cum"), use_container_width=True)
            with t2: st.plotly_chart(draw_chart("day"), use_container_width=True)

    elif category == "🧨 Мінування":
        df = conn.read(worksheet="Мінування", ttl=300, header=None).fillna("")
        raw_m = df.values.tolist()[1:]; m_list = []
        for r in raw_m:
            dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
            if pd.notnull(dt):
                vq, uq = get_mine_data(to_native(r[2]), r[3])
                m_list.append({"D": dt, "Month": MONTHS_UKR.get(dt.month, "") + " " + str(dt.year), "V": vq, "U": uq})
        if m_list:
            sel_m = st.selectbox("ПЕРІОД:", sorted(list(set([x["Month"] for x in m_list if x["Month"] != ""])), reverse=True))
            m_data = [x for x in m_list if x["Month"] == sel_m]
            labs = [f"{d}.{str(m_data[0]['D'].month).zfill(2)}" for d in range(1, pd.Period(f"{m_data[0]['D'].year}-{m_data[0]['D'].month}").days_in_month + 1)]
            vv, uu = {l:0.0 for l in labs}, {l:0.0 for l in labs}
            for r in m_data:
                l = f"{r['D'].day}.{str(r['D'].month).zfill(2)}"
                if l in vv: vv[l] += r["V"]; uu[l] += r["U"]
            st.metric("ВЕРИФІКОВАНО МІН:", int(sum(vv.values())))
            fm = go.Figure()
            fm.add_trace(go.Bar(x=labs, y=[vv[l] for l in labs], name='Вериф', marker_color='#444444'))
            fm.add_trace(go.Bar(x=labs, y=[uu[l] for l in labs], name='Не вериф', marker_color='#CC0000'))
            fm.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category'), tickangle=-45)
            st.plotly_chart(fm, use_container_width=True)

    elif category == "🔥 Ураження":
        sel_ur = st.selectbox("ОБЕРІТЬ ПЕРІОД:", ["04.2026", "03.2026", "02.2026", "01.2026"])
        df = conn.read(worksheet=f"Ураження {sel_ur}", ttl=300, header=None).fillna("")
        raw_u = df.values.tolist()[1:]; clean_u, last_dt, obs = [], None, {}
        for r_u in raw_u:
            if str(r_u[0]).strip() != "":
                dt = pd.to_datetime(str(r_u[0]), dayfirst=True, errors='coerce')
                if pd.notnull(dt): last_dt = dt
            if last_dt and str(r_u[1]).strip() not in ["", "-", "•", ".", "Ціль"]:
                vp, vq = get_urazh_data(to_native(r_u[2]), str(r_u[1]), str(r_u[3]))
                clean_u.append({"D": last_dt, "V": vp, "U": (to_native(r_u[2])*POINTS_MAP.get(str(r_u[1]).strip(), 0))-vp, "T": str(r_u[1]), "QT": to_native(r_u[2]), "QV": vq})
        if clean_u:
            st.metric("ВЕРИФІКОВАНІ БАЛИ БАТАЛЬЙОНУ:", int(sum(r_u["V"] for r_u in clean_u)))
            labs = [f"{d}.{str(clean_u[0]['D'].month).zfill(2)}" for d in range(1, pd.Period(f"{clean_u[0]['D'].year}-{clean_u[0]['D'].month}").days_in_month + 1)]
            vv, uu = {l:0.0 for l in labs}, {l:0.0 for l in labs}
            for r_u in clean_u:
                l = f"{r_u['D'].day}.{str(r_u['D'].month).zfill(2)}"
                if l in vv: vv[l] += r_u["V"]; uu[l] += r_u["U"]
                n = r_u["T"]
                if n not in obs: obs[n] = [0,0,0]
                obs[n][0]+=r_u["QT"]; obs[n][1]+=r_u["QV"]; obs[n][2]+=r_u["V"]
            fu = go.Figure()
            fu.add_trace(go.Bar(x=labs, y=[vv[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            fu.add_trace(go.Bar(x=labs, y=[uu[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            fu.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category'), tickangle=-45)
            st.plotly_chart(fu, use_container_width=True)
            st.table(pd.DataFrame([{"Тип цілі":k, "Всього":int(v[0]), "Верифіковано":int(v[1]), "Бали":int(v[2])} for k,v in sorted(obs.items(), key=lambda x:x[1][2], reverse=True)]))

except Exception as e:
    st.error(f"СИСТЕМНА ПОМИЛКА: {e}")
