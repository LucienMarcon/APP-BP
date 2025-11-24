import streamlit as st
from calculations import run_financial_model  # exemple selon ton architecture
from utils import load_excel_data              # idem

# ==========================================
# UI Styling modern importé depuis Style.txt
# ==========================================
def apply_custom_style():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            background-color: #F8FAFC;
        }

        .stApp {
            background-color: #F8FAFC;
            font-family: 'Inter', sans-serif;
        }

        header[data-testid="stHeader"] {
            display: none;
        }

        div[data-testid="metric-container"] {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: all .2s ease-in-out;
        }
        div[data-testid="metric-container"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
            border-color: #3B82F6;
        }

        .stTabs [data-baseweb="tab-list"] {
            background-color: #FFFFFF;
            padding: 6px;
            border-radius: 12px;
            gap: 5px;
            border: 1px solid #E2E8F0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        .stTabs [data-baseweb="tab"] {
            height: 40px;
            border-radius: 8px;
            background-color: transparent;
            color: #64748B;
            font-weight: 500;
            font-size: 0.9rem;
        }

        .stTabs [aria-selected="true"] {
            background-color: #EFF6FF;
            color: #2563EB;
            font-weight: 600;
        }

        .stTextInput input,
        .stNumberInput input,
        .stSelectbox div[data-baseweb="select"] {
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            min-height: 42px;
            font-family: 'Inter', sans-serif;
        }

        .stButton button {
            width: 100%;
            background: linear-gradient(135deg,#0F172A,#334155);
            color: white;
            border-radius: 10px;
            padding: .75rem 1.5rem;
            font-weight: 600;
            letter-spacing: .5px;
            border: none;
            transition: .1s ease-in-out;
        }
        .stButton button:hover {
            transform: translateY(-1px);
            box-shadow: 0 10px 15px -3px rgba(15,23,42,.2);
        }

        [data-testid="stDataFrame"],
        [data-testid="stPlotlyChart"] {
            background: white;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
            padding: 12px;
        }
        </style>
    """, unsafe_allow_html=True)


# ==========================================
# INTERFACE — STREAMLIT APP
# ==========================================
def main():

    apply_custom_style()

    st.title("📊 Real Estate Investment Dashboard")
    st.write("Modelisation complète du BP — version moderne & responsive")

    tabs = st.tabs(["General", "CAPEX", "Operations", "Financing", "Cashflow", "Exit"])

    with tabs[0]:
        st.subheader("General Assumptions")
        file = st.file_uploader("Upload BP Excel", type=["xlsx"])
        if file:
            df = load_excel_data(file)
            st.success("Fichier chargé")
            st.dataframe(df)

    with tabs[1]:
        st.subheader("CAPEX Overview")
        st.write("…")

    with tabs[2]:
        st.subheader("Operational Parameters")
        st.write("…")

    with tabs[3]:
        st.subheader("Financing")
        st.write("…")

    with tabs[4]:
        st.subheader("Cashflow")
        st.write("…")

    with tabs[5]:
        st.subheader("Exit / IRR")
        st.write("…")


if __name__ == "__main__":
    main()
