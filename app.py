import streamlit as st
import pandas as pd
from financial_model import General, Construction, Financing, OperationExit, Amortization, Scheduler, CashflowEngine, Parking

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="BP Immo - Zero Deviation")
st.title("🏢 Real Estate Financial Model (Modular Architecture)")
st.info("Strict replication of 'logique_bp_immo.txt' with Granular Units (Occupancy, Growth overrides).")

# =============================================================================
# 1. GENERAL CONFIGURATION
# =============================================================================
st.markdown("### 🌍 Configuration du Projet")
with st.container(border=True):
    col_geo, col_urba, col_fin = st.columns(3)
    with col_geo:
        st.markdown("#### 📍 Site & Localisation")
        c1, c2 = st.columns(2)
        i_city = c1.text_input("Ville", "Dar es Salaam")
        i_country = c2.text_input("Pays", "Tanzanie")
        i_land_area = st.number_input("Surface Terrain (m²)", value=7454, step=100)
        i_parcels = st.number_input("Nombre de Parcelles", value=3, step=1)
    with col_urba:
        st.markdown("#### 🏗️ Urbanisme & Densité")
        i_const_rate = st.slider("Emprise au sol (%)", 0, 100, 60)
        i_far = st.number_input("FAR (Coefficient d'Emprise)", value=3.45, step=0.05)
        i_efficiency = st.slider("Efficacité Bâtiment (%)", 50, 100, 80)
        calc_footprint = i_land_area * (i_const_rate / 100)
        calc_gfa = calc_footprint * i_far
        calc_gla = calc_gfa * (i_efficiency / 100)
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("GFA (Construit)", f"{calc_gfa:,.0f} m²")
        m2.metric("GLA (Louable)", f"{calc_gla:,.0f} m²")
    with col_fin:
        st.markdown("#### 💰 Finance & Fiscalité")
        i_fx = st.number_input("Taux de Change (EUR/Local)", value=2853.1)
        c3, c4 = st.columns(2)
        i_tax_rate = c3.number_input("Impôt Société (%)", value=30.0)
        i_tax_holiday = c4.number_input("Exonération (Ans)", value=3)
        i_discount = st.number_input("Taux d'Actualisation (%)", value=10.0)

# =============================================================================
# 2. CONSTRUCTION & PARKING
# =============================================================================
st.markdown("### 🏗️ Construction & Capex")
with st.container(border=True):
    tab_build, tab_amenities, tab_parking, tab_scurve = st.tabs(["🧱 Coûts Bâtiment", "🎾 Amenities", "🚗 Parking", "📈 Planning (S-Curve)"])
    
    with tab_build:
        use_research = st.toggle("Utiliser les coûts détaillés par classe d'actif ?", value=True)
        default_asset_costs = pd.DataFrame([
            {"Asset Class": "Residential", "Cost €/m²": 1190},
            {"Asset Class": "Office", "Cost €/m²": 1093},
            {"Asset Class": "Retail", "Cost €/m²": 1200},
            {"Asset Class": "Logistics", "Cost €/m²": 800},
        ])
        if use_research:
            st.info("Mode Expert : Le 'Nom' doit correspondre au 'Type' dans les unités.")
            df_asset_costs = st.data_editor(default_asset_costs, num_rows="dynamic", use_container_width=True, key="editor_costs")
            i_struct = i_finish = 0
        else:
            st.warning("Mode Rapide : Coût moyen appliqué.")
            df_asset_costs = pd.DataFrame()
            c1, c2, c3 = st.columns(3)
            i_struct = c1.number_input("Structure (€/m²)", value=800)
            i_finish = c2.number_input("Finitions (€/m²)", value=400)
            i_util = c3.number_input("VRD (€/m²)", value=200)
        
        st.divider()
        fc1, fc2, fc3, fc4 = st.columns(4)
        i_permits = fc1.number_input("Permis (Fixe €)", value=20000)
        i_arch = fc2.number_input("Archi (%)", value=3.0)
        i_dev = fc3.number_input("Dev/Mkting (%)", value=3.0)
        i_contingency = fc4.number_input("Contingence (%)", value=5.0)

    with tab_amenities:
        default_amenities = pd.DataFrame([
            {"Nom": "Padel Court", "Surface (m²)": 300, "Coût (€/m²)": 400, "Actif": True},
            {"Nom": "Gym", "Surface (m²)": 100, "Coût (€/m²)": 800, "Actif": False},
        ])
        edited_amenities = st.data_editor(default_amenities, num_rows="dynamic", use_container_width=True)
        amenities_capex = (edited_amenities[edited_amenities["Actif"]]["Surface (m²)"] * edited_amenities[edited_amenities["Actif"]]["Coût (€/m²)"]).sum()
        st.metric("Total Amenities CAPEX", f"{amenities_capex:,.0f} €")

    with tab_parking:
        st.caption("Calcul automatique basé sur les colonnes 'Parking per unit' et 'Parking ratio' du tableau Units.")
        i_parking_cost = st.number_input("Coût par place de parking (€)", value=18754, step=100)

    with tab_scurve:
        sc1, sc2, sc3 = st.columns(3)
        i_s1 = sc1.slider("Année 1 (%)", 0, 100, 40)
        i_s2 = sc2.slider("Année 2 (%)", 0, 100, 40)
        remain = max(0, 100 - (i_s1 + i_s2))
        i_s3 = sc3.slider("Année 3 (%)", 0, 100, remain, disabled=True)

# =============================================================================
# 3. PARAMETRES FINANCIERS & OPERATIONNELS (FUSIONNÉS)
# =============================================================================
st.markdown("### ⚙️ Paramètres Financiers & Opérationnels")
with st.container(border=True):
    # On utilise des onglets pour séparer proprement les 3 feuilles Excel concernées
    tab_fin, tab_op, tab_exit = st.tabs(["🏦 Financement (Dette)", "⚙️ Opérations (OPEX)", "🚀 Exit & Valorisation"])

    # --- TAB 1 : FINANCING ---
    with tab_fin:
        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
        i_debt = col_f1.number_input("Dette Senior (€)", value=14504579, step=100000, help="Montant total de l'emprunt (Cell B5)")
        i_rate = col_f2.number_input("Taux d'Intérêt (%)", value=4.5, step=0.1, format="%.2f", help="Taux annuel (Cell B6)")
        i_term = col_f3.number_input("Durée Prêt (Années)", value=20, step=1, help="Loan term (Cell B7)")
        # Excel en mois -> Conversion Python en années pour le calcul
        i_grace_months = col_f4.number_input("Franchise (Mois)", value=24, step=6, help="Période Interest-Only (Cell B8)")
        i_grace = i_grace_months / 12.0

        st.divider()
        st.caption("Frais Bancaires & Structuration")
        fee1, fee2, fee3 = st.columns(3)
        i_arr_fee_pct = fee1.number_input("Arrangement Fee (% Dette)", value=1.0, step=0.1, help="Cell B9")
        i_upfront_flat = fee2.number_input("Frais Dossier Fixe (€)", value=150000, step=5000, help="Cell B10")
        i_prepay_fee = fee3.number_input("Pénalité Remb. Anticipé (%)", value=2.0, step=0.5, help="Cell B16")

        # Calcul "Live" pour l'ergonomie (Cell D13)
        total_upfront = i_upfront_flat + (i_debt * i_arr_fee_pct / 100)
        st.info(f"💰 Total Frais Upfront (Calculé) : **{total_upfront:,.0f} €** (déduits au T0)")

    # --- TAB 2 : OPERATION ---
    with tab_op:
        col_o1, col_o2, col_o3 = st.columns(3)
        i_occupancy_def = col_o1.slider("Taux d'Occupation Défaut (%)", 50, 100, 90, help="Utilisé si vide dans Units (Cell B4)")
        i_opex_m2 = col_o2.number_input("OPEX (€/m²/an)", value=28.0, step=1.0, help="Operating expenses (Cell B5)")
        i_pm_fee = col_o3.number_input("Gestion (PM) (% Revenus)", value=4.5, step=0.5, help="Property management fee (Cell B6)")

        st.divider()
        col_o4, col_o5 = st.columns(2)
        i_inflation = col_o4.number_input("Inflation Générale (%/an)", value=4.0, step=0.1, help="Pour OPEX et Prix Vente (Cell B7)")
        i_rent_growth_def = col_o5.number_input("Croissance Loyers Défaut (%/an)", value=2.5, step=0.1, help="Utilisé si vide dans Units (Cell B8)")

    # --- TAB 3 : EXIT ---
    with tab_exit:
        col_e1, col_e2, col_e3 = st.columns(3)
        i_hold_period = col_e1.number_input("Durée Détention (Années)", value=20, step=1, help="Holding period (Cell B4)")
        i_exit_yield = col_e2.number_input("Taux de Sortie (Yield %)", value=8.25, step=0.25, help="Cap rate à la revente (Cell B5)")
        i_transac_fees = col_e3.number_input("Frais Transaction Sortie (%)", value=5.0, step=0.5, help="Sur prix de vente brut (Cell B6)")

# =============================================================================
# 4. UNIT MIX (PRE-LOADED DATA)
# =============================================================================
st.subheader("Unit Mix & Parking Definition")

units_data = []
# Offices (Occupancy 90, Growth 5, Asset Growth 4.5)
units_data.extend([
    {"Code": "OF-L", "Type": "Bureaux", "Surface (m²)": 3000, "Rent (€/m²/mo)": 20, "Price (€/m²)": 0, "Start Year": 3, "Sale Year": "Exit", "Mode": "Rent", "Parking per unit": 0, "Parking ratio": 2.5, "Occupancy %": 90, "Rent Growth %": 5, "Appreciation %": 4.5},
    {"Code": "OF-M", "Type": "Bureaux", "Surface (m²)": 3000, "Rent (€/m²/mo)": 20, "Price (€/m²)": 0, "Start Year": 3, "Sale Year": "Exit", "Mode": "Rent", "Parking per unit": 0, "Parking ratio": 2.5, "Occupancy %": 90, "Rent Growth %": 5, "Appreciation %": 4.5},
    {"Code": "OF-S", "Type": "Bureaux", "Surface (m²)": 2640, "Rent (€/m²/mo)": 20, "Price (€/m²)": 0, "Start Year": 3, "Sale Year": "Exit", "Mode": "Rent", "Parking per unit": 0, "Parking ratio": 2.5, "Occupancy %": 90, "Rent Growth %": 5, "Appreciation %": 4.5},
])
# T2 VP (4 rows) (Occupancy 95, Growth 4, Asset Growth 4)
for _ in range(4): units_data.append({"Code": "T2-VP", "Type": "T2", "Surface (m²)": 70, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
# T2 VEFA (6 rows)
for _ in range(6): units_data.append({"Code": "T2-VEFA", "Type": "T2", "Surface (m²)": 70, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
# T3 VP (4 rows)
for _ in range(4): units_data.append({"Code": "T3-VP", "Type": "T3", "Surface (m²)": 110, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
# T3 VEFA (8 rows)
for _ in range(8): units_data.append({"Code": "T3-VEFA", "Type": "T3", "Surface (m²)": 110, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
# T4 VP (6 rows)
for _ in range(6): units_data.append({"Code": "T4-VP", "Type": "T4", "Surface (m²)": 150, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})
# T4 VEFA (6 rows)
for _ in range(6): units_data.append({"Code": "T4-VEFA", "Type": "T4", "Surface (m²)": 150, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 2, "Parking ratio": 0, "Occupancy %": 95, "Rent Growth %": 4, "Appreciation %": 4})

df_default_units = pd.DataFrame(units_data)

col_conf = {
    "Price (€/m²)": st.column_config.NumberColumn(format="%d €"),
    "Rent (€/m²/mo)": st.column_config.NumberColumn(format="%.2f €"),
    "Mode": st.column_config.SelectboxColumn(options=["Rent", "Sale", "Mixed"]),
    "Parking per unit": st.column_config.NumberColumn(label="Parking (Fixed)", help="Places fixes par unité"),
    "Parking ratio": st.column_config.NumberColumn(label="Parking Ratio", help="Places pour 100m²"),
    "Occupancy %": st.column_config.NumberColumn(label="Occ %", help="Taux d'occupation", format="%d %%"),
    "Rent Growth %": st.column_config.NumberColumn(label="Rent Growth", help="Croissance Loyer Annuelle", format="%.1f %%"),
    "Appreciation %": st.column_config.NumberColumn(label="Asset Growth", help="Valorisation Annuelle", format="%.1f %%"),
}

df_units = st.data_editor(df_default_units, column_config=col_conf, num_rows="dynamic", use_container_width=True)

# =============================================================================
# 5. ORCHESTRATION & CALCUL
# =============================================================================
if st.button("Run Model", type="primary"):
    
    # A. COLLECT INPUTS
    inp_gen = {
        'land_area': i_land_area, 'parcels': i_parcels, 'construction_rate': i_const_rate, 
        'far': i_far, 'building_efficiency': i_efficiency, 'country': i_country, 'city': i_city, 
        'fx_eur_local': i_fx, 'corporate_tax_rate': i_tax_rate, 'tax_holiday': i_tax_holiday, 'discount_rate': i_discount
    }
    
    inp_park = {'cost_per_space': i_parking_cost}
    
    # 1. Parking Calculation First
    park = Parking(inp_park, df_units)
    
    inp_const = {
        'structure_cost': i_struct, 'finishing_cost': i_finish, 'utilities_cost': 200, 'permit_fees': i_permits,
        'architect_fees_pct': i_arch, 'development_fees_pct': i_dev, 'marketing_fees_pct': 0, 'contingency_pct': i_contingency,
        's_curve_y1': i_s1, 's_curve_y2': i_s2, 's_curve_y3': i_s3, 'use_research_cost': use_research,
        'df_asset_costs': df_asset_costs, 'amenities_total_capex': amenities_capex,
        'parking_capex': park.total_capex 
    }
    
    # MAPPING FINANCING INPUTS (Nouveaux champs ajoutés)
    inp_fin = {
        'debt_amount': i_debt, 
        'interest_rate': i_rate, 
        'loan_term': i_term, 
        'grace_period': i_grace, 
        'arrangement_fee_pct': i_arr_fee_pct,
        'upfront_fees': i_upfront_flat,
        'prepayment_fee_pct': i_prepay_fee
    }
    
    # MAPPING OPERATION & EXIT INPUTS (Nouveaux champs ajoutés)
    inp_op = {
        'rent_growth': i_rent_growth_def, 
        'exit_yield': i_exit_yield, 
        'holding_period': i_hold_period,
        'inflation': i_inflation,
        'opex_per_m2': i_opex_m2,
        'pm_fee_pct': i_pm_fee,
        'occupancy_rate': i_occupancy_def,
        'transac_fees_exit': i_transac_fees
    }

    # B. RUN CLASSES
    try:
        gen = General(inp_gen)
        const = Construction(inp_const, gen, df_units)
        fin = Financing(inp_fin, const.total_capex)
        amort = Amortization(fin)
        op = OperationExit(inp_op)
        sched = Scheduler(df_units, op, gen, fin)
        cf = CashflowEngine(gen, const, fin, op, amort, sched)

        # C. DISPLAY RESULTS
        st.success(f"Calcul terminé avec succès ! Parking généré : {park.total_spaces:,.1f} places pour un coût de {park.total_capex:,.0f} €")
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Levered IRR", f"{cf.kpis['Levered IRR']:.2f}%")
        k2.metric("Equity Multiple", f"{cf.kpis['Equity Multiple']:.2f}x")
        k3.metric("Peak Equity", f"€{cf.kpis['Peak Equity']:,.0f}")
        k4.metric("NPV", f"€{cf.kpis['NPV']:,.0f}")
        
        st.subheader("Detailed Cashflow")
        st.dataframe(cf.df.style.format("{:,.0f}"), use_container_width=True)
        st.bar_chart(cf.df[['NOI', 'Debt Service', 'Net Cash Flow']])
        
    except Exception as e:
        st.error(f"Erreur lors du calcul : {e}")
