
# app.py
import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf

# ----------------------------------------------------------------------
# 1. DEFAULT PARAMETERS (from logique_bp_immo.txt)
# ----------------------------------------------------------------------


def get_default_params():
    """
    All global parameters reconstructed from the Excel logic.
    Values are the defaults you had in the BP.
    """
    params = {
        "general": {
            "corp_tax_rate": 30.0 / 100.0,  # General!B12
            "tax_holiday_years": 3,         # General!B13
            "discount_rate": 10.0 / 100.0,  # General!B14
            # Building efficiency is logically in General but used by Construction
            "building_efficiency_pct": 80.0,  # General!B8
        },
        "operation": {
            "default_occupancy": 90.0 / 100.0,     # Operation!B4
            "opex_per_m2_year": 28.0,             # Operation!B5
            "pm_pct_of_revenue": 4.5 / 100.0,     # Operation!B6
            "inflation": 4.0 / 100.0,             # Operation!B7 (used for opex / selling price)
            "rent_growth": 2.5 / 100.0,           # Operation!B8
            # global default if Asset Value Growth left blank
            "value_growth": 4.0 / 100.0,          # use same as Exit NOI growth (Operation!B8) as reasonable default
        },
        "exit": {
            "holding_period": 20,            # Exit!B4
            "exit_yield": 8.25 / 100.0,      # Exit!B5
            "transaction_fees_pct": 5.0 / 100.0,  # Exit!B6
            # Exit corporate tax on sale (not explicitly used in CF row but kept)
            "exit_corp_tax_rate": 3.0 / 100.0,    # Exit!B10
        },
        "construction": {
            "structure_cost_per_m2": 800.0,       # Construction!B4
            "finishing_cost_per_m2": 400.0,       # Construction!B5
            "utilities_cost_per_m2": 200.0,       # Construction!B6
            "permit_fees_fixed": 20000.0,         # Construction!B7
            "architect_fees_pct_hard": 3.0,       # Construction!B8
            "development_fees_pct_hard": 2.0,     # Construction!B9
            "marketing_fees_pct_hard": 1.0,       # Construction!B10
            "contingency_pct_subtotal": 5.0,      # Construction!B11
            "duration_months": 24,                # Construction!B12
            "s_curve": [40.0, 40.0, 20.0],        # Construction!B13:B15
        },
        "financing": {
            "debt_amount": 14504578.56,           # Financing!B5
            "interest_rate": 4.5 / 100.0,         # Financing!B6
            "loan_term_years": 20,                # Financing!B7
            "grace_period_months": 24,            # Financing!B8
            "arrangement_fees_pct": 1.0 / 100.0,  # Financing!B9
            "upfront_fees": 150000.0,             # Financing!B10
            "prepayment_fee_pct": 2.0 / 100.0,    # Financing!B16
        },
        "amenities": {
            "amenities_capex": 0.0,               # Construction!B49 (Padel etc. – simplified)
            "amenities_net_annual_impact": -3000.0,  # Construction!B50 (Padel OPEX=3000)
        },
    }
    return params


# ----------------------------------------------------------------------
# 2. DEFAULT UNITS TABLE (from Units sheet – simplified subset)
# ----------------------------------------------------------------------


def get_default_units_df():
    """
    Rebuilds a minimal but realistic Units table from logique_bp_immo.txt.
    The user can extend / edit freely via st.data_editor.
    """
    data = [
        # Offices
        {
            "Code": "OF-L",
            "AssetClass": "office",
            "Mode": "rent",
            "Surface (GLA m²)": 3000.0,
            "Rent €/m²/mo": 20.0,
            "Price €/m²": 0.0,
            "Occ %": 90.0,
            "Start Year": 3,
            "Sale Year": "",
            "Rent growth %": 5.0,
            "Asset Value Growth (%/yr)": 4.5,
            "Phase": "P1",
            "Notes": "Large Office floorplates",
            "Parking per unit": np.nan,
            "Parking ratio (per 100 m²)": 2.5,
            "UNIT TYPE": "Bureaux",
        },
        {
            "Code": "OF-M",
            "AssetClass": "office",
            "Mode": "rent",
            "Surface (GLA m²)": 3000.0,
            "Rent €/m²/mo": 20.0,
            "Price €/m²": 0.0,
            "Occ %": 90.0,
            "Start Year": 3,
            "Sale Year": "",
            "Rent growth %": 5.0,
            "Asset Value Growth (%/yr)": 4.5,
            "Phase": "P1",
            "Notes": "Medium Office floorplates",
            "Parking per unit": np.nan,
            "Parking ratio (per 100 m²)": 2.5,
            "UNIT TYPE": "Bureaux",
        },
        {
            "Code": "OF-S",
            "AssetClass": "office",
            "Mode": "rent",
            "Surface (GLA m²)": 2640.0,
            "Rent €/m²/mo": 20.0,
            "Price €/m²": 0.0,
            "Occ %": 90.0,
            "Start Year": 3,
            "Sale Year": "",
            "Rent growth %": 5.0,
            "Asset Value Growth (%/yr)": 4.5,
            "Phase": "P1",
            "Notes": "Small Office floorplates",
            "Parking per unit": np.nan,
            "Parking ratio (per 100 m²)": 2.5,
            "UNIT TYPE": "Bureaux",
        },
        # Example residential T3 VPAT (just to have resi in the model)
        {
            "Code": "T3-VPAT",
            "AssetClass": "residential",
            "Mode": "rent",
            "Surface (GLA m²)": 110.0,
            "Rent €/m²/mo": 16.0,
            "Price €/m²": 2300.0,
            "Occ %": 95.0,
            "Start Year": 3,
            "Sale Year": "",
            "Rent growth %": 4.0,
            "Asset Value Growth (%/yr)": 4.0,
            "Phase": "P1",
            "Notes": "T3 VPAT",
            "Parking per unit": 2.0,
            "Parking ratio (per 100 m²)": np.nan,
            "UNIT TYPE": "T3",
        },
        # Example residential T3 VEFA – sold in year 5
        {
            "Code": "T3-VEFA",
            "AssetClass": "residential",
            "Mode": "sell",
            "Surface (GLA m²)": 110.0,
            "Rent €/m²/mo": 0.0,
            "Price €/m²": 2300.0,
            "Occ %": 0.0,
            "Start Year": 0,
            "Sale Year": 5,
            "Rent growth %": 0.0,
            "Asset Value Growth (%/yr)": 4.0,
            "Phase": "P1",
            "Notes": "T3 VEFA sold in year 5",
            "Parking per unit": 2.0,
            "Parking ratio (per 100 m²)": np.nan,
            "UNIT TYPE": "T3",
        },
    ]

    df = pd.DataFrame(data)
    return df


# ----------------------------------------------------------------------
# 3. LOAN SCHEDULE (Amortization sheet – simplified but faithful)
# ----------------------------------------------------------------------


def calculate_loan_schedule(debt_amount, annual_rate, term_years, grace_years, max_year):
    """
    Reproduces the core logic of the Amortization sheet:

    - Constant amortizing payment after grace period
    - Interest-only during grace (no principal)
    - Schedule built for full term, then truncated to project horizon.
    - Returns a DataFrame indexed by "Year" with:
      Opening, Payment, Interest, Principal, Closing
    """

    years = np.arange(1, term_years + 1)

    # Payment only on amortizing period (term_years - grace_years)
    effective_amort_years = max(term_years - grace_years, 1)
    annuity_payment = float(npf.pmt(annual_rate, effective_amort_years, -debt_amount))

    opening = []
    payment = []
    interest = []
    principal = []
    closing = []

    outstanding = debt_amount

    for y in years:
        if outstanding <= 1e-8:
            # Loan fully repaid
            opening.append(0.0)
            payment.append(0.0)
            interest.append(0.0)
            principal.append(0.0)
            closing.append(0.0)
            continue

        opening.append(outstanding)
        if y <= grace_years:
            # Interest-only period
            int_y = outstanding * annual_rate
            pay_y = int_y
            princ_y = 0.0
        else:
            pay_y = annuity_payment
            int_y = outstanding * annual_rate
            princ_y = max(pay_y - int_y, 0.0)
            # avoid tiny numeric noise
            if princ_y > outstanding:
                princ_y = outstanding
                pay_y = int_y + princ_y

        new_outstanding = max(outstanding - princ_y, 0.0)

        payment.append(pay_y)
        interest.append(int_y)
        principal.append(princ_y)
        closing.append(new_outstanding)
        outstanding = new_outstanding

    sched = pd.DataFrame(
        {
            "Year": years,
            "Opening": opening,
            "Payment": payment,
            "Interest": interest,
            "Principal": principal,
            "Closing": closing,
        }
    ).set_index("Year")

    # For consistency with Cashflow: add Year 0 with zeros, Opening=0, Closing=debt_amount
    sched0 = pd.DataFrame(
        {
            "Opening": [0.0],
            "Payment": [0.0],
            "Interest": [0.0],
            "Principal": [0.0],
            "Closing": [debt_amount],
        },
        index=pd.Index([0], name="Year"),
    )
    sched = pd.concat([sched0, sched])

    # Truncate to project horizon (max_year) if needed
    sched = sched.loc[sched.index <= max_year]
    return sched


# ----------------------------------------------------------------------
# 4. MAIN CALCULATION ENGINE (Cashflow sheet reconstruction)
# ----------------------------------------------------------------------


def calculate_flows(df_units_raw, params):
    """
    Core engine reproducing the logic of:
    - RentSchedule
    - SaleSchedule
    - Construction & CAPEX_Summary
    - Amortization
    - Cashflow
    Returns:
    - cashflow_df (DataFrame)
    - kpis (dict)
    """

    # -----------------------------
    # Unpack params
    # -----------------------------
    general = params["general"]
    op = params["operation"]
    exit_p = params["exit"]
    cons = params["construction"]
    fin = params["financing"]
    amenities = params["amenities"]

    holding_period = int(exit_p["holding_period"])
    years = np.arange(0, holding_period + 1)

    # -----------------------------------
    # Clean / normalize Units DataFrame
    # -----------------------------------
    df_units = df_units_raw.copy()

    # Ensure required columns exist
    required_cols = [
        "Code",
        "AssetClass",
        "Mode",
        "Surface (GLA m²)",
        "Rent €/m²/mo",
        "Price €/m²",
        "Occ %",
        "Start Year",
        "Sale Year",
        "Rent growth %",
        "Asset Value Growth (%/yr)",
        "Phase",
        "Notes",
        "Parking per unit",
        "Parking ratio (per 100 m²)",
        "UNIT TYPE",
    ]
    for c in required_cols:
        if c not in df_units.columns:
            df_units[c] = np.nan

    # Fill defaults
    df_units["Occ %"] = df_units["Occ %"].fillna(op["default_occupancy"] * 100.0)
    df_units["Rent growth %"] = df_units["Rent growth %"].fillna(op["rent_growth"] * 100.0)
    df_units["Asset Value Growth (%/yr)"] = df_units["Asset Value Growth (%/yr)"].fillna(
        op["value_growth"] * 100.0
    )

    # Convert numeric columns safely
    num_cols = [
        "Surface (GLA m²)",
        "Rent €/m²/mo",
        "Price €/m²",
        "Occ %",
        "Start Year",
        "Sale Year",
        "Rent growth %",
        "Asset Value Growth (%/yr)",
    ]
    for c in num_cols:
        df_units[c] = pd.to_numeric(df_units[c], errors="coerce")

    # -----------------------------
    # RentSchedule equivalent
    # -----------------------------
    rental_income = np.zeros_like(years, dtype=float)
    m2_rented = np.zeros_like(years, dtype=float)

    for _, row in df_units.iterrows():
        asset_class = str(row["AssetClass"]).strip().lower()
        mode = str(row["Mode"]).strip().lower()

        gla = float(row["Surface (GLA m²)"]) if not np.isnan(row["Surface (GLA m²)"]) else 0.0
        rent_m2 = float(row["Rent €/m²/mo"]) if not np.isnan(row["Rent €/m²/mo"]) else 0.0
        occ = float(row["Occ %"]) / 100.0 if not np.isnan(row["Occ %"]) else op["default_occupancy"]
        start_year = int(row["Start Year"]) if not np.isnan(row["Start Year"]) else None
        sale_year_raw = row["Sale Year"]
        rent_growth = (
            float(row["Rent growth %"]) / 100.0 if not np.isnan(row["Rent growth %"]) else op["rent_growth"]
        )

        # Units with no rent don't contribute to rental income
        if gla <= 0 or rent_m2 <= 0:
            continue

        for iy, y in enumerate(years):
            # Start condition
            if start_year is None or y < start_year:
                continue

            # Sale condition (only apply to units with a numeric sale year)
            stop = False
            if not pd.isna(sale_year_raw):
                sale_year = int(sale_year_raw)
                # If sold in year = sale_year, we do NOT collect rent on that year anymore
                if y >= sale_year:
                    stop = True
            # If "Sale Year" is text (e.g. "Exit"), treat as not sold by unit schedule (sold via Exit sheet)
            # -> in that case, we never stop
            if stop:
                continue

            # Only rented if Mode is not "sell"
            if mode == "sell":
                continue

            year_index = int(y)  # matches exponent in RentSchedule!K$2 etc.
            annual_rent = gla * rent_m2 * 12.0 * occ * (1.0 + rent_growth) ** year_index
            rental_income[iy] += annual_rent
            # M² rented used for OPEX
            m2_rented[iy] += gla * occ

    # -----------------------------
    # SaleSchedule equivalent
    # -----------------------------
    sales_income = np.zeros_like(years, dtype=float)

    for _, row in df_units.iterrows():
        asset_class = str(row["AssetClass"]).strip().lower()
        gla = float(row["Surface (GLA m²)"]) if not np.isnan(row["Surface (GLA m²)"]) else 0.0
        price_m2 = float(row["Price €/m²"]) if not np.isnan(row["Price €/m²"]) else 0.0
        val_growth = (
            float(row["Asset Value Growth (%/yr)"]) / 100.0
            if not np.isnan(row["Asset Value Growth (%/yr)"])
            else op["value_growth"]
        )

        # Ignore units with no sale value
        if gla <= 0 or price_m2 <= 0:
            continue

        sale_year_raw = row["Sale Year"]

        # If sale year is text "Exit" or blank -> handled via Exit sheet logic (NOI * yield)
        if isinstance(sale_year_raw, str) and sale_year_raw.strip().lower() == "exit":
            continue

        if pd.isna(sale_year_raw):
            continue

        sale_year = int(sale_year_raw)
        if sale_year < 0 or sale_year > holding_period:
            continue

        year_index = sale_year
        sale_val = gla * price_m2 * (1.0 + val_growth) ** year_index
        sales_income[years == sale_year] += sale_val

    # -----------------------------
    # Construction & CAPEX Summary
    # -----------------------------
    # GFA from units: Construction!D18 = SUM(Units!E)*(1+(100-B8)/100)
    building_eff_pct = general["building_efficiency_pct"] / 100.0  # e.g. 0.80
    total_gla = df_units["Surface (GLA m²)"].fillna(0.0).sum()
    gfa_multiplier = 1.0 + (1.0 - building_eff_pct)  # (1 + (100-80)/100) = 1.2 for 80%
    gfa = total_gla * gfa_multiplier

    # Hard cost per m²: B4 + B5 + B6
    hard_cost_per_m2 = (
        cons["structure_cost_per_m2"] + cons["finishing_cost_per_m2"] + cons["utilities_cost_per_m2"]
    )
    hard_costs_total = gfa * hard_cost_per_m2

    # Soft fees = (B8+B9+B10)% of hard cost
    soft_fees_pct_total = (
        cons["architect_fees_pct_hard"]
        + cons["development_fees_pct_hard"]
        + cons["marketing_fees_pct_hard"]
    ) / 100.0
    soft_fees_total = soft_fees_pct_total * hard_costs_total

    # Subtotal before contingency = hard + soft + permit
    subtotal_before_contingency = hard_costs_total + soft_fees_total + cons["permit_fees_fixed"]

    # Contingency
    contingency = cons["contingency_pct_subtotal"] / 100.0 * subtotal_before_contingency

    # Total pre-financing cost (Construction D25)
    total_pre_financing = subtotal_before_contingency + contingency

    # Add Parking & Amenities CAPEX (Construction D39 = D25 + D38 + B49)
    total_pre_financing += amenities["amenities_capex"]

    # Upfront fees total (Financing D13 = B10 + (B9/100)*B5)
    upfront_fees_total = fin["upfront_fees"] + fin["arrangement_fees_pct"] * fin["debt_amount"]

    # CAPEX_Summary B6 = pre-financing incl. parking & amenities + upfront fees
    total_capex = total_pre_financing + upfront_fees_total

    # -----------------------------
    # INVESTMENTS (CAPEX) by S-curve – Cashflow!C21:E21
    # -----------------------------
    investments = np.zeros_like(years, dtype=float)
    s_curve = cons["s_curve"]  # [Y1, Y2, Y3] in %
    for i, pct in enumerate(s_curve, start=1):
        if i <= holding_period:
            investments[years == i] = total_capex * (pct / 100.0)

    # -----------------------------
    # Debt drawdowns – Cashflow!B27:V27
    # B27 = IF(B21=0,0,B21*(Financing!B5/CAPEX_Summary!B6))
    # -----------------------------
    debt_amount = fin["debt_amount"]
    if total_capex > 0:
        debt_ratio = debt_amount / total_capex
    else:
        debt_ratio = 0.0
    debt_drawdowns = investments * debt_ratio

    # -----------------------------
    # OPEX + Property management – Cashflow rows 12-14
    # -----------------------------
    pm_cost = op["pm_pct_of_revenue"] * rental_income  # property management only on rental income

    # Operating expenses excl PM = op.B5 * RentSchedule!M² rented
    # (here we ignore additional inflation term for simplicity, or we can add it)
    # In original: no explicit inflation applied in formula snippet; yearly opex/m² is already "today €".
    opex_excl_pm = op["opex_per_m2_year"] * m2_rented

    opex_total = pm_cost + opex_excl_pm

    # -----------------------------
    # NOI – Cashflow!row 16
    # -----------------------------
    total_revenues = rental_income + sales_income
    noi = total_revenues - opex_total

    # -----------------------------
    # Corporate tax & Tax holiday – Cashflow!rows 18-19
    # -----------------------------
    corp_tax = noi * general["corp_tax_rate"]

    tax_after_holiday = np.zeros_like(years, dtype=float)
    tax_holiday = int(general["tax_holiday_years"])
    for i, y in enumerate(years):
        if y <= tax_holiday:
            tax_after_holiday[i] = 0.0
        else:
            tax_after_holiday[i] = corp_tax[i]

    # -----------------------------
    # Exit Net Value – Exit sheet + Cashflow row 8
    # Exit!B15 = NOI at Exit (Year n) = NOIy(exit_year) ignoring PM subtleties
    # Exit!B16 = NOI at Exit (n+1) = B15*(1+Rent growth)
    # Exit!B17 = Gross Exit Value = B16 / ExitYield
    # Exit!B18 = Net Exit Value = B17*(1-TransactionFees)
    # Cashflow!B8:V8 = IF(Year=HoldingPeriod,Exit!B18,0)
    # -----------------------------
    exit_year = holding_period
    if exit_year <= holding_period:
        noi_at_exit = noi[years == exit_year][0]
    else:
        noi_at_exit = 0.0

    noi_at_exit_next = noi_at_exit * (1.0 + op["rent_growth"])
    if exit_p["exit_yield"] > 0:
        gross_exit_value = noi_at_exit_next / exit_p["exit_yield"]
    else:
        gross_exit_value = 0.0
    net_exit_value = gross_exit_value * (1.0 - exit_p["transaction_fees_pct"])

    exit_proceeds = np.zeros_like(years, dtype=float)
    exit_proceeds[years == exit_year] = net_exit_value

    # -----------------------------
    # UNLEVERED OPERATING CF (After Tax) – Cashflow row 23
    # B23 = NOI - TaxAfterHoliday - Investments + ExitProceeds
    # -----------------------------
    unlevered_cf = noi - tax_after_holiday - investments + exit_proceeds

    # -----------------------------
    # Loan schedule & Debt service – Amortization + Cashflow rows 28-30
    # -----------------------------
    grace_years = int(round(fin["grace_period_months"] / 12.0))
    loan_sched = calculate_loan_schedule(
        debt_amount=debt_amount,
        annual_rate=fin["interest_rate"],
        term_years=fin["loan_term_years"],
        grace_years=grace_years,
        max_year=holding_period,
    )

    # Interest CF row 28 = -XLOOKUP(Year, Amortization!Interest)
    interest_cf = np.zeros_like(years, dtype=float)
    principal_cf = np.zeros_like(years, dtype=float)
    bullet_cf = np.zeros_like(years, dtype=float)

    for i, y in enumerate(years):
        if y in loan_sched.index:
            interest_cf[i] = -loan_sched.loc[y, "Interest"]
            principal_cf[i] = -loan_sched.loc[y, "Principal"]
        else:
            interest_cf[i] = 0.0
            principal_cf[i] = 0.0

    # Bullet repayment at Exit: principal + remaining closing balance in exit year
    if exit_year in loan_sched.index:
        closing_exit = loan_sched.loc[exit_year, "Closing"]
        bullet_cf[years == exit_year] -= closing_exit  # negative cashflow at exit

    # Prepayment fee row 30 = -Closing_at_exit * PrepaymentFee%
    prepayment_fee_cf = np.zeros_like(years, dtype=float)
    if exit_year in loan_sched.index:
        closing_exit = loan_sched.loc[exit_year, "Closing"]
        prepayment_fee_cf[years == exit_year] -= closing_exit * fin["prepayment_fee_pct"]

    # -----------------------------
    # LEVERED CF BEFORE EQUITY – Cashflow row 32
    # B32 = B23+B27+B28+B29+B30
    # -----------------------------
    levered_cf_before_equity = (
        unlevered_cf + debt_drawdowns + interest_cf + principal_cf + bullet_cf + prepayment_fee_cf
    )

    # -----------------------------
    # Equity injection – Cashflow row 36
    # Financing!B4 = CAPEX_Summary!B6 - Financing!B5
    # -----------------------------
    equity_amount = total_capex - debt_amount
    equity_injection = np.zeros_like(years, dtype=float)
    equity_injection[0] = -equity_amount  # negative (cash out)

    # -----------------------------
    # Equity cash flow – Cashflow row 38
    # B38 = B32 + B36 (if not zero)
    # -----------------------------
    equity_cf = levered_cf_before_equity + equity_injection

    # -----------------------------
    # KPIs (Cashflow KPIs block)
    # -----------------------------
    # IRRs
    def safe_irr(cf):
        try:
            if np.allclose(cf, 0.0):
                return np.nan
            return float(npf.irr(cf))
        except Exception:
            return np.nan

    unlevered_irr = safe_irr(unlevered_cf)
    levered_irr = safe_irr(equity_cf)

    # Equity Multiple / Cash-on-Cash – Cashflow row 49
    # Equity multiple = SUM(positive eq CF up to exit) / ABS(SUM(negative eq CF up to exit))
    eq_cf_until_exit = equity_cf[(years >= 0) & (years <= exit_year)]
    pos = eq_cf_until_exit[eq_cf_until_exit > 0].sum()
    neg = eq_cf_until_exit[eq_cf_until_exit < 0].sum()
    equity_multiple = pos / abs(neg) if neg < 0 else np.nan

    # Net Margin – we approximate as (sum of unlevered CF over project) / total_capex
    net_margin = unlevered_cf.sum() / total_capex if total_capex > 0 else np.nan

    # NPV (unlevered)
    discount_rate = general["discount_rate"]
    npv_unlevered = float(npf.npv(discount_rate, unlevered_cf[1:]) + unlevered_cf[0])

    kpis = {
        "unlevered_irr": unlevered_irr,
        "levered_irr": levered_irr,
        "equity_multiple": equity_multiple,
        "net_margin": net_margin,
        "npv_unlevered": npv_unlevered,
        "equity_amount": equity_amount,
        "total_capex": total_capex,
        "debt_amount": debt_amount,
    }

    # -----------------------------
    # Build Cashflow DataFrame (for display)
    # -----------------------------
    cf_df = pd.DataFrame(
        {
            "Year": years,
            "Rental Income": rental_income,
            "Sales Income": sales_income,
            "Exit Proceeds": exit_proceeds,
            "Total Revenues": total_revenues,
            "Property Management": pm_cost,
            "Opex excl PM": opex_excl_pm,
            "OPEX": opex_total,
            "NOI": noi,
            "Corporate Tax": corp_tax,
            "Tax after Holiday": tax_after_holiday,
            "Investments (CAPEX)": investments,
            "Unlevered CF (after tax)": unlevered_cf,
            "Debt Drawdowns": debt_drawdowns,
            "Interest": interest_cf,
            "Principal (scheduled)": principal_cf,
            "Bullet Repayment": bullet_cf,
            "Prepayment Fee": prepayment_fee_cf,
            "Levered CF before Equity": levered_cf_before_equity,
            "Equity Injection": equity_injection,
            "Equity CF": equity_cf,
        }
    )

    cf_df["Cumulative Unlevered CF"] = cf_df["Unlevered CF (after tax)"].cumsum()
    cf_df["Cumulative Equity CF"] = cf_df["Equity CF"].cumsum()

    return cf_df, kpis


# ----------------------------------------------------------------------
# 5. STREAMLIT UI
# ----------------------------------------------------------------------


def main():
    st.set_page_config(page_title="Real Estate BP Model", layout="wide")

    st.title("Real Estate BP – Streamlit Model (Dar es Salaam)")

    # ------------------- SIDEBAR INPUTS -------------------
    st.sidebar.header("Global Parameters")

    # Load / init params in session_state
    if "params" not in st.session_state:
        st.session_state["params"] = get_default_params()
    params = st.session_state["params"]

    # GENERAL
    st.sidebar.subheader("General")
    general = params["general"]
    general["corp_tax_rate"] = (
        st.sidebar.number_input("Corporate Tax Rate (%)", 0.0, 100.0, general["corp_tax_rate"] * 100.0)
        / 100.0
    )
    general["tax_holiday_years"] = st.sidebar.number_input(
        "Tax Holiday (years)", 0, 50, int(general["tax_holiday_years"])
    )
    general["discount_rate"] = (
        st.sidebar.number_input("Discount Rate (%/yr)", 0.0, 100.0, general["discount_rate"] * 100.0)
        / 100.0
    )
    general["building_efficiency_pct"] = st.sidebar.number_input(
        "Building efficiency (%)", 1.0, 100.0, float(general["building_efficiency_pct"])
    )

    # CONSTRUCTION
    st.sidebar.subheader("Construction")
    cons = params["construction"]
    cons["structure_cost_per_m2"] = st.sidebar.number_input(
        "Structure cost (€/m²)", 0.0, 10000.0, cons["structure_cost_per_m2"]
    )
    cons["finishing_cost_per_m2"] = st.sidebar.number_input(
        "Finishing cost (€/m²)", 0.0, 10000.0, cons["finishing_cost_per_m2"]
    )
    cons["utilities_cost_per_m2"] = st.sidebar.number_input(
        "Utilities/VRD cost (€/m²)", 0.0, 10000.0, cons["utilities_cost_per_m2"]
    )
    cons["permit_fees_fixed"] = st.sidebar.number_input(
        "Permit fees (fixed, €)", 0.0, 1e8, cons["permit_fees_fixed"]
    )
    cons["contingency_pct_subtotal"] = st.sidebar.number_input(
        "Contingency (% of subtotal)", 0.0, 100.0, cons["contingency_pct_subtotal"]
    )
    cons["duration_months"] = st.sidebar.number_input(
        "Construction duration (months)", 0, 120, cons["duration_months"]
    )
    col_sc1, col_sc2, col_sc3 = st.sidebar.columns(3)
    cons["s_curve"][0] = col_sc1.number_input("S-curve Y1 (%)", 0.0, 100.0, cons["s_curve"][0])
    cons["s_curve"][1] = col_sc2.number_input("S-curve Y2 (%)", 0.0, 100.0, cons["s_curve"][1])
    cons["s_curve"][2] = col_sc3.number_input("S-curve Y3 (%)", 0.0, 100.0, cons["s_curve"][2])

    # FINANCING
    st.sidebar.subheader("Financing")
    fin = params["financing"]
    fin["debt_amount"] = st.sidebar.number_input(
        "Debt amount (€)", 0.0, 1e9, fin["debt_amount"], step=100000.0
    )
    fin["interest_rate"] = (
        st.sidebar.number_input("Interest rate (%/yr)", 0.0, 100.0, fin["interest_rate"] * 100.0)
        / 100.0
    )
    fin["loan_term_years"] = st.sidebar.number_input(
        "Loan term (years)", 1, 100, fin["loan_term_years"]
    )
    fin["grace_period_months"] = st.sidebar.number_input(
        "Grace period (months)", 0, 120, fin["grace_period_months"]
    )
    fin["arrangement_fees_pct"] = (
        st.sidebar.number_input("Arrangement fees (% of debt)", 0.0, 100.0, fin["arrangement_fees_pct"] * 100.0)
        / 100.0
    )
    fin["upfront_fees"] = st.sidebar.number_input(
        "Upfront financial fees (€)", 0.0, 1e8, fin["upfront_fees"]
    )
    fin["prepayment_fee_pct"] = (
        st.sidebar.number_input("Prepayment fee (% of outstanding)", 0.0, 100.0, fin["prepayment_fee_pct"] * 100.0)
        / 100.0
    )

    # EXIT
    st.sidebar.subheader("Exit")
    exit_p = params["exit"]
    exit_p["holding_period"] = st.sidebar.number_input(
        "Holding period (years)", 1, 100, exit_p["holding_period"]
    )
    exit_p["exit_yield"] = (
        st.sidebar.number_input("Exit Yield (%)", 0.01, 100.0, exit_p["exit_yield"] * 100.0) / 100.0
    )
    exit_p["transaction_fees_pct"] = (
        st.sidebar.number_input("Transaction fees on sale (%)", 0.0, 100.0, exit_p["transaction_fees_pct"] * 100.0)
        / 100.0
    )

    # OPERATION
    st.sidebar.subheader("Operations")
    op = params["operation"]
    op["default_occupancy"] = (
        st.sidebar.number_input("Default occupancy (%)", 0.0, 100.0, op["default_occupancy"] * 100.0) / 100.0
    )
    op["opex_per_m2_year"] = st.sidebar.number_input(
        "Operating expenses (€/m²/yr)", 0.0, 1000.0, op["opex_per_m2_year"]
    )
    op["pm_pct_of_revenue"] = (
        st.sidebar.number_input("Property management (% of rental revenue)", 0.0, 100.0, op["pm_pct_of_revenue"] * 100.0)
        / 100.0
    )
    op["inflation"] = (
        st.sidebar.number_input("Inflation (%/yr)", 0.0, 100.0, op["inflation"] * 100.0) / 100.0
    )
    op["rent_growth"] = (
        st.sidebar.number_input("Rent growth (%/yr)", 0.0, 100.0, op["rent_growth"] * 100.0) / 100.0
    )
    op["value_growth"] = (
        st.sidebar.number_input("Asset value growth default (%/yr)", 0.0, 100.0, op["value_growth"] * 100.0) / 100.0
    )

    # Save back
    st.session_state["params"] = params

    # ------------------- MAIN LAYOUT -------------------
    tab_units, tab_cashflow, tab_kpis = st.tabs(
        ["Units (core input)", "Cashflow", "KPIs & Charts"]
    )

    # UNITS TAB
    with tab_units:
        st.subheader("Units — Granular listing (Residential / Office / etc.)")

        if "df_units" not in st.session_state:
            st.session_state["df_units"] = get_default_units_df()

        df_units = st.session_state["df_units"]

        edited_df = st.data_editor(
            df_units,
            use_container_width=True,
            num_rows="dynamic",
            key="units_editor",
        )

        # Update session state
        st.session_state["df_units"] = edited_df

        st.info(
            "Modify unit surfaces, rents, sale years, etc. "
            "Any change will update the entire cashflow once you switch tabs."
        )

    # CALCULATION (re-run every time because of Streamlit reactivity)
    df_units_current = st.session_state["df_units"]
    cf_df, kpis = calculate_flows(df_units_current, st.session_state["params"])

    # CASHFLOW TAB
    with tab_cashflow:
        st.subheader("Cashflow Reconstruction (Annual)")

        # Format some columns a bit
        display_df = cf_df.copy()
        money_cols = [c for c in display_df.columns if c != "Year"]
        display_df[money_cols] = display_df[money_cols].round(0)

        st.dataframe(display_df, use_container_width=True)

    # KPIs & CHARTS TAB
    with tab_kpis:
        st.subheader("Key Performance Indicators")

        col1, col2, col3 = st.columns(3)
        col1.metric("Unlevered IRR", f"{kpis['unlevered_irr']*100:.2f} %" if not np.isnan(kpis['unlevered_irr']) else "n/a")
        col2.metric("Levered IRR", f"{kpis['levered_irr']*100:.2f} %" if not np.isnan(kpis['levered_irr']) else "n/a")
        col3.metric("Equity Multiple (Cash-on-Cash)", f"{kpis['equity_multiple']:.2f}" if not np.isnan(kpis['equity_multiple']) else "n/a")

        col4, col5, col6 = st.columns(3)
        col4.metric("Net Margin (Unlevered CF / Total CAPEX)", f"{kpis['net_margin']*100:.2f} %" if not np.isnan(kpis['net_margin']) else "n/a")
        col5.metric("Unlevered NPV", f"{kpis['npv_unlevered']:,.0f} €")
        col6.metric("Equity Amount", f"{kpis['equity_amount']:,.0f} €")

        st.markdown("---")
        st.subheader("Cashflow Profile")

        exit_year = int(st.session_state["params"]["exit"]["holding_period"])
        cf_plot = cf_df[cf_df["Year"] <= exit_year].copy()

        plot_df = pd.DataFrame(
            {
                "Year": cf_plot["Year"],
                "Operating CF (Unlevered)": cf_plot["Unlevered CF (after tax)"],
                "Debt Service (Interest+Principal+Fees)": cf_plot["Interest"]
                + cf_plot["Principal (scheduled)"]
                + cf_plot["Bullet Repayment"]
                + cf_plot["Prepayment Fee"],
                "Net CF to Equity": cf_plot["Equity CF"],
            }
        ).set_index("Year")

        st.bar_chart(plot_df)


if __name__ == "__main__":
    main()
```

