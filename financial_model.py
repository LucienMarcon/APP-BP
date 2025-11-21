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
                # Mapping EXACT [Feuille Units]
                fixed = pd.to_numeric(row.get('Parking per unit', 0), errors='coerce')
                ratio = pd.to_numeric(row.get('Parking ratio (per 100 m²)', 0), errors='coerce')
                surface = pd.to_numeric(row.get('Surface (GLA m²)', 0), errors='coerce') # CORRIGÉ
                
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

        # GFA check (Cell D18) - Uses Surface (GLA m²)
        total_units_gla = df_units['Surface (GLA m²)'].sum() if not df_units.empty else 0
        efficiency_factor = (1 + (100 - (general.building_efficiency * 100)) / 100)
        self.gfa_calculated = total_units_gla * efficiency_factor

        self.total_hard_costs = 0
        if self.use_research_cost and not self.df_asset_costs.empty:
            for _, row in self.df_asset_costs.iterrows():
                asset_name = str(row['Asset Class'])
                cost_per_m2 = row['Cost €/m²']
                # Recherche dans 'AssetClass' (sans espace, colonne Excel)
                mask = df_units['AssetClass'].astype(str).str.contains(asset_name, case=False, na=False)
                gla = df_units.loc[mask, 'Surface (GLA m²)'].sum() # CORRIGÉ
                
                eff_decimal = general.building_efficiency
                gfa = gla / eff_decimal if eff_decimal else 0
                
                self.total_hard_costs += (gfa * cost_per_m2)
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
        return {
            1: self.total_capex * self.s_curve_y1,
            2: self.total_capex * self.s_curve_y2,
            3: self.total_capex * self.s_curve_y3
        }

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
    def __init__(self, financing: Financing, operation: OperationExit):
        self.schedule = {}
        balance = financing.debt_principal
        rate = financing.interest_rate
        term = financing.loan_term
        grace = financing.grace_period
        exit_year = operation.holding_period
        
        amortization_duration = term - grace
        annuity = npf.pmt(rate, amortization_duration, -balance) if amortization_duration > 0 else 0

        current_balance = balance
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
    Manages Rent Schedule and Sale Schedule using EXACT columns from Units.txt.
    """
    def __init__(self, df_units, operation: OperationExit, general: General, financing: Financing):
        self.rent_schedule = {} 
        self.rent_schedule_by_asset = {} 
        self.sale_schedule = {}
        self.sale_schedule_by_asset = {}
        self.occupied_area_schedule = {}

        years = range(1, operation.holding_period + 2)
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
            if asset_key not in self.rent_schedule_by_asset: asset_key = 'other'

            # --- MAPPING CRITIQUE DES COLONNES ---
            surface = pd.to_numeric(row.get('Surface (GLA m²)', 0), errors='coerce') # CORRIGÉ
            base_rent_monthly = pd.to_numeric(row.get('Rent (€/m²/mo)', 0), errors='coerce')
            base_price_m2 = pd.to_numeric(row.get('Price €/m²', 0), errors='coerce') # CORRIGÉ
            mode = str(row.get('Mode', '')).lower()
            start_year = int(pd.to_numeric(row.get('Start Year', 999), errors='coerce'))
            
            sale_year_val = row.get('Sale Year', 'Exit')
            is_exit_sale = str(sale_year_val).strip().lower() == 'exit'
            sale_year = operation.holding_period if is_exit_sale else int(pd.to_numeric(sale_year_val, errors='coerce') or 999)
            
            occ = (pd.to_numeric(row.get('Occ %', np.nan), errors='coerce') / 100.0) if pd.notna(row.get('Occ %')) else operation.occupancy_default
            rent_growth = (pd.to_numeric(row.get('Rent growth %', np.nan), errors='coerce') / 100.0) if pd.notna(row.get('Rent growth %')) else operation.rent_growth
            price_growth = (pd.to_numeric(row.get('Asset Value Growth (%/yr)', np.nan), errors='coerce') / 100.0) if pd.notna(row.get('Asset Value Growth (%/yr)')) else operation.inflation

            if mode in ['rent', 'mixed']:
                current_rent_m2 = base_rent_monthly * 12
                for y in years:
                    receives_rent = False
                    if y >= start_year:
                        if is_exit_sale: receives_rent = True
                        elif sale_year > y: receives_rent = True
                    
                    if receives_rent:
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
    def __init__(self, general: General, construction: Construction, financing: Financing, capex_summary: CapexSummary, operation: OperationExit, amortization: Amortization, scheduler: Scheduler):
        self.df = pd.DataFrame()
        self.kpis = {}
        years = range(0, operation.holding_period + 1)
        data = []
        
        rent_n = scheduler.rent_schedule.get(operation.holding_period, 0)
        opex_fixed_n = general.gfa * operation.opex_per_m2 * ((1 + operation.inflation) ** (operation.holding_period - 1))
        opex_var_n = rent_n * operation.pm_fee_pct
        noi_n = rent_n - (opex_fixed_n + opex_var_n)
        noi_n_plus_1 = noi_n * (1 + operation.rent_growth)
        net_exit_val = (noi_n_plus_1 / operation.exit_yield) * (1 - operation.transac_fees_exit)
        ltc_ratio = financing.debt_principal / capex_summary.total_capex if capex_summary.total_capex > 0 else 0

        for y in years:
            row = {'Year': y}
            if y == 0:
                row['Rental Income'] = 0; row['Sales Income'] = 0; row['OPEX'] = 0; row['NOI'] = 0
                row['CAPEX'] = 0; row['Debt Service'] = 0; row['Tax'] = 0; row['Debt Drawdown'] = 0
                row['Upfront Fees'] = -financing.total_upfront_fees
                row['Net Cash Flow'] = row['Upfront Fees']
                row['Equity Injection'] = -(capex_summary.total_capex - financing.debt_principal)
                row['Equity CF'] = row['Equity Injection']
            else:
                rent = scheduler.rent_schedule.get(y, 0)
                sales = scheduler.sale_schedule.get(y, 0)
                exit_proc = net_exit_val if y == operation.holding_period else 0
                row['Exit Proceeds'] = exit_proc
                area_rented = scheduler.occupied_area_schedule.get(y, 0)
                opex_fixed = area_rented * operation.opex_per_m2 * ((1 + operation.inflation) ** (y - 1))
                opex_var = rent * operation.pm_fee_pct
                noi = rent + sales - (opex_fixed + opex_var)
                row['Rental Income'] = rent; row['Sales Income'] = sales; row['OPEX'] = -(opex_fixed + opex_var); row['NOI'] = noi
                
                s_curve_map = {1: construction.s_curve_y1, 2: construction.s_curve_y2, 3: construction.s_curve_y3}
                capex_amt = s_curve_map.get(y, 0) * capex_summary.total_capex
                row['CAPEX'] = -capex_amt
                row['Drawdowns'] = capex_amt * ltc_ratio
                
                debt = amortization.schedule.get(y, {'payment': 0, 'closing': 0, 'interest': 0, 'principal': 0})
                bullet = debt['closing'] if y == operation.holding_period else 0
                prep_fee = bullet * financing.prepayment_fee_pct
                row['Debt Service'] = -(debt['payment'] + bullet + prep_fee)
                
                ebt = noi - debt['interest']
                row['Tax'] = -(ebt * general.corporate_tax_rate) if (ebt > 0 and y > general.tax_holiday) else 0
                
                row['Net Cash Flow'] = noi + row['CAPEX'] + row['Debt Service'] + row['Tax'] + row['Drawdowns'] + exit_proc
            data.append(row)
            
        self.df = pd.DataFrame(data).set_index('Year')
        equity_needed = capex_summary.total_capex - financing.debt_principal
        self.calculate_kpis(general.discount_rate, equity_needed)

    def calculate_kpis(self, discount_rate, equity_needed):
        flows = self.df['Net Cash Flow'].values
        try: irr = npf.irr(flows)
        except: irr = 0
        npv = npf.npv(discount_rate, flows)
        positive = flows[flows > 0].sum()
        self.kpis = {'Levered IRR': irr * 100, 'NPV': npv, 'Equity Multiple': positive / equity_needed if equity_needed > 0 else 0, 'Peak Equity': equity_needed}
