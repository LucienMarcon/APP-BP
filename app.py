import streamlit as st
import pandas as pd
import plotly.express as px
from financial_model import General, Construction, Financing, OperationExit, Amortization, Scheduler, CashflowEngine, Parking, CapexSummary

st.set_page_config(layout="wide", page_title="EstateOS", page_icon="🏢", initial_sidebar_state="collapsed")

# --- CSS INJECTION (Style Titanium) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
    .stApp {background-color: #F8FAFC; font-family: 'Inter', sans-serif;}
    header[data-testid="stHeader"] {display: none;}
    
    /* KPI CARDS */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); border-left: 4px solid #2563EB;
    }
    div[data-testid="metric-container"] label {color: #64748B; font-size: 0.8rem; font-weight: 600;}
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {font-family: 'JetBrains Mono'; color: #0F172A; font-size: 1.6rem;}
    
    /* TABS */
    .stTabs [data-baseweb="tab-list"] {background-color: white; padding: 5px; border-radius: 10px; gap: 5px;}
    .stTabs [data-baseweb="tab"] {border-radius: 8px; border: 1px solid #E2E8F0; color: #64748B;}
    .stTabs [aria-selected="true"] {background-color: #EFF6FF; border-color: #2563EB; color: #2563EB;}
    
    /* BUTTON */
    .stButton button {background-color: #0F172A; color: white; border-radius: 8px; padding: 0.8rem; font-weight: 600;}
    </style>
""", unsafe_allow_html=True)

# --- HERO HEADER ---
c1, c2 = st.columns([0.5, 10])
with c1: st.markdown("# 🏢")
with c2: st.markdown("## EstateOS\n<span style='color:grey'>Modélisation Financière Avancée</span>", unsafe_allow_html=True)

st.divider()

# --- WORKSPACE (Split View) ---
col_build, col_viz = st.columns([4, 5], gap="large")

with col_build:
    st.markdown("### 🛠️ Configuration")
    tab_site, tab_build, tab_units, tab_fin = st.tabs(["📍 Site", "🏗️ Travaux", "🏘️ Unités", "💰 Finance"])

    # 1. SITE
    with tab_site:
        c1, c2 = st.columns(2)
        i_city = c1.text_input("Ville", "Dar es Salaam")
        i_land_area = c2.number_input("Terrain (m²)", 7454, step=100)
        st.markdown("**Urbanisme**")
        u1, u2, u3 = st.columns(3)
        i_const_rate = u1.number_input("Emprise %", 60)
        i_far = u2.number_input("FAR", 3.45)
        i_eff = u3.number_input("Efficacité %", 80)
        gfa = i_land_area * i_const_rate/100 * i_far
        gla = gfa * i_eff/100
        st.info(f"🏗️ GFA: **{gfa:,.0f} m²** | 🔑 GLA: **{gla:,.0f} m²**")

    # 2. CONSTRUCTION
    with tab_build:
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
            i_struct = c1.number_input("Structure", 800)
            i_finish = c2.number_input("Finitions", 400)
            df_asset_costs = pd.DataFrame()
        
        with st.expander("Honoraires & Planning"):
            c1, c2 = st.columns(2)
            i_permits = c1.number_input("Permis €", 20000)
            i_arch = c2.number_input("Archi %", 3.0)
            i_contingency = c1.number_input("Contingence %", 5.0)
            i_amenities = c2.number_input("Amenities €", 120000)
            st.caption("S-Curve (Y1 / Y2)")
            s1 = st.slider("Y1 %", 0, 100, 40)
            s2 = st.slider("Y2 %", 0, 100, 40)
            s3 = 100 - s1 - s2

    # 3. UNITS (EXACT COLUMNS)
    with tab_units:
        i_parking_cost = st.number_input("Coût Parking (€/pl)", 18754)
        
        units_data = []
        for t in ["OF-L", "OF-M", "OF-S"]:
            surf = 3000 if t != "OF-S" else 2640
            units_data.append({"Code": t, "AssetClass": "office", "Surface (GLA m²)": surf, "Rent (€/m²/mo)": 20, "Price €/m²": 0, "Start Year": 3, "Sale Year": "Exit", "Mode": "Rent", "Parking per unit": 0, "Parking ratio (per 100 m²)": 2.5, "Occ %": 90, "Rent growth %": 5, "Asset Value Growth (%/yr)": 4.5})
        for _ in range(4): units_data.append({"Code": "T2-VP", "AssetClass": "residential", "Surface (GLA m²)": 70, "Rent (€/m²/mo)": 16, "Price €/m²": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio (per 100 m²)": 0, "Occ %": 95, "Rent growth %": 4, "Asset Value Growth (%/yr)": 4})
        for _ in range(6): units_data.append({"Code": "T2-VEFA", "AssetClass": "residential", "Surface (GLA m²)": 70, "Rent (€/m²/mo)": 16, "Price €/m²": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio (per 100 m²)": 0, "Occ %": 95, "Rent growth %": 4, "Asset Value Growth (%/yr)": 4})
        
        df_default_units = pd.DataFrame(units_data)
        
        col_conf = {
            "AssetClass": st.column_config.SelectboxColumn(options=["office", "residential", "retail", "logistics", "hotel"]),
            "Mode": st.column_config.SelectboxColumn(options=["Rent", "Sale", "Mixed"]),
            "Price €/m²": st.column_config.NumberColumn(format="%d €"),
            "Rent (€/m²/mo)": st.column_config.NumberColumn(format="%.2f €"),
        }
        # KEY CHANGÉE POUR FORCER LE RELOAD
        df_units = st.data_editor(df_default_units, column_config=col_conf, num_rows="dynamic", use_container_width=True, height=350, key="units_editor_v6")

    # 4. FINANCE
    with tab_fin:
        c1, c2 = st.columns(2)
        i_debt = c1.number_input("Dette (€)", 14504579)
        i_rate = c2.number_input("Taux (%)", 4.5)
        i_term = c1.number_input("Durée (ans)", 20)
        i_grace = c2.number_input("Franchise (mois)", 24)/12
        
        with st.expander("Structuration & Exit"):
            c1, c2 = st.columns(2)
            i_arr_fee = c1.number_input("Arrangement %", 1.0)
            i_upfront = c2.number_input("Frais Fixes", 150000)
            i_prepay = c1.number_input("Pénalité %", 2.0)
            i_hold = c2.number_input("Année Sortie", 20)
            i_exit_y = c1.number_input("Yield Sortie %", 8.25)
            i_sell_fees = c2.number_input("Frais Vente %", 5.0)
            i_tax = c1.number_input("IS %", 30.0)
            i_tax_h = c2.number_input("Exonération", 3)
        
        i_occ = 90; i_rent_g = 2.5; i_inf = 4.0; i_opex = 28.0; i_pm = 4.5

    st.write("")
    run = st.button("⚡ CALCULER & GÉNÉRER LE RAPPORT", type="primary", use_container_width=True)


# --- DASHBOARD DE RÉSULTATS ---
with col_viz:
    if run:
        # MAPPING
        inp_gen = {'land_area': i_land_area, 'parcels': 3, 'construction_rate': i_const_rate, 'far': i_far, 'building_efficiency': i_eff, 'country': "Tanzanie", 'city': i_city, 'fx_eur_local': 2853.1, 'corporate_tax_rate': i_tax, 'tax_holiday': i_tax_h, 'discount_rate': 10.0}
        inp_park = {'cost_per_space': i_parking_cost}
        park = Parking(inp_park, df_units)
        inp_const = {'structure_cost': i_struct if not use_research else 0, 'finishing_cost': i_finish if not use_research else 0, 'utilities_cost': 200, 'permit_fees': i_permits, 'architect_fees_pct': i_arch, 'development_fees_pct': 2.0, 'marketing_fees_pct': 1.0, 'contingency_pct': i_contingency, 's_curve_y1': s1/100, 's_curve_y2': s2/100, 's_curve_y3': s3/100, 'use_research_cost': use_research, 'df_asset_costs': df_asset_costs, 'amenities_total_capex': i_amenities, 'parking_capex': park.total_capex}
        inp_fin = {'debt_amount': i_debt, 'interest_rate': i_rate, 'loan_term': i_term, 'grace_period': i_grace, 'arrangement_fee_pct': i_arr_fee, 'upfront_fees': i_upfront, 'prepayment_fee_pct': i_prepay}
        inp_op = {'rent_growth': i_rent_g, 'exit_yield': i_exit_y, 'holding_period': i_hold, 'inflation': i_inf, 'opex_per_m2': i_opex, 'pm_fee_pct': i_pm, 'occupancy_rate': i_occ, 'transac_fees_exit': i_sell_fees}

        try:
            # INSTANCIATION SANS ERREUR
            gen = General(inp_gen)
            const = Construction(inp_const, gen, df_units)
            fin = Financing(inp_fin)
            op = OperationExit(inp_op)
            capex_sum = CapexSummary(const, fin)
            amort = Amortization(fin, op)
            sched = Scheduler(df_units, op, gen, fin)
            cf = CashflowEngine(gen, const, fin, capex_sum, op, amort, sched)

            st.markdown("### 🎯 Performance")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("TRI (IRR)", f"{cf.kpis['Levered IRR']:.2f}%", delta="Cible > 15%")
            k2.metric("Equity Mult.", f"{cf.kpis['Equity Multiple']:.2f}x")
            k3.metric("Profit (NPV)", f"€{cf.kpis['NPV']:,.0f}")
            k4.metric("Equity Req.", f"€{cf.kpis['Peak Equity']:,.0f}")

            t1, t2, t3 = st.tabs(["📊 Flux", "📋 CAPEX", "📈 Détails"])
            
            with t1:
                fig = px.bar(cf.df, x=cf.df.index, y=['NOI', 'Debt Service', 'Net Cash Flow'], 
                             title="Flux de Trésorerie", 
                             color_discrete_map={'NOI': '#10B981', 'Debt Service': '#EF4444', 'Net Cash Flow': '#3B82F6'})
                fig.update_layout(plot_bgcolor="white", height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with t2:
                df_capex = pd.DataFrame([
                    {"Poste": "Construction", "Montant": capex_sum.construction_pre_financing},
                    {"Poste": "Frais Bancaires", "Montant": capex_sum.upfront_financing_fees},
                    {"Poste": "TOTAL", "Montant": capex_sum.total_capex}
                ])
                st.dataframe(df_capex.style.format({"Montant": "{:,.0f} €"}), use_container_width=True, hide_index=True)

            with t3:
                st.dataframe(cf.df.style.format("{:,.0f}"), use_container_width=True)

        except Exception as e:
            st.error(f"Erreur de calcul : {e}")
    else:
        st.info("👈 Modifiez les paramètres et lancez la simulation.")
        # Placeholder
        dummy = pd.DataFrame({'An': [1,2,3,4], 'Val': [10, 15, 13, 20]})
        fig = px.line(dummy, x='An', y='Val', title="Aperçu")
        fig.update_layout(plot_bgcolor="#F8FAFC")
        st.plotly_chart(fig, use_container_width=True)
