import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple

class MetaAdsClient:
    """Client for interacting with Meta Marketing API to fetch campaign data."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://graph.facebook.com/v18.0"
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    def validate_token_and_permissions(self) -> Tuple[bool, str]:
        """
        Validate access token and check required permissions.
        
        Returns:
            tuple: (is_valid: bool, message: str)
        """
        try:
            # Check token validity and permissions
            url = f"{self.base_url}/me"
            params = {
                "fields": "id,name",
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                return False, f"Invalid token: {response.text}"
            
            # Check permissions
            permissions_url = f"{self.base_url}/me/permissions"
            permissions_params = {
                "access_token": self.access_token
            }
            
            permissions_response = requests.get(permissions_url, params=permissions_params, timeout=10)
            
            if permissions_response.status_code != 200:
                return False, "Cannot verify permissions"
            
            permissions_data = permissions_response.json()
            required_permissions = ['ads_read', 'read_insights']
            granted_permissions = [
                perm['permission'] for perm in permissions_data.get('data', [])
                if perm.get('status') == 'granted'
            ]
            
            missing_permissions = [perm for perm in required_permissions if perm not in granted_permissions]
            
            if missing_permissions:
                return False, f"Missing required permissions: {', '.join(missing_permissions)}"
            
            user_data = response.json()
            return True, f"Token valid for user: {user_data.get('name', 'Unknown')}"
            
        except Exception as e:
            return False, f"Error validating token: {str(e)}"
    
    def get_ad_accounts(self) -> List[Dict]:
        """
        Fetch available ad accounts.
        
        Returns:
            List[Dict]: List of ad account information
        """
        try:
            url = f"{self.base_url}/me/adaccounts"
            params = {
                "fields": "id,name,currency,account_status,business",
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                st.error(f"Failed to fetch ad accounts: {response.text}")
                return []
            
            data = response.json()
            return data.get('data', [])
            
        except Exception as e:
            st.error(f"Error fetching ad accounts: {str(e)}")
            return []
    
    def get_campaigns(self, account_id: str, date_range: Dict) -> List[Dict]:
        """
        Fetch campaigns for a specific ad account.
        
        Args:
            account_id: Meta ad account ID
            date_range: Dictionary with 'start_date' and 'end_date'
            
        Returns:
            List[Dict]: List of campaign information
        """
        try:
            url = f"{self.base_url}/{account_id}/campaigns"
            params = {
                "fields": "id,name,objective,status,created_time,updated_time,effective_status",
                "access_token": self.access_token,
                "effective_status": ["ACTIVE", "PAUSED"],
                "time_range": {
                    "since": date_range['start_date'],
                    "until": date_range['end_date']
                }
            }
            
            response = requests.get(url, params=params, timeout=20)
            
            if response.status_code != 200:
                st.error(f"Failed to fetch campaigns: {response.text}")
                return []
            
            data = response.json()
            return data.get('data', [])
            
        except Exception as e:
            st.error(f"Error fetching campaigns: {str(e)}")
            return []
    
    def get_insights_data(self, account_id: str, date_range: Dict, breakdowns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Fetch insights data from Meta API.
        
        Args:
            account_id: Meta ad account ID
            date_range: Dictionary with 'start_date' and 'end_date'
            breakdowns: List of breakdown dimensions
            
        Returns:
            pandas.DataFrame: Insights data
        """
        try:
            url = f"{self.base_url}/{account_id}/insights"
            
            # Default fields matching our expected schema
            fields = [
                'campaign_id', 'campaign_name', 'adset_id', 'adset_name', 
                'ad_id', 'ad_name', 'date_start', 'date_stop',
                'spend', 'impressions', 'clicks', 'actions', 'action_values',
                'objective', 'cpc', 'cpm', 'ctr', 'frequency'
            ]
            
            params = {
                "fields": ",".join(fields),
                "access_token": self.access_token,
                "time_range": {
                    "since": date_range['start_date'],
                    "until": date_range['end_date']
                },
                "time_increment": "1",  # Daily breakdown
                "level": "ad"
            }
            
            # Add breakdowns if specified
            if breakdowns:
                params["breakdowns"] = ",".join(breakdowns)
            
            all_data = []
            
            # Handle pagination
            while True:
                response = requests.get(url, params=params, timeout=30)
                
                if response.status_code != 200:
                    st.error(f"API request failed: {response.text}")
                    break
                
                data = response.json()
                
                if 'data' not in data:
                    break
                
                all_data.extend(data['data'])
                
                # Check for next page
                if 'paging' in data and 'next' in data['paging']:
                    url = data['paging']['next']
                    params = {}  # URL already contains all parameters
                else:
                    break
            
            if not all_data:
                st.warning("No data returned from Meta API")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(all_data)
            
            # Process the data to match our expected schema
            df = self._process_insights_data(df)
            
            st.success(f"Fetched {len(df)} records from Meta API")
            
            return df
            
        except Exception as e:
            st.error(f"Error fetching insights: {str(e)}")
            return pd.DataFrame()
    
    def _process_insights_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process raw Meta API insights data to match our expected schema.
        
        Args:
            df: Raw insights DataFrame
            
        Returns:
            pandas.DataFrame: Processed data matching our schema
        """
        if df.empty:
            return df
        
        processed_df = df.copy()
        
        # Rename and map columns to our schema
        column_mapping = {
            'date_start': 'date',
            'ad_id': 'ad_id',
            'ad_name': 'ad_name',
            'campaign_id': 'campaign_id',
            'campaign_name': 'campaign_name'
        }
        
        processed_df = processed_df.rename(columns=column_mapping)
        
        # Add account_id (extract from campaign_id or use provided account_id)
        if 'account_id' not in processed_df.columns:
            if 'campaign_id' in processed_df.columns:
                processed_df['account_id'] = processed_df['campaign_id'].astype(str).str.split('_').str[0]
            else:
                processed_df['account_id'] = 'unknown'
        
        # Convert numeric fields
        numeric_fields = ['spend', 'impressions', 'clicks']
        for field in numeric_fields:
            if field in processed_df.columns:
                processed_df[field] = pd.to_numeric(processed_df[field], errors='coerce')
                processed_df[field] = processed_df[field].fillna(0)
        
        # Extract purchases and revenue from actions
        if 'actions' in processed_df.columns:
            processed_df['purchases'] = processed_df['actions'].apply(
                lambda x: self._extract_action_value(x, 'purchase') if pd.notnull(x) else 0
            )
        else:
            processed_df['purchases'] = 0
        
        if 'action_values' in processed_df.columns:
            processed_df['revenue'] = processed_df['action_values'].apply(
                lambda x: self._extract_action_value(x, 'purchase') if pd.notnull(x) else 0
            )
        else:
            processed_df['revenue'] = 0
        
        # Convert date
        if 'date' in processed_df.columns:
            processed_df['date'] = pd.to_datetime(processed_df['date'])
        
        # Select only the columns we need
        expected_columns = [
            'account_id', 'campaign_id', 'date', 'spend', 'impressions', 'clicks',
            'purchases', 'revenue', 'ad_id', 'ad_name', 'campaign_name', 'objective'
        ]
        
        # Only keep columns that exist in the dataframe
        final_columns = [col for col in expected_columns if col in processed_df.columns]
        if final_columns:
            result_df = processed_df[final_columns].copy()
            return result_df
        else:
            return pd.DataFrame()
    
    def _extract_action_value(self, actions_data: str, action_type: str) -> float:
        """
        Extract specific action value from Meta API actions field.
        
        Args:
            actions_data: JSON string of actions data
            action_type: Type of action to extract (e.g., 'purchase')
            
        Returns:
            float: Action value
        """
        try:
            if isinstance(actions_data, str):
                actions = json.loads(actions_data)
            else:
                actions = actions_data
            
            if not isinstance(actions, list):
                return 0
            
            for action in actions:
                if action.get('action_type') == action_type:
                    return float(action.get('value', 0))
            
            return 0
            
        except (json.JSONDecodeError, TypeError, ValueError):
            return 0
    
    def save_raw_data(self, data: pd.DataFrame, account_id: str, date_range: Dict) -> str:
        """
        Save raw data to CSV for backup/reference.
        
        Args:
            data: DataFrame to save
            account_id: Ad account ID
            date_range: Date range used for the data
            
        Returns:
            str: Filename where data was saved
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"meta_data_{account_id}_{date_range['start_date']}_{date_range['end_date']}_{timestamp}.csv"
            
            # Save to CSV
            data.to_csv(filename, index=False)
            
            st.success(f"Raw data saved to {filename}")
            return filename
            
        except Exception as e:
            st.warning(f"Could not save raw data: {str(e)}")
            return ""