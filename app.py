import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Import our custom logic
from reconciliation_engine import reconcile_invoices, reconcile_line_items

# --- Page Configuration ---
st.set_page_config(page_title="Invoice Reconciliation Dashboard", page_icon="🧾", layout="wide")

# --- Header ---
st.title("🧾 Invoice Reconciliation Dashboard")
st.markdown("Upload your data to automatically reconcile extracted invoices against source breakdowns.")

# --- Sidebar: Data Ingestion ---
st.sidebar.header("📂 Upload Data")
invoices_file = st.sidebar.file_uploader("Upload Invoices (CSV)", type=["csv"])
breakdowns_file = st.sidebar.file_uploader("Upload Breakdowns (CSV)", type=["csv"])

if invoices_file and breakdowns_file:
    # 1. Load Data
    invoices = pd.read_csv(invoices_file)
    breakdowns = pd.read_csv(breakdowns_file)
    
    # 2. Run Engine (Business Logic)
    with st.spinner('Crunching the numbers...'):
        global_results = reconcile_invoices(invoices, breakdowns)
    
    # 3. Display Metrics
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    total = len(global_results)
    matches = len(global_results[global_results['status'] == 'Matched'])
    mismatches = len(global_results[global_results['status'] == 'Mismatch'])
    accuracy = (matches / total) * 100 if total > 0 else 0
    
    m1.metric("Total Invoices", total)
    m2.metric("Matched ✅", matches)
    m3.metric("Mismatched ⚠️", mismatches, delta=-mismatches, delta_color="inverse")
    m4.metric("Accuracy Rate", f"{accuracy:.1f}%")
    st.divider()

    # 4. Tabs Interface
    tab1, tab2 = st.tabs(["📊 Global Overview", "🔍 Deep Dive Analysis"])
    
    # === TAB 1: GLOBAL OVERVIEW ===
    with tab1:
        col_chart, col_data = st.columns([1, 2])
        
        with col_chart:
            st.subheader("Status Distribution")
            fig, ax = plt.subplots(figsize=(6, 4))
            sns.countplot(data=global_results, x='status', palette='viridis', ax=ax)
            
            # Add labels to bars
            for p in ax.patches:
                ax.annotate(f'{int(p.get_height())}', 
                           (p.get_x() + p.get_width() / 2., p.get_height()), 
                           ha='center', va='center', xytext=(0, 5), textcoords='offset points')
            st.pyplot(fig)
            
            st.markdown("**Root Cause Analysis:**")
            st.write(global_results[global_results['status'] == 'Mismatch']['potential_cause'].value_counts())

        with col_data:
            st.subheader("Full Reconciliation Data")
            
            # Filter Widget
            all_statuses = global_results['status'].unique()
            filter_status = st.multiselect("Filter by Status:", all_statuses, default=all_statuses)
            
            # Apply Filter
            filtered_df = global_results[global_results['status'].isin(filter_status)]
            
            st.dataframe(
                filtered_df[['invoice_id', 'amount_inv', 'amount_brk', 'difference', 'status', 'potential_cause']], 
                use_container_width=True, 
                height=300
            )
            
            # Download Button
            st.download_button(
                label="⬇️ Download Filtered Report (CSV)",
                data=filtered_df.to_csv(index=False).encode('utf-8'),
                file_name='reconciliation_overview.csv',
                mime='text/csv',
            )

    # === TAB 2: DEEP DIVE ANALYSIS ===
    with tab2:
        st.subheader("Invoice Drill-Down")
        
        col_select, col_breakdown = st.columns([1, 3])
        
        with col_select:
            st.markdown("### 1. Select Invoice")
            # Only show mismatched invoices in the dropdown for efficiency
            mismatch_ids = global_results[global_results['status'] == 'Mismatch']['invoice_id'].unique()
            
            if len(mismatch_ids) > 0:
                selected_invoice = st.selectbox("Choose a Mismatched Invoice:", mismatch_ids)
                
                # Show summary card for selected invoice
                row = global_results[global_results['invoice_id'] == selected_invoice].iloc[0]
                st.info(f"""
                **ID:** {selected_invoice}  
                **Status:** {row['status']}  
                **Diff:** {row['difference']:.2f}  
                **Cause:** {row['potential_cause']}
                """)
            else:
                st.success("No mismatches found! 🎉")
                selected_invoice = None

        with col_breakdown:
            if selected_invoice:
                st.markdown(f"### 2. Line Item Analysis for {selected_invoice}")
                
                # Call Engine Function for Drill-Down
                line_items = reconcile_line_items(invoices, breakdowns, selected_invoice)
                
                # Styling the dataframe for display
                st.dataframe(
                    line_items.style.format({
                        'amount_extracted': '{:.2f}', 
                        'amount_source': '{:.2f}', 
                        'variance': '{:.2f}'
                    }).applymap(
                        lambda v: 'color: red; font-weight: bold;' if v == '❌ Mismatch' else 'color: green;', 
                        subset=['status']
                    ),
                    use_container_width=True
                )
                
                # Download Button for specific invoice
                st.download_button(
                    label=f"⬇️ Download Details for {selected_invoice}",
                    data=line_items.to_csv(index=False).encode('utf-8'),
                    file_name=f"{selected_invoice}_breakdown.csv",
                    mime='text/csv',
                )

else:
    # Empty State Hint
    st.info("👈 Please upload both your **Invoices** and **Breakdowns** CSV files in the sidebar.")