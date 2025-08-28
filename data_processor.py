import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

class DataProcessor:
    """Handles data loading, cleaning, and normalization for campaign data."""
    
    def __init__(self):
        self.column_mapping = {
            # Map your Excel columns to our standard schema
            'campaign name': 'campaign_name',
            'reporting starts': 'date', 
            'amount spent (inr)': 'spend',
            'impressions': 'impressions',
            'link clicks': 'clicks',
            'results': 'purchases',
            'reach': 'reach',
            'frequency': 'frequency',
            'cpm (cost per 1,000 impressions) (inr)': 'cpm_original',
            'cpc (cost per link click) (inr)': 'cpc_original',
            'ctr (link click-through rate)': 'ctr_original',
            'clicks (all)': 'clicks_all',
            'ctr (all)': 'ctr_all',
            'cpc (all) (inr)': 'cpc_all',
            'shop_clicks': 'shop_clicks',
            'cost per results': 'cost_per_results',
            'result indicator': 'result_indicator',
            'campaign delivery': 'campaign_delivery'
        }
    
    def load_excel_data(self, uploaded_file):
        """
        Load data from uploaded Excel file.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            pandas.DataFrame: Raw data from Excel
        """
        try:
            # Read the Excel file
            df = pd.read_excel(uploaded_file, sheet_name=0)
            
            # Log basic info
            st.info(f"Loaded {len(df)} rows and {len(df.columns)} columns from Excel file")
            
            return df
            
        except Exception as e:
            st.error(f"Error loading Excel file: {str(e)}")
            raise e
    
    def clean_and_normalize(self, df):
        """
        Clean and normalize the campaign data.
        
        Args:
            df: Raw pandas DataFrame
            
        Returns:
            pandas.DataFrame: Cleaned and normalized data
        """
        # Create a copy to avoid modifying original
        processed_df = df.copy()
        
        # Normalize column names
        processed_df = self._normalize_column_names(processed_df)
        
        # Clean and convert data types
        processed_df = self._clean_data_types(processed_df)
        
        # Handle missing values
        processed_df = self._handle_missing_values(processed_df)
        
        # Remove duplicates
        processed_df = self._remove_duplicates(processed_df)
        
        # Validate data consistency
        processed_df = self._validate_data_consistency(processed_df)
        
        # Generate missing required fields
        processed_df = self._generate_missing_fields(processed_df)
        
        # Sort by date and campaign
        processed_df = processed_df.sort_values(['date', 'campaign_name']).reset_index(drop=True)
        
        st.success(f"Data processing complete: {len(processed_df)} records ready for analysis")
        
        return processed_df
    
    def _normalize_column_names(self, df):
        """Normalize column names to standard format."""
        # Convert to lowercase and strip whitespace
        df.columns = [col.lower().strip() for col in df.columns]
        
        # Map to standard column names
        column_mapping_lower = {k.lower(): v for k, v in self.column_mapping.items()}
        df = df.rename(columns=column_mapping_lower)
        
        return df
    
    def _clean_data_types(self, df):
        """Clean and convert data types."""
        # Convert date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        
        # Convert numeric columns (including the new column names)
        numeric_columns = ['spend', 'impressions', 'clicks', 'purchases', 'revenue', 'results', 'reach', 'frequency']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Replace negative values with 0 for metrics that can't be negative
                if col in ['impressions', 'clicks']:
                    df[col] = df[col].clip(lower=0)
        
        # Handle mixed data type columns that might cause Arrow conversion issues
        string_columns = ['ad set budget', 'ad set budget type', 'campaign delivery', 'attribution setting', 'result indicator']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].astype(str)
        
        # Convert ID columns to string
        id_columns = ['account_id', 'campaign_id', 'ad_id', 'creative_id']
        for col in id_columns:
            if col in df.columns:
                df[col] = df[col].astype(str)
        
        return df
    
    def _handle_missing_values(self, df):
        """Handle missing values in the dataset."""
        # Fill numeric columns with 0
        numeric_columns = ['spend', 'impressions', 'clicks', 'purchases', 'revenue']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = df[col].fillna(0)
        
        # Remove rows where required columns are missing
        required_columns = ['campaign_name', 'date']
        for col in required_columns:
            if col in df.columns:
                df = df.dropna(subset=[col])
        
        # Fill optional string columns with 'Unknown'
        string_columns = ['ad_name', 'campaign_name', 'objective']
        for col in string_columns:
            if col in df.columns:
                df[col] = df[col].fillna('Unknown')
        
        return df
    
    def _remove_duplicates(self, df):
        """Remove duplicate rows."""
        initial_count = len(df)
        
        # Define columns for duplicate detection
        duplicate_cols = ['campaign_name', 'date']
        if 'ad_id' in df.columns:
            duplicate_cols.append('ad_id')
        
        # Remove duplicates, keeping the first occurrence
        df = df.drop_duplicates(subset=duplicate_cols, keep='first')
        
        removed_count = initial_count - len(df)
        if removed_count > 0:
            st.warning(f"Removed {removed_count} duplicate rows")
        
        return df
    
    def _validate_data_consistency(self, df):
        """Validate and fix data consistency issues."""
        # Fix impossible relationships (clicks > impressions)
        if 'clicks' in df.columns and 'impressions' in df.columns:
            invalid_mask = df['clicks'] > df['impressions']
            invalid_count = invalid_mask.sum()
            
            if invalid_count > 0:
                st.warning(f"Found {invalid_count} rows where clicks > impressions. Setting clicks = impressions for these rows.")
                df.loc[invalid_mask, 'clicks'] = df.loc[invalid_mask, 'impressions']
        
        # Fix negative spend (should not happen after earlier cleaning, but just in case)
        if 'spend' in df.columns:
            negative_spend = (df['spend'] < 0).sum()
            if negative_spend > 0:
                st.warning(f"Found {negative_spend} rows with negative spend. Setting to 0.")
                df['spend'] = df['spend'].clip(lower=0)
        
        # Validate purchases vs revenue relationship
        if 'purchases' in df.columns and 'revenue' in df.columns:
            # If there's revenue but no purchases, set purchases to 1
            mask = (df['revenue'] > 0) & (df['purchases'] == 0)
            if mask.any():
                df.loc[mask, 'purchases'] = 1
                st.info(f"Set purchases = 1 for {mask.sum()} rows with revenue but no purchases")
        
        return df
    
    def _generate_missing_fields(self, df):
        """Generate missing required fields from available data."""
        # Generate account_id (since your data doesn't have it, we'll create a default one)
        if 'account_id' not in df.columns:
            df['account_id'] = 'desky_account_001'
        
        # Generate campaign_id from campaign_name
        if 'campaign_id' not in df.columns and 'campaign_name' in df.columns:
            # Create simple ID from campaign name
            df['campaign_id'] = df['campaign_name'].str.replace(' ', '_').str.lower() + '_' + df.index.astype(str)
        
        # Ensure we have purchases column (map from Results if available)
        if 'purchases' not in df.columns:
            if 'results' in df.columns:
                df['purchases'] = df['results']
            else:
                df['purchases'] = 0
        
        # Add revenue column if not present (we don't have this in your data)
        if 'revenue' not in df.columns:
            df['revenue'] = 0
        
        # Add other standard fields if missing
        if 'ad_id' not in df.columns:
            df['ad_id'] = df['campaign_id'] + '_ad_' + df.index.astype(str)
        
        if 'ad_name' not in df.columns:
            df['ad_name'] = df['campaign_name'] + ' - Ad'
            
        return df
    
    def get_data_summary(self, df):
        """
        Generate a summary of the processed data.
        
        Args:
            df: Processed pandas DataFrame
            
        Returns:
            dict: Summary statistics
        """
        summary = {
            'total_rows': len(df),
            'date_range': {
                'start': df['date'].min().strftime('%Y-%m-%d') if 'date' in df.columns else None,
                'end': df['date'].max().strftime('%Y-%m-%d') if 'date' in df.columns else None
            },
            'campaigns': df['campaign_id'].nunique() if 'campaign_id' in df.columns else 0,
            'accounts': df['account_id'].nunique() if 'account_id' in df.columns else 0,
            'total_spend': df['spend'].sum() if 'spend' in df.columns else 0,
            'total_impressions': df['impressions'].sum() if 'impressions' in df.columns else 0,
            'total_clicks': df['clicks'].sum() if 'clicks' in df.columns else 0,
            'total_purchases': df['purchases'].sum() if 'purchases' in df.columns else 0,
            'total_revenue': df['revenue'].sum() if 'revenue' in df.columns else 0
        }
        
        return summary
