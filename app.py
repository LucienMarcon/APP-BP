import streamlit as st
import pandas as pd
from financial_model import General, Construction, Financing, OperationExit, Amortization, Scheduler, CashflowEngine

st.set_page_config(layout="wide", page_title="BP Immo - Zero Deviation")

st.title("🏢 Real Estate Financial Model (Modular Architecture)")
st.info("Running strict replication of 'logique_bp_immo.txt'. All formulas are native Python implementations of the Excel logic.")

# --- 1. CONFIGURATION DU PROJET (DESIGN DASHBOARD) ---
st.markdown("### 🌍 Configuration du Projet")

# On utilise un container avec une bordure pour grouper visuellement les paramètres
with st.container(border=True):
    # On divise en 3 colonnes thématiques pour aérer l'affichage
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
        
        # Sliders pour les pourcentages, c'est plus visuel
        i_const_rate = st.slider("Emprise au sol (%)", 0, 100, 60, help="Construction rate / Footprint")
        i_far = st.number_input("FAR (Coefficient d'Emprise)", value=3.45, step=0.05)
        i_efficiency = st.slider("Efficacité Bâtiment (%)", 50, 100, 80, help="Ratio GLA / GFA")

        # CALCULS EN DIRECT (Feedback visuel immédiat)
        # On calcule "à la volée" juste pour l'affichage avant même de lancer le modèle complet
        calc_footprint = i_land_area * (i_const_rate / 100)
        calc_gfa = calc_footprint * i_far
        calc_gla = calc_gfa * (i_efficiency / 100)
        
        st.divider()
        # Affichage type "Cartes de Score"
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

# --- RESTE DES PARAMÈTRES (Moins prioritaires, on peut les laisser en expander discret) ---
with st.expander("🛠️ Paramètres Avancés (Construction, Dette, Exit)", expanded=False):
    col_p1, col_p2, col_p3 = st.columns(3)
    
    with col_p1:
        st.caption("Construction Costs")
        i_struct = st.number_input("Structure (€/m2)", 800)
        i_finish = st.number_input("Finishing (€/m2)", 400)
        # S-Curve
        i_s_curve_y1 = st.slider("S-Curve Y1 (%)", 0, 100, 40)
        i_s_curve_y2 = st.slider("S-Curve Y2 (%)", 0, 100, 40)
        i_s_curve_y3 = st.slider("S-Curve Y3 (%)", 0, 100, 20)

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

# Collect Inputs into Dictionaries (Updated Structure)
inputs_general = {
    'land_area': i_land_area, 
    'parcels': i_parcels,
    'construction_rate': i_const_rate,
    'far': i_far,
    'building_efficiency': i_efficiency,
    'country': i_country,
    'city': i_city,
    'fx_eur_local': i_fx,
    'corporate_tax_rate': i_tax_rate, 
    'tax_holiday': i_tax_holiday, 
    'discount_rate': i_discount
}
# ... (Le reste des dictionnaires inputs_construction, inputs_financing reste inchangé)

# Collect Inputs into Dictionaries
inputs_general = {
    'land_area': i_land_area, 'corporate_tax_rate': i_tax_rate, 
    'tax_holiday': i_tax_holiday, 'discount_rate': i_discount
}
inputs_construction = {
    'structure_cost': i_struct, 'finishing_cost': i_finish,
    's_curve_y1': i_s_curve_y1, 's_curve_y2': i_s_curve_y2, 's_curve_y3': i_s_curve_y3
}
inputs_financing = {
    'debt_amount': i_debt, 'interest_rate': i_rate, 
    'loan_term': i_term, 'grace_period': i_grace, 'upfront_fees': i_upfront
}
inputs_op_exit = {
    'rent_growth': i_rent_growth, 'exit_yield': i_exit_yield, 'holding_period': 20
}

# --- MAIN: UNITS TABLE ---
st.subheader("Unit Mix (Granular Control)")
# CORRECTION : Ajout de la colonne "Price (€/m²)" indispensable pour le calcul
default_units = pd.DataFrame([
    {
        "Type": "Office", 
        "Surface (m²)": 3000, 
        "Rent (€/m²/mo)": 20, 
        "Price (€/m²)": 2500,  # <--- AJOUTÉ ICI
        "Start Year": 3, 
        "Mode": "Rent", 
        "Sale Year": "Exit"
    },
    {
        "Type": "Residential", 
        "Surface (m²)": 1000, 
        "Rent (€/m²/mo)": 16, 
        "Price (€/m²)": 4000,  # <--- AJOUTÉ ICI
        "Start Year": 2, 
        "Mode": "Rent", 
        "Sale Year": "Exit"
    },
    {
        "Type": "Retail", 
        "Surface (m²)": 500, 
        "Rent (€/m²/mo)": 35, 
        "Price (€/m²)": 3000,  # <--- AJOUTÉ ICI
        "Start Year": 3, 
        "Mode": "Rent", 
        "Sale Year": "Exit"
    },
])

# Configuration des colonnes pour que ce soit joli et fonctionnel
column_config = {
    "Price (€/m²)": st.column_config.NumberColumn(
        "Price (€/m²)",
        help="Prix de vente au m² (si Mode = Sale ou Mixed)",
        min_value=0,
        step=100,
        format="%d €"
    ),
    "Rent (€/m²/mo)": st.column_config.NumberColumn(
        "Rent (€/m²/mo)",
        min_value=0,
        step=1,
        format="%.2f €"
    ),
    "Mode": st.column_config.SelectboxColumn(
        "Mode",
        options=["Rent", "Sale", "Mixed"],
        required=True
    )
}

df_units = st.data_editor(
    default_units, 
    column_config=column_config, 
    num_rows="dynamic",
    use_container_width=True
)

# --- ORCHESTRATION (The Logic Pipeline) ---
if st.button("Run Model"):
    # 1. Init General
    gen = General(inputs_general)
    
    # 2. Init Construction (Depends on General for GFA)
    const = Construction(inputs_construction, gen)
    
    # 3. Init Financing
    fin = Financing(inputs_financing, const.total_capex)
    
    # 4. Init Amortization (Depends on Financing)
    amort = Amortization(fin)
    
    # 5. Init Operation
    op = OperationExit(inputs_op_exit)
    
    # 6. Init Schedules (Depends on Units, Op, Gen)
    sched = Scheduler(df_units, op, gen, fin)
    
    # 7. Final Cashflow
    cf = CashflowEngine(gen, const, fin, op, amort, sched)
    
    # --- DISPLAY RESULTS ---
    st.success("Calculations Complete.")
    
    # KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Levered IRR", f"{cf.kpis['Levered IRR']:.2f}%")
    k2.metric("Equity Multiple", f"{cf.kpis['Equity Multiple']:.2f}x")
    k3.metric("Peak Equity", f"€{cf.kpis['Peak Equity']:,.0f}")
    k4.metric("NPV", f"€{cf.kpis['NPV']:,.0f}")
    
    # Cashflow Table
    st.subheader("Detailed Cashflow")
    st.dataframe(cf.df.style.format("{:,.0f}"))
    
    # Charts
    st.subheader("Visuals")
    st.bar_chart(cf.df[['NOI', 'Debt Service', 'Net Cash Flow']])

    with st.expander("Audit: Amortization Schedule"):
        st.write("Check logic: Interest Only vs Principal")
        st.dataframe(pd.DataFrame(amort.schedule).T)


