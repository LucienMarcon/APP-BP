import streamlit as st
import pandas as pd
import plotly.express as px
from financial_model import General, Construction, Financing, OperationExit, Amortization, Scheduler, CashflowEngine, Parking, CapexSummary

st.set_page_config(layout="wide", page_title="ImmoGenius", page_icon="🏢")

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    html, body, [class*="css"] {font-family: 'Inter', sans-serif;}
    .stApp {background-color: #F8F9FA;}
    .stMetric {background: white; padding: 15px; border-radius: 12px; border-left: 5px solid #3B82F6; box-shadow: 0 2px 5px rgba(0,0,0,0.05);}
    .stTabs [data-baseweb="tab-list"] {gap: 10px;}
    .stTabs [data-baseweb="tab"] {background-color: white; border-radius: 8px; padding: 10px 20px; border: 1px solid #E2E8F0;}
    .stTabs [aria-selected="true"] {background-color: #EFF6FF; border-color: #3B82F6; color: #3B82F6;}
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
c_logo, c_titre = st.columns([1, 6])
with c_logo: st.write("# 🏢")
with c_titre:
    st.title("ImmoGenius 3.0")
    st.caption("Plateforme de Modélisation Immobilière Intelligente")

# --- WIZARD ---
step1, step2, step3, step4 = st.tabs(["📍 1. Terrain", "🏗️ 2. Construction", "🏘️ 3. Unités", "💰 4. Finance & KPI"])

# 1. TERRAIN
with step1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("### Site")
        i_city = st.text_input("Ville", "Dar es Salaam")
        i_land_area = st.number_input("Surface Terrain (m²)", 7454, step=100)
    with c2:
        st.markdown("### Urbanisme")
        uc1, uc2, uc3 = st.columns(3)
        i_const_rate = uc1.number_input("Emprise (%)", 60)
        i_far = uc2.number_input("FAR", 3.45)
        i_efficiency = uc3.number_input("Efficacité (%)", 80)
        calc_gfa = i_land_area * i_const_rate/100 * i_far
        calc_gla = calc_gfa * i_efficiency/100
        st.success(f"🏗️ GFA: **{calc_gfa:,.0f} m²** | 🔑 GLA: **{calc_gla:,.0f} m²**")

# 2. CONSTRUCTION
with step2:
    st.markdown("### Coûts & Planning")
    use_research = st.toggle("Coûts par Asset Class", True)
    
    if use_research:
        default_asset_costs = pd.DataFrame([
            {"Asset Class": "residential", "Cost €/m²": 1190},
            {"Asset Class": "office", "Cost €/m²": 1093},
            {"Asset Class": "retail", "Cost €/m²": 1200},
            {"Asset Class": "logistics", "Cost €/m²": 800},
            {"Asset Class": "hotel", "Cost €/m²": 1500},
        ])
        df_asset_costs = st.data_editor(default_asset_costs, num_rows="dynamic", use_container_width=True, hide_index=True)
        i_struct = i_finish = 0
    else:
        c1, c2 = st.columns(2)
        i_struct = c1.number_input("Structure (€/m²)", 800)
        i_finish = c2.number_input("Finitions (€/m²)", 400)
        df_asset_costs = pd.DataFrame()

    with st.expander("Honoraires & Amenities"):
        c1, c2, c3 = st.columns(3)
        i_permits = c1.number_input("Permis (€)", 20000)
        i_arch = c2.number_input("Archi (%)", 3.0)
        i_contingency = c3.number_input("Contingence (%)", 5.0)
        st.write("Amenities")
        default_amenities = pd.DataFrame([{"Nom": "Padel", "Surface": 300, "Coût": 400, "Actif": True}])
        edited_amenities = st.data_editor(default_amenities, num_rows="dynamic", hide_index=True)
        am_capex = (edited_amenities[edited_amenities["Actif"]]["Surface"] * edited_amenities[edited_amenities["Actif"]]["Coût"]).sum()

    st.caption("S-Curve")
    i_s1 = st.slider("Y1 (%)", 0, 100, 40)
    i_s2 = st.slider("Y2 (%)", 0, 100, 40)
    i_s3 = 100 - i_s1 - i_s2

# 3. UNITS
with step3:
    st.markdown("### Mix Unités")
    col_top_u, col_top_p = st.columns([3, 1])
    with col_top_p:
        i_parking_cost = st.number_input("Coût Parking (€)", 18754)
    
    units_data = []
    for t in ["OF-L", "OF-M", "OF-S"]:
        surf = 3000 if t != "OF-S" else 2640
        units_data.append({"Code": t, "Asset Class": "office", "Surface (m²)": surf, "Rent (€/m²/mo)": 20, "Price (€/m²)": 0, "Start Year": 3, "Sale Year": "Exit", "Mode": "Rent", "Parking per unit": 0, "Parking ratio": 2.5, "Occupancy %": 90, "Rent Growth %": 5, "Appreciation %": 4.5})
    for _ in range(4): units_data.append({"Code": "T2-VP", "Asset Class": "residential", "Surface (m²)": 70, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
    for _ in range(6): units_data.append({"Code": "T2-VEFA", "Asset Class": "residential", "Surface (m²)": 70, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
    for _ in range(4): units_data.append({"Code": "T3-VP", "Asset Class": "residential", "Surface (m²)": 110, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
    for _ in range(8): units_data.append({"Code": "T3-VEFA", "Asset Class": "residential", "Surface (m²)": 110, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
    for _ in range(6): units_data.append({"Code": "T4-VP", "Asset Class": "residential", "Surface (m²)": 150, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
    for _ in range(6): units_data.append({"Code": "T4-VEFA", "Asset Class": "residential", "Surface (m²)": 150, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})

    df_default_units = pd.DataFrame(units_data)
    col_conf = {
        "Asset Class": st.column_config.SelectboxColumn(options=["office", "residential", "retail", "logistics", "hotel"]),
        "Mode": st.column_config.SelectboxColumn(options=["Rent", "Sale", "Mixed"]),
        "Price (€/m²)": st.column_config.NumberColumn(format="%d €"),
        "Rent (€/m²/mo)": st.column_config.NumberColumn(format="%.2f €"),
    }
    df_units = st.data_editor(df_default_units, column_config=col_conf, num_rows="dynamic", use_container_width=True, height=300, hide_index=True)

# 4. FINANCE & CAPEX SUMMARY
with step4:
    st.markdown("### Hypothèses Financières")
    t_fin, t_op, t_exit = st.tabs(["🏦 Dette & CAPEX", "⚙️ Opérations", "🚀 Exit"])
    
    with t_fin:
        c1, c2 = st.columns(2)
        with c1:
            i_debt = st.number_input("Dette (€)", 14504579)
            i_rate = st.number_input("Taux (%)", 4.5)
            i_term = st.number_input("Durée (ans)", 20)
        with c2:
            i_grace = st.number_input("Franchise (mois)", 24) / 12
            i_arr_fee_pct = st.number_input("Arrangement Fee (%)", 1.0)
            i_upfront_flat = st.number_input("Frais Fixes (€)", 150000)
            i_prepay_fee = st.number_input("Pénalité (%)", 2.0)

    with t_op:
        c1, c2 = st.columns(2)
        i_occupancy_def = c1.number_input("Occ. Défaut (%)", 90)
        i_rent_growth_def = c2.number_input("Croissance Loyer (%)", 2.5)
        i_inflation = c1.number_input("Inflation (%)", 4.0)
        i_opex_m2 = c2.number_input("OPEX (€/m²)", 28.0)
        i_pm_fee = st.number_input("Gestion (%)", 4.5)

    with t_exit:
        c1, c2 = st.columns(2)
        i_hold_period = c1.number_input("Année Sortie", 20)
        i_exit_yield = c2.number_input("Yield (%)", 8.25)
        i_transac_fees = c1.number_input("Frais Vente (%)", 5.0)
        i_tax_rate = c2.number_input("IS (%)", 30.0)
        i_tax_holiday = c1.number_input("Exonération (ans)", 3)

st.write("")
if st.button("✨ LANCER LA SIMULATION", type="primary", use_container_width=True):
    # MAPPINGS
    inp_gen = {'land_area': i_land_area, 'parcels': 3, 'construction_rate': 60, 'far': i_far, 'building_efficiency': i_efficiency, 'country': "Tanzanie", 'city': i_city, 'fx_eur_local': 2853.1, 'corporate_tax_rate': i_tax_rate, 'tax_holiday': i_tax_holiday, 'discount_rate': 10.0}
    inp_park = {'cost_per_space': i_parking_cost}
    park = Parking(inp_park, df_units)
    inp_const = {'structure_cost': i_struct if not use_research else 0, 'finishing_cost': i_finish if not use_research else 0, 'utilities_cost': 200, 'permit_fees': i_permits, 'architect_fees_pct': i_arch, 'development_fees_pct': 2.0, 'marketing_fees_pct': 1.0, 'contingency_pct': i_contingency, 's_curve_y1': i_s1/100, 's_curve_y2': i_s2/100, 's_curve_y3': i_s3/100, 'use_research_cost': use_research, 'df_asset_costs': df_asset_costs, 'amenities_total_capex': am_capex, 'parking_capex': park.total_capex}
    inp_fin = {'debt_amount': i_debt, 'interest_rate': i_rate, 'loan_term': i_term, 'grace_period': i_grace, 'arrangement_fee_pct': i_arr_fee_pct, 'upfront_fees': i_upfront_flat, 'prepayment_fee_pct': i_prepay_fee}
    inp_op = {'rent_growth': i_rent_growth_def, 'exit_yield': i_exit_yield, 'holding_period': i_hold_period, 'inflation': i_inflation, 'opex_per_m2': i_opex_m2, 'pm_fee_pct': i_pm_fee, 'occupancy_rate': i_occupancy_def, 'transac_fees_exit': i_transac_fees}

    try:
        gen = General(inp_gen)
        const = Construction(inp_const, gen, df_units)
        fin = Financing(inp_fin) 
        capex_sum = CapexSummary(const, fin)
        amort = Amortization(fin, OperationExit(inp_op)) # Pass operation for exit year
        op = OperationExit(inp_op)
        sched = Scheduler(df_units, op, gen, fin)
        cf = CashflowEngine(gen, const, fin, capex_sum, op, amort, sched)

        # --- VISUALISATION ---
        st.markdown("---")
        st.markdown("### 📊 CAPEX SUMMARY (Feuille Excel Répliquée)")
        
        df_capex = pd.DataFrame([
            {"Component": "Construction pre-financing", "Amount (€)": capex_sum.construction_pre_financing},
            {"Component": "Upfront financing fees", "Amount (€)": capex_sum.upfront_financing_fees},
            {"Component": "TOTAL CAPEX", "Amount (€)": capex_sum.total_capex}
        ])
        st.dataframe(df_capex.style.format({"Amount (€)": "{:,.0f}"}), use_container_width=True)

        st.markdown("### 🎯 KPIs & Cashflow")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("IRR (Levered)", f"{cf.kpis['Levered IRR']:.2f}%")
        k2.metric("Equity Multiple", f"{cf.kpis['Equity Multiple']:.2f}x")
        k3.metric("Peak Equity", f"€{cf.kpis['Peak Equity']:,.0f}")
        k4.metric("Profit (NPV)", f"€{cf.kpis['NPV']:,.0f}")

        t1, t2, t3, t4 = st.tabs(["Graphique", "Rent Schedule", "Sale Schedule", "Détails"])
        with t1: st.bar_chart(cf.df[['NOI', 'Debt Service', 'Net Cash Flow']], color=["#22c55e", "#ef4444", "#3b82f6"])
        with t2: st.dataframe(pd.DataFrame(sched.rent_schedule_by_asset).style.format("{:,.0f}"), use_container_width=True)
        with t3: st.dataframe(pd.DataFrame(sched.sale_schedule_by_asset).style.format("{:,.0f}"), use_container_width=True)
        with t4: st.dataframe(cf.df.style.format("{:,.0f}"), use_container_width=True)

    except Exception as e:
        st.error(f"Erreur: {e}")
