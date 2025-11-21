import streamlit as st
import pandas as pd
from financial_model import General, Construction, Financing, OperationExit, Amortization, Scheduler, CashflowEngine, Parking

# --- CONFIGURATION DU SITE & STYLE ---
st.set_page_config(layout="wide", page_title="ImmoGenius AI", page_icon="🏢")

# Custom CSS pour un look "App Moderne"
st.markdown("""
    <style>
    .stApp {background-color: #f8fafc;}
    .block-container {padding-top: 1rem; padding-bottom: 5rem;}
    .stMetric {background-color: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
    h1 {color: #1e293b; font-family: 'Helvetica Neue', sans-serif;}
    h2, h3 {color: #334155;}
    .stTabs [data-baseweb="tab-list"] {gap: 24px;}
    .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; background-color: white; border-radius: 8px 8px 0 0; padding: 0 20px;}
    .stTabs [aria-selected="true"] {background-color: #f1f5f9; border-bottom: 2px solid #3b82f6;}
    </style>
""", unsafe_allow_html=True)

# --- HEADER HERO ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.write("## 🏢")
with col_title:
    st.title("ImmoGenius Plan")
    st.caption("Modélisation Financière Immobilière de Précision")

st.write("")

# =============================================================================
# 1. WIZARD DE SAISIE (EN 4 ÉTAPES)
# =============================================================================
# On utilise des Expander ou des Tabs pour séquencer la saisie sans scroller à l'infini

step1, step2, step3, step4 = st.tabs(["📍 1. Terrain & Gabarit", "🏗️ 2. Construction", "🏘️ 3. Unités & Parking", "💰 4. Finance & Exit"])

# --- ETAPE 1 : TERRAIN ---
with step1:
    col_left, col_right = st.columns([1, 2])
    with col_left:
        st.markdown("#### Données Site")
        i_city = st.text_input("Ville", "Dar es Salaam")
        i_land_area = st.number_input("Surface Terrain (m²)", value=7454, step=100)
        
    with col_right:
        st.markdown("#### Paramètres Urbanistiques")
        c1, c2, c3 = st.columns(3)
        i_const_rate = c1.number_input("Emprise (%)", value=60, step=5)
        i_far = c2.number_input("FAR", value=3.45, step=0.05)
        i_efficiency = c3.number_input("Efficacité (%)", value=80, step=5)
        
        # Live KPI
        calc_gfa = (i_land_area * i_const_rate/100) * i_far
        calc_gla = calc_gfa * (i_efficiency / 100)
        st.info(f"📊 **Résultat Potentiel :**\nGFA (Construit) : **{calc_gfa:,.0f} m²**\nGLA (Louable) : **{calc_gla:,.0f} m²**")

# --- ETAPE 2 : CONSTRUCTION ---
with step2:
    st.markdown("#### Coûts de Construction & Planning")
    
    col_toggle, col_details = st.columns([1, 3])
    use_research = col_toggle.toggle("Mode Expert (Par Asset)", value=True)
    
    if use_research:
        default_asset_costs = pd.DataFrame([
            {"Asset Class": "Residential", "Cost €/m²": 1190},
            {"Asset Class": "Office", "Cost €/m²": 1093},
            {"Asset Class": "Retail", "Cost €/m²": 1200},
            {"Asset Class": "Logistics", "Cost €/m²": 800},
        ])
        df_asset_costs = st.data_editor(default_asset_costs, num_rows="dynamic", use_container_width=True, hide_index=True)
        i_struct = i_finish = 0
    else:
        c1, c2 = st.columns(2)
        i_struct = c1.number_input("Structure (€/m²)", 800)
        i_finish = c2.number_input("Finitions (€/m²)", 400)
        df_asset_costs = pd.DataFrame()

    with st.expander("Voir les Soft Costs & Amenities", expanded=False):
        sc1, sc2, sc3 = st.columns(3)
        i_permits = sc1.number_input("Permis (€)", 20000)
        i_arch = sc2.number_input("Archi (%)", 3.0)
        i_contingency = sc3.number_input("Contingence (%)", 5.0)
        
        st.markdown("---")
        st.write("**Amenities (Padel, Gym...)**")
        default_amenities = pd.DataFrame([
            {"Nom": "Padel", "Surface": 300, "Coût": 400, "Actif": True},
            {"Nom": "Gym", "Surface": 100, "Coût": 800, "Actif": False},
        ])
        edited_amenities = st.data_editor(default_amenities, num_rows="dynamic", use_container_width=True, hide_index=True)
        am_capex = (edited_amenities[edited_amenities["Actif"]]["Surface"] * edited_amenities[edited_amenities["Actif"]]["Coût"]).sum()
        st.caption(f"Budget Amenities: {am_capex:,.0f} €")

    st.caption("Planning S-Curve")
    i_s1 = st.slider("Année 1 (%)", 0, 100, 40)
    i_s2 = st.slider("Année 2 (%)", 0, 100, 40)
    i_s3 = 100 - i_s1 - i_s2

# --- ETAPE 3 : UNITÉS ---
with step3:
    st.markdown("#### Mix Produit & Parking")
    col_u_left, col_u_right = st.columns([3, 1])
    
    with col_u_right:
        st.info("💡 Saisissez vos unités ici. Le parking est calculé automatiquement.")
        i_parking_cost = st.number_input("Coût Place Parking (€)", 18754)
    
    with col_u_left:
        # Chargement des 37 unités
        units_data = []
        # Offices
        units_data.extend([
            {"Code": "OF-L", "Type": "Bureaux", "Surface (m²)": 3000, "Rent (€/m²/mo)": 20, "Price (€/m²)": 0, "Start Year": 3, "Sale Year": "Exit", "Mode": "Rent", "Parking per unit": 0, "Parking ratio": 2.5, "Occupancy %": 90, "Rent Growth %": 5, "Appreciation %": 4.5},
            {"Code": "OF-M", "Type": "Bureaux", "Surface (m²)": 3000, "Rent (€/m²/mo)": 20, "Price (€/m²)": 0, "Start Year": 3, "Sale Year": "Exit", "Mode": "Rent", "Parking per unit": 0, "Parking ratio": 2.5, "Occupancy %": 90, "Rent Growth %": 5, "Appreciation %": 4.5},
            {"Code": "OF-S", "Type": "Bureaux", "Surface (m²)": 2640, "Rent (€/m²/mo)": 20, "Price (€/m²)": 0, "Start Year": 3, "Sale Year": "Exit", "Mode": "Rent", "Parking per unit": 0, "Parking ratio": 2.5, "Occupancy %": 90, "Rent Growth %": 5, "Appreciation %": 4.5},
        ])
        # T2 VP
        for _ in range(4): units_data.append({"Code": "T2-VP", "Type": "T2", "Surface (m²)": 70, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
        # T2 VEFA
        for _ in range(6): units_data.append({"Code": "T2-VEFA", "Type": "T2", "Surface (m²)": 70, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
        # T3 VP
        for _ in range(4): units_data.append({"Code": "T3-VP", "Type": "T3", "Surface (m²)": 110, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
        # T3 VEFA
        for _ in range(8): units_data.append({"Code": "T3-VEFA", "Type": "T3", "Surface (m²)": 110, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
        # T4 VP
        for _ in range(6): units_data.append({"Code": "T4-VP", "Type": "T4", "Surface (m²)": 150, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
        # T4 VEFA
        for _ in range(6): units_data.append({"Code": "T4-VEFA", "Type": "T4", "Surface (m²)": 150, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})

        df_default_units = pd.DataFrame(units_data)
        
        col_conf = {
            "Price (€/m²)": st.column_config.NumberColumn(format="%d €"),
            "Rent (€/m²/mo)": st.column_config.NumberColumn(format="%.2f €"),
            "Mode": st.column_config.SelectboxColumn(options=["Rent", "Sale", "Mixed"]),
            "Parking per unit": st.column_config.NumberColumn(label="Pk Fixed"),
            "Parking ratio": st.column_config.NumberColumn(label="Pk Ratio"),
            "Occupancy %": st.column_config.NumberColumn(label="Occ %", format="%d %%"),
            "Rent Growth %": st.column_config.NumberColumn(label="Rent Grow", format="%.1f %%"),
            "Appreciation %": st.column_config.NumberColumn(label="Asset Grow", format="%.1f %%"),
        }
        df_units = st.data_editor(df_default_units, column_config=col_conf, num_rows="dynamic", use_container_width=True, height=300, hide_index=True)

# --- ETAPE 4 : FINANCE ---
with step4:
    st.markdown("#### Hypothèses Financières")
    
    # Disposition en 3 colonnes claires
    c_fin, c_op, c_exit = st.columns(3)
    
    with c_fin:
        st.markdown("**🏦 Dette**")
        i_debt = st.number_input("Montant (€)", 14504579)
        i_rate = st.number_input("Taux (%)", 4.5)
        i_term = st.number_input("Durée (ans)", 20)
        i_grace_months = st.number_input("Franchise (mois)", 24)
        i_arr_fee_pct = st.number_input("Frais Dossier (%)", 1.0)
        i_upfront_flat = st.number_input("Frais Fixes (€)", 150000)
        i_prepay_fee = st.number_input("Pénalité Sortie (%)", 2.0)
        
    with c_op:
        st.markdown("**🔌 Opérations**")
        i_occupancy_def = st.number_input("Occ. Défaut (%)", 90)
        i_rent_growth_def = st.number_input("Croissance Loyer (%)", 2.5)
        i_inflation = st.number_input("Inflation (%)", 4.0)
        i_opex_m2 = st.number_input("OPEX (€/m²)", 28.0)
        i_pm_fee = st.number_input("Gestion (%)", 4.5)
        
    with c_exit:
        st.markdown("**🚀 Exit**")
        i_hold_period = st.number_input("Année Sortie", 20)
        i_exit_yield = st.number_input("Yield Sortie (%)", 8.25)
        i_transac_fees = st.number_input("Frais Vente (%)", 5.0)
        st.markdown("**Taxes**")
        i_tax_rate = st.number_input("IS (%)", 30.0)
        i_tax_holiday = st.number_input("Exonération (ans)", 3)

# =============================================================================
# 6. ACTION & DASHBOARD RÉSULTATS
# =============================================================================
st.write("")
st.write("")
_, col_btn, _ = st.columns([1, 2, 1])
run_btn = col_btn.button("✨ LANCER LA SIMULATION", type="primary", use_container_width=True)

if run_btn:
    # Mapping des inputs pour le moteur
    inp_gen = {'land_area': i_land_area, 'parcels': 3, 'construction_rate': 60, 'far': i_far, 'building_efficiency': i_efficiency, 'country': "Tanzanie", 'city': i_city, 'fx_eur_local': 2853.1, 'corporate_tax_rate': i_tax_rate, 'tax_holiday': i_tax_holiday, 'discount_rate': 10.0}
    inp_park = {'cost_per_space': i_parking_cost}
    park = Parking(inp_park, df_units)
    
    inp_const = {
        'structure_cost': i_struct if not use_research else 0, 'finishing_cost': i_finish if not use_research else 0, 'utilities_cost': 200, 
        'permit_fees': i_permits, 'architect_fees_pct': i_arch, 'development_fees_pct': 2.0, 'marketing_fees_pct': 1.0, 'contingency_pct': i_contingency,
        's_curve_y1': i_s1/100, 's_curve_y2': i_s2/100, 's_curve_y3': i_s3/100, 'use_research_cost': use_research,
        'df_asset_costs': df_asset_costs, 'amenities_total_capex': am_capex, 'parking_capex': park.total_capex 
    }
    inp_fin = {'debt_amount': i_debt, 'interest_rate': i_rate, 'loan_term': i_term, 'grace_period': i_grace_months/12, 'arrangement_fee_pct': i_arr_fee_pct, 'upfront_fees': i_upfront_flat, 'prepayment_fee_pct': i_prepay_fee}
    inp_op = {'rent_growth': i_rent_growth_def, 'exit_yield': i_exit_yield, 'holding_period': i_hold_period, 'inflation': i_inflation, 'opex_per_m2': i_opex_m2, 'pm_fee_pct': i_pm_fee, 'occupancy_rate': i_occupancy_def, 'transac_fees_exit': i_transac_fees}

    try:
        gen = General(inp_gen)
        const = Construction(inp_const, gen, df_units)
        fin = Financing(inp_fin, const.total_capex)
        amort = Amortization(fin)
        op = OperationExit(inp_op)
        sched = Scheduler(df_units, op, gen, fin)
        cf = CashflowEngine(gen, const, fin, op, amort, sched)

        st.markdown("### 🎯 Résultats Clés")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("IRR (Levered)", f"{cf.kpis['Levered IRR']:.2f}%")
        k2.metric("Equity Multiple", f"{cf.kpis['Equity Multiple']:.2f}x")
        k3.metric("Equity Nécessaire", f"€{cf.kpis['Peak Equity']:,.0f}")
        k4.metric("Profit (NPV)", f"€{cf.kpis['NPV']:,.0f}")
        
        tab_graph, tab_data = st.tabs(["📊 Graphique Cashflow", "📋 Tableau Détaillé"])
        with tab_graph:
            st.bar_chart(cf.df[['NOI', 'Debt Service', 'Net Cash Flow']], color=["#10b981", "#ef4444", "#3b82f6"])
        with tab_data:
            st.dataframe(cf.df.style.format("{:,.0f}"), use_container_width=True)
            
    except Exception as e:
        st.error(f"Erreur : {e}")
