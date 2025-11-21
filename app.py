import streamlit as st
import pandas as pd
from financial_model import General, Construction, Financing, OperationExit, Amortization, Scheduler, CashflowEngine, Parking

# --- CONFIGURATION DU SITE & STYLE ---
st.set_page_config(layout="wide", page_title="ImmoGenius AI", page_icon="🏢")

# Custom CSS pour affiner le look (titres plus jolis, espacements)
st.markdown("""
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    h1 {color: #0f172a; font-weight: 700;}
    h3 {color: #334155; font-weight: 600; font-size: 1.4rem; margin-top: 1rem;}
    .stMetric {background-color: #f8fafc; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;}
    </style>
""", unsafe_allow_html=True)

st.title("🏢 ImmoGenius : Modélisation Immobilière")
st.markdown("---")

# =============================================================================
# 1. DASHBOARD SYNTHÉTIQUE (EN HAUT DE PAGE)
# =============================================================================
# Cette section sert à définir le projet ET à voir les surfaces résultantes immédiatement.

col_proj_left, col_proj_right = st.columns([1.5, 1])

with col_proj_left:
    with st.container(border=True):
        st.markdown("### 🌍 1. Identité & Terrain")
        c1, c2 = st.columns(2)
        i_city = c1.text_input("📍 Ville", "Dar es Salaam")
        i_country = c2.text_input("🏳️ Pays", "Tanzanie")
        
        c3, c4 = st.columns(2)
        i_land_area = c3.number_input("📐 Surface Terrain (m²)", value=7454, step=100)
        i_parcels = c4.number_input("🧩 Parcelles", value=3, step=1)

with col_proj_right:
    with st.container(border=True):
        st.markdown("### 🏗️ 2. Gabarit & Densité")
        # Sliders compacts pour une saisie rapide
        i_const_rate = st.slider("Emprise au sol (%)", 0, 100, 60)
        i_far = st.number_input("FAR (Coefficient)", value=3.45, step=0.05)
        i_efficiency = st.slider("Efficacité Bâtiment (%)", 50, 100, 80)
        
        # CALCUL LIVE (Feedback visuel immédiat)
        calc_gfa = (i_land_area * i_const_rate/100) * i_far
        calc_gla = calc_gfa * (i_efficiency / 100)
        
        # Affichage des résultats en "Métriques"
        m1, m2 = st.columns(2)
        m1.metric("GFA (Construit)", f"{calc_gfa:,.0f} m²")
        m2.metric("GLA (Louable)", f"{calc_gla:,.0f} m²", delta="Surface Utile")

# =============================================================================
# 3. LE MOTEUR DE COÛTS (CONSTRUCTION)
# =============================================================================
st.write("") # Spacer
with st.container(border=True):
    st.markdown("### 🧱 3. Construction & CAPEX")
    
    # Utilisation des Tabs pour ne pas surcharger l'écran
    tab_build, tab_amenities, tab_parking, tab_planning = st.tabs([
        "🏗️ Coûts Bâtiment", "🎾 Amenities (Loisirs)", "🚗 Parking", "📅 Planning (S-Curve)"
    ])

    with tab_build:
        col_toggle, col_inputs = st.columns([1, 3])
        use_research = col_toggle.toggle("Mode Expert (Par Asset)", value=True, help="Détail les coûts par typologie")
        
        if use_research:
            default_asset_costs = pd.DataFrame([
                {"Asset Class": "Residential", "Cost €/m²": 1190},
                {"Asset Class": "Office", "Cost €/m²": 1093},
                {"Asset Class": "Retail", "Cost €/m²": 1200},
                {"Asset Class": "Logistics", "Cost €/m²": 800},
            ])
            df_asset_costs = st.data_editor(default_asset_costs, num_rows="dynamic", use_container_width=True, key="editor_costs")
            i_struct = i_finish = 0
        else:
            c1, c2, c3 = st.columns(3)
            i_struct = c1.number_input("Structure (€/m²)", 800)
            i_finish = c2.number_input("Finitions (€/m²)", 400)
            i_util = c3.number_input("VRD (€/m²)", 200)
            df_asset_costs = pd.DataFrame()

        with st.expander("Honoraires & Soft Costs (Détails)", expanded=False):
            fc1, fc2, fc3, fc4 = st.columns(4)
            i_permits = fc1.number_input("Permis (Fixe €)", 20000)
            i_arch = fc2.number_input("Archi (%)", 3.0)
            i_dev = fc3.number_input("Dev/Mkting (%)", 3.0)
            i_contingency = fc4.number_input("Contingence (%)", 5.0)

    with tab_amenities:
        col_am_1, col_am_2 = st.columns([3, 1])
        default_amenities = pd.DataFrame([
            {"Nom": "Padel Court", "Surface (m²)": 300, "Coût (€/m²)": 400, "Actif": True},
            {"Nom": "Gym", "Surface (m²)": 100, "Coût (€/m²)": 800, "Actif": False},
        ])
        edited_amenities = col_am_1.data_editor(default_amenities, num_rows="dynamic", use_container_width=True)
        
        # Live Calc
        am_capex = (edited_amenities[edited_amenities["Actif"]]["Surface (m²)"] * edited_amenities[edited_amenities["Actif"]]["Coût (€/m²)"]).sum()
        col_am_2.metric("Budget Amenities", f"{am_capex:,.0f} €")

    with tab_parking:
        col_pk_1, col_pk_2 = st.columns([1, 2])
        i_parking_cost = col_pk_1.number_input("Coût par place (€)", value=18754)
        col_pk_2.info("ℹ️ Le nombre de places est calculé automatiquement selon le mix des unités (Ratio/100m² + Places fixes).")

    with tab_planning:
        st.caption("Distribution des décaissements travaux sur 3 ans")
        sc1, sc2, sc3 = st.columns(3)
        i_s1 = sc1.slider("Année 1", 0, 100, 40)
        i_s2 = sc2.slider("Année 2", 0, 100, 40)
        i_s3 = sc3.slider("Année 3", 0, 100, max(0, 100-i_s1-i_s2), disabled=True)

# =============================================================================
# 4. PARAMÈTRES FINANCIERS (CONCATÉNATION ERGONOMIQUE)
# =============================================================================
st.write("")
with st.container(border=True):
    st.markdown("### ⚙️ 4. Paramètres Financiers & Opérationnels")
    
    # C'est ici que la magie opère : 3 onglets clairs au lieu d'une liste infinie
    tab_fin, tab_ops, tab_exit = st.tabs(["🏦 Financement & Dette", "🔌 Opérations (OPEX)", "🚀 Exit & Valorisation"])

    # --- TAB FINANCEMENT ---
    with tab_fin:
        f1, f2 = st.columns([1, 1])
        with f1:
            st.markdown("**Dette Senior**")
            i_debt = st.number_input("Montant Dette (€)", value=14504579, step=100000)
            c_rate, c_term = st.columns(2)
            i_rate = c_rate.number_input("Taux Intérêt (%)", 4.5)
            i_term = c_term.number_input("Durée (ans)", 20)
            
            c_grace, c_prepay = st.columns(2)
            i_grace_months = c_grace.number_input("Franchise (mois)", 24)
            i_grace = i_grace_months / 12
            i_prepay_fee = c_prepay.number_input("Pénalité Remb. Anticipé (%)", 2.0)

        with f2:
            st.markdown("**Frais & Structuration**")
            c_arr, c_up = st.columns(2)
            i_arr_fee_pct = c_arr.number_input("Arrangement Fee (%)", 1.0)
            i_upfront_flat = c_up.number_input("Frais Fixes (€)", 150000)
            
            # Feedback Visuel : Calcul immédiat des frais
            total_upfront_fees = i_upfront_flat + (i_debt * i_arr_fee_pct / 100)
            st.info(f"💸 **Total Frais Upfront (T0) :** {total_upfront_fees:,.0f} €\n\n_Ces frais sont déduits du cashflow initial._")

    # --- TAB OPERATIONS ---
    with tab_ops:
        o1, o2, o3 = st.columns(3)
        i_occupancy_def = o1.slider("Occupation par défaut (%)", 0, 100, 90, help="Si non spécifié par unité")
        i_rent_growth_def = o2.number_input("Croissance Loyer (%/an)", 2.5)
        i_inflation = o3.number_input("Inflation (%/an)", 4.0)
        
        st.divider()
        o4, o5 = st.columns(2)
        i_opex_m2 = o4.number_input("OPEX (€/m²/an)", 28.0)
        i_pm_fee = o5.number_input("Property Mgmt (% Rev)", 4.5)

    # --- TAB EXIT ---
    with tab_exit:
        e1, e2, e3 = st.columns(3)
        i_hold_period = e1.number_input("Durée Détention (ans)", 20)
        i_exit_yield = e2.number_input("Exit Yield (Taux de Sortie %)", 8.25)
        i_transac_fees = e3.number_input("Frais Vente (%)", 5.0)
        
        st.divider()
        col_tax, col_hol = st.columns(2)
        i_tax_rate = col_tax.number_input("Impôt Société (%)", 30.0)
        i_tax_holiday = col_hol.number_input("Années Exonération (Tax Holiday)", 3)
        i_discount = 10.0 # Hidden or simplified

        # Petite note pédagogique sur l'Exit
        st.caption(f"ℹ️ La valeur de sortie sera calculée sur le NOI de l'année {i_hold_period+1} divisé par {i_exit_yield}%.")

# =============================================================================
# 5. UNIT MIX (TABLEAU COMPLET)
# =============================================================================
st.write("")
with st.container(border=True):
    st.markdown("### 🏘️ 5. Unit Mix & Parking")
    st.caption("Définissez vos unités ligne par ligne. Vous pouvez copier-coller depuis Excel.")

    # Chargement des données (identique à avant mais dans un conteneur propre)
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
    df_units = st.data_editor(df_default_units, column_config=col_conf, num_rows="dynamic", use_container_width=True, height=400)

# =============================================================================
# 6. BOUTON D'ACTION & RÉSULTATS
# =============================================================================
st.write("")
col_btn_1, col_btn_2, col_btn_3 = st.columns([1, 2, 1])
with col_btn_2:
    run_btn = st.button("🚀 LANCER LA SIMULATION COMPLÈTE", type="primary", use_container_width=True)

if run_btn:
    # A. INPUTS COLLECTION
    inp_gen = {
        'land_area': i_land_area, 'parcels': i_parcels, 'construction_rate': i_const_rate, 
        'far': i_far, 'building_efficiency': i_efficiency, 'country': i_country, 'city': i_city, 
        'fx_eur_local': i_fx, 'corporate_tax_rate': i_tax_rate, 'tax_holiday': i_tax_holiday, 'discount_rate': i_discount
    }
    inp_park = {'cost_per_space': i_parking_cost}
    park = Parking(inp_park, df_units)
    
    inp_const = {
        'structure_cost': i_struct, 'finishing_cost': i_finish, 'utilities_cost': 200, 'permit_fees': i_permits,
        'architect_fees_pct': i_arch, 'development_fees_pct': i_dev, 'marketing_fees_pct': 0, 'contingency_pct': i_contingency,
        's_curve_y1': i_s1, 's_curve_y2': i_s2, 's_curve_y3': i_s3, 'use_research_cost': use_research,
        'df_asset_costs': df_asset_costs, 'amenities_total_capex': am_capex,
        'parking_capex': park.total_capex 
    }
    inp_fin = {
        'debt_amount': i_debt, 'interest_rate': i_rate, 'loan_term': i_term, 'grace_period': i_grace, 
        'arrangement_fee_pct': i_arr_fee_pct, 'upfront_fees': i_upfront_flat, 'prepayment_fee_pct': i_prepay_fee
    }
    inp_op = {
        'rent_growth': i_rent_growth_def, 'exit_yield': i_exit_yield, 'holding_period': i_hold_period,
        'inflation': i_inflation, 'opex_per_m2': i_opex_m2, 'pm_fee_pct': i_pm_fee,
        'occupancy_rate': i_occupancy_def, 'transac_fees_exit': i_transac_fees
    }

    # B. RUN ENGINE
    try:
        gen = General(inp_gen)
        const = Construction(inp_const, gen, df_units)
        fin = Financing(inp_fin, const.total_capex)
        amort = Amortization(fin)
        op = OperationExit(inp_op)
        sched = Scheduler(df_units, op, gen, fin)
        cf = CashflowEngine(gen, const, fin, op, amort, sched)

        # C. DISPLAY DASHBOARD RESULTS
        st.markdown("---")
        st.success(f"✅ Calcul terminé ! Parking généré : **{park.total_spaces:,.1f} places** | Coût Parking : **{park.total_capex:,.0f} €**")
        
        # KPIs Cards
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("📈 TRI (IRR Levered)", f"{cf.kpis['Levered IRR']:.2f}%", border=True)
        k2.metric("💰 Equity Multiple", f"{cf.kpis['Equity Multiple']:.2f}x", border=True)
        k3.metric("🏦 Peak Equity", f"€{cf.kpis['Peak Equity']:,.0f}", border=True)
        k4.metric("💎 NPV", f"€{cf.kpis['NPV']:,.0f}", border=True)
        
        # Tabs for Outputs
        tab_res_1, tab_res_2 = st.tabs(["📊 Graphiques & Cashflow", "📋 Tableau Détail"])
        
        with tab_res_1:
            st.bar_chart(cf.df[['NOI', 'Debt Service', 'Net Cash Flow']], color=["#22c55e", "#ef4444", "#3b82f6"])
        
        with tab_res_2:
            st.dataframe(cf.df.style.format("{:,.0f}"), use_container_width=True, height=500)
            
    except Exception as e:
        st.error(f"Oups, une erreur dans le calcul : {e}")
