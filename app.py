import streamlit as st
import pandas as pd
from financial_model import General, Construction, Financing, OperationExit, Amortization, Scheduler, CashflowEngine

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(layout="wide", page_title="BP Immo - Zero Deviation")

st.title("🏢 Real Estate Financial Model (Modular Architecture)")
st.info("Running strict replication of 'logique_bp_immo.txt'. All formulas are native Python implementations of the Excel logic.")

# =============================================================================
# 1. GENERAL & CONFIGURATION (LE DASHBOARD DU HAUT)
# =============================================================================
st.markdown("### 🌍 Configuration du Projet")

with st.container(border=True):
    col_geo, col_urba, col_fin = st.columns(3)

    # --- COLONNE 1 : LOCALISATION & TERRAIN ---
    with col_geo:
        st.markdown("#### 📍 Site & Localisation")
        c1, c2 = st.columns(2)
        i_city = c1.text_input("Ville", "Dar es Salaam")
        i_country = c2.text_input("Pays", "Tanzanie")
        
        i_land_area = st.number_input("Surface Terrain (m²)", value=7454, step=100)
        i_parcels = st.number_input("Nombre de Parcelles", value=3, step=1)

    # --- COLONNE 2 : URBANISME & DENSITÉ ---
    with col_urba:
        st.markdown("#### 🏗️ Urbanisme & Densité")
        
        i_const_rate = st.slider("Emprise au sol (%)", 0, 100, 60, help="Construction rate / Footprint")
        i_far = st.number_input("FAR (Coefficient d'Emprise)", value=3.45, step=0.05)
        i_efficiency = st.slider("Efficacité Bâtiment (%)", 50, 100, 80, help="Ratio GLA / GFA")

        # CALCULS EN DIRECT (Feedback visuel)
        calc_footprint = i_land_area * (i_const_rate / 100)
        calc_gfa = calc_footprint * i_far
        calc_gla = calc_gfa * (i_efficiency / 100)
        
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("GFA (Construit)", f"{calc_gfa:,.0f} m²", delta_color="off")
        m2.metric("GLA (Louable)", f"{calc_gla:,.0f} m²", delta="Surface Utile")

    # --- COLONNE 3 : MACRO-ÉCONOMIE & TAXES ---
    with col_fin:
        st.markdown("#### 💰 Finance & Fiscalité")
        i_fx = st.number_input("Taux de Change (EUR/Local)", value=2853.1, help="FX Rate")
        
        c3, c4 = st.columns(2)
        i_tax_rate = c3.number_input("Impôt Société (%)", value=30.0)
        i_tax_holiday = c4.number_input("Exonération (Ans)", value=3, help="Tax Holiday")
        i_discount = st.number_input("Taux d'Actualisation (%)", value=10.0)

# =============================================================================
# 2. CONSTRUCTION (DESIGN GAMIFIÉ)
# =============================================================================
st.markdown("### 🏗️ Construction & Capex")

with st.container(border=True):
    tab_build, tab_amenities, tab_scurve = st.tabs(["🧱 Coûts Bâtiment", "🎾 Amenities & Extras", "📈 Planning (S-Curve)"])

  with tab_build:
        use_research = st.toggle("Utiliser les coûts détaillés par classe d'actif ?", value=True)
        
        # Initialisation du DataFrame de coûts (vide ou par défaut)
        default_asset_costs = pd.DataFrame([
            {"Asset Class": "Residential", "Cost €/m²": 1190},
            {"Asset Class": "Office", "Cost €/m²": 1093},
            {"Asset Class": "Retail", "Cost €/m²": 1200},
            {"Asset Class": "Logistics", "Cost €/m²": 800},
        ])

        if use_research:
            st.info("💡 Mode Expert : Ajoutez/Supprimez des lignes. Le 'Nom' doit correspondre au 'Type' dans la liste des unités.")
            
            # TABLEAU ÉDITABLE DYNAMIQUE
            column_config_costs = {
                "Asset Class": st.column_config.TextColumn("Classe d'Actif (Mot-clé)", help="Ce mot doit se trouver dans le Type d'unité (ex: 'Office' matchera 'Office-Large')"),
                "Cost €/m²": st.column_config.NumberColumn("Coût GFA (€/m²)", format="%d €")
            }
            
            df_asset_costs = st.data_editor(
                default_asset_costs, 
                column_config=column_config_costs, 
                num_rows="dynamic", 
                use_container_width=True,
                key="editor_costs"
            )
            
            # On met à zéro les variables globales pour la logique
            i_struct = i_finish = 0
        else:
            st.warning("⚡ Mode Rapide : Coût moyen appliqué à tout le bâtiment.")
            # On garde un DataFrame vide pour le moteur
            df_asset_costs = pd.DataFrame()
            
            c1, c2, c3 = st.columns(3)
            i_struct = c1.number_input("Structure (€/m²)", value=800, step=50)
            i_finish = c2.number_input("Finitions (€/m²)", value=400, step=50)
            i_util_dummy = c3.number_input("VRD / Utilities (€/m²)", value=200, step=50)

        st.divider()
        st.markdown("**Frais & Honoraires (Soft Costs)**")
        fc1, fc2, fc3, fc4 = st.columns(4)
        i_permits = fc1.number_input("Permis (Fixe €)", value=20000)
        i_arch = fc2.number_input("Archi (%)", value=3.0, step=0.1)
        i_dev = fc3.number_input("Dev/Marketing (%)", value=3.0, step=0.1)
        i_contingency = fc4.number_input("Contingence (%)", value=5.0, step=0.5)
        
        if use_research:
            st.info("💡 Mode Expert Activé : Coûts différenciés par typologie.")
            c_res, c_off, c_ret = st.columns(3)
            i_cost_res = c_res.number_input("Coût Résidentiel (€/m² GFA)", value=1190, step=50)
            i_cost_off = c_off.number_input("Coût Bureaux (€/m² GFA)", value=1093, step=50)
            i_cost_ret = c_ret.number_input("Coût Retail (€/m² GFA)", value=1200, step=50)
            # Variables globales à 0 pour la logique
            i_struct = i_finish = 0
        else:
            st.warning("⚡ Mode Rapide : Coût moyen appliqué à tout le bâtiment.")
            c1, c2, c3 = st.columns(3)
            i_struct = c1.number_input("Structure (€/m²)", value=800, step=50)
            i_finish = c2.number_input("Finitions (€/m²)", value=400, step=50)
            i_util_dummy = c3.number_input("VRD / Utilities (€/m²)", value=200, step=50)
            # Variables par asset à 0
            i_cost_res = i_cost_off = i_cost_ret = 0

        st.divider()
        st.markdown("**Frais & Honoraires (Soft Costs)**")
        fc1, fc2, fc3, fc4 = st.columns(4)
        i_permits = fc1.number_input("Permis (Fixe €)", value=20000)
        i_arch = fc2.number_input("Archi (%)", value=3.0, step=0.1)
        i_dev = fc3.number_input("Dev/Marketing (%)", value=3.0, step=0.1)
        i_contingency = fc4.number_input("Contingence (%)", value=5.0, step=0.5)

    with tab_amenities:
        st.caption("Ajoutez ici les équipements spécifiques (Padel, Piscine, etc.)")
        default_amenities = pd.DataFrame([
            {"Nom": "Padel Court", "Surface (m²)": 300, "Coût (€/m²)": 400, "Actif": True},
            {"Nom": "Gym", "Surface (m²)": 100, "Coût (€/m²)": 800, "Actif": False},
        ])
        edited_amenities = st.data_editor(default_amenities, num_rows="dynamic", use_container_width=True)
        amenities_capex = (edited_amenities[edited_amenities["Actif"]]["Surface (m²)"] * edited_amenities[edited_amenities["Actif"]]["Coût (€/m²)"]).sum()
        st.metric("Total Amenities CAPEX", f"{amenities_capex:,.0f} €")

    with tab_scurve:
        st.write("Distribution des décaissements sur 3 ans")
        sc1, sc2, sc3 = st.columns(3)
        i_s1 = sc1.slider("Année 1 (%)", 0, 100, 40)
        i_s2 = sc2.slider("Année 2 (%)", 0, 100, 40)
        remain = max(0, 100 - (i_s1 + i_s2))
        i_s3 = sc3.slider("Année 3 (%)", 0, 100, remain, disabled=True, help="Calculé automatiquement")

# =============================================================================
# 3. AUTRES PARAMÈTRES (Dette, Exit...)
# =============================================================================
with st.expander("🛠️ Paramètres Avancés (Dette, Exit, Inflation)", expanded=False):
    col_p2, col_p3 = st.columns(2)
    with col_p2:
        st.caption("Financing")
        i_debt = st.number_input("Dette Totale (€)", 14_500_000)
        i_rate = st.number_input("Taux Intérêt (%)", 4.5)
        i_term = st.number_input("Durée (Années)", 20)
        i_grace = st.number_input("Franchise (Années)", 2)
        i_upfront = st.number_input("Frais Dossier (€)", 150_000)
    with col_p3:
        st.caption("Operation & Exit")
        i_rent_growth = st.number_input("Croissance Loyer (%)", 2.5)
        i_exit_yield = st.number_input("Taux de Sortie (%)", 8.25)

# =============================================================================
# 4. TABLEAU DES UNITÉS (UNITS)
# =============================================================================
st.subheader("Unit Mix (Granular Control)")
default_units = pd.DataFrame([
    {"Type": "Office", "Surface (m²)": 3000, "Rent (€/m²/mo)": 20, "Price (€/m²)": 2500, "Start Year": 3, "Mode": "Rent", "Sale Year": "Exit"},
    {"Type": "Residential", "Surface (m²)": 1000, "Rent (€/m²/mo)": 16, "Price (€/m²)": 4000, "Start Year": 2, "Mode": "Rent", "Sale Year": "Exit"},
    {"Type": "Retail", "Surface (m²)": 500, "Rent (€/m²/mo)": 35, "Price (€/m²)": 3000, "Start Year": 3, "Mode": "Rent", "Sale Year": "Exit"},
])

column_config = {
    "Price (€/m²)": st.column_config.NumberColumn("Price (€/m²)", help="Prix de vente au m²", min_value=0, format="%d €"),
    "Rent (€/m²/mo)": st.column_config.NumberColumn("Rent (€/m²/mo)", min_value=0, format="%.2f €"),
    "Mode": st.column_config.SelectboxColumn("Mode", options=["Rent", "Sale", "Mixed"], required=True)
}
df_units = st.data_editor(default_units, column_config=column_config, num_rows="dynamic", use_container_width=True)

# =============================================================================
# 5. ORCHESTRATION & CALCUL
# =============================================================================
if st.button("Run Model", type="primary"):
    
    # A. Collect Inputs
    inputs_general = {
        'land_area': i_land_area, 'parcels': i_parcels, 'construction_rate': i_const_rate,
        'far': i_far, 'building_efficiency': i_efficiency, 'country': i_country, 'city': i_city,
        'fx_eur_local': i_fx, 'corporate_tax_rate': i_tax_rate, 
        'tax_holiday': i_tax_holiday, 'discount_rate': i_discount
    }
    
    inputs_construction = {
        'structure_cost': i_struct, 'finishing_cost': i_finish, 'utilities_cost': 200,
        'permit_fees': i_permits, 'architect_fees_pct': i_arch, 'development_fees_pct': i_dev, 'marketing_fees_pct': 0,
        'contingency_pct': i_contingency,
        's_curve_y1': i_s1, 's_curve_y2': i_s2, 's_curve_y3': i_s3,
        'use_research_cost': use_research,
        'df_asset_costs': df_asset_costs,  # <--- LE NOUVEAU TABLEAU EST PASSÉ ICI
        'amenities_total_capex': amenities_capex
    }
    
    inputs_financing = {
        'debt_amount': i_debt, 'interest_rate': i_rate, 'loan_term': i_term, 
        'grace_period': i_grace, 'upfront_fees': i_upfront
    }
    
    inputs_op_exit = {
        'rent_growth': i_rent_growth, 'exit_yield': i_exit_yield, 'holding_period': 20
    }

    # B. Run Classes
    gen = General(inputs_general)
    const = Construction(inputs_construction, gen, df_units) # <-- Passe bien df_units
    fin = Financing(inputs_financing, const.total_capex)
    amort = Amortization(fin)
    op = OperationExit(inputs_op_exit)
    sched = Scheduler(df_units, op, gen, fin)
    cf = CashflowEngine(gen, const, fin, op, amort, sched)

    # C. Display
    st.success("Calculations Complete.")
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Levered IRR", f"{cf.kpis['Levered IRR']:.2f}%")
    k2.metric("Equity Multiple", f"{cf.kpis['Equity Multiple']:.2f}x")
    k3.metric("Peak Equity", f"€{cf.kpis['Peak Equity']:,.0f}")
    k4.metric("NPV", f"€{cf.kpis['NPV']:,.0f}")
    
    st.subheader("Detailed Cashflow")
    st.dataframe(cf.df.style.format("{:,.0f}"), use_container_width=True)
    
    st.bar_chart(cf.df[['NOI', 'Debt Service', 'Net Cash Flow']])






