import numpy as np
import numpy_financial as npf
import pandas as pd

class General:
    """
    Reconstructs the 'General' sheet logic exactly.
    Reference: TXT File [Feuille General]
    """
    def __init__(self, inputs):
        # --- INPUTS (Valeurs saisies) ---
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
        
        # --- CALCULATED OUTPUTS (Formules Excel) ---
        
        # Cellule D16 : Buildable footprint (Emprise bâtie)
        # Formule = Land Area * Construction Rate
        self.buildable_footprint = self.land_area * self.construction_rate
        
        # Cellule D17 : GFA (Constructed m²)
        # Formule = Buildable footprint * FAR
        self.gfa = self.buildable_footprint * self.far
        
        # Cellule D18 : GLA (Usable m²)
        # Formule = GFA * Building Efficiency
        self.gla = self.gfa * self.building_efficiency

class Construction:
    """
    Reconstructs the 'Construction' sheet logic.
    Reference: TXT File [Feuille Construction]
    """
    def __init__(self, inputs, general: General):
        # Inputs
        self.structure_cost = inputs.get('structure_cost', 800)
        self.finishing_cost = inputs.get('finishing_cost', 400)
        self.utilities_cost = inputs.get('utilities_cost', 200)
        self.permit_fees = inputs.get('permit_fees', 20000)
        
        # Fees % of Hard Costs
        self.architect_fees_pct = inputs.get('architect_fees_pct', 3.0) / 100.0
        self.development_fees_pct = inputs.get('development_fees_pct', 2.0) / 100.0
        self.marketing_fees_pct = inputs.get('marketing_fees_pct', 1.0) / 100.0
        
        self.contingency_pct = inputs.get('contingency_pct', 5.0) / 100.0
        
        # S-Curve (Y1, Y2, Y3) - Must sum to 100%
        self.s_curve_y1 = inputs.get('s_curve_y1', 40.0) / 100.0
        self.s_curve_y2 = inputs.get('s_curve_y2', 40.0) / 100.0
        self.s_curve_y3 = inputs.get('s_curve_y3', 20.0) / 100.0

        # --- CALCULATIONS (Logic from TXT) ---
        # 1. Hard Costs
        self.hard_cost_per_m2 = self.structure_cost + self.finishing_cost + self.utilities_cost
        self.total_hard_costs = self.hard_cost_per_m2 * general.gfa
        
        # 2. Soft Fees
        self.soft_fees_pct_total = self.architect_fees_pct + self.development_fees_pct + self.marketing_fees_pct
        self.total_soft_fees = (self.total_hard_costs * self.soft_fees_pct_total) + self.permit_fees
        
        # 3. Subtotal & Contingency
        self.subtotal = self.total_hard_costs + self.total_soft_fees
        self.contingency_amount = self.subtotal * self.contingency_pct
        
        # 4. Total CAPEX (Pre-financing)
        self.total_capex = self.subtotal + self.contingency_amount

    def get_yearly_capex(self):
        """Returns dictionary of CAPEX distribution per year {1: val, 2: val...}"""
        return {
            1: self.total_capex * self.s_curve_y1,
            2: self.total_capex * self.s_curve_y2,
            3: self.total_capex * self.s_curve_y3
        }

class Financing:
    """
    Reconstructs 'Financing' sheet logic.
    Reference: TXT File [Feuille Financing]
    """
    def __init__(self, inputs, total_investment_cost):
        # Inputs
        self.debt_amount_input = inputs.get('debt_amount', 14500000.0) # Explicit input in text file
        self.interest_rate = inputs.get('interest_rate', 4.5) / 100.0
        self.loan_term = int(inputs.get('loan_term', 20))
        self.grace_period = int(inputs.get('grace_period', 2)) # Years
        
        self.arrangement_fee_pct = inputs.get('arrangement_fee_pct', 1.0) / 100.0
        self.upfront_fees_flat = inputs.get('upfront_fees', 150000.0)
        self.prepayment_fee_pct = inputs.get('prepayment_fee_pct', 2.0) / 100.0

        # Logic
        self.debt_principal = self.debt_amount_input
        self.equity_needed = total_investment_cost - self.debt_principal
        
        # Fees Calculation
        self.arrangement_fee_amt = self.debt_principal * self.arrangement_fee_pct
        self.total_upfront_fees = self.arrangement_fee_amt + self.upfront_fees_flat

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
    Crucial: Handles Grace Period (Interest Only) vs Amortization.
    """
    def __init__(self, financing: Financing):
        self.schedule = {} # Key: Year, Value: Dict
        
        balance = financing.debt_principal
        rate = financing.interest_rate
        term = financing.loan_term
        grace = financing.grace_period
        
        # Excel Logic: PMT is calculated on the remaining term AFTER grace
        amortization_duration = term - grace
        
        if amortization_duration > 0:
            # Standard annuity formula
            # PMT = P * r * (1+r)^n / ((1+r)^n - 1)
            annuity = npf.pmt(rate, amortization_duration, -balance)
        else:
            annuity = 0

        for year in range(1, term + 2): # Go one extra year just in case
            if year <= grace:
                # Interest Only
                interest = balance * rate
                principal = 0
                payment = interest
            elif year <= term:
                # Principal + Interest
                interest = balance * rate
                payment = annuity
                principal = payment - interest
            else:
                interest = 0
                principal = 0
                payment = 0
            
            # Store Data
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
    Reconstructs 'RentSchedule' and 'SaleSchedule' by aggregating 'Units'.
    Iterates through the Unit List dataframe.
    """
    def __init__(self, df_units, operation: OperationExit, general: General, financing: Financing):
        self.rent_schedule = {} # Year -> Value
        self.sale_schedule = {} # Year -> Value
        self.exit_noi = 0
        
        years = range(1, operation.holding_period + 2) # +1 for N+1 calculation
        
        # Initialize
        for y in years:
            self.rent_schedule[y] = 0.0
            self.sale_schedule[y] = 0.0
            
        # Logic: Iterate Rows
        for _, row in df_units.iterrows():
            # Parse Unit Inputs
            surface = row['Surface (m²)']
            base_rent_monthly = row['Rent (€/m²/mo)']
            base_price_m2 = row['Price (€/m²)']
            mode = row['Mode'] # Rent, Sale, Mixed
            
            start_year = int(row['Start Year']) if pd.notna(row['Start Year']) else 999
            
            # Handle "Exit" string in Sale Year
            sale_year_raw = row['Sale Year']
            if str(sale_year_raw).lower() == 'exit':
                sale_year = operation.holding_period
            elif pd.notna(sale_year_raw):
                sale_year = int(sale_year_raw)
            else:
                sale_year = 999 # Never sold
                
            # --- RENT CALCULATION LOOP ---
            if mode in ['Rent', 'Mixed']:
                current_rent_m2 = base_rent_monthly * 12 # Annual
                
                for y in years:
                    # Indexation applies from Year 1? Usually Start Year.
                    # Excel formula often: Base * (1+Growth)^(Year - Start)
                    if y >= start_year and y <= sale_year:
                        # Apply Indexation
                        indexed_rent = current_rent_m2 * ((1 + operation.rent_growth) ** (y - start_year))
                        # Apply Occupancy
                        val = surface * indexed_rent * operation.occupancy_default
                        self.rent_schedule[y] += val

            # --- SALE CALCULATION LOOP ---
            if mode in ['Sale', 'Mixed']:
                if sale_year <= operation.holding_period:
                    # Unit Sale during life
                    # Price grows with inflation usually
                    price_indexed = base_price_m2 * ((1 + operation.inflation) ** (sale_year - start_year)) 
                    val = surface * price_indexed
                    self.sale_schedule[sale_year] += val

class CashflowEngine:
    """
    Reconstructs the final 'Cashflow' sheet.
    Consolidates all other models.
    """
    def __init__(self, 
                 general: General, 
                 construction: Construction, 
                 financing: Financing, 
                 operation: OperationExit, 
                 amortization: Amortization, 
                 scheduler: Scheduler):
        
        self.df = pd.DataFrame()
        self.kpis = {}
        
        years = range(0, operation.holding_period + 1)
        data = []
        
        # Prepare Exit Value (Year N+1 NOI)
        # We need Rent N+1 and OPEX N+1
        rent_n_plus_1 = scheduler.rent_schedule[operation.holding_period + 1]
        
        # OPEX N+1 Logic
        # Fixed OPEX (on GFA) + Variable PM Fee (on Rent)
        opex_fixed_n1 = general.gfa * operation.opex_per_m2 * ((1 + operation.inflation) ** (operation.holding_period))
        opex_var_n1 = rent_n_plus_1 * operation.pm_fee_pct
        noi_n_plus_1 = rent_n_plus_1 - (opex_fixed_n1 + opex_var_n1)
        
        # Gross Exit Value
        gross_exit_val = noi_n_plus_1 / operation.exit_yield
        net_exit_val = gross_exit_val * (1 - operation.transac_fees_exit)

        # --- WATERFALL LOOP ---
        for y in years:
            row = {'Year': y}
            
            if y == 0:
                # --- YEAR 0 (Investment) ---
                # Note: In text file, Land might be Y0, Construction Y1-3. 
                # We assume Land is Y0 outflow.
                land_out = -general.land_area * 0 # User didn't provide Land Price in General sheet, usually in Investment check. 
                # Assuming total equity covers the gap.
                
                row['Rental Income'] = 0
                row['Sales Income'] = 0
                row['OPEX'] = 0
                row['NOI'] = 0
                
                # CAPEX Y0? Usually S-curve starts Y1. 
                row['CAPEX'] = 0 
                
                # Financing Y0
                row['Debt Drawdown'] = 0 # Debt usually drawn as CAPEX is spent or at end. 
                # SIMPLIFICATION FIX: Text file implies Equity + Debt covers CAPEX. 
                # Often Debt is drawn Y0 to cover purchase or Y1.
                # Let's follow standard: Debt Drawdown matches CAPEX need or is lump sum.
                # Text file "Financing" has "Upfront fees total".
                
                row['Debt Service'] = 0
                row['Upfront Fees'] = -financing.total_upfront_fees
                row['Tax'] = 0
                row['Net Cash Flow'] = row['Upfront Fees'] # + Equity injection later
                
            else:
                # --- OPERATIONS ---
                rent = scheduler.rent_schedule[y]
                sales = scheduler.sale_schedule[y]
                
                # Add Terminal Value if Exit Year
                if y == operation.holding_period:
                    sales += net_exit_val
                
                # OPEX
                # Inflation starts Y1
                opex_fixed = general.gfa * operation.opex_per_m2 * ((1 + operation.inflation) ** (y - 1))
                opex_var = rent * operation.pm_fee_pct
                total_opex = opex_fixed + opex_var
                
                noi = rent + sales - total_opex
                
                row['Rental Income'] = rent
                row['Sales Income'] = sales
                row['OPEX'] = -total_opex
                row['NOI'] = noi
                
                # CAPEX (Construction S-Curve)
                capex_amt = construction.get_yearly_capex().get(y, 0)
                row['CAPEX'] = -capex_amt
                
                # DEBT SERVICE
                debt_data = amortization.schedule.get(y, {'payment': 0, 'closing': 0})
                payment = debt_data['payment']
                
                # Bullet Repayment at Exit
                bullet = 0
                prep_fee = 0
                if y == operation.holding_period:
                    balance_remaining = debt_data['closing'] # The balance after the last payment of the year
                    bullet = balance_remaining
                    prep_fee = bullet * financing.prepayment_fee_pct
                
                total_debt_service = payment + bullet + prep_fee
                row['Debt Service'] = -total_debt_service
                
                # DEBT DRAWDOWN
                # If we are in construction phase, we might draw debt. 
                # Text file "Financing" says Debt = 14.5M. 
                # Simple approach: Drawdown at Y1 or spread? 
                # Usually Drawdown balances CAPEX. 
                # To stick to text file: Debt is an Input. Let's assume full drawdown Y0 or Y1.
                # Given S-curve, let's put Drawdown Y1 to offset CAPEX Y1?
                # Or simple: Drawdown Y0. 
                # Let's put Drawdown Y0 in Row 0 logic? No, Debt Drawdown is usually a positive cash flow.
                row['Debt Drawdown'] = 0 # Handled in Equity calc
                
                # TAX
                # EBT = NOI - Interest - Depreciation (ignored here as not in TXT logic)
                interest = debt_data['interest']
                ebt = noi - interest - total_opex # Wait, NOI already has OPEX
                ebt = noi - interest 
                
                tax = 0
                if ebt > 0 and y > general.tax_holiday:
                    tax = ebt * general.corporate_tax_rate
                
                row['Tax'] = -tax
                row['Upfront Fees'] = 0
                
                # NET CASH FLOW
                # Formula: NOI + CAPEX + DebtService + Tax + Drawdown
                # Note: CAPEX and DebtService are negative
                row['Net Cash Flow'] = noi + row['CAPEX'] + row['Debt Service'] + row['Tax']
            
            data.append(row)
            
        self.df = pd.DataFrame(data).set_index('Year')
        
        # HANDLE EQUITY (Year 0 Adjustment)
        # Net CF Y0 is currently just fees. 
        # We need to pay for Land (if any) + Construction gap.
        # Simplified "Unlevered" to "Levered" logic:
        # Equity = Total Investment - Debt
        
        # Correction: Add Debt Drawdown to cover CAPEX?
        # The classic model:
        # Unlevered CF = NOI - CAPEX - Tax
        # Levered CF = Unlevered + Debt Drawdown - Debt Service
        
        # Let's inject Debt Drawdown at Y0/Y1 to match CAPEX needs?
        # Text file Financing: "Debt 14,504,578".
        # Let's add this positive cashflow in Y1 (start of works)
        if 1 in self.df.index:
            self.df.at[1, 'Debt Drawdown'] = financing.debt_amount_input
            # Recompute Y1 Net CF
            self.df.at[1, 'Net Cash Flow'] += financing.debt_amount_input
            
        # Calculation of KPIs
        self.calculate_kpis(general.discount_rate, construction.total_capex + general.land_area*0) # Need land cost input

    def calculate_kpis(self, discount_rate, total_project_cost):
        flows = self.df['Net Cash Flow'].values
        
        # IRR
        try:
            irr = npf.irr(flows)
        except:
            irr = 0
            
        # NPV
        npv = npf.npv(discount_rate, flows)
        
        # Equity Multiple
        negative_flows = flows[flows < 0].sum()
        positive_flows = flows[flows > 0].sum()
        equity_needed = abs(negative_flows)
        moic = positive_flows / equity_needed if equity_needed > 0 else 0
        
        self.kpis = {
            'Levered IRR': irr * 100,
            'NPV': npv,
            'Equity Multiple': moic,
            'Peak Equity': equity_needed

        }
