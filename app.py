import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.graph_objects as go
import base64
import re

# --- 1. НАЛАШТУВАННЯ СТОРІНКИ ---
st.set_page_config(page_title="СИТУАЦІЙНИЙ ЦЕНТР 1 аемб", layout="wide", page_icon="🛡️")

# АКТУАЛЬНИЙ СЛОВНИК БАЛІВ (ОСТАННЯ ВЕРСІЯ)
POINTS_MAP = {
    "О/С 200": 12, "О/С 300": 8, "Молнія": 10, "Укриття": 1, "Фортифікація": 1,
    "Антена": 4, "ФПВ": 6, "Танк": 40, "Бомбер": 6, "РЛС": 50, "САУ": 30,
    "Міномет": 5, "ЛАТ": 8, "Генератор": 4, "Електросамокат": 4, "Квадроцикл": 4,
    "Мотоцикл": 4, "РЕБ": 8, "Мавік": 6, "Орлан": 40, "Шахед": 20, "Ждун": 10,
    "Автомобіль": 5, "Гаубиця": 40, "ББМ": 20, "Гармата": 20
}

USER_PASSWORD = "2887" 
MONTHS_UKR = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень", 5: "Травень", 6: "Червень",
    7: "Липень", 8: "Серпень", 9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень"
}

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return None

def to_native(val):
    try: return float(str(val).replace(',', '.'))
    except: return 0.0

def calculate_verif_data(qty, target, status):
    """Повертає (Верифіковані бали, Верифікована кількість штук)"""
    t_clean = str(target).strip()
    unit_p = POINTS_MAP.get(t_clean, 0)
    st_clean = str(status).lower().strip()
    if "не верифіковано" in st_clean:
        match = re.search(r'(\d+)', st_clean)
        unv_q = float(match.group(1)) if match else qty
        v_q = max(0.0, qty - unv_q)
    else: v_q = qty
    return v_q * unit_p, v_q

# --- 2. ЕКРАН ВХОДУ ---
if "password_correct" not in st.session_state:
    logo = get_base64_image("logo.png")
    st.markdown("<style>.stApp { background-color: #0E1117; }</style>", unsafe_allow_html=True)
    col_l, col_c, col_r = st.columns([1.2, 1.5, 1.2])
    with col_c:
        if logo: st.markdown(f"<div style='text-align:center;'><img src='data:image/png;base64,{logo}' style='max-width:200px; border-radius:15px;'></div>", unsafe_allow_html=True)
        st.markdown("<div style='background:rgba(255,255,255,0.04); padding:30px; border-radius:20px; border: 1px solid rgba(255,255,255,0.15); text-align:center;'><h2 style='color:white; margin:0;'>1 аемб</h2><p style='color:#ffd700; font-weight:600;'>77 ОАЕМБр • ДШВ ЗСУ 🇺🇦</p></div>", unsafe_allow_html=True)
        pwd = st.text_input("КОД ДОСТУПУ:", type="password")
        if st.button("УВІЙТИ") and pwd == USER_PASSWORD:
            st.session_state["password_correct"] = True
            st.rerun()
    st.stop()

# --- 3. ДИЗАЙН ---
bg = get_base64_image("background.jpg")
bg_style = f'background-image: url("data:image/png;base64,{bg}");' if bg else 'background-color: #0E1117;'
st.markdown(f"""
    <style>
    .stApp {{ {bg_style} background-size: cover; background-position: center; background-attachment: fixed; }}
    [data-testid="stTable"], .stDataFrame {{ background-color: transparent !important; }}
    table {{ background-color: rgba(255,255,255,0.05) !important; color: white !important; border-radius: 10px; width: 100%; }}
    thead tr th {{ background-color: rgba(0,0,0,0.4) !important; color: #ffd700 !important; }}
    [data-testid="stSidebar"] {{ background-color: rgba(14, 17, 23, 0.95); }}
    [data-testid="stMetricValue"] {{ color: #ffd700 !important; font-size: 34px !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 4. НАВІГАЦІЯ ---
conn = st.connection("gsheets", type=GSheetsConnection)
category = st.sidebar.radio("Напрямок:", ["⚔️ Бригадні звіти", "🧨 Мінування", "🔥 Ураження"])
if st.sidebar.button('🔄 ОНОВИТИ ДАНІ'):
    st.cache_data.clear()
    st.rerun()

# --- 5. ЛОГІКА ВІДОБРАЖЕННЯ ---
try:
    # --- БРИГАДНІ ЗВІТИ ---
    if category == "⚔️ Бригадні звіти":
        df = conn.read(worksheet="Бригадний1", ttl=300, header=None).fillna("")
        st.markdown("<h3 style='text-align:center; color:white;'>⚔️ ЗАГАЛЬНОБРИГАДНИЙ ЗВІТ</h3>", unsafe_allow_html=True)
        data = df.values.tolist()
        # СТРУКТУРА: 5 колонок для аемб, 4 для ЗРДН
        units = {"1аемб":[0,1,2,3,4], "2аемб":[5,6,7,8,9], "3аемб":[10,11,12,13,14], "4аемб":[15,16,17,18,19], "ЗРДН":[20,21,22,23]}
        clrs = {'1аемб':'#92D050', '2аемб':'#A5A5A5', '3аемб':'#4472C4', '4аемб':'#ED7D31', 'ЗРДН':'#FFC000'}
        mine_clr = "#7030A0" 
        
        res = []
        for b_name, cols in units.items():
            last_dt = None
            for row in data[1:]:
                if len(row) <= max(cols): continue
                if str(row[cols[0]]).strip() != "":
                    dt = pd.to_datetime(str(row[cols[0]]), dayfirst=True, errors='coerce')
                    if pd.notnull(dt): last_dt = dt
                if not last_dt: continue
                
                target = str(row[cols[1]]).strip()
                if target != "" and target != "Ціль":
                    v_p, v_q = calculate_verif_data(to_native(row[cols[2]]), target, str(row[cols[3]]))
                    res.append({"D": last_dt, "B": b_name, "T": target, "P_U": v_p, "P_M": 0.0, "QT": to_native(row[cols[2]]), "QV": v_q})
                
                if len(cols) == 5:
                    m_qty = to_native(row[cols[4]])
                    if m_qty > 0:
                        res.append({"D": last_dt, "B": b_name, "T": "Мінування", "P_U": 0.0, "P_M": m_qty, "QT": m_qty, "QV": m_qty})

        if res:
            all_d = sorted(list(set([r["D"] for r in res])))
            x_labs = [d.strftime('%d.%m') for d in all_d]
            st.metric("УРАЖЕННЯ + МІНУВАННЯ (БРИГАДА):", int(sum(r["P_U"] + r["P_M"] for r in res)))
            
            t1, t2 = st.tabs(["📈 Прогрес за місяць", "📊 Статистика по днях"])
            
            def draw_brigade(mode):
                fig = go.Figure()
                for b in units.keys():
                    yu, ym = [], []
                    au, am = 0.0, 0.0
                    for d in all_d:
                        du = sum(r["P_U"] for r in res if r["D"] == d and r["B"] == b)
                        dm = sum(r["P_M"] for r in res if r["D"] == d and r["B"] == b)
                        if mode == "cum": au += du; am += dm; yu.append(au); ym.append(am)
                        else: yu.append(du); ym.append(dm)
                    if (sum(yu) + sum(ym)) > 0:
                        txt = [f"<b>{int(u+m)}</b><br>{b}" if (u+m) > 0 else "" for u, m in zip(yu, ym)]
                        fig.add_trace(go.Bar(x=x_labs, y=yu, marker_color=clrs[b], offsetgroup=b, showlegend=False))
                        fig.add_trace(go.Bar(x=x_labs, y=ym, marker_color=mine_clr, offsetgroup=b, base=yu, showlegend=False, text=txt, textposition='outside', textfont=dict(color='white', size=11)))
                fig.update_layout(barmode='group', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", height=550, xaxis=dict(type='category'), margin=dict(t=80))
                return fig

            with t1: st.plotly_chart(draw_brigade("cum"), use_container_width=True)
            with t2: st.plotly_chart(draw_brigade("day"), use_container_width=True)
            
            st.markdown("---")
            sel = st.selectbox("Деталізація підрозділу:", list(units.keys()))
            u_res = [r for r in res if r["B"] == sel]
            u_sum = []
            for t in sorted(list(set([r["T"] for r in u_res]))):
                u_sum.append({"Тип цілі": t, "Всього (шт)": int(sum(r["QT"] for r in u_res if r["T"] == t)), "Верифіковано (шт)": int(sum(r["QV"] for r in u_res if r["T"] == t)), "Бали": int(sum(r["P_U"]+r["P_M"] for r in u_res if r["T"] == t))})
            st.table(pd.DataFrame(u_sum).sort_values(by="Бали", ascending=False))

    # --- МІНУВАННЯ ---
    elif category == "🧨 Мінування":
        df = conn.read(worksheet="Мінування", ttl=300, header=None).fillna("")
        raw = df.values.tolist()[1:]; clean = []
        for r in raw:
            dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
            if pd.notnull(dt):
                q = to_native(r[2]); st_cl = str(r[3]).lower()
                v_q = q - (float(re.search(r'(\d+)', st_cl).group(1)) if "не верифіковано" in st_cl and re.search(r'(\d+)', st_cl) else (q if "не верифіковано" in st_cl else 0))
                clean.append({"D": dt, "M": MONTHS_UKR.get(dt.month) + " " + str(dt.year), "V": v_q, "U": q-v_q})
        if clean:
            opts = sorted(list(set([r["M"] for r in clean])), reverse=True)
            sel_m = st.selectbox("Оберіть місяць:", opts)
            m_d = [r for r in clean if r["M"] == sel_m]
            labs = [f"{d}.{str(m_d[0]['D'].month).zfill(2)}" for d in range(1, pd.Period(f"{m_d[0]['D'].year}-{m_d[0]['D'].month}").days_in_month + 1)]
            vv, uu = {l:0.0 for l in labs}, {l:0.0 for l in labs}
            for r in m_d:
                l = f"{r['D'].day}.{str(r['D'].month).zfill(2)}"
                if l in vv: vv[l] += r["V"]; uu[l] += r["U"]
            st.metric("ВЕРИФІКОВАНО МІН ЗА МІСЯЦЬ:", int(sum(vv.values())))
            f_m = go.Figure()
            f_m.add_trace(go.Bar(x=labs, y=[vv[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            f_m.add_trace(go.Bar(x=labs, y=[uu[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            f_m.add_trace(go.Scatter(x=labs, y=[vv[l]+uu[l] for l in labs], mode='text', text=[str(int(vv[l])) if vv[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white')))
            f_m.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(f_m, use_container_width=True)

    # --- УРАЖЕННЯ ---
    elif category == "🔥 Ураження":
        ur_months = ["04.2026", "03.2026", "02.2026", "01.2026", "12.2025", "11.2025"]
        sel_ur = st.selectbox("Період уражень:", ur_months)
        df = conn.read(worksheet=f"Ураження {sel_ur}", ttl=300, header=None).fillna("")
        raw = df.values.tolist()[1:]; clean, last_dt = [], None
        for r in raw:
            if str(r[0]).strip() != "":
                dt = pd.to_datetime(str(r[0]), dayfirst=True, errors='coerce')
                if pd.notnull(dt): last_dt = dt
            if last_dt and str(r[1]).strip() != "":
                vp, vq = calculate_verif_data(to_native(r[2]), r[1], r[3])
                clean.append({"D": last_dt, "V": vp, "U": (to_native(r[2])*POINTS_MAP.get(str(r[1]).strip(), 0))-vp, "T": str(r[1]).strip(), "QT": to_native(r[2]), "QV": vq})
        if clean:
            st.metric("БАЛИ БАТАЛЬЙОНУ (ВЕРИФІКОВАНО):", int(sum(r["V"] for r in clean)))
            labs = [f"{d}.{str(clean[0]['D'].month).zfill(2)}" for d in range(1, pd.Period(f"{clean[0]['D'].year}-{clean[0]['D'].month}").days_in_month + 1)]
            vv, uu, obs = {l:0.0 for l in labs}, {l:0.0 for l in labs}, {}
            for r in clean:
                l = f"{r['D'].day}.{str(r['D'].month).zfill(2)}"
                if l in vv: vv[l] += r["V"]; uu[l] += r["U"]
                n = r["T"]
                if n not in obs: obs[n] = [0,0,0]
                obs[n][0]+=r["QT"]; obs[n][1]+=r["QV"]; obs[n][2]+=r["V"]
            f_u = go.Figure()
            f_u.add_trace(go.Bar(x=labs, y=[vv[l] for l in labs], name='Верифіковано', marker_color='#444444'))
            f_u.add_trace(go.Bar(x=labs, y=[uu[l] for l in labs], name='Не верифіковано', marker_color='#CC0000'))
            f_u.add_trace(go.Scatter(x=labs, y=[vv[l]+uu[l] for l in labs], mode='text', text=[str(int(vv[l])) if vv[l]>0 else "" for l in labs], textposition='top center', showlegend=False, textfont=dict(color='white')))
            f_u.update_layout(barmode='stack', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", xaxis=dict(type='category', tickangle=-45))
            st.plotly_chart(f_u, use_container_width=True)
            st.table(pd.DataFrame([{"Тип цілі":k, "Всього (шт)":int(v[0]), "Верифіковано (шт)":int(v[1]), "Бали":int(v[2])} for k, v in sorted(obs.items(), key=lambda x:x[1][2], reverse=True)]))

except Exception as e:
    st.error(f"Помилка системи: {e}")
