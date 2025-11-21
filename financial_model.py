import numpy as np
import numpy_financial as npf
import pandas as pd

class General:
    def __init__(self, inputs):
        self.land_area = inputs.get('land_area', 7454)
        self.parcels = inputs.get('parcels', 3)
        self.construction_rate = inputs.get('construction_rate', 60.0) / 100.0
        self.far = inputs.get('far', 3.45)
        self.building_efficiency = inputs.get('building_efficiency', 80.0) / 100.0
        self.country = inputs.get('country', "Tanzanie")
        self.city = inputs.get('city', "Dar es Salaam")
        self.fx_eur_local = inputs.get('fx_eur_local', 2853.1)
        self.corporate_tax_rate = inputs.get('corporate_tax_rate', 30.0) / 100.0
        self.tax_holiday = inputs.get('tax_holiday', 3)
        self.discount_rate = inputs.get('discount_rate', 10.0) / 100.0
        self.buildable_footprint = self.land_area * self.construction_rate
        self.gfa = self.buildable_footprint * self.far
        self.gla = self.gfa * self.building_efficiency

class Parking:
    def __init__(self, inputs, df_units: pd.DataFrame):
        self.cost_per_space = inputs.get('cost_per_space', 18754)
        self.total_spaces = 0
        if not df_units.empty:
            for _, row in df_units.iterrows():
                fixed = pd.to_numeric(row.get('Parking per unit', 0), errors='coerce')
                ratio = pd.to_numeric(row.get('Parking ratio', 0), errors='coerce')
                surface = pd.to_numeric(row.get('Surface (m²)', 0), errors='coerce')
                spaces = (fixed if not pd.isna(fixed) else 0) + ((surface / 100) * (ratio if not pd.isna(ratio) else 0))
                self.total_spaces += spaces
        self.total_capex = self.total_spaces * self.cost_per_space

class Construction:
    def __init__(self, inputs, general: General, df_units: pd.DataFrame):
        self.structure_cost = inputs.get('structure_cost', 800)
        self.finishing_cost = inputs.get('finishing_cost', 400)
        self.utilities_cost = inputs.get('utilities_cost', 200)
        self.permit_fees = inputs.get('permit_fees', 20000)
        self.architect_fees_pct = inputs.get('architect_fees_pct', 3.0)
        self.development_fees_pct = inputs.get('development_fees_pct', 2.0)
        self.marketing_fees_pct = inputs.get('marketing_fees_pct', 1.0)
        self.contingency_pct = inputs.get('contingency_pct', 5.0)
        self.s_curve_y1 = inputs.get('s_curve_y1', 40.0) / 100.0
        self.s_curve_y2 = inputs.get('s_curve_y2', 40.0) / 100.0
        self.s_curve_y3 = inputs.get('s_curve_y3', 20.0) / 100.0
        self.use_research_cost = inputs.get('use_research_cost', True)
        self.df_asset_costs = inputs.get('df_asset_costs', pd.DataFrame())
        self.amenities_capex = inputs.get('amenities_total_capex', 0)
        self.parking_capex = inputs.get('parking_capex', 0)

        total_units_gla = df_units['Surface (m²)'].sum() if not df_units.empty else 0
        efficiency_factor = (1 + (100 - (general.building_efficiency * 100)) / 100)
        self.gfa_calculated = total_units_gla * efficiency_factor

        self.total_hard_costs = 0
        if self.use_research_cost and not self.df_asset_costs.empty:
            for _, row in self.df_asset_costs.iterrows():
                asset_name = str(row['Asset Class'])
                cost_per_m2 = row['Cost €/m²']
                mask = df_units['Asset Class'].astype(str).str.contains(asset_name, case=False, na=False)
                gla_for_this_asset = df_units.loc[mask, 'Surface (m²)'].sum()
                eff_decimal = general.building_efficiency
                gfa_for_this_asset = gla_for_this_asset / eff_decimal if eff_decimal else 0
                self.total_hard_costs += (gfa_for_this_asset * cost_per_m2)
        else:
            self.hard_cost_per_m2 = self.structure_cost + self.finishing_cost + self.utilities_cost
            self.total_hard_costs = self.hard_cost_per_m2 * self.gfa_calculated

        soft_pct = self.architect_fees_pct + self.development_fees_pct + self.marketing_fees_pct
        self.total_soft_fees = (self.total_hard_costs * (soft_pct / 100)) + self.permit_fees
        subtotal = self.total_hard_costs + self.total_soft_fees
        self.contingency_amount = subtotal * (self.contingency_pct / 100)
        self.capex_construction_only = subtotal + self.contingency_amount
        self.total_capex = self.capex_construction_only + self.amenities_capex + self.parking_capex

    def get_yearly_capex(self):
        return {1: self.total_capex * self.s_curve_y1, 2: self.total_capex * self.s_curve_y2, 3: self.total_capex * self.s_curve_y3}

class Financing:
    def __init__(self, inputs):
        self.debt_amount_input = inputs.get('debt_amount', 14500000.0)
        self.interest_rate = inputs.get('interest_rate', 4.5) / 100.0
        self.loan_term = int(inputs.get('loan_term', 20))
        self.grace_period = int(inputs.get('grace_period', 2))
        self.arrangement_fee_pct = inputs.get('arrangement_fee_pct', 1.0) / 100.0
        self.upfront_fees_flat = inputs.get('upfront_fees', 150000.0)
        self.prepayment_fee_pct = inputs.get('prepayment_fee_pct', 2.0) / 100.0

        self.debt_principal = self.debt_amount_input
        self.arrangement_fee_amt = self.debt_principal * self.arrangement_fee_pct
        self.total_upfront_fees = self.arrangement_fee_amt + self.upfront_fees_flat
        self.equity_needed = 0 

class CapexSummary:
    def __init__(self, construction: Construction, financing: Financing):
        self.construction_pre_financing = construction.total_capex
        self.upfront_financing_fees = financing.total_upfront_fees
        self.total_capex = self.construction_pre_financing + self.upfront_financing_fees

class OperationExit:
    def __init__(self, inputs):
        self.inflation = inputs.get('inflation', 4.0) / 100.0
        self.rent_growth = inputs.get('rent_growth', 2.5) / 100.0
        self.opex_per_m2 = inputs.get('opex_per_m2', 28.0)
        self.pm_fee_pct = inputs.get('pm_fee_pct', 4.5) / 100.0
        self.occupancy_default = inputs.get('occupancy_rate', 90.0) / 100.0
        self.holding_period = int(inputs.get('holding_period', 20))
        self.exit_yield = inputs.get('exit_yield', 8.25) / 100.0
        self.transac_fees_exit = inputs.get('transac_fees_exit', 5.0) / 100.0

class Amortization:
    def __init__(self, financing: Financing):
        self.schedule = {}
        balance = financing.debt_principal
        rate = financing.interest_rate
        term = financing.loan_term
        grace = financing.grace_period
        amortization_duration = term - grace
        annuity = npf.pmt(rate, amortization_duration, -balance) if amortization_duration > 0 else 0
        for year in range(1, term + 2):
            if year <= grace:
                interest = balance * rate
                principal = 0
                payment = interest
            elif year <= term:
                interest = balance * rate
                payment = annuity
                principal = payment - interest
            else:
                interest = principal = payment = 0
            self.schedule[year] = {'opening': balance, 'payment': payment, 'interest': interest, 'principal': principal, 'closing': balance - principal}
            balance -= principal
            if balance < 0: balance = 0

class Scheduler:
    def __init__(self, df_units, operation: OperationExit, general: General, financing: Financing):
        self.rent_schedule = {} 
        self.rent_schedule_by_asset = {} 
        self.sale_schedule = {}
        self.sale_schedule_by_asset = {}
        self.occupied_area_schedule = {} # NEW: Track rented m² for OPEX

        years = range(1, operation.holding_period + 2)
        for y in years:
            self.rent_schedule[y] = 0.0
            self.sale_schedule[y] = 0.0
            self.occupied_area_schedule[y] = 0.0
            
        asset_classes = df_units['Asset Class'].unique() if 'Asset Class' in df_units.columns else []
        asset_classes = [str(ac).lower().strip() for ac in asset_classes]
        for ac in asset_classes:
            self.rent_schedule_by_asset[ac] = {y: 0.0 for y in years}
            self.sale_schedule_by_asset[ac] = {y: 0.0 for y in years}
        self.rent_schedule_by_asset['other'] = {y: 0.0 for y in years}
        self.sale_schedule_by_asset['other'] = {y: 0.0 for y in years}

        for _, row in df_units.iterrows():
            raw_asset = str(row.get('Asset Class', 'Other'))
            asset_key = raw_asset.lower().strip()
            if asset_key not in self.rent_schedule_by_asset: asset_key = 'other'

            surface = pd.to_numeric(row.get('Surface (m²)', 0), errors='coerce')
            base_rent_monthly = pd.to_numeric(row.get('Rent (€/m²/mo)', 0), errors='coerce')
            base_price_m2 = pd.to_numeric(row.get('Price (€/m²)', 0), errors='coerce')
            mode = str(row.get('Mode', '')).lower()
            start_year = int(pd.to_numeric(row.get('Start Year', 999), errors='coerce'))
            
            sale_year_val = row.get('Sale Year', 'Exit')
            is_exit_sale = str(sale_year_val).strip().lower() == 'exit'
            sale_year = operation.holding_period if is_exit_sale else int(pd.to_numeric(sale_year_val, errors='coerce') or 999)
            
            occ = (pd.to_numeric(row.get('Occupancy %', np.nan), errors='coerce') / 100.0) if pd.notna(row.get('Occupancy %')) else operation.occupancy_default
            rent_growth = (pd.to_numeric(row.get('Rent Growth %', np.nan), errors='coerce') / 100.0) if pd.notna(row.get('Rent Growth %')) else operation.rent_growth
            price_growth = (pd.to_numeric(row.get('Appreciation %', np.nan), errors='coerce') / 100.0) if pd.notna(row.get('Appreciation %')) else operation.inflation

            if mode in ['rent', 'mixed']:
                current_rent_m2 = base_rent_monthly * 12
                for y in years:
                    if y >= start_year and (is_exit_sale or sale_year > y):
                        indexed_rent = current_rent_m2 * ((1 + rent_growth) ** y)
                        val = surface * indexed_rent * occ
                        self.rent_schedule[y] += val
                        self.rent_schedule_by_asset[asset_key][y] += val
                        self.occupied_area_schedule[y] += (surface * occ)

            if mode in ['sale', 'mixed']:
                if not is_exit_sale and sale_year in years:
                    val = surface * (base_price_m2 * ((1 + price_growth) ** sale_year))
                    self.sale_schedule[sale_year] += val
                    self.sale_schedule_by_asset[asset_key][sale_year] += val

class CashflowEngine:
    """
    Reconstructs the Cashflow sheet according to specific user mapping.
    """
    def __init__(self, general: General, construction: Construction, financing: Financing, capex_summary: CapexSummary, operation: OperationExit, amortization: Amortization, scheduler: Scheduler):
        self.df = pd.DataFrame()
        self.kpis = {}
        years = range(0, operation.holding_period + 1)
        data = []
        
        # Exit Valuation (Cell A16: NOI n+1)
        rent_n = scheduler.rent_schedule.get(operation.holding_period, 0)
        # OPEX at Exit Year (Calculated same as yearly flow)
        opex_fixed_n = scheduler.occupied_area_schedule.get(operation.holding_period, 0) * operation.opex_per_m2 * ((1 + operation.inflation) ** (operation.holding_period - 1))
        opex_var_n = rent_n * operation.pm_fee_pct
        noi_n = rent_n - (opex_fixed_n + opex_var_n)
        
        # Apply Growth for N+1
        noi_n_plus_1 = noi_n * (1 + operation.rent_growth)
        gross_exit_val = noi_n_plus_1 / operation.exit_yield
        net_exit_val = gross_exit_val * (1 - operation.transac_fees_exit)

        # LTC Ratio for Drawdowns (Cell Financing!D12 logic applied to Drawdowns)
        # Drawdown = Investment_Flow * (Debt / Total_Capex)
        ltc_ratio = financing.debt_principal / capex_summary.total_capex if capex_summary.total_capex > 0 else 0

        for y in years:
            row = {'Year': y}
            if y == 0:
                row['Rental Income'] = 0; row['Sales Proceeds'] = 0; row['Exit Proceeds'] = 0
                row['Total Revenues'] = 0
                row['Prop. Mgmt'] = 0; row['Op. Expenses'] = 0; row['Total OPEX'] = 0
                row['NOI'] = 0
                row['Corporate Tax'] = 0
                row['CAPEX'] = 0
                row['Unlevered CF'] = 0 # Calculated below
                row['Drawdowns'] = 0
                row['Interest'] = 0
                row['Principal'] = 0
                row['Prepayment'] = 0
                row['Levered CF'] = 0
                row['Equity Injection'] = 0
                row['Equity CF'] = 0
                
                # Y0 Specifics
                # According to logic map: Y0 often has 0 flow except Equity Injection and Fees?
                # But prompt says Equity Injection B36 = -Financing!B4
                # And Financing!B4 = Total Capex - Debt.
                # So Equity is injected at Y0.
                row['Equity Injection'] = -(capex_summary.total_capex - financing.debt_principal)
                row['Equity CF'] = row['Equity Injection']

            else:
                # 1. OPERATIONS
                rent = scheduler.rent_schedule.get(y, 0)
                unit_sales = scheduler.sale_schedule.get(y, 0)
                exit_proc = net_exit_val if y == operation.holding_period else 0
                
                row['Rental Income'] = rent
                row['Sales Proceeds'] = unit_sales
                row['Exit Proceeds'] = exit_proc
                row['Total Revenues'] = rent + unit_sales + exit_proc # Note: NOI usually excludes Exit, but Unlevered CF includes it.
                # Correction based on prompt Cell A16 (NOI) = B9 - B14 (Revenues - OPEX).
                # If B9 includes Exit (Cell A8), then NOI includes Exit? 
                # Prompt A9 = Sum(B6, B7). B6=Rent, B7=Sales. B8=Exit.
                # Wait, Prompt A9 formula is =B6+B7. It DOES NOT include B8 (Exit).
                # So NOI = Rent + Unit Sales - OPEX.
                # Exit is added later in Unlevered CF (Cell B23).
                
                op_revenue_noi = rent + unit_sales 

                # OPEX
                pm_fee = rent * operation.pm_fee_pct
                # OPEX Fixed: Area * Rate * Inflation. Note: inflation starts Y1? Prompt says "for opex".
                # Formula A13: Operation!B5 * RentSchedule!B19. RentSchedule!B19 is m² Rented.
                # Assuming inflation applied in Operation!B5 or implicitly. We apply it here for robustness.
                area_rented = scheduler.occupied_area_schedule.get(y, 0)
                opex_fixed = area_rented * operation.opex_per_m2 * ((1 + operation.inflation) ** (y - 1))
                
                row['Prop. Mgmt'] = -pm_fee
                row['Op. Expenses'] = -opex_fixed
                row['Total OPEX'] = -(pm_fee + opex_fixed)
                
                row['NOI'] = op_revenue_noi - (pm_fee + opex_fixed)
                
                # Tax
                # Prompt A19: If Y <= Holiday, 0. Else Tax on NOI.
                tax = 0
                if y > general.tax_holiday and row['NOI'] > 0:
                    tax = row['NOI'] * general.corporate_tax_rate
                row['Corporate Tax'] = -tax

                # Investments (CAPEX)
                # Formula A21: Construction S-Curve * Total CAPEX Summary
                # Total CAPEX Summary includes Fees. So Fees are distributed too.
                s_curve_pct = construction.get_yearly_capex().get(y, 0) / construction.total_capex if construction.total_capex > 0 else 0
                # Actually Construction.get_yearly gives amounts.
                # We need % from S-Curve inputs.
                s_curve_map = {1: construction.s_curve_y1, 2: construction.s_curve_y2, 3: construction.s_curve_y3}
                yearly_capex_dist = s_curve_map.get(y, 0) * capex_summary.total_capex
                row['CAPEX'] = -yearly_capex_dist

                # Unlevered Operating CF (A23)
                # Formula: NOI - Tax - CAPEX + Exit Proceeds
                row['Unlevered CF'] = row['NOI'] + row['Corporate Tax'] + row['CAPEX'] + exit_proc

                # 2. FINANCING
                # Drawdowns (A27): CAPEX * LTC
                row['Drawdowns'] = yearly_capex_dist * ltc_ratio
                
                # Debt Service
                debt_data = amortization.schedule.get(y, {'payment': 0, 'closing': 0, 'interest': 0, 'principal': 0})
                row['Interest'] = -debt_data['interest']
                
                # Principal & Bullet
                principal = debt_data['principal']
                bullet = 0
                prepayment = 0
                
                if y == operation.holding_period:
                    bullet = debt_data['closing'] # Pay remaining
                    prepayment = bullet * financing.prepayment_fee_pct
                
                row['Principal'] = -(principal + bullet)
                row['Prepayment'] = -prepayment
                
                # Levered CF (A32)
                # Unlevered + Drawdowns + Interest + Principal + Prepay
                row['Levered CF'] = row['Unlevered CF'] + row['Drawdowns'] + row['Interest'] + row['Principal'] + row['Prepayment']

                # 3. EQUITY
                row['Equity Injection'] = 0 # Done at Y0
                row['Equity CF'] = row['Levered CF'] # + Injection (0 here)

            data.append(row)
            
        self.df = pd.DataFrame(data).set_index('Year')
        
        # Calculate KPIs
        self.calculate_kpis(general.discount_rate)

    def calculate_kpis(self, discount_rate):
        # Unlevered IRR & NPV
        unlevered_flows = self.df['Unlevered CF'].values
        try: irr_unlev = npf.irr(unlevered_flows)
        except: irr_unlev = 0
        npv_unlev = npf.npv(discount_rate, unlevered_flows)

        # Levered (Equity) IRR & Multiple
        equity_flows = self.df['Equity CF'].values
        try: irr_lev = npf.irr(equity_flows)
        except: irr_lev = 0
        
        pos_flows = equity_flows[equity_flows > 0].sum()
        neg_flows = abs(equity_flows[equity_flows < 0].sum())
        moic = pos_flows / neg_flows if neg_flows > 0 else 0
        
        self.kpis = {
            'Unlevered IRR': irr_unlev * 100,
            'Levered IRR': irr_lev * 100,
            'NPV': npv_unlev,
            'Equity Multiple': moic,
            'Peak Equity': neg_flows
        }
