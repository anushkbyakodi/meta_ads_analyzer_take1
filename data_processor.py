import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st

class DataProcessor:
    """Handles data loading, cleaning, and normalization for campaign data."""
    
    def __init__(self):
        self.column_mapping = {
            'account_id': 'account_id',
            'campaign_id': 'campaign_id', 
            'date': 'date',
            'spend': 'spend',
            'impressions': 'impressions',
            'clicks': 'clicks',
            'purchases': 'purchases',
            'revenue': 'revenue',
            'ad_id': 'ad_id',
            'ad_name': 'ad_name',
            'campaign_name': 'campaign_name',
            'objective': 'objective',
            'creative_id': 'creative_id'
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
        
        # Sort by date and campaign
        processed_df = processed_df.sort_values(['date', 'campaign_id']).reset_index(drop=True)
        
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
        
        # Convert numeric columns
        numeric_columns = ['spend', 'impressions', 'clicks', 'purchases', 'revenue']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                # Replace negative values with 0 for metrics that can't be negative
                if col in ['impressions', 'clicks']:
                    df[col] = df[col].clip(lower=0)
        
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
        required_columns = ['account_id', 'campaign_id', 'date']
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
        duplicate_cols = ['account_id', 'campaign_id', 'date']
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
