import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Real Estate Business Plan Modeler",
    page_icon="🏢",
    layout="wide"
)

# --- CUSTOM CSS FOR STYLING ---
st.markdown("""
    <style>
    .main-header {font-size: 2rem; font-weight: bold; color: #1E3A8A;}
    .sub-header {font-size: 1.5rem; font-weight: bold; color: #3B82F6;}
    .kpi-card {background-color: #f0f2f6; padding: 20px; border-radius: 10px; text-align: center;}
    </style>
""", unsafe_allow_html=True)

# --- 1. CALCULATION FUNCTIONS (THE ENGINE) ---

def calculate_loan_schedule(principal, annual_rate, duration_years, grace_period_years):
    """
    Generates a loan amortization schedule matching the 'Amortization' sheet logic:
    - Interest Only during grace period.
    - Constant annuities (Principal + Interest) afterwards.
    """
    schedule = []
    monthly_rate = annual_rate / 12
    total_months = int(duration_years * 12)
    grace_months = int(grace_period_years * 12)
    
    remaining_balance = principal
    
    # Calculate monthly payment (PMT) for the post-grace period
    amortization_months = total_months - grace_months
    if amortization_months > 0 and principal > 0 and monthly_rate > 0:
        monthly_payment = principal * (monthly_rate * (1 + monthly_rate)**amortization_months) / ((1 + monthly_rate)**amortization_months - 1)
    elif amortization_months > 0 and principal > 0:
        monthly_payment = principal / amortization_months
    else:
        monthly_payment = 0

    # Generate yearly aggregation
    # We simulate month by month to be precise, then aggregate by year
    
    current_balance = principal
    
    yearly_data = {}
    
    for m in range(1, total_months + 1):
        year = (m - 1) // 12 + 1
        
        if year not in yearly_data:
            yearly_data[year] = {'interest': 0, 'principal': 0, 'payment': 0, 'balance_start': current_balance}
        
        # Interest Calculation
        interest = current_balance * monthly_rate
        
        # Principal Calculation
        if m <= grace_months:
            principal_pay = 0
            payment = interest
        else:
            payment = monthly_payment
            principal_pay = payment - interest
            
        # Update Balance
        current_balance -= principal_pay
        if current_balance < 0: current_balance = 0 # Avoid floating point errors
        
        # Aggregate
        yearly_data[year]['interest'] += interest
        yearly_data[year]['principal'] += principal_pay
        yearly_data[year]['payment'] += payment
        yearly_data[year]['balance_end'] = current_balance

    return yearly_data

def calculate_model(params, df_units):
    """
    Core engine that reconstructs the Cashflow, RentSchedule, and SaleSchedule sheets.
    """
    years = range(0, int(params['holding_period']) + 2) # +2 to calculate n+1 for exit
    cols = [f"Y{y}" for y in years]
    
    # --- A. CONSTRUCTION CAPEX (S-Curve) ---
    # Rebuilding logic from 'Construction' sheet
    land_cost = params['land_area'] * params['land_price_per_m2'] if 'land_price_per_m2' in params else 0 # Assuming land is already owned or part of GFA inputs
    # Note: In the text file, Land Area is in General, but cost isn't explicit. We assume Land is an initial outflow or part of total investment.
    # Let's calculate Construction Costs based on GFA
    gfa = params['land_area'] * params['far']
    gla = gfa * (params['building_efficiency'] / 100)
    
    # Hard Costs
    hard_costs_total = gfa * (params['cost_structure'] + params['cost_finishing'] + params['cost_utilities'])
    
    # Soft Fees (Permits + % based fees)
    soft_fees_pct = (params['fee_architect'] + params['fee_development'] + params['fee_marketing']) / 100
    soft_costs_total = params['fee_permits'] + (hard_costs_total * soft_fees_pct)
    
    # Contingency
    subtotal_capex = hard_costs_total + soft_costs_total
    contingency_amount = subtotal_capex * (params['contingency'] / 100)
    
    total_capex = subtotal_capex + contingency_amount
    
    # S-Curve Distribution (Y1, Y2, Y3)
    capex_flow = {y: 0.0 for y in years}
    capex_flow[1] = total_capex * (params['s_curve_y1'] / 100)
    capex_flow[2] = total_capex * (params['s_curve_y2'] / 100)
    capex_flow[3] = total_capex * (params['s_curve_y3'] / 100)
    
    # --- B. RENT & SALE SCHEDULES (Units Sheet) ---
    rent_flow = {y: 0.0 for y in years}
    sale_flow = {y: 0.0 for y in years}
    
    # Iterate over units
    for _, unit in df_units.iterrows():
        surface = unit['Surface (m²)']
        base_rent = unit['Rent (€/m²/mo)'] * 12 # Annualized
        base_price = unit['Price (€/m²)']
        start_year = int(unit['Start Year']) if pd.notna(unit['Start Year']) else 999
        sale_year_input = unit['Sale Year']
        
        # Determine Sale Year
        if str(sale_year_input).lower() == 'exit':
            unit_sale_year = int(params['holding_period'])
        elif pd.notna(sale_year_input):
            unit_sale_year = int(sale_year_input)
        else:
            unit_sale_year = 999 # Never sold
            
        growth_rate = (params['rent_growth'] / 100) # Could be unit specific, here using global for simplicity override
        price_growth_rate = (params['inflation'] / 100)
        
        for y in years:
            if y == 0: continue
            
            # RENT CALCULATION
            if start_year <= y <= unit_sale_year:
                # Indexation formula: Base * (1+g)^(y - start)
                # Note: Usually indexation starts from Y1. Let's assume Base is Y1 value.
                current_rent = surface * base_rent * ((1 + growth_rate)**(y - start_year))
                # Apply Vacancy/Occupancy from global params
                occupancy = params['occupancy_rate'] / 100
                # If sold this year, maybe partial rent? Keeping simple: Rent collected if sold at end of year.
                if unit['Mode'] == 'Rent' or unit['Mode'] == 'Mixed':
                    rent_flow[y] += current_rent * occupancy
            
            # SALE CALCULATION (Unit by Unit sales)
            if y == unit_sale_year and unit['Mode'] != 'Rent': # Sale or Mixed
                sale_value = surface * base_price * ((1 + price_growth_rate)**(y - start_year)) # Growing price
                sale_flow[y] += sale_value

    # --- C. EXIT VALUATION (Terminal Value) ---
    # Calculate NOI for Year N+1 to determine Exit Value
    exit_year = int(params['holding_period'])
    
    # Re-calculate Total Rent in Year N+1 for Exit Valuation
    rent_n_plus_1 = 0
    for _, unit in df_units.iterrows():
        surface = unit['Surface (m²)']
        base_rent = unit['Rent (€/m²/mo)'] * 12
        start_year = int(unit['Start Year']) if pd.notna(unit['Start Year']) else 999
        # Assuming all remaining rental units are part of the exit sale
        if unit['Mode'] in ['Rent', 'Mixed'] and (str(unit['Sale Year']).lower() == 'exit' or pd.isna(unit['Sale Year'])):
             current_rent = surface * base_rent * ((1 + (params['rent_growth']/100))**(exit_year + 1 - start_year))
             rent_n_plus_1 += current_rent * (params['occupancy_rate'] / 100)

    opex_n_plus_1 = rent_n_plus_1 * (params['property_mgmt_fee']/100) + (gfa * params['opex_per_m2'] * ((1 + params['inflation']/100)**exit_year))
    noi_n_plus_1 = rent_n_plus_1 - opex_n_plus_1
    
    gross_exit_value = noi_n_plus_1 / (params['exit_yield'] / 100) if params['exit_yield'] > 0 else 0
    net_exit_value = gross_exit_value * (1 - params['transaction_fees_exit'] / 100)
    
    # Add Terminal Value to Sale Flow in Exit Year
    if exit_year in sale_flow:
        sale_flow[exit_year] += net_exit_value

    # --- D. DEBT & AMORTIZATION ---
    loan_schedule = calculate_loan_schedule(
        params['debt_amount'], 
        params['interest_rate']/100, 
        params['loan_term'], 
        params['grace_period']
    )

    # --- E. CASHFLOW WATERFALL ---
    cf_data = []
    
    cumulative_cf = 0
    
    for y in years:
        if y == 0:
            # Initial Investment Year
            row = {
                'Year': 0,
                'Rental Income': 0,
                'Sales Income': 0,
                'OPEX': 0,
                'NOI': 0,
                'CAPEX': -params['land_cost_input'], # Assuming land bought at Y0
                'Debt Drawdown': params['debt_amount'],
                'Debt Service': 0,
                'Upfront Fees': -(params['upfront_fees_amount'] + (params['debt_amount'] * params['arrangement_fee_pct']/100)),
                'Tax': 0,
                'Net Cash Flow': 0 # Calculated below
            }
            # Adjust CAPEX Y0 if needed, usually construction starts Y1
        else:
            # Operating Phase
            rental_income = rent_flow[y]
            sales_income = sale_flow[y]
            
            # OPEX Calculation: Per m2 + % of Revenue
            opex_fixed = gfa * params['opex_per_m2'] * ((1 + params['inflation']/100)**(y-1))
            opex_var = rental_income * (params['property_mgmt_fee'] / 100)
            total_opex = opex_fixed + opex_var
            
            noi = rental_income + sales_income - total_opex
            
            # Debt
            debt_data = loan_schedule.get(y, {'payment': 0, 'interest': 0, 'principal': 0, 'balance_end': 0})
            debt_service = debt_data['payment']
            interest = debt_data['interest']
            
            # Bullet Repayment check
            bullet = 0
            prepayment_penality = 0
            if y == exit_year:
                remaining_principal = debt_data['balance_end']
                bullet = remaining_principal
                prepayment_penality = bullet * (params['prepayment_fee'] / 100)
                # Add to debt service
                debt_service += (bullet + prepayment_penality)
            
            # Tax Calculation
            depreciation = 0 # Simplified, usually strictly defined in Accounting
            # EBT (Earnings Before Tax)
            ebt = noi - interest - depreciation # Simplified
            
            tax = 0
            if ebt > 0:
                # Tax Holiday Logic
                if y > params['tax_holiday']:
                    tax = ebt * (params['corporate_tax_rate'] / 100)
            
            row = {
                'Year': y,
                'Rental Income': rental_income,
                'Sales Income': sales_income,
                'OPEX': -total_opex,
                'NOI': noi,
                'CAPEX': -capex_flow[y],
                'Debt Drawdown': 0,
                'Debt Service': -debt_service,
                'Upfront Fees': 0,
                'Tax': -tax,
            }
            
        # Net Cash Flow Calculation
        net_cf = (row['Rental Income'] + row['Sales Income'] + row['OPEX'] + 
                  row['CAPEX'] + row['Debt Drawdown'] + row['Debt Service'] + 
                  row['Upfront Fees'] + row['Tax'])
        
        row['Net Cash Flow'] = net_cf
        cf_data.append(row)

    df_cf = pd.DataFrame(cf_data).set_index('Year')
    
    # --- F. KPIs ---
    flows = df_cf['Net Cash Flow'].values
    try:
        irr = npf.irr(flows)
    except:
        irr = 0.0
        
    equity_invested = -df_cf.loc[df_cf['Net Cash Flow'] < 0, 'Net Cash Flow'].sum()
    total_returned = df_cf.loc[df_cf['Net Cash Flow'] > 0, 'Net Cash Flow'].sum()
    
    equity_multiple = total_returned / equity_invested if equity_invested > 0 else 0
    
    try:
        npv = npf.npv(params['discount_rate']/100, flows)
    except:
        npv = 0

    kpis = {
        'IRR': irr * 100,
        'Equity Multiple': equity_multiple,
        'NPV': npv,
        'Total Equity Needed': equity_invested,
        'Exit Value (Net)': net_exit_value
    }
    
    return df_cf, kpis, gfa, gla

# --- 2. SIDEBAR INPUTS ---

st.sidebar.title("🔧 Parameters")

with st.sidebar.expander("General", expanded=True):
    p_land_area = st.number_input("Land Area (m²)", value=7454)
    p_land_cost = st.number_input("Land Acquisition Cost (€)", value=5000000, step=100000)
    p_far = st.number_input("FAR (Floor Area Ratio)", value=3.45)
    p_efficiency = st.number_input("Building Efficiency (%)", value=80.0)
    p_tax_rate = st.number_input("Corporate Tax Rate (%)", value=30.0)
    p_tax_holiday = st.number_input("Tax Holiday (Years)", value=3)
    p_discount_rate = st.number_input("Discount Rate (%)", value=10.0)

with st.sidebar.expander("Construction", expanded=False):
    st.caption("Costs per m² of GFA")
    p_c_structure = st.number_input("Structure (€/m²)", value=800)
    p_c_finishing = st.number_input("Finishing (€/m²)", value=400)
    p_c_utilities = st.number_input("Utilities/VRD (€/m²)", value=200)
    st.markdown("---")
    p_f_permits = st.number_input("Fixed Permit Fees (€)", value=20000)
    p_f_arch = st.number_input("Architect Fees (% Hard)", value=3.0)
    p_f_dev = st.number_input("Dev Fees (% Hard)", value=2.0)
    p_f_mark = st.number_input("Marketing Fees (% Hard)", value=1.0)
    p_contingency = st.number_input("Contingency (%)", value=5.0)
    st.markdown("---")
    st.caption("S-Curve Distribution")
    col_s1, col_s2, col_s3 = st.columns(3)
    p_s1 = col_s1.number_input("Y1 %", value=40.0)
    p_s2 = col_s2.number_input("Y2 %", value=40.0)
    p_s3 = col_s3.number_input("Y3 %", value=20.0)

with st.sidebar.expander("Financing", expanded=False):
    p_debt_amount = st.number_input("Debt Amount (€)", value=14500000, step=100000, help="Manual override. Check Financing sheet logic.")
    p_rate = st.number_input("Interest Rate (%)", value=4.5)
    p_term = st.number_input("Loan Term (Years)", value=20)
    p_grace = st.number_input("Grace Period (Years)", value=2)
    p_fee_arr = st.number_input("Arrangement Fee (% Debt)", value=1.0)
    p_fee_upfront = st.number_input("Upfront Fin. Fees (€)", value=150000)
    p_fee_prepay = st.number_input("Prepayment Fee (%)", value=2.0)

with st.sidebar.expander("Operation & Exit", expanded=False):
    p_inflation = st.number_input("Inflation / Price Growth (%)", value=4.0)
    p_rent_growth = st.number_input("Rent Growth (%)", value=2.5)
    p_opex_m2 = st.number_input("OPEX (€/m²/yr)", value=28.0)
    p_pm_fee = st.number_input("Property Mgmt Fee (% Rev)", value=4.5)
    p_occupancy = st.number_input("Occupancy Rate (%)", value=90.0)
    st.markdown("---")
    p_hold_period = st.number_input("Holding Period (Years)", value=20)
    p_exit_yield = st.number_input("Exit Yield (%)", value=8.25)
    p_exit_fees = st.number_input("Exit Transac. Fees (%)", value=5.0)

# Packing parameters
params = {
    'land_area': p_land_area, 'land_cost_input': p_land_cost, 'far': p_far, 'building_efficiency': p_efficiency,
    'corporate_tax_rate': p_tax_rate, 'tax_holiday': p_tax_holiday, 'discount_rate': p_discount_rate,
    'cost_structure': p_c_structure, 'cost_finishing': p_c_finishing, 'cost_utilities': p_c_utilities,
    'fee_permits': p_f_permits, 'fee_architect': p_f_arch, 'fee_development': p_f_dev, 'fee_marketing': p_f_mark,
    'contingency': p_contingency, 's_curve_y1': p_s1, 's_curve_y2': p_s2, 's_curve_y3': p_s3,
    'debt_amount': p_debt_amount, 'interest_rate': p_rate, 'loan_term': p_term, 'grace_period': p_grace,
    'arrangement_fee_pct': p_fee_arr, 'upfront_fees_amount': p_fee_upfront, 'prepayment_fee': p_fee_prepay,
    'inflation': p_inflation, 'rent_growth': p_rent_growth, 'opex_per_m2': p_opex_m2, 'property_mgmt_fee': p_pm_fee,
    'occupancy_rate': p_occupancy, 'holding_period': p_hold_period, 'exit_yield': p_exit_yield, 'transaction_fees_exit': p_exit_fees
}

# --- 3. MAIN PAGE LAYOUT ---

st.markdown('<div class="main-header">🏢 Real Estate AI Modeler</div>', unsafe_allow_html=True)
st.markdown("Interactive reconstruction of the Business Plan logic.")

tab_units, tab_cashflow, tab_kpis = st.tabs(["🏙️ Units & Definition", "💰 Cashflow Table", "📊 KPIs & Charts"])

# --- TAB 1: UNITS ---
with tab_units:
    st.markdown('<div class="sub-header">Unit Definition</div>', unsafe_allow_html=True)
    st.write("Define the asset mix here. Start Year indicates when rent collection begins. Sale Year = 'Exit' means sale at end of holding period.")
    
    # Default Data inspired by the TXT file
    default_data = [
        {"Type": "Office-L", "Mode": "Rent", "Surface (m²)": 3000, "Rent (€/m²/mo)": 20, "Price (€/m²)": 0, "Start Year": 3, "Sale Year": "Exit"},
        {"Type": "Office-M", "Mode": "Rent", "Surface (m²)": 3000, "Rent (€/m²/mo)": 20, "Price (€/m²)": 0, "Start Year": 3, "Sale Year": "Exit"},
        {"Type": "T2-Patrimonial", "Mode": "Mixed", "Surface (m²)": 70, "Rent (€/m²/mo)": 16, "Price (€/m²)": 2300, "Start Year": 4, "Sale Year": "Exit"},
        {"Type": "T3-VEFA", "Mode": "Sale", "Surface (m²)": 110, "Rent (€/m²/mo)": 0, "Price (€/m²)": 2300, "Start Year": 1, "Sale Year": 1},
        {"Type": "Retail-Grd", "Mode": "Rent", "Surface (m²)": 500, "Rent (€/m²/mo)": 35, "Price (€/m²)": 0, "Start Year": 3, "Sale Year": "Exit"},
    ]
    
    df_units_input = pd.DataFrame(default_data)
    
    column_config = {
        "Type": st.column_config.TextColumn("Unit Type", width="medium"),
        "Mode": st.column_config.SelectboxColumn("Mode", options=["Rent", "Sale", "Mixed"], width="small"),
        "Surface (m²)": st.column_config.NumberColumn("Surface", min_value=0, format="%d m²"),
        "Rent (€/m²/mo)": st.column_config.NumberColumn("Rent/m²", min_value=0, format="€%.2f"),
        "Price (€/m²)": st.column_config.NumberColumn("Price/m²", min_value=0, format="€%d"),
        "Start Year": st.column_config.NumberColumn("Start Yr", min_value=0, max_value=30),
        # Sale Year is text to allow "Exit"
    }
    
    df_units = st.data_editor(df_units_input, column_config=column_config, num_rows="dynamic", use_container_width=True)
    
    # Run Calculations
    df_cf, kpis, gfa, gla = calculate_model(params, df_units)
    
    col_u1, col_u2, col_u3 = st.columns(3)
    col_u1.metric("Total GFA (Constructed)", f"{gfa:,.0f} m²")
    col_u2.metric("Total GLA (Leasable)", f"{gla:,.0f} m²")
    col_u3.metric("Efficiency Check", f"{(gla/gfa)*100:.1f}%")

# --- TAB 2: CASHFLOW ---
with tab_cashflow:
    st.markdown('<div class="sub-header">Annual Cashflow Statement</div>', unsafe_allow_html=True)
    
    # Formatting for display
    df_display = df_cf.copy()
    format_cols = df_display.columns
    
    st.dataframe(df_display.style.format("{:,.0f}"), height=500, use_container_width=True)
    
    st.download_button("Download Excel", df_display.to_csv().encode('utf-8'), "bp_cashflow.csv", "text/csv")

# --- TAB 3: KPIs & CHARTS ---
with tab_kpis:
    st.markdown('<div class="sub-header">Financial Performance</div>', unsafe_allow_html=True)
    
    # Top Metrics
    k1, k2, k3, k4 = st.columns(4)
    
    k1.markdown(f"""<div class="kpi-card"><h3>IRR (Levered)</h3><h2>{kpis['IRR']:.2f}%</h2></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="kpi-card"><h3>Equity Multiple</h3><h2>{kpis['Equity Multiple']:.2f}x</h2></div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class="kpi-card"><h3>NPV (@{p_discount_rate}%)</h3><h2>{kpis['NPV']/1e6:,.2f}M€</h2></div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class="kpi-card"><h3>Peak Equity</h3><h2>{kpis['Total Equity Needed']/1e6:,.2f}M€</h2></div>""", unsafe_allow_html=True)
    
    st.divider()
    
    # Charts
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader("Cash Flow Profile")
        chart_data = df_cf[['NOI', 'Debt Service', 'Net Cash Flow']]
        st.bar_chart(chart_data)
        
    with c2:
        st.subheader("Sources & Uses (Approx)")
        # Simple pie chart logic
        debt = params['debt_amount']
        equity = kpis['Total Equity Needed']
        source_data = pd.DataFrame({
            'Source': ['Debt', 'Equity'],
            'Amount': [debt, equity]
        }).set_index('Source')
        st.dataframe(source_data.style.format("€{:,.0f}"))
