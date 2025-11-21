import numpy as np
import numpy_financial as npf
import pandas as pd

class General:
    """
    Reconstructs the 'General' sheet logic exactly.
    Reference: TXT File [Feuille General]
    """
    def __init__(self, inputs):
        # --- INPUTS ---
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
        
        # --- CALCULATED OUTPUTS ---
        # Cell D16: Buildable footprint
        self.buildable_footprint = self.land_area * self.construction_rate
        
        # Cell D17: GFA
        self.gfa = self.buildable_footprint * self.far
        
        # Cell D18: GLA
        self.gla = self.gfa * self.building_efficiency

class Parking:
    """
    Reconstructs the 'Parking' sheet logic.
    Calculates required spaces based on Unit Mix and specific columns.
    Reference: TXT File [Feuille Parking] & [Feuille Units]
    """
    def __init__(self, inputs, df_units: pd.DataFrame):
        # Input cost from Parking sheet
        self.cost_per_space = inputs.get('cost_per_space', 18754)
        
        self.total_spaces = 0
        
        # Logic: Iterate through units to calculate spaces
        # Formula: Fixed Spaces + (Surface / 100 * Ratio)
        if not df_units.empty:
            for _, row in df_units.iterrows():
                # Secure retrieval of columns (handle cases where cols might be missing initally)
                fixed_spaces = pd.to_numeric(row.get('Parking per unit', 0), errors='coerce')
                ratio_per_100m2 = pd.to_numeric(row.get('Parking ratio', 0), errors='coerce')
                surface = pd.to_numeric(row.get('Surface (m²)', 0), errors='coerce')
                
                # Handle NaNs
                if pd.isna(fixed_spaces): fixed_spaces = 0
                if pd.isna(ratio_per_100m2): ratio_per_100m2 = 0
                if pd.isna(surface): surface = 0
                
                # Calculation
                spaces = fixed_spaces + ((surface / 100) * ratio_per_100m2)
                self.total_spaces += spaces
        
        # Final CAPEX Calculation
        self.total_capex = self.total_spaces * self.cost_per_space

class Construction:
    """
    Reconstructs the 'Construction' sheet logic exactly.
    Includes the branching logic: Global Cost vs Research Cost per Asset Class.
    """
    def __init__(self, inputs, general: General, df_units: pd.DataFrame):
        # --- INPUTS ---
        self.structure_cost = inputs.get('structure_cost', 800)
        self.finishing_cost = inputs.get('finishing_cost', 400)
        self.utilities_cost = inputs.get('utilities_cost', 200)
        self.permit_fees = inputs.get('permit_fees', 20000)
        
        # Fees %
        self.architect_fees_pct = inputs.get('architect_fees_pct', 3.0)
        self.development_fees_pct = inputs.get('development_fees_pct', 2.0)
        self.marketing_fees_pct = inputs.get('marketing_fees_pct', 1.0)
        self.contingency_pct = inputs.get('contingency_pct', 5.0)
        
        # S-Curve
        self.s_curve_y1 = inputs.get('s_curve_y1', 40.0) / 100.0
        self.s_curve_y2 = inputs.get('s_curve_y2', 40.0) / 100.0
        self.s_curve_y3 = inputs.get('s_curve_y3', 20.0) / 100.0

        # --- LOGIC: THE "SWITCH" (Cell B27) ---
        self.use_research_cost = inputs.get('use_research_cost', True)
        
        # DYNAMIC ASSET CLASSES TABLE
        self.df_asset_costs = inputs.get('df_asset_costs', pd.DataFrame())

        # Amenities & Parking Inputs
        self.amenities_capex = inputs.get('amenities_total_capex', 0)
        self.parking_capex = inputs.get('parking_capex', 0) # Coming from Parking Class output
        
        # --- CALCULATIONS ---

        # 1. GFA Calculation (Global)
        total_units_gla = df_units['Surface (m²)'].sum() if not df_units.empty else 0
        efficiency_factor = (1 + (100 - (general.building_efficiency * 100)) / 100)
        self.gfa_calculated = total_units_gla * efficiency_factor

        # 2. Hard Costs Calculation
        self.total_hard_costs = 0
        
        if self.use_research_cost and not self.df_asset_costs.empty:
            # METHOD B: Dynamic Cost per Asset Class
            for _, row in self.df_asset_costs.iterrows():
                asset_name = str(row['Asset Class'])
                cost_per_m2 = row['Cost €/m²']
                
                # Smart Match: We look for the asset name INSIDE the Unit Type
                mask = df_units['Asset Class'].astype(str).str.contains(asset_name, case=False, na=False)
                gla_for_this_asset = df_units.loc[mask, 'Surface (m²)'].sum()
                
                # Convert GLA to GFA using efficiency
                eff_decimal = general.building_efficiency
                gfa_for_this_asset = gla_for_this_asset / eff_decimal if eff_decimal else 0
                
                self.total_hard_costs += (gfa_for_this_asset * cost_per_m2)
                
        else:
            # METHOD A: Global Cost
            self.hard_cost_per_m2 = self.structure_cost + self.finishing_cost + self.utilities_cost
            self.total_hard_costs = self.hard_cost_per_m2 * self.gfa_calculated

        # 3. Soft Fees
        soft_pct = self.architect_fees_pct + self.development_fees_pct + self.marketing_fees_pct
        self.total_soft_fees = (self.total_hard_costs * (soft_pct / 100)) + self.permit_fees

        # 4. Contingency
        subtotal = self.total_hard_costs + self.total_soft_fees
        self.contingency_amount = subtotal * (self.contingency_pct / 100)

        # 5. Total Construction Pre-Financing
        self.capex_construction_only = subtotal + self.contingency_amount
        
        # 6. FINAL TOTAL
        # We integrate the Parking CAPEX here, ensuring compatibility
        self.total_capex = self.capex_construction_only + self.amenities_capex + self.parking_capex

    def get_yearly_capex(self):
        return {
            1: self.total_capex * self.s_curve_y1,
            2: self.total_capex * self.s_curve_y2,
            3: self.total_capex * self.s_curve_y3
        }

class Financing:
    """
    Reconstructs 'Financing' sheet logic.
    """
    def __init__(self, inputs, total_investment_cost):
        self.debt_amount_input = inputs.get('debt_amount', 14500000.0)
        self.interest_rate = inputs.get('interest_rate', 4.5) / 100.0
        self.loan_term = int(inputs.get('loan_term', 20))
        self.grace_period = int(inputs.get('grace_period', 2))
        self.arrangement_fee_pct = inputs.get('arrangement_fee_pct', 1.0) / 100.0
        self.upfront_fees_flat = inputs.get('upfront_fees', 150000.0)
        self.prepayment_fee_pct = inputs.get('prepayment_fee_pct', 2.0) / 100.0

        self.debt_principal = self.debt_amount_input
        
        # Fees Calculation
        self.arrangement_fee_amt = self.debt_principal * self.arrangement_fee_pct
        self.total_upfront_fees = self.arrangement_fee_amt + self.upfront_fees_flat
        
        # Initialisation simple, l'equity sera calculée par CapexSummary
        self.equity_needed = 0 

class CapexSummary:
    """
    Reconstructs 'CAPEX_Summary' sheet logic.
    This class bridges Construction and Financing.
    """
    def __init__(self, construction: Construction, financing: Financing):
        # Cell B4: Construction pre-financing (Construction!D39)
        self.construction_pre_financing = construction.total_capex
        
        # Cell B5: Upfront financing fees (Financing!D13)
        self.upfront_financing_fees = financing.total_upfront_fees
        
        # Cell B6: TOTAL CAPEX
        self.total_capex = self.construction_pre_financing + self.upfront_financing_fees

class OperationExit:
    """
    Reconstructs 'Operation' and 'Exit' logic.
    """
    def __init__(self, inputs):
        # Operation
        self.inflation = inputs.get('inflation', 4.0) / 100.0
        self.rent_growth = inputs.get('rent_growth', 2.5) / 100.0
        self.opex_per_m2 = inputs.get('opex_per_m2', 28.0)
        self.pm_fee_pct = inputs.get('pm_fee_pct', 4.5) / 100.0
        self.occupancy_default = inputs.get('occupancy_rate', 90.0) / 100.0
        
        # Exit
        self.holding_period = int(inputs.get('holding_period', 20))
        self.exit_yield = inputs.get('exit_yield', 8.25) / 100.0
        self.transac_fees_exit = inputs.get('transac_fees_exit', 5.0) / 100.0

class Amortization:
    """
    Reconstructs 'Amortization' sheet logic exactly.
    """
    def __init__(self, financing: Financing):
        self.schedule = {}
        
        balance = financing.debt_principal
        rate = financing.interest_rate
        term = financing.loan_term
        grace = financing.grace_period
        
        amortization_duration = term - grace
        
        if amortization_duration > 0:
            annuity = npf.pmt(rate, amortization_duration, -balance)
        else:
            annuity = 0

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
                interest = 0
                principal = 0
                payment = 0
            
            self.schedule[year] = {
                'opening': balance,
                'payment': payment,
                'interest': interest,
                'principal': principal,
                'closing': balance - principal
            }
            
            balance -= principal
            if balance < 0: balance = 0

class Scheduler:
    """
    Manages Rent Schedule and Sale Schedule.
    Splits BOTH Rent and Sales by Asset Class for granular reporting.
    """
    def __init__(self, df_units, operation: OperationExit, general: General, financing: Financing):
        self.rent_schedule = {} 
        self.rent_schedule_by_asset = {} 
        
        self.sale_schedule = {}
        self.sale_schedule_by_asset = {} 
        
        years = range(1, operation.holding_period + 2)
        
        # Initialize Global & Breakdown dictionaries
        for y in years:
            self.rent_schedule[y] = 0.0
            self.sale_schedule[y] = 0.0
            
        asset_classes = df_units['Asset Class'].unique() if 'Asset Class' in df_units.columns else []
        asset_classes = [str(ac).lower().strip() for ac in asset_classes]
        
        for ac in asset_classes:
            self.rent_schedule_by_asset[ac] = {y: 0.0 for y in years}
            self.sale_schedule_by_asset[ac] = {y: 0.0 for y in years}
        
        # Generic bucket for unmatched
        self.rent_schedule_by_asset['other'] = {y: 0.0 for y in years}
        self.sale_schedule_by_asset['other'] = {y: 0.0 for y in years}

        # Iterate over units
        for _, row in df_units.iterrows():
            raw_asset = str(row.get('Asset Class', 'Other'))
            asset_key = raw_asset.lower().strip()
            if asset_key not in self.rent_schedule_by_asset:
                asset_key = 'other'

            surface = pd.to_numeric(row.get('Surface (m²)', 0), errors='coerce')
            base_rent_monthly = pd.to_numeric(row.get('Rent (€/m²/mo)', 0), errors='coerce')
            base_price_m2 = pd.to_numeric(row.get('Price (€/m²)', 0), errors='coerce')
            mode = str(row.get('Mode', '')).lower()
            
            start_year = pd.to_numeric(row.get('Start Year', np.nan), errors='coerce')
            if pd.isna(start_year): start_year = 999
            else: start_year = int(start_year)
            
            sale_year_val = row.get('Sale Year', 'Exit')
            is_exit_sale = str(sale_year_val).strip().lower() == 'exit'
            
            if is_exit_sale:
                sale_year = operation.holding_period 
            else:
                sale_year = pd.to_numeric(sale_year_val, errors='coerce')
                if pd.isna(sale_year): sale_year = 999
                else: sale_year = int(sale_year)
            
            # Overrides
            occ = pd.to_numeric(row.get('Occupancy %', np.nan), errors='coerce')
            occupancy = (occ / 100.0) if pd.notna(occ) else operation.occupancy_default
            
            rg = pd.to_numeric(row.get('Rent Growth %', np.nan), errors='coerce')
            rent_growth = (rg / 100.0) if pd.notna(rg) else operation.rent_growth
            
            ag = pd.to_numeric(row.get('Appreciation %', np.nan), errors='coerce')
            price_growth = (ag / 100.0) if pd.notna(ag) else operation.inflation

            # --- RENT SCHEDULE LOGIC ---
            if mode in ['rent', 'mixed']:
                current_rent_m2 = base_rent_monthly * 12
                for y in years:
                    receives_rent = False
                    if y >= start_year:
                        if is_exit_sale:
                            receives_rent = True
                        elif sale_year > y:
                            receives_rent = True
                    
                    if receives_rent:
                        indexed_rent = current_rent_m2 * ((1 + rent_growth) ** y)
                        val = surface * indexed_rent * occupancy
                        self.rent_schedule[y] += val
                        self.rent_schedule_by_asset[asset_key][y] += val

            # --- SALE SCHEDULE LOGIC ---
            if mode in ['sale', 'mixed']:
                if not is_exit_sale:
                    if sale_year in years:
                        price_indexed = base_price_m2 * ((1 + price_growth) ** sale_year)
                        val = surface * price_indexed
                        self.sale_schedule[sale_year] += val
                        self.sale_schedule_by_asset[asset_key][sale_year] += val

class CashflowEngine:
    """
    Reconstructs the final 'Cashflow' sheet.
    NOW ACCEPTS CAPEX SUMMARY to calculate Equity Needed.
    """
    def __init__(self, 
                 general: General, 
                 construction: Construction, 
                 financing: Financing, 
                 capex_summary: CapexSummary, # Passed correctly
                 operation: OperationExit, 
                 amortization: Amortization, 
                 scheduler: Scheduler):
        
        self.df = pd.DataFrame()
        self.kpis = {}
        years = range(0, operation.holding_period + 1)
        data = []
        
        # Exit Valuation (N+1)
        rent_n = scheduler.rent_schedule.get(operation.holding_period, 0)
        opex_fixed_n = general.gfa * operation.opex_per_m2 * ((1 + operation.inflation) ** (operation.holding_period - 1))
        opex_var_n = rent_n * operation.pm_fee_pct
        noi_n = rent_n - (opex_fixed_n + opex_var_n)
        noi_n_plus_1 = noi_n * (1 + operation.rent_growth)
        
        gross_exit_val = noi_n_plus_1 / operation.exit_yield
        net_exit_val = gross_exit_val * (1 - operation.transac_fees_exit)

        for y in years:
            row = {'Year': y}
            
            if y == 0:
                row['Rental Income'] = 0
                row['Sales Income'] = 0
                row['OPEX'] = 0
                row['NOI'] = 0
                row['CAPEX'] = 0 
                row['Debt Service'] = 0
                row['Tax'] = 0
                row['Debt Drawdown'] = 0
                # Cashflow sheet logic: Y0 contains Upfront Fees (negative)
                row['Upfront Fees'] = -financing.total_upfront_fees
                row['Net Cash Flow'] = row['Upfront Fees']
                
            else:
                rent = scheduler.rent_schedule.get(y, 0)
                sales = scheduler.sale_schedule.get(y, 0)
                
                if y == operation.holding_period:
                    sales += net_exit_val
                
                opex_fixed = general.gfa * operation.opex_per_m2 * ((1 + operation.inflation) ** (y - 1))
                opex_var = rent * operation.pm_fee_pct
                total_opex = opex_fixed + opex_var
                
                noi = rent + sales - total_opex
                
                row['Rental Income'] = rent
                row['Sales Income'] = sales
                row['OPEX'] = -total_opex
                row['NOI'] = noi
                
                capex_amt = construction.get_yearly_capex().get(y, 0)
                row['CAPEX'] = -capex_amt
                
                debt_data = amortization.schedule.get(y, {'payment': 0, 'closing': 0, 'interest': 0})
                payment = debt_data['payment']
                
                bullet = 0
                prep_fee = 0
                if y == operation.holding_period:
                    bullet = debt_data['closing']
                    prep_fee = bullet * financing.prepayment_fee_pct
                
                row['Debt Service'] = -(payment + bullet + prep_fee)
                
                interest = debt_data['interest']
                ebt = noi - interest
                
                tax = 0
                if ebt > 0 and y > general.tax_holiday:
                    tax = ebt * general.corporate_tax_rate
                
                row['Tax'] = -tax
                row['Upfront Fees'] = 0
                row['Debt Drawdown'] = 0
                
                row['Net Cash Flow'] = noi + row['CAPEX'] + row['Debt Service'] + row['Tax']
            
            data.append(row)
            
        self.df = pd.DataFrame(data).set_index('Year')
        
        # Equity Drawdown (Simulation: Debt is injected in Y1)
        if 1 in self.df.index:
            self.df.at[1, 'Debt Drawdown'] = financing.debt_amount_input
            self.df.at[1, 'Net Cash Flow'] += financing.debt_amount_input
            
        # Calculate Equity Needed based on CAPEX Summary Logic (Total Capex - Debt)
        equity_needed = capex_summary.total_capex - financing.debt_principal
        
        self.calculate_kpis(general.discount_rate, equity_needed)

    def calculate_kpis(self, discount_rate, equity_needed):
        flows = self.df['Net Cash Flow'].values
        try: irr = npf.irr(flows)
        except: irr = 0
        npv = npf.npv(discount_rate, flows)
        positive_flows = flows[flows > 0].sum()
        
        moic = positive_flows / equity_needed if equity_needed > 0 else 0
        
        self.kpis = {'Levered IRR': irr * 100, 'NPV': npv, 'Equity Multiple': moic, 'Peak Equity': equity_needed}
