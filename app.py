import streamlit as st
import pandas as pd
from financial_model import General, Construction, Financing, OperationExit, Amortization, Scheduler, CashflowEngine

st.set_page_config(layout="wide", page_title="BP Immo - Zero Deviation")

st.title("🏢 Real Estate Financial Model (Modular Architecture)")
st.info("Running strict replication of 'logique_bp_immo.txt'. All formulas are native Python implementations of the Excel logic.")

# --- SIDEBAR: INPUTS ---
st.sidebar.header("1. General")
i_land_area = st.sidebar.number_input("Land Area", 7454)
i_tax_rate = st.sidebar.number_input("Corp Tax Rate (%)", 30.0)
i_tax_holiday = st.sidebar.number_input("Tax Holiday (Yrs)", 3)
i_discount = st.sidebar.number_input("Discount Rate (%)", 10.0)

st.sidebar.header("2. Construction")
i_struct = st.sidebar.number_input("Structure Cost (€/m2)", 800)
i_finish = st.sidebar.number_input("Finishing Cost (€/m2)", 400)
i_s_curve_y1 = st.sidebar.slider("S-Curve Y1 (%)", 0, 100, 40)
i_s_curve_y2 = st.sidebar.slider("S-Curve Y2 (%)", 0, 100, 40)
i_s_curve_y3 = st.sidebar.slider("S-Curve Y3 (%)", 0, 100, 20)

st.sidebar.header("3. Financing")
i_debt = st.sidebar.number_input("Debt Amount (€)", 14_500_000)
i_rate = st.sidebar.number_input("Interest Rate (%)", 4.5)
i_term = st.sidebar.number_input("Loan Term (Yrs)", 20)
i_grace = st.sidebar.number_input("Grace Period (Yrs)", 2)
i_upfront = st.sidebar.number_input("Upfront Fees (€)", 150_000)

st.sidebar.header("4. Operation & Exit")
i_rent_growth = st.sidebar.number_input("Rent Growth (%)", 2.5)
i_exit_yield = st.sidebar.number_input("Exit Yield (%)", 8.25)

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

