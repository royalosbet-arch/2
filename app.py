import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64
import re

# =================================================================
# 1. НАЛАШТУВАННЯ ТА КОНСТАНТИ
# =================================================================
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

USER_PASSWORD = "2887"
# Актуальні бали згідно зі списком
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
    """Binary логіка: Тільки статус 'Верифіковано' """
    t_clean = str(target).strip()
    unit_p = POINTS_MAP.get(t_clean, 0)
    st_clean = str(status).lower().strip()
    if st_clean == "верифіковано":
        return qty * unit_p, qty
    return 0.0, 0.0

def get_mine_data(qty, status):
    """Арифметична логіка для мінування: віднімання не верифікованих """
    st_cl = str(status).lower().strip()
    if "не верифіковано" in st_cl:
        match = re.search(r'(\d+)', st_cl)
        unv_q = float(match.group(1)) if match else qty
        return max(0.0, qty - unv_q), unv_q
    elif st_cl == "верифіковано":
        return qty, 0.0
    return 0.0, qty

# =================================================================
# 3. ЕКРАН ВХОДУ ТА ДИЗАЙН
# =================================================================
if "password_correct" not in st.session_state:
    logo = get_base64("logo.png")
    st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)
    _, col_c, _ = st.columns([1.2, 1.5, 1.2])
    with col_c:
        st.write("<br><br>", unsafe_allow_html=True)
        if logo: st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{logo}' style='max-width:210px; border-radius:15px;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='background:rgba(255,255,255,0.04); padding: 35px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.15); text-align: center; font-family: sans-serif;'><h2 style='color:white; margin:0;'>1 аемб</h2><p style='color:#ffd700; font-weight: 600;'>77 ОАЕМБр • ДШВ ЗСУ 🇺🇦</p><hr style='border:0; border-top: 1px solid rgba(255,255,255,0.1);'><p style='color:white; font-size: 13px; font-weight: 800; letter-spacing: 2px; text-transform: uppercase; margin-top: 15px;'>СИТУАЦІЙНИЙ ЦЕНТР БАТАЛЬЙОНУ</p></div>", unsafe_allow_html=True)
        pwd = st.text_input("ВВЕДІТЬ КОД ДОСТУПУ:", type="password")
        if st.button("УВІЙТИ") and pwd == USER_PASSWORD:
            st.session_state["password_correct"] = True
            st.rerun()
    st.stop()

# Жорсткий CSS для прозорості таблиць
bg = get_base64("background.jpg")
bg_style = f'background-image: url("data:image/png;base64,{bg}");' if bg else 'background-color: #0E1117;'
st.markdown(f"""
    <style>
    .stApp {{ {bg_style} background-size: cover; background-position: center; background-attachment: fixed; font-family: sans-serif; }}
    [data-testid="stTable"], .stDataFrame, [data-testid="stDataFrame"] {{ background-color: transparent !important; }}
    table {{ background-color: rgba(255,255,255,0.05) !important; color: white !important; border-radius: 10px; width: 100%; }}
    thead tr th {{ background-color: rgba(0,0,0,0.6) !important; color: #ffd700 !important; font-weight: 800 !important; }}
    tbody tr td {{ background-color: rgba(255,255,255,0.02) !important; color: white !important; }}
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
        df = conn.read(worksheet="Бригадний1", ttl=300, header=None).fillna("")
        data = df.values.tolist()
        units_cfg = {"1аемб":[0,1,2,3,4], "2аемб":[5,6,7,8,9], "3аемб":[10,11,12,13,14], "4аемб":[15,16,17,18,19], "ЗРДН":[20,21,22,23]}
        
        results = []
        for b_name, cols in units_cfg.items():
            last_dt = None
            for row in data[2:]: # Стрибаємо через заголовки 
                if len(row) <= max(cols): continue
                d_str = str(row[cols[0]]).strip()
                if d_str != "":
                    dt = pd.to_datetime(d_str, dayfirst=True, errors='coerce')
                    if pd.notnull(dt): last_dt = dt
                if not last_dt: continue

                target = str(row[cols[1]]).strip()
                # Фільтр технічних символів 
                if target not in ["", "-", "•", ".", "Ціль"]:
                    vp, vq = get_urazh_data(to_native(row[cols[2]]), target, str(row[cols[3]]))
                    results.append({"D": last_dt, "B": b_name, "T": target, "PU": vp, "PM": 0.0, "QT": to_native(row[cols[2]]), "QV": vq})
                
                if len(cols) == 5:
                    m_qty = to_native(row[cols[4]])
                    if m_qty > 0:
                        results.append({"D": last_dt, "B": b_name, "T": "Мінування", "PU": 0.0, "PM": m_qty, "QT": m_qty, "QV": m_qty})

        if results:
            all_dates = sorted(list(set([r["D"] for r in results])))
            x_labs = [d.strftime('%d.%m') for d in all_dates]
            st.metric("БРИГАДА (ВЕРИФІКОВАНО):", int(sum(r["PU"] + r["PM"] for r in results)))

            t1, t2 = st.tabs(["📈 Прогрес за місяць", "📊 Статистика за день"])
            
            def draw_sandwich(mode):
                fig = go.Figure()
                for b in units_cfg.keys():
                    yu, ym = [], []
                    acc_u, acc_m = 0.0, 0.0
                    for d in all_dates:
                        du = sum(r["PU"] for r in results if r["D"] == d and r["B"] == b)
                        dm = sum(r["PM"] for r in results if r["D"] == d and r["B"] == b)
                        if mode == "cum":
                            acc_u += du; acc_m += dm
                            yu.append(acc_u); ym.append(acc_m)
                        else:
                            yu.append(du); ym.append(dm)
                    
                    if (sum(yu) + sum(ym)) > 0:
                        lbls = [f"<b>{int(u+m)}</b><br>{b}" if (u+m) > 0 else "" for u, m in zip(yu, ym)]
                        # Ураження
                        fig.add_trace(go.Bar(x=x_labs, y=yu, name=f"{b} Ураж.", marker_color=CLRS[b], offsetgroup=b, showlegend=False))
                        # Мінування (шапка)
                        fig.add_trace(go.Bar(x=x_labs, y=ym, name=f"{b} Мін.", marker_color=MINE_CLR, offsetgroup=b, base=yu, showlegend=False, text=lbls, textposition='outside', cliponaxis=False, textfont=dict(color='white')))
                
                fig.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=550, xaxis=dict(type='category'), margin=dict(t=80))
                return fig

            with t1: st.plotly_chart(draw_sandwich("cum"), use_container_width=True)
            with t2: st.plotly_chart(draw_sandwich("day"), use_container_width=True)

            st.markdown("---")
            sel_b = st.selectbox("ДЕТАЛІЗАЦІЯ:", list(units_cfg.keys()))
            u_res = [r for r in results if r["B"] == sel_b]
            u_table = []
            for t in sorted(list(set([r["T"] for r in u_res]))):
                u_table.append({
                    "Тип цілі": t,
                    "Всього (шт)": int(sum(r["QT"] for r in u_res if r["T"] == t)),
                    "Верифіковано (шт)": int(sum(r["QV"] for r in u_res if r["T"] == t)),
                    "Бали": int(sum(r["PU"] + r["PM"] for r in u_res if r["T"] == t))
                })
            st.table(pd.DataFrame(u_table).sort_values(by="Бали", ascending=False))

    elif category == "🧨 Мінування":
        df = conn.read(worksheet="Мінування", ttl=300, header=None).fillna("")
        raw_m = df.values.tolist()[1:]; m_list = []
        for r in raw_m:
            dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
            if pd.notnull(dt):
                vq, uq = get_mine_data(to_native(r[2]), r[3])
                m_list.append({"D": dt, "Month": MONTHS_UKR.get(dt.month, "") + " " + str(dt.year), "V": vq, "U": uq})
        if m_list:
            opts = sorted(list(set([x["Month"] for x in m_list if x["Month"] != ""])), reverse=True)
            sel_m = st.selectbox("ПЕРІОД:", opts)
            m_d = [x for x in m_list if x["Month"] == sel_m]
            labs = [f"{d}.{str(m_d[0]['D'].month).zfill(2)}" for d in range(1, pd.Period(f"{m_d[0]['D'].year}-{m_d[0]['D'].month}").days_in_month + 1)]
            vv, uu = {l:0.0 for l in labs}, {l:0.0 for l in labs}
            for r in m_d:
                l = f"{r['D'].day}.{str(r['D'].month).zfill(2)}"
                if l in vv: vv[l] += r["V"]; uu[l] += r["U"]
            st.metric("ВЕРИФІКОВАНО ЗА МІСЯЦЬ:", int(sum(vv.values())))
            fig_m = go.Figure()
            fig_m.add_trace(go.Bar(x=labs, y=[vv[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            fig_m.add_trace(go.Bar(x=labs, y=[uu[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            fig_m.add_trace(go.Scatter(x=labs, y=[vv[l]+uu[l] for l in labs], mode='text', text=[str(int(vv[l])) if vv[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white')))
            fig_m.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(fig_m, use_container_width=True)

    elif category == "🔥 Ураження":
        ur_opts = ["04.2026", "03.2026", "02.2026", "01.2026"]
        sel_ur = st.selectbox("ОБЕРІТЬ ПЕРІОД:", ur_opts)
        df = conn.read(worksheet=f"Ураження {sel_ur}", ttl=300, header=None).fillna("")
        raw_u = df.values.tolist()[1:]; u_list, last_dt, obj_stats = [], None, {}
        for r in raw_u:
            if str(r[0]).strip() != "":
                dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                if pd.notnull(dt): last_dt = dt
            if last_dt and str(r[1]).strip() not in ["", "-", "•", ".", "Ціль"]:
                vp, vq = get_urazh_data(to_native(r[2]), r[1], r[3])
                total_pts = to_native(r[2]) * POINTS_MAP.get(str(r[1]).strip(), 0)
                u_list.append({"D": last_dt, "V": vp, "U": total_pts - vp})
                n = str(r[1]).strip()
                if n not in obj_stats: obj_stats[n] = [0,0,0]
                obj_stats[n][0] += to_native(r[2]); obj_stats[n][1] += vq; obj_stats[n][2] += vp
        if u_list:
            st.metric("ВЕРИФІКОВАНІ БАЛИ:", int(sum(x["V"] for x in u_list)))
            labs = [f"{d}.{str(u_list[0]['D'].month).zfill(2)}" for d in range(1, pd.Period(f"{u_list[0]['D'].year}-{u_list[0]['D'].month}").days_in_month + 1)]
            vv, uu = {l:0.0 for l in labs}, {l:0.0 for l in labs}
            for r in u_list:
                l = f"{r['D'].day}.{str(r['D'].month).zfill(2)}"
                if l in vv: vv[l] += r["V"]; uu[l] += r["U"]
            fig_u = go.Figure()
            fig_u.add_trace(go.Bar(x=labs, y=[vv[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            fig_u.add_trace(go.Bar(x=labs, y=[uu[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            fig_u.add_trace(go.Scatter(x=labs, y=[vv[l]+uu[l] for l in labs], mode='text', text=[str(int(vv[l])) if vv[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white')))
            fig_u.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(fig_u, use_container_width=True)
            st.table(pd.DataFrame([{"Тип цілі":k, "Всього":int(v[0]), "Верифіковано":int(v[1]), "Бали":int(v[2])} for k,v in sorted(obj_stats.items(), key=lambda x:x[1][2], reverse=True)]))

except Exception as e:
    st.error(f"ПОМИЛКА: {e}")
