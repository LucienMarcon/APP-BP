import numpy as np
import numpy_financial as npf
import pandas as pd

class General:
    """
    Source: [Feuille General]
    """
    def __init__(self, inputs):
        self.land_area = inputs.get('land_area', 7454)
        self.parcels = inputs.get('parcels', 3)
        self.construction_rate = inputs.get('construction_rate', 60.0) / 100.0
        self.far = inputs.get('far', 3.45)
        self.building_efficiency = inputs.get('building_efficiency', 80.0) / 100.0
        self.corporate_tax_rate = inputs.get('corporate_tax_rate', 30.0) / 100.0
        self.tax_holiday = inputs.get('tax_holiday', 3)
        self.discount_rate = inputs.get('discount_rate', 10.0) / 100.0
        
        # D16, D17, D18
        self.buildable_footprint = self.land_area * self.construction_rate
        self.gfa = self.buildable_footprint * self.far
        self.gla = self.gfa * self.building_efficiency

class Parking:
    """
    Source: [Feuille Parking]
    """
    def __init__(self, inputs, df_units: pd.DataFrame):
        self.cost_per_space = inputs.get('cost_per_space', 18754)
        self.total_spaces = 0
        
        if not df_units.empty:
            for _, row in df_units.iterrows():
                # Map specific column names from Units.txt
                fixed = pd.to_numeric(row.get('Parking per unit', 0), errors='coerce')
                ratio = pd.to_numeric(row.get('Parking ratio (per 100 m²)', 0), errors='coerce') # Exact Excel header
                surface = pd.to_numeric(row.get('Surface (GLA m²)', 0), errors='coerce') # Exact Excel header
                
                if pd.isna(fixed): fixed = 0
                if pd.isna(ratio): ratio = 0
                if pd.isna(surface): surface = 0
                
                spaces = fixed + ((surface / 100) * ratio)
                self.total_spaces += spaces
        
        self.total_capex = self.total_spaces * self.cost_per_space

class Construction:
    """
    Source: [Feuille Construction]
    """
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

        # GFA check (D18)
        total_units_gla = df_units['Surface (GLA m²)'].sum() if not df_units.empty else 0
        efficiency_factor = (1 + (100 - (general.building_efficiency * 100)) / 100)
        self.gfa_calculated = total_units_gla * efficiency_factor

        # Hard Costs (D20)
        self.total_hard_costs = 0
        if self.use_research_cost and not self.df_asset_costs.empty:
            for _, row in self.df_asset_costs.iterrows():
                asset_name = str(row['Asset Class'])
                cost_per_m2 = row['Cost €/m²']
                # Column 'AssetClass' in Units.txt
                mask = df_units['AssetClass'].astype(str).str.contains(asset_name, case=False, na=False)
                gla = df_units.loc[mask, 'Surface (GLA m²)'].sum()
                
                eff_decimal = general.building_efficiency
                gfa = gla / eff_decimal if eff_decimal else 0
                
                self.total_hard_costs += (gfa * cost_per_m2)
        else:
            self.hard_cost_per_m2 = self.structure_cost + self.finishing_cost + self.utilities_cost
            self.total_hard_costs = self.hard_cost_per_m2 * self.gfa_calculated

        # Soft Fees (D22)
        soft_pct = self.architect_fees_pct + self.development_fees_pct + self.marketing_fees_pct
        self.total_soft_fees = (self.total_hard_costs * (soft_pct / 100)) + self.permit_fees

        # Subtotal (D23)
        subtotal = self.total_hard_costs + self.total_soft_fees
        
        # Contingency (D24)
        self.contingency_amount = subtotal * (self.contingency_pct / 100)
        
        # Pre-financing (D25)
        self.capex_construction_only = subtotal + self.contingency_amount
        
        # Total CAPEX (D39)
        self.total_capex = self.capex_construction_only + self.amenities_capex + self.parking_capex

    def get_yearly_capex(self):
        return {
            1: self.total_capex * self.s_curve_y1,
            2: self.total_capex * self.s_curve_y2,
            3: self.total_capex * self.s_curve_y3
        }

class Financing:
    """
    Source: [Feuille Financing]
    """
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
        
        # Equity is derived later via CapexSummary

class CapexSummary:
    """
    Source: [Feuille CAPEX_Summary]
    """
    def __init__(self, construction: Construction, financing: Financing):
        # B4
        self.construction_pre_financing = construction.total_capex
        # B5
        self.upfront_financing_fees = financing.total_upfront_fees
        # B6
        self.total_capex = self.construction_pre_financing + self.upfront_financing_fees

class OperationExit:
    """
    Source: [Feuille Operation] & [Feuille Exit]
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
    Source: [Feuille Amortization]
    """
    def __init__(self, financing: Financing, operation: OperationExit):
        self.schedule = {}
        balance = financing.debt_principal
        rate = financing.interest_rate
        term = financing.loan_term
        grace = financing.grace_period
        exit_year = operation.holding_period
        
        amortization_duration = term - grace
        
        if amortization_duration > 0:
            annuity = npf.pmt(rate, amortization_duration, -balance)
        else:
            annuity = 0

        current_balance = balance
        
        # Loop 1 to Term
        for year in range(1, term + 5):
            if year > exit_year:
                self.schedule[year] = {'opening': 0, 'payment': 0, 'interest': 0, 'principal': 0, 'closing': 0}
                continue
                
            opening = current_balance
            interest = opening * rate
            
            if year <= grace:
                principal = 0
                payment = interest
            elif year <= term:
                payment = annuity
                principal = payment - interest
            else:
                payment = 0; principal = 0; interest = 0
            
            closing = opening - principal
            if closing < 0.01: closing = 0
            
            self.schedule[year] = {'opening': opening, 'payment': payment, 'interest': interest, 'principal': principal, 'closing': closing}
            current_balance = closing

class Scheduler:
    """
    Source: [Feuille RentSchedule] & [Feuille SaleSchedule]
    """
    def __init__(self, df_units, operation: OperationExit, general: General, financing: Financing):
        self.rent_schedule = {} 
        self.rent_schedule_by_asset = {} 
        self.sale_schedule = {}
        self.sale_schedule_by_asset = {} 
        self.occupied_area_schedule = {}

        years = range(1, operation.holding_period + 2)
        
        # Init
        for y in years:
            self.rent_schedule[y] = 0.0
            self.sale_schedule[y] = 0.0
            self.occupied_area_schedule[y] = 0.0
            
        asset_classes = df_units['AssetClass'].unique() if 'AssetClass' in df_units.columns else []
        asset_classes = [str(ac).lower().strip() for ac in asset_classes]
        
        for ac in asset_classes:
            self.rent_schedule_by_asset[ac] = {y: 0.0 for y in years}
            self.sale_schedule_by_asset[ac] = {y: 0.0 for y in years}
        
        self.rent_schedule_by_asset['other'] = {y: 0.0 for y in years}
        self.sale_schedule_by_asset['other'] = {y: 0.0 for y in years}

        for _, row in df_units.iterrows():
            raw_asset = str(row.get('AssetClass', 'Other'))
            asset_key = raw_asset.lower().strip()
            if asset_key not in self.rent_schedule_by_asset:
                asset_key = 'other'

            # MAPPING EXACT DES COLONNES DU TXT
            surface = pd.to_numeric(row.get('Surface (GLA m²)', 0), errors='coerce')
            base_rent_monthly = pd.to_numeric(row.get('Rent (€/m²/mo)', 0), errors='coerce')
            base_price_m2 = pd.to_numeric(row.get('Price €/m²', 0), errors='coerce')
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
            occ = pd.to_numeric(row.get('Occ %', np.nan), errors='coerce')
            occupancy = (occ / 100.0) if pd.notna(occ) else operation.occupancy_default
            
            rg = pd.to_numeric(row.get('Rent growth %', np.nan), errors='coerce')
            rent_growth = (rg / 100.0) if pd.notna(rg) else operation.rent_growth
            
            ag = pd.to_numeric(row.get('Asset Value Growth (%/yr)', np.nan), errors='coerce')
            price_growth = (ag / 100.0) if pd.notna(ag) else operation.inflation

            # --- RENT SCHEDULE (RentSchedule!B6) ---
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
                        # Formula: 12 * Surface * Rent * Occ * (1+g)^Year
                        indexed_rent = current_rent_m2 * ((1 + rent_growth) ** y)
                        val = surface * indexed_rent * occupancy
                        
                        self.rent_schedule[y] += val
                        self.rent_schedule_by_asset[asset_key][y] += val
                        self.occupied_area_schedule[y] += (surface * occupancy)

            # --- SALE SCHEDULE (SaleSchedule!B6) ---
            if mode in ['sale', 'mixed']:
                if not is_exit_sale:
                    if sale_year in years:
                         # Formula: Surface * Price * (1+g)^Year
                        price_indexed = base_price_m2 * ((1 + price_growth) ** sale_year)
                        val = surface * price_indexed
                        
                        self.sale_schedule[sale_year] += val
                        self.sale_schedule_by_asset[asset_key][sale_year] += val

class CashflowEngine:
    """
    Source: [Feuille Cashflow]
    """
    def __init__(self, 
                 general: General, 
                 construction: Construction, 
                 financing: Financing, 
                 capex_summary: CapexSummary, 
                 operation: OperationExit, 
                 amortization: Amortization, 
                 scheduler: Scheduler):
        
        self.df = pd.DataFrame()
        self.kpis = {}
        years = range(0, operation.holding_period + 1)
        data = []
        
        # Exit Valuation (Exit!A16)
        rent_n = scheduler.rent_schedule.get(operation.holding_period, 0)
        
        # OPEX N+1 logic
        # Cashflow A13: OPEX = Rate * Area * Inflation^(y-1)
        area_n = scheduler.occupied_area_schedule.get(operation.holding_period, 0)
        opex_fixed_n = area_n * operation.opex_per_m2 * ((1 + operation.inflation) ** (operation.holding_period - 1))
        opex_var_n = rent_n * operation.pm_fee_pct
        
        noi_n = rent_n - (opex_fixed_n + opex_var_n)
        
        # NOI N+1 (Exit!B16)
        noi_n_plus_1 = noi_n * (1 + operation.rent_growth)
        
        # Exit Values
        gross_exit_val = noi_n_plus_1 / operation.exit_yield
        net_exit_val = gross_exit_val * (1 - operation.transac_fees_exit)

        # LTC Ratio
        ltc_ratio = financing.debt_principal / capex_summary.total_capex if capex_summary.total_capex > 0 else 0

        for y in years:
            row = {'Year': y}
            
            if y == 0:
                row['Rental Income'] = 0; row['Sales Proceeds'] = 0; row['Exit Proceeds'] = 0
                row['Total Revenues'] = 0
                row['Total OPEX'] = 0
                row['NOI'] = 0
                row['CAPEX'] = 0 
                row['Debt Service'] = 0
                row['Tax'] = 0
                row['Debt Drawdown'] = 0
                row['Upfront Fees'] = -financing.total_upfront_fees
                row['Net Cash Flow'] = row['Upfront Fees']
                
            else:
                # I. OPERATIONS
                rent = scheduler.rent_schedule.get(y, 0)
                unit_sales = scheduler.sale_schedule.get(y, 0)
                
                exit_proc = net_exit_val if y == operation.holding_period else 0
                
                row['Rental Income'] = rent
                row['Sales Proceeds'] = unit_sales
                row['Exit Proceeds'] = exit_proc
                
                # NOI Calculation Basis (Rent + Sales)
                row['Total Revenues'] = rent + unit_sales
                
                # OPEX
                area_rented = scheduler.occupied_area_schedule.get(y, 0)
                opex_fixed = area_rented * operation.opex_per_m2 * ((1 + operation.inflation) ** (y - 1))
                pm_fee = rent * operation.pm_fee_pct
                total_opex = opex_fixed + pm_fee
                
                row['Total OPEX'] = -total_opex
                row['NOI'] = (rent + unit_sales) - total_opex
                
                # Tax (on NOI)
                tax = 0
                if row['NOI'] > 0 and y > general.tax_holiday:
                    tax = row['NOI'] * general.corporate_tax_rate
                
                row['Tax'] = -tax
                row['Upfront Fees'] = 0
                
                # CAPEX
                s_curve_map = {1: construction.s_curve_y1, 2: construction.s_curve_y2, 3: construction.s_curve_y3}
                capex_flow = s_curve_map.get(y, 0) * capex_summary.total_capex
                row['CAPEX'] = -capex_flow
                
                # II. FINANCING
                row['Debt Drawdown'] = capex_flow * ltc_ratio
                
                debt_vals = amortization.schedule.get(y, {'payment': 0, 'closing': 0, 'interest': 0, 'principal': 0})
                
                payment = debt_vals['payment']
                bullet = 0
                prep_fee = 0
                
                if y == operation.holding_period:
                    bullet = debt_vals['closing']
                    prep_fee = bullet * financing.prepayment_fee_pct
                
                row['Debt Service'] = -(payment + bullet + prep_fee)
                
                # Net CF
                row['Net Cash Flow'] = row['NOI'] + row['CAPEX'] + row['Debt Service'] + row['Tax'] + row['Debt Drawdown'] + exit_proc

            data.append(row)
            
        self.df = pd.DataFrame(data).set_index('Year')
        
        # Financing!B4: Equity = Total Capex - Debt
        equity_req = capex_summary.total_capex - financing.debt_principal
        self.calculate_kpis(general.discount_rate, equity_req)

    def calculate_kpis(self, discount_rate, equity_needed):
        flows = self.df['Net Cash Flow'].values
        
        # Adjust T0 for IRR: T0 Flow is -Equity
        final_flows = flows.copy()
        final_flows[0] = -equity_needed
        
        try: irr = npf.irr(final_flows)
        except: irr = 0
        
        npv = npf.npv(discount_rate, final_flows)
        
        pos = final_flows[final_flows > 0].sum()
        neg = abs(final_flows[final_flows < 0].sum())
        moic = pos / neg if neg > 0 else 0
        
        self.kpis = {'Levered IRR': irr * 100, 'NPV': npv, 'Equity Multiple': moic, 'Peak Equity': equity_needed}
