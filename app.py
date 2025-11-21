import streamlit as st
import pandas as pd
import plotly.express as px
from financial_model import General, Construction, Financing, OperationExit, Amortization, Scheduler, CashflowEngine, Parking, CapexSummary

st.set_page_config(layout="wide", page_title="EstateOS", page_icon="🏢")

# Injection CSS
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        pass
local_css("assets/style.css")

# HERO
c1, c2 = st.columns([1, 6])
with c1: st.write("# 🏢")
with c2: 
    st.title("EstateOS")
    st.caption("Modélisation Immobilière & Financière")

# WIZARD
step1, step2, step3, step4 = st.tabs(["📍 1. Site & Urbanisme", "🏗️ 2. Construction", "🏘️ 3. Unités", "💰 4. Finance & Exit"])

with step1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown("### Données Site")
        i_city = st.text_input("Ville", "Dar es Salaam")
        i_land_area = st.number_input("Terrain (m²)", 7454)
    with c2:
        st.markdown("### Gabarit")
        u1, u2, u3 = st.columns(3)
        i_const_rate = u1.number_input("Emprise (%)", 60)
        i_far = u2.number_input("FAR", 3.45)
        i_efficiency = u3.number_input("Efficacité (%)", 80)
        st.info(f"GFA: {(i_land_area*i_const_rate/100*i_far):,.0f} m²")

with step2:
    st.markdown("### Stratégie Travaux")
    use_research = st.toggle("Coûts par Asset Class", True)
    if use_research:
        default_costs = pd.DataFrame([
            {"Asset Class": "residential", "Cost €/m²": 1190},
            {"Asset Class": "office", "Cost €/m²": 1093},
            {"Asset Class": "retail", "Cost €/m²": 1200},
            {"Asset Class": "logistics", "Cost €/m²": 800},
            {"Asset Class": "hotel", "Cost €/m²": 1500},
        ])
        df_asset_costs = st.data_editor(default_costs, num_rows="dynamic", use_container_width=True)
        i_struct = i_finish = 0
    else:
        c1, c2 = st.columns(2)
        i_struct = c1.number_input("Structure (€/m²)", 800)
        i_finish = c2.number_input("Finitions (€/m²)", 400)
        df_asset_costs = pd.DataFrame()
    
    st.markdown("### Soft Costs & Planning")
    c1, c2, c3 = st.columns(3)
    i_arch = c1.number_input("Archi (%)", 3.0)
    i_contingency = c2.number_input("Contingence (%)", 5.0)
    i_permits = c3.number_input("Permis (€)", 20000)
    
    st.caption("S-Curve")
    s1 = st.slider("Année 1 (%)", 0, 100, 40)
    s2 = st.slider("Année 2 (%)", 0, 100, 40)
    s3 = 100 - s1 - s2
    
    st.write("**Amenities**")
    df_amenities = st.data_editor(pd.DataFrame([{"Nom": "Padel", "Surface": 300, "Coût": 400, "Actif": True}]), num_rows="dynamic")
    am_capex = (df_amenities[df_amenities["Actif"]]["Surface"] * df_amenities[df_amenities["Actif"]]["Coût"]).sum()

with step3:
    st.markdown("### Inventaire")
    i_parking_cost = st.number_input("Coût Parking (€)", 18754)
    
    # PRE-FILL 37 UNITS EXACTLY MATCHING EXCEL COLUMNS
    units_data = []
    for t in ["OF-L", "OF-M", "OF-S"]:
        surf = 3000 if t != "OF-S" else 2640
        units_data.append({"Code": t, "AssetClass": "office", "Surface (GLA m²)": surf, "Rent (€/m²/mo)": 20, "Price €/m²": 0, "Start Year": 3, "Sale Year": "Exit", "Mode": "Rent", "Parking per unit": 0, "Parking ratio (per 100 m²)": 2.5, "Occ %": 90, "Rent growth %": 5, "Asset Value Growth (%/yr)": 4.5})
    for _ in range(4): units_data.append({"Code": "T2-VP", "AssetClass": "residential", "Surface (GLA m²)": 70, "Rent (€/m²/mo)": 16, "Price €/m²": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio (per 100 m²)": 0, "Occ %": 95, "Rent growth %": 4, "Asset Value Growth (%/yr)": 4})
    for _ in range(6): units_data.append({"Code": "T2-VEFA", "AssetClass": "residential", "Surface (GLA m²)": 70, "Rent (€/m²/mo)": 16, "Price €/m²": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio (per 100 m²)": 0, "Occ %": 95, "Rent growth %": 4, "Asset Value Growth (%/yr)": 4})
    for _ in range(4): units_data.append({"Code": "T3-VP", "AssetClass": "residential", "Surface (GLA m²)": 110, "Rent (€/m²/mo)": 16, "Price €/m²": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 2, "Parking ratio (per 100 m²)": 0, "Occ %": 95, "Rent growth %": 4, "Asset Value Growth (%/yr)": 4})
    for _ in range(8): units_data.append({"Code": "T3-VEFA", "AssetClass": "residential", "Surface (GLA m²)": 110, "Rent (€/m²/mo)": 16, "Price €/m²": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 2, "Parking ratio (per 100 m²)": 0, "Occ %": 95, "Rent growth %": 4, "Asset Value Growth (%/yr)": 4})
    for _ in range(6): units_data.append({"Code": "T4-VP", "AssetClass": "residential", "Surface (GLA m²)": 150, "Rent (€/m²/mo)": 16, "Price €/m²": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 2, "Parking ratio (per 100 m²)": 0, "Occ %": 95, "Rent growth %": 4, "Asset Value Growth (%/yr)": 4})
    for _ in range(6): units_data.append({"Code": "T4-VEFA", "AssetClass": "residential", "Surface (GLA m²)": 150, "Rent (€/m²/mo)": 16, "Price €/m²": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 2, "Parking ratio (per 100 m²)": 0, "Occ %": 95, "Rent growth %": 4, "Asset Value Growth (%/yr)": 4})

    df_units = st.data_editor(pd.DataFrame(units_data), num_rows="dynamic", use_container_width=True, height=400)

with step4:
    t1, t2, t3 = st.tabs(["🏦 Dette", "⚙️ Opérations", "🚀 Exit"])
    with t1:
        c1, c2 = st.columns(2)
        i_debt = c1.number_input("Dette (€)", 14504579)
        i_rate = c2.number_input("Taux (%)", 4.5)
        i_term = c1.number_input("Durée", 20)
        i_grace = c2.number_input("Franchise", 24) / 12
        i_arr_fee = c1.number_input("Arrangement (%)", 1.0)
        i_upfront = c2.number_input("Frais Fixes", 150000)
        i_prepay = c1.number_input("Pénalité", 2.0)
    with t2:
        c1, c2 = st.columns(2)
        i_occ = c1.number_input("Occ. Défaut (%)", 90)
        i_rent_g = c2.number_input("Croissance Loyer (%)", 2.5)
        i_inf = c1.number_input("Inflation (%)", 4.0)
        i_opex = c2.number_input("OPEX (€/m²)", 28.0)
        i_pm = c1.number_input("Gestion (%)", 4.5)
    with t3:
        c1, c2 = st.columns(2)
        i_hold = c1.number_input("Sortie (Année)", 20)
        i_exit_y = c2.number_input("Yield (%)", 8.25)
        i_sell_fees = c1.number_input("Frais Vente (%)", 5.0)
        i_tax = c2.number_input("IS (%)", 30.0)
        i_tax_h = c1.number_input("Exonération", 3)

st.write("---")
if st.button("✨ CALCULER", type="primary", use_container_width=True):
    try:
        # MAPPING
        gen = General({'land_area': i_land_area, 'parcels': 3, 'construction_rate': i_const_rate, 'far': i_far, 'building_efficiency': i_efficiency, 'country': "Tanzanie", 'city': i_city, 'fx_eur_local': 2853.1, 'corporate_tax_rate': i_tax, 'tax_holiday': i_tax_h, 'discount_rate': 10.0})
        park = Parking({'cost_per_space': i_parking_cost}, df_units)
        const = Construction({'structure_cost': i_struct if not use_research else 0, 'finishing_cost': i_finish if not use_research else 0, 'utilities_cost': 200, 'permit_fees': i_permits, 'architect_fees_pct': i_arch, 'development_fees_pct': 2.0, 'marketing_fees_pct': 1.0, 'contingency_pct': i_contingency, 's_curve_y1': s1/100, 's_curve_y2': s2/100, 's_curve_y3': s3/100, 'use_research_cost': use_research, 'df_asset_costs': df_asset_costs, 'amenities_total_capex': am_capex, 'parking_capex': park.total_capex}, gen, df_units)
        fin = Financing({'debt_amount': i_debt, 'interest_rate': i_rate, 'loan_term': i_term, 'grace_period': i_grace, 'arrangement_fee_pct': i_arr_fee, 'upfront_fees': i_upfront, 'prepayment_fee_pct': i_prepay})
        op = OperationExit({'rent_growth': i_rent_g, 'exit_yield': i_exit_y, 'holding_period': i_hold, 'inflation': i_inf, 'opex_per_m2': i_opex, 'pm_fee_pct': i_pm, 'occupancy_rate': i_occ, 'transac_fees_exit': i_sell_fees})
        
        capex_sum = CapexSummary(const, fin)
        amort = Amortization(fin, op)
        sched = Scheduler(df_units, op, gen, fin)
        cf = CashflowEngine(gen, const, fin, capex_sum, op, amort, sched)

        # RESULTS
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("IRR", f"{cf.kpis['Levered IRR']:.2f}%")
        k2.metric("Equity Mult.", f"{cf.kpis['Equity Multiple']:.2f}x")
        k3.metric("Peak Equity", f"€{cf.kpis['Peak Equity']:,.0f}")
        k4.metric("Profit", f"€{cf.kpis['NPV']:,.0f}")

        st.bar_chart(cf.df[['NOI', 'Debt Service', 'Net Cash Flow']])
        st.dataframe(cf.df.style.format("{:,.0f}"), use_container_width=True)
    
    except Exception as e:
        st.error(f"Erreur: {e}")
