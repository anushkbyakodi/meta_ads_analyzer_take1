import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import traceback
import os

from data_processor import DataProcessor
from kpi_calculator import KPICalculator
from gpt_client import GPTClient
from validators import ExcelValidator
from meta_client import MetaAdsClient

def main():
    st.set_page_config(
        page_title="Ad Campaign Analyzer",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Ad Campaign Analyzer")
    st.markdown("Upload your campaign Excel data to generate AI-powered insights and KPI analysis")
    
    # Initialize session state
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'insights' not in st.session_state:
        st.session_state.insights = None
    if 'kpis' not in st.session_state:
        st.session_state.kpis = None
    if 'data_source' not in st.session_state:
        st.session_state.data_source = None
    if 'meta_accounts' not in st.session_state:
        st.session_state.meta_accounts = None
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        openai_api_key = st.text_input(
            "OpenAI API Key",
            type="password",
            help="Enter your OpenAI API key for GPT-powered insights generation",
            value=os.getenv('OPENAI_API_KEY', '')
        )
        
        st.markdown("---")
        st.markdown("**Required Excel Columns:**")
        st.markdown("""
        - Campaign name
        - Reporting starts (date)
        - Amount spent (INR)
        - Impressions
        - Link clicks
        
        **Optional Columns:**
        - Results (conversions)
        - Reach, Frequency
        - CTR, CPC, CPM metrics
        """)
    
    # Step 1: Collect Inputs
    st.subheader("📊 Step 1: Choose Data Source")
    
    data_source = st.radio(
        "Select your data source:",
        ["Meta (Facebook/Instagram) Ads API", "Upload Excel File"],
        help="Choose how you want to provide your campaign data"
    )
    
    st.session_state.data_source = data_source
    
    if data_source == "Meta (Facebook/Instagram) Ads API":
        # Meta API Path
        st.markdown("### A) Meta Access Token")
        
        meta_access_token = st.text_input(
            "Meta Access Token",
            type="password",
            help="Enter your Meta Marketing API access token"
        )
        
        if meta_access_token:
            # Step 2: Validate Token
            st.subheader("📋 Step 2: Validate Input")
            
            try:
                with st.spinner("Validating Meta access token..."):
                    meta_client = MetaAdsClient(meta_access_token)
                    is_valid, message = meta_client.validate_token_and_permissions()
                
                if not is_valid:
                    st.error(f"❌ Token validation failed: {message}")
                else:
                    st.success(f"✅ {message}")
                    
                    # Step 3: Select Ad Accounts
                    st.subheader("🏢 Step 3: Select Ad Accounts")
                    
                    with st.spinner("Fetching ad accounts..."):
                        accounts = meta_client.get_ad_accounts()
                        st.session_state.meta_accounts = accounts
                    
                    if accounts:
                        account_options = {f"{acc['name']} ({acc['id']})": acc['id'] for acc in accounts}
                        selected_accounts = st.multiselect(
                            "Select ad accounts to analyze:",
                            options=list(account_options.keys()),
                            help="Choose one or more ad accounts"
                        )
                        
                        # Date range selection
                        col_date1, col_date2 = st.columns(2)
                        from datetime import date, timedelta
                        with col_date1:
                            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
                        with col_date2:
                            end_date = st.date_input("End Date", value=date.today())
                        
                        if selected_accounts and st.button("📥 Fetch Campaign Data"):
                            try:
                                # Step 4: Process Meta Data
                                st.subheader("🔄 Step 4: Processing Meta Data")
                                
                                all_data = []
                                date_range = {
                                    'start_date': start_date.strftime('%Y-%m-%d'),
                                    'end_date': end_date.strftime('%Y-%m-%d')
                                }
                                
                                for account_display in selected_accounts:
                                    account_id = account_options[account_display]
                                    
                                    with st.spinner(f"Fetching data from {account_display}..."):
                                        account_data = meta_client.get_insights_data(account_id, date_range)
                                        if not account_data.empty:
                                            all_data.append(account_data)
                                
                                if all_data:
                                    # Combine all account data
                                    combined_data = pd.concat(all_data, ignore_index=True)
                                    
                                    # Process and clean the data
                                    processor = DataProcessor()
                                    processed_data = processor.clean_and_normalize(combined_data)
                                    st.session_state.processed_data = processed_data
                                    
                                    st.success(f"✅ Processed {len(processed_data)} records from Meta API")
                                    
                                    # Continue to KPI calculation
                                    process_kpis_and_insights(processed_data, openai_api_key)
                                    
                            except Exception as e:
                                st.error(f"❌ Error fetching Meta data: {str(e)}")
                                st.expander("Error details").code(traceback.format_exc())
                    else:
                        st.warning("No ad accounts found. Please check your token permissions.")
                        
            except Exception as e:
                st.error(f"❌ Error with Meta API: {str(e)}")
                st.expander("Error details").code(traceback.format_exc())
    
    else:
        # Excel Upload Path
        st.markdown("### B) Upload Campaign Excel")
        
        uploaded_file = st.file_uploader(
            "Choose an Excel file",
            type=['xlsx', 'xls'],
            help="Upload your campaign data Excel file"
        )
        
        if uploaded_file is not None:
            try:
                # Step 2: Validate Excel file
                st.subheader("📋 Step 2: Validate Input")
                
                with st.spinner("Validating Excel file..."):
                    validator = ExcelValidator()
                    is_valid, validation_message = validator.validate_excel_file(uploaded_file)
                
                if not is_valid:
                    st.error(f"❌ Validation failed: {validation_message}")
                else:
                    st.success("✅ Excel file validated successfully")
                    
                    # Step 3: Process data
                    st.subheader("🔄 Step 3: Load Data")
                    
                    with st.spinner("Processing campaign data..."):
                        processor = DataProcessor()
                        raw_data = processor.load_excel_data(uploaded_file)
                        processed_data = processor.clean_and_normalize(raw_data)
                        st.session_state.processed_data = processed_data
                    
                    st.success(f"✅ Processed {len(processed_data)} records")
                    
                    # Continue to KPI calculation
                    process_kpis_and_insights(processed_data, openai_api_key)
                
            except Exception as e:
                st.error(f"❌ Error processing file: {str(e)}")
                st.expander("Error details").code(traceback.format_exc())

def process_kpis_and_insights(processed_data, openai_api_key):
    """Helper function to process KPIs and generate insights."""
    
    # Step 4/5: Calculate KPIs
    st.subheader("📊 Step 4: Clean & Enrich")
    
    with st.spinner("Calculating KPIs..."):
        calculator = KPICalculator()
        kpis_data = calculator.calculate_all_kpis(processed_data)
        st.session_state.kpis = kpis_data
    
    st.success("✅ KPIs calculated successfully")
    
    # Step 5/6: Generate insights
    st.subheader("🤖 Step 5: Generate Insights")
    
    if openai_api_key:
        with st.spinner("Generating GPT insights..."):
            gpt_client = GPTClient(openai_api_key)
            insights = gpt_client.generate_insights(kpis_data)
            st.session_state.insights = insights
        
        st.success("✅ GPT insights generated")
    else:
        st.warning("⚠️ Please provide OpenAI API key to generate insights")

    # Data Overview Section
    if st.session_state.processed_data is not None:
        st.markdown("---")
        st.subheader("📈 Data Overview")
        
        data = st.session_state.processed_data
        
        # Summary metrics
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("Total Records", len(data))
        with col_b:
            st.metric("Campaigns", data['campaign_id'].nunique())
        with col_c:
            st.metric("Date Range", f"{data['date'].dt.date.min()} to {data['date'].dt.date.max()}")
        with col_d:
            st.metric("Total Spend", f"${data['spend'].sum():,.2f}")
        
        # Data preview
        st.markdown("**Data Preview:**")
        st.dataframe(data.head(10), width='stretch')
        
        # JSON format display
        st.markdown("**Data in JSON Format:**")
        import json
        
        # Convert the first 5 rows to JSON for display
        json_data = data.head(5).to_dict('records')
        
        # Display as formatted JSON
        st.code(json.dumps(json_data, indent=2, default=str), language='json')
    
    # KPIs Section
    if st.session_state.kpis is not None:
        st.markdown("---")
        st.subheader("📊 Step 3: Key Performance Indicators")
        
        kpis = st.session_state.kpis
        
        # KPI Metrics
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            avg_cpc = kpis['cpc'].mean()
            st.metric("Avg CPC", f"${avg_cpc:.2f}")
        
        with col2:
            avg_cpm = kpis['cpm'].mean()
            st.metric("Avg CPM", f"${avg_cpm:.2f}")
        
        with col3:
            avg_ctr = kpis['ctr'].mean() * 100
            st.metric("Avg CTR", f"{avg_ctr:.2f}%")
        
        with col4:
            if 'cpa' in kpis.columns:
                avg_cpa = kpis['cpa'].mean()
                st.metric("Avg CPA", f"${avg_cpa:.2f}")
        
        with col5:
            if 'roas' in kpis.columns:
                avg_roas = kpis['roas'].mean()
                st.metric("Avg ROAS", f"{avg_roas:.2f}x")
        
        with col6:
            if 'cvr' in kpis.columns:
                avg_cvr = kpis['cvr'].mean() * 100
                st.metric("Avg CVR", f"{avg_cvr:.2f}%")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            # Spend over time
            daily_spend = kpis.groupby('date')['spend'].sum().reset_index()
            fig1 = px.line(daily_spend, x='date', y='spend', title="Daily Spend Trend")
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # Performance by campaign
            campaign_perf = kpis.groupby('campaign_id').agg({
                'spend': 'sum',
                'clicks': 'sum',
                'impressions': 'sum'
            }).reset_index()
            
            fig2 = px.scatter(campaign_perf, x='spend', y='clicks', 
                            size='impressions', hover_data=['campaign_id'],
                            title="Campaign Performance: Spend vs Clicks")
            st.plotly_chart(fig2, use_container_width=True)
        
        # Detailed KPIs table
        st.markdown("**Detailed KPIs:**")
        st.dataframe(kpis, width='stretch')
    
    # Insights Section
    if st.session_state.insights is not None:
        st.markdown("---")
        st.subheader("🤖 Step 4: AI-Generated Insights")
        
        insights = st.session_state.insights
        
        # Display insights in an attractive format
        st.markdown("### 📋 Campaign Analysis Summary")
        st.markdown(insights)
        
        # Download button for insights
        st.download_button(
            label="📥 Download Insights Report",
            data=insights,
            file_name="campaign_insights.txt",
            mime="text/plain"
        )
    
    # Export functionality
    if st.session_state.kpis is not None:
        st.markdown("---")
        st.subheader("📥 Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export KPIs to Excel
            output = BytesIO()
            st.session_state.kpis.to_excel(output, engine='openpyxl', sheet_name='KPIs', index=False)
            output.seek(0)
            
            st.download_button(
                label="📊 Download KPIs Excel",
                data=output.getvalue(),
                file_name="campaign_kpis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        with col2:
            # Export KPIs to CSV
            csv_data = st.session_state.kpis.to_csv(index=False)
            st.download_button(
                label="📄 Download KPIs CSV",
                data=csv_data,
                file_name="campaign_kpis.csv",
                mime="text/csv"
            )

if __name__ == "__main__":
    main()
