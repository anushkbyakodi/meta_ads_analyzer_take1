import pandas as pd
import streamlit as st
from datetime import datetime
import numpy as np

class ExcelValidator:
    """Validates Excel files for campaign data structure and content."""
    
    REQUIRED_COLUMNS = [
        'account_id',
        'campaign_id', 
        'date',
        'spend',
        'impressions',
        'clicks'
    ]
    
    OPTIONAL_COLUMNS = [
        'purchases',
        'revenue',
        'ad_id',
        'ad_name',
        'campaign_name',
        'objective',
        'creative_id'
    ]
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_excel_file(self, uploaded_file):
        """
        Validate the uploaded Excel file structure and content.
        
        Args:
            uploaded_file: Streamlit uploaded file object
            
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        try:
            self.errors = []
            self.warnings = []
            
            # Read Excel file
            df = pd.read_excel(uploaded_file, sheet_name=0)
            
            # Validate basic structure
            if not self._validate_structure(df):
                return False, "; ".join(self.errors)
            
            # Validate column presence
            if not self._validate_columns(df):
                return False, "; ".join(self.errors)
            
            # Validate data types and content
            if not self._validate_data_content(df):
                return False, "; ".join(self.errors)
            
            # Check for warnings
            self._check_warnings(df)
            
            message = "Validation successful"
            if self.warnings:
                message += f" (Warnings: {'; '.join(self.warnings)})"
            
            return True, message
            
        except Exception as e:
            return False, f"Error reading Excel file: {str(e)}"
    
    def _validate_structure(self, df):
        """Validate basic DataFrame structure."""
        if df.empty:
            self.errors.append("Excel file is empty")
            return False
        
        if len(df.columns) < len(self.REQUIRED_COLUMNS):
            self.errors.append(f"Insufficient columns. Found {len(df.columns)}, need at least {len(self.REQUIRED_COLUMNS)}")
            return False
        
        return True
    
    def _validate_columns(self, df):
        """Validate required columns are present."""
        df_columns = [col.lower().strip() for col in df.columns]
        missing_columns = []
        
        for required_col in self.REQUIRED_COLUMNS:
            if required_col.lower() not in df_columns:
                missing_columns.append(required_col)
        
        if missing_columns:
            self.errors.append(f"Missing required columns: {', '.join(missing_columns)}")
            return False
        
        return True
    
    def _validate_data_content(self, df):
        """Validate data content and types."""
        # Normalize column names for validation
        df_norm = df.copy()
        df_norm.columns = [col.lower().strip() for col in df_norm.columns]
        
        # Check for completely empty rows
        empty_rows = df_norm.isnull().all(axis=1).sum()
        if empty_rows > 0:
            self.warnings.append(f"{empty_rows} completely empty rows found")
        
        # Validate numeric columns
        numeric_columns = ['spend', 'impressions', 'clicks']
        if 'purchases' in df_norm.columns:
            numeric_columns.append('purchases')
        if 'revenue' in df_norm.columns:
            numeric_columns.append('revenue')
        
        for col in numeric_columns:
            if col in df_norm.columns:
                if not pd.api.types.is_numeric_dtype(df_norm[col]):
                    # Try to convert to numeric
                    df_norm[col] = pd.to_numeric(df_norm[col], errors='coerce')
                
                # Check for negative values where they shouldn't be
                if col in ['spend', 'impressions', 'clicks'] and (df_norm[col] < 0).any():
                    self.errors.append(f"Negative values found in {col} column")
                    return False
        
        # Validate date column
        if 'date' in df_norm.columns:
            try:
                pd.to_datetime(df_norm['date'], errors='raise')
            except:
                self.errors.append("Date column contains invalid date formats")
                return False
        
        # Validate ID columns are not empty
        id_columns = ['account_id', 'campaign_id']
        for col in id_columns:
            if col in df_norm.columns:
                if df_norm[col].isnull().any():
                    self.errors.append(f"{col} column contains empty values")
                    return False
        
        return True
    
    def _check_warnings(self, df):
        """Check for potential data quality issues."""
        df_norm = df.copy()
        df_norm.columns = [col.lower().strip() for col in df_norm.columns]
        
        # Check for high percentage of missing values
        for col in df_norm.columns:
            missing_pct = df_norm[col].isnull().mean()
            if missing_pct > 0.1:  # More than 10% missing
                self.warnings.append(f"{col} has {missing_pct:.1%} missing values")
        
        # Check for duplicate rows
        duplicate_count = df_norm.duplicated().sum()
        if duplicate_count > 0:
            self.warnings.append(f"{duplicate_count} duplicate rows found")
        
        # Check for unrealistic values
        if 'spend' in df_norm.columns and 'clicks' in df_norm.columns:
            # Check for very high CPC (might indicate data quality issues)
            df_norm['temp_cpc'] = df_norm['spend'] / df_norm['clicks'].replace(0, np.nan)
            high_cpc_count = (df_norm['temp_cpc'] > 100).sum()
            if high_cpc_count > 0:
                self.warnings.append(f"{high_cpc_count} records with CPC > $100 (potential data quality issue)")
        
        if 'impressions' in df_norm.columns and 'clicks' in df_norm.columns:
            # Check for CTR > 100% (impossible)
            df_norm['temp_ctr'] = df_norm['clicks'] / df_norm['impressions'].replace(0, np.nan)
            impossible_ctr = (df_norm['temp_ctr'] > 1).sum()
            if impossible_ctr > 0:
                self.errors.append(f"{impossible_ctr} records with clicks > impressions (impossible)")
