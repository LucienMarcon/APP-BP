import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from financial_model import General, Construction, Financing, OperationExit, Amortization, Scheduler, CashflowEngine, Parking, CapexSummary

st.set_page_config(layout="wide", page_title="EstateOS", page_icon="🏢", initial_sidebar_state="collapsed")

# --- CSS INJECTION ---
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        pass
local_css("assets/style.css")

# --- TITLE HEADER ---
col_logo, col_text = st.columns([1, 15])
with col_logo:
    st.markdown("# 🏢")
with col_text:
    st.markdown("## EstateOS")
    st.caption("Real Estate Financial Modeling Platform")

st.markdown("---")

# --- MAIN LAYOUT: SPLIT SCREEN ---
left_col, right_col = st.columns([4, 5])

with left_col:
    st.markdown("### 🛠️ Configuration")
    
    # WIZARD TABS
    tab1, tab2, tab3, tab4 = st.tabs(["1. Site", "2. Travaux", "3. Unités", "4. Finance"])
    
    # --- TAB 1: SITE ---
    with tab1:
        c1, c2 = st.columns(2)
        i_city = c1.text_input("Ville", "Dar es Salaam")
        i_land_area = c2.number_input("Terrain (m²)", value=7454, step=100)
        
        st.markdown("#### Urbanisme")
        c1, c2, c3 = st.columns(3)
        i_const_rate = c1.number_input("Emprise %", 60)
        i_far = c2.number_input("FAR", 3.45)
        i_eff = c3.number_input("Efficacité %", 80)
        
        # Live feedback
        gfa = (i_land_area * i_const_rate / 100) * i_far
        gla = gfa * i_eff / 100
        st.info(f"🏗️ GFA: {gfa:,.0f} m²  |  🔑 GLA: {gla:,.0f} m²")

    # --- TAB 2: CONSTRUCTION ---
    with tab2:
        use_research = st.toggle("Coûts détaillés par Asset", True)
        if use_research:
            df_costs = pd.DataFrame([
                {"Asset Class": "residential", "Cost €/m²": 1190},
                {"Asset Class": "office", "Cost €/m²": 1093},
                {"Asset Class": "retail", "Cost €/m²": 1200},
                {"Asset Class": "logistics", "Cost €/m²": 800},
                {"Asset Class": "hotel", "Cost €/m²": 1500},
            ])
            df_asset_costs = st.data_editor(df_costs, num_rows="dynamic", use_container_width=True)
            i_struct = i_finish = 0
        else:
            c1, c2 = st.columns(2)
            i_struct = c1.number_input("Structure €/m²", 800)
            i_finish = c2.number_input("Finitions €/m²", 400)
            df_asset_costs = pd.DataFrame()

        with st.expander("Soft Costs & Planning"):
            c1, c2 = st.columns(2)
            i_permits = c1.number_input("Permis €", 20000)
            i_arch = c2.number_input("Archi %", 3.0)
            i_contingency = c1.number_input("Contingence %", 5.0)
            i_amenities = c2.number_input("Amenities €", 120000)
            
            st.caption("S-Curve (Y1 / Y2)")
            s1 = st.slider("Y1", 0, 100, 40)
            s2 = st.slider("Y2", 0, 100, 40)
            s3 = 100 - s1 - s2

    # --- TAB 3: UNITS ---
    with tab3:
        i_parking_cost = st.number_input("Coût Parking (€/pl)", 18754)
        
        # DATA LOADING (EXACT COLUMNS FROM TXT)
        units_data = []
        for t in ["OF-L", "OF-M", "OF-S"]:
            surf = 3000 if t != "OF-S" else 2640
            units_data.append({"Code": t, "AssetClass": "office", "Surface (GLA m²)": surf, "Rent (€/m²/mo)": 20, "Price €/m²": 0, "Start Year": 3, "Sale Year": "Exit", "Mode": "Rent", "Parking per unit": 0, "Parking ratio (per 100 m²)": 2.5, "Occ %": 90, "Rent growth %": 5, "Asset Value Growth (%/yr)": 4.5})
        for _ in range(4): units_data.append({"Code": "T2-VP", "AssetClass": "residential", "Surface (GLA m²)": 70, "Rent (€/m²/mo)": 16, "Price €/m²": 2300, "Start Year": 3, "Sale Year": "Exit", "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio (per 100 m²)": 0, "Occ %": 95, "Rent growth %": 4, "Asset Value Growth (%/yr)": 4})
        for _ in range(6): units_data.append({"Code": "T2-VEFA", "AssetClass": "residential", "Surface (GLA m²)": 70, "Rent (€/m²/mo)": 16, "Price €/m²": 2300, "Start Year": 3, "Sale Year": 1, "Mode": "Mixed", "Parking per unit": 1.5, "Parking ratio (per 100 m²)": 0, "Occ %": 95, "Rent growth %": 4, "Asset Value Growth (%/yr)": 4})
        
        df_default_units = pd.DataFrame(units_data)
        
        col_conf = {
            "AssetClass": st.column_config.SelectboxColumn(options=["office", "residential", "retail", "hotel"]),
            "Mode": st.column_config.SelectboxColumn(options=["Rent", "Sale", "Mixed"]),
            "Price €/m²": st.column_config.NumberColumn(format="%d €"),
            "Rent (€/m²/mo)": st.column_config.NumberColumn(format="%.2f €"),
        }
        df_units = st.data_editor(df_default_units, column_config=col_conf, num_rows="dynamic", use_container_width=True, height=300)

    # --- TAB 4: FINANCE ---
    with tab4:
        c1, c2 = st.columns(2)
        i_debt = c1.number_input("Dette (€)", 14504579)
        i_rate = c2.number_input("Taux (%)", 4.5)
        i_term = c1.number_input("Durée (ans)", 20)
        i_grace = c2.number_input("Franchise (mois)", 24)/12
        
        with st.expander("Frais & Exit"):
            i_arr_fee = st.number_input("Arrangement %", 1.0)
            i_upfront = st.number_input("Frais Fixes", 150000)
            i_prepay = st.number_input("Pénalité %", 2.0)
            st.markdown("---")
            i_hold = st.number_input("Année Sortie", 20)
            i_exit_y = st.number_input("Yield Sortie %", 8.25)
            i_sell_fees = st.number_input("Frais Vente %", 5.0)
            i_tax = st.number_input("IS %", 30.0)
            i_tax_h = st.number_input("Tax Holiday", 3)
        
        # GLOBAL OPS
        i_occ = 90; i_rent_g = 2.5; i_inf = 4.0; i_opex = 28.0; i_pm = 4.5

    # --- RUN BUTTON ---
    st.markdown("###")
    run = st.button("⚡ ACTUALISER LE MODÈLE", type="primary", use_container_width=True)


# --- RIGHT COL: RESULTS DASHBOARD ---
with right_col:
    if run:
        # MAPPING
        inp_gen = {'land_area': i_land_area, 'parcels': 3, 'construction_rate': i_const_rate, 'far': i_far, 'building_efficiency': i_eff, 'country': "Tanzanie", 'city': i_city, 'fx_eur_local': 2853.1, 'corporate_tax_rate': i_tax, 'tax_holiday': i_tax_h, 'discount_rate': 10.0}
        inp_park = {'cost_per_space': i_parking_cost}
        park = Parking(inp_park, df_units)
        inp_const = {'structure_cost': i_struct if not use_research else 0, 'finishing_cost': i_finish if not use_research else 0, 'utilities_cost': 200, 'permit_fees': i_permits, 'architect_fees_pct': i_arch, 'development_fees_pct': 2.0, 'marketing_fees_pct': 1.0, 'contingency_pct': i_contingency, 's_curve_y1': s1/100, 's_curve_y2': s2/100, 's_curve_y3': s3/100, 'use_research_cost': use_research, 'df_asset_costs': df_asset_costs, 'amenities_total_capex': i_amenities, 'parking_capex': park.total_capex}
        inp_fin = {'debt_amount': i_debt, 'interest_rate': i_rate, 'loan_term': i_term, 'grace_period': i_grace, 'arrangement_fee_pct': i_arr_fee, 'upfront_fees': i_upfront, 'prepayment_fee_pct': i_prepay}
        inp_op = {'rent_growth': i_rent_g, 'exit_yield': i_exit_y, 'holding_period': i_hold, 'inflation': i_inf, 'opex_per_m2': i_opex, 'pm_fee_pct': i_pm, 'occupancy_rate': i_occ, 'transac_fees_exit': i_sell_fees}

        try:
            gen = General(inp_gen)
            const = Construction(inp_const, gen, df_units)
            fin = Financing(inp_fin)
            op = OperationExit(inp_op)
            capex_sum = CapexSummary(const, fin)
            amort = Amortization(fin, op)
            sched = Scheduler(df_units, op, gen, fin)
            cf = CashflowEngine(gen, const, fin, capex_sum, op, amort, sched)

            # --- KPI CARDS ---
            st.markdown("### 🎯 Performance")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("IRR (Levered)", f"{cf.kpis['Levered IRR']:.2f}%", delta="Objectif > 15%")
            k2.metric("Equity Multiple", f"{cf.kpis['Equity Multiple']:.2f}x")
            k3.metric("Peak Equity", f"€{cf.kpis['Peak Equity']:,.0f}")
            k4.metric("Profit (NPV)", f"€{cf.kpis['NPV']:,.0f}")

            # --- CHARTS ---
            t1, t2, t3 = st.tabs(["📊 Cashflow", "📈 Revenus", "📑 Bilan CAPEX"])
            
            with t1:
                fig = px.bar(cf.df, x=cf.df.index, y=['NOI', 'Debt Service', 'Net Cash Flow'], 
                             title="Flux de Trésorerie Annuel", 
                             color_discrete_map={'NOI': '#10B981', 'Debt Service': '#EF4444', 'Net Cash Flow': '#3B82F6'})
                fig.update_layout(plot_bgcolor="white", height=350, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig, use_container_width=True)

            with t2:
                st.caption("Répartition des Revenus Locatifs")
                st.area_chart(pd.DataFrame(sched.rent_schedule_by_asset))

            with t3:
                df_capex = pd.DataFrame([
                    {"Item": "Construction", "Montant": capex_sum.construction_pre_financing},
                    {"Item": "Frais Bancaires", "Montant": capex_sum.upfront_financing_fees},
                    {"Item": "TOTAL", "Montant": capex_sum.total_capex}
                ])
                st.dataframe(df_capex.style.format({"Montant": "{:,.0f} €"}), use_container_width=True, hide_index=True)

            st.markdown("### 📋 Détail Annuel")
            st.dataframe(cf.df.style.format("{:,.0f}"), use_container_width=True, height=300)

        except Exception as e:
            st.error(f"Erreur de calcul : {e}")
            st.write("Vérifiez que les colonnes du tableau 'Unités' correspondent exactement.")
    else:
        # EMPTY STATE
        st.info("👈 Modifiez les paramètres à gauche et cliquez sur **ACTUALISER LE MODÈLE** pour voir les résultats.")
        
        # Placeholder visuel
        st.caption("Aperçu du CAPEX (Exemple)")
        fake_data = pd.DataFrame({'Poste': ['Construction', 'Parking', 'Soft Costs'], 'Montant': [15000000, 5000000, 2000000]})
        fig = px.pie(fake_data, values='Montant', names='Poste', hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
