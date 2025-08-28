import pandas as pd
import numpy as np
import streamlit as st

class KPICalculator:
    """Calculates marketing KPIs from campaign data."""
    
    def __init__(self):
        self.kpi_definitions = {
            'cpc': 'Cost Per Click',
            'cpm': 'Cost Per Mille (1000 impressions)',
            'ctr': 'Click Through Rate',
            'cpa': 'Cost Per Acquisition',
            'roas': 'Return On Ad Spend',
            'cvr': 'Conversion Rate',
            'frequency': 'Average Frequency'
        }
    
    def calculate_all_kpis(self, df):
        """
        Calculate all available KPIs from the dataset.
        
        Args:
            df: Cleaned pandas DataFrame with campaign data
            
        Returns:
            pandas.DataFrame: DataFrame with original data plus calculated KPIs
        """
        # Create a copy to avoid modifying original data
        kpi_df = df.copy()
        
        # Calculate basic KPIs
        kpi_df = self._calculate_cpc(kpi_df)
        kpi_df = self._calculate_cpm(kpi_df)
        kpi_df = self._calculate_ctr(kpi_df)
        
        # Calculate conversion KPIs if purchase data is available
        if 'purchases' in kpi_df.columns:
            kpi_df = self._calculate_cpa(kpi_df)
            kpi_df = self._calculate_cvr(kpi_df)
        
        # Calculate ROAS if revenue data is available
        if 'revenue' in kpi_df.columns:
            kpi_df = self._calculate_roas(kpi_df)
        
        # Calculate frequency if possible (simplified version)
        kpi_df = self._calculate_frequency(kpi_df)
        
        # Add derived metrics
        kpi_df = self._calculate_derived_metrics(kpi_df)
        
        # Log summary
        self._log_kpi_summary(kpi_df)
        
        return kpi_df
    
    def _calculate_cpc(self, df):
        """Calculate Cost Per Click."""
        df['cpc'] = np.where(
            df['clicks'] > 0,
            df['spend'] / df['clicks'],
            0
        )
        return df
    
    def _calculate_cpm(self, df):
        """Calculate Cost Per Mille (1000 impressions)."""
        df['cpm'] = np.where(
            df['impressions'] > 0,
            (df['spend'] / df['impressions']) * 1000,
            0
        )
        return df
    
    def _calculate_ctr(self, df):
        """Calculate Click Through Rate."""
        df['ctr'] = np.where(
            df['impressions'] > 0,
            df['clicks'] / df['impressions'],
            0
        )
        return df
    
    def _calculate_cpa(self, df):
        """Calculate Cost Per Acquisition."""
        if 'purchases' in df.columns:
            df['cpa'] = np.where(
                df['purchases'] > 0,
                df['spend'] / df['purchases'],
                0
            )
        return df
    
    def _calculate_roas(self, df):
        """Calculate Return On Ad Spend."""
        if 'revenue' in df.columns:
            df['roas'] = np.where(
                df['spend'] > 0,
                df['revenue'] / df['spend'],
                0
            )
        return df
    
    def _calculate_cvr(self, df):
        """Calculate Conversion Rate."""
        if 'purchases' in df.columns:
            df['cvr'] = np.where(
                df['clicks'] > 0,
                df['purchases'] / df['clicks'],
                0
            )
        return df
    
    def _calculate_frequency(self, df):
        """Calculate simplified frequency metric."""
        # Simplified frequency calculation: impressions / unique users
        # Since we don't have unique users, we'll use a proxy based on impressions/clicks ratio
        df['frequency'] = np.where(
            df['clicks'] > 0,
            df['impressions'] / df['clicks'],
            df['impressions'] / 1  # Fallback when no clicks
        )
        return df
    
    def _calculate_derived_metrics(self, df):
        """Calculate additional derived metrics."""
        # Cost per impression
        df['cost_per_impression'] = np.where(
            df['impressions'] > 0,
            df['spend'] / df['impressions'],
            0
        )
        
        # Revenue per impression (if revenue available)
        if 'revenue' in df.columns:
            df['revenue_per_impression'] = np.where(
                df['impressions'] > 0,
                df['revenue'] / df['impressions'],
                0
            )
        
        # Revenue per click (if revenue available)
        if 'revenue' in df.columns:
            df['revenue_per_click'] = np.where(
                df['clicks'] > 0,
                df['revenue'] / df['clicks'],
                0
            )
        
        # Purchase rate (purchases per impression)
        if 'purchases' in df.columns:
            df['purchase_rate'] = np.where(
                df['impressions'] > 0,
                df['purchases'] / df['impressions'],
                0
            )
        
        # Average order value (if both revenue and purchases available)
        if 'revenue' in df.columns and 'purchases' in df.columns:
            df['aov'] = np.where(
                df['purchases'] > 0,
                df['revenue'] / df['purchases'],
                0
            )
        
        return df
    
    def _log_kpi_summary(self, df):
        """Log summary of calculated KPIs."""
        st.info("KPI Calculation Summary:")
        
        # Basic metrics summary
        if 'cpc' in df.columns:
            avg_cpc = df[df['cpc'] > 0]['cpc'].mean()
            st.write(f"• Average CPC: ${avg_cpc:.2f}")
        
        if 'cpm' in df.columns:
            avg_cpm = df[df['cpm'] > 0]['cpm'].mean()
            st.write(f"• Average CPM: ${avg_cpm:.2f}")
        
        if 'ctr' in df.columns:
            avg_ctr = df['ctr'].mean() * 100
            st.write(f"• Average CTR: {avg_ctr:.2f}%")
        
        if 'cpa' in df.columns:
            avg_cpa = df[df['cpa'] > 0]['cpa'].mean()
            st.write(f"• Average CPA: ${avg_cpa:.2f}")
        
        if 'roas' in df.columns:
            avg_roas = df[df['roas'] > 0]['roas'].mean()
            st.write(f"• Average ROAS: {avg_roas:.2f}x")
        
        if 'cvr' in df.columns:
            avg_cvr = df['cvr'].mean() * 100
            st.write(f"• Average CVR: {avg_cvr:.2f}%")
    
    def get_campaign_summary(self, df):
        """
        Get aggregated KPIs by campaign.
        
        Args:
            df: DataFrame with calculated KPIs
            
        Returns:
            pandas.DataFrame: Campaign-level KPI summary
        """
        # Aggregate by campaign
        agg_dict = {
            'spend': 'sum',
            'impressions': 'sum',
            'clicks': 'sum',
            'date': ['min', 'max']
        }
        
        # Add purchases and revenue if available
        if 'purchases' in df.columns:
            agg_dict['purchases'] = 'sum'
        if 'revenue' in df.columns:
            agg_dict['revenue'] = 'sum'
        
        campaign_summary = df.groupby('campaign_id').agg(agg_dict).reset_index()
        
        # Flatten column names
        campaign_summary.columns = ['_'.join(col).strip('_') if col[1] else col[0] 
                                  for col in campaign_summary.columns]
        
        # Recalculate KPIs at campaign level
        calculator = KPICalculator()
        campaign_summary = calculator.calculate_all_kpis(campaign_summary)
        
        return campaign_summary
    
    def get_date_summary(self, df):
        """
        Get aggregated KPIs by date.
        
        Args:
            df: DataFrame with calculated KPIs
            
        Returns:
            pandas.DataFrame: Daily KPI summary
        """
        # Aggregate by date
        agg_dict = {
            'spend': 'sum',
            'impressions': 'sum',
            'clicks': 'sum',
            'campaign_id': 'nunique'
        }
        
        # Add purchases and revenue if available
        if 'purchases' in df.columns:
            agg_dict['purchases'] = 'sum'
        if 'revenue' in df.columns:
            agg_dict['revenue'] = 'sum'
        
        date_summary = df.groupby('date').agg(agg_dict).reset_index()
        
        # Recalculate KPIs at daily level
        calculator = KPICalculator()
        date_summary = calculator.calculate_all_kpis(date_summary)
        
        # Rename campaign count column
        date_summary = date_summary.rename(columns={'campaign_id': 'active_campaigns'})
        
        return date_summary
