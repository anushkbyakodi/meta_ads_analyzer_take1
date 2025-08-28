import requests
import json
import pandas as pd
import streamlit as st
import os

class RelevanceClient:
    """Client for interacting with Relevance API to generate insights."""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("RELEVANCE_API_KEY")
        self.base_url = "https://api.relevanceai.com/latest"
        
        if not self.api_key:
            raise ValueError("Relevance API key is required")
    
    def generate_insights(self, kpi_data):
        """
        Generate AI insights from campaign KPI data.
        
        Args:
            kpi_data: pandas.DataFrame with calculated KPIs
            
        Returns:
            str: AI-generated insights text
        """
        try:
            # Prepare data summary for the API
            data_summary = self._prepare_data_summary(kpi_data)
            
            # Print JSON data to console for debugging/reference
            import json
            print("=" * 50)
            print("JSON DATA BEING SENT TO RELEVANCE API:")
            print("=" * 50)
            print(json.dumps(data_summary, indent=2, default=str))
            print("=" * 50)
            
            # Call Relevance API
            insights = self._call_relevance_api(data_summary)
            
            return insights
            
        except Exception as e:
            st.error(f"Error generating insights: {str(e)}")
            return self._generate_fallback_insights(kpi_data)
    
    def _prepare_data_summary(self, df):
        """Prepare a structured summary of the data for the API."""
        summary = {
            "campaign_overview": {
                "total_campaigns": df['campaign_id'].nunique(),
                "date_range": {
                    "start": df['date'].min().strftime('%Y-%m-%d'),
                    "end": df['date'].max().strftime('%Y-%m-%d')
                },
                "total_spend": float(df['spend'].sum()),
                "total_impressions": int(df['impressions'].sum()),
                "total_clicks": int(df['clicks'].sum())
            },
            "performance_metrics": {
                "avg_cpc": float(df['cpc'].mean()),
                "avg_cpm": float(df['cpm'].mean()),
                "avg_ctr": float(df['ctr'].mean()),
                "overall_ctr": float(df['clicks'].sum() / df['impressions'].sum()) if df['impressions'].sum() > 0 else 0
            },
            "campaign_performance": self._get_campaign_performance(df),
            "time_trends": self._get_time_trends(df)
        }
        
        # Add conversion metrics if available
        if 'purchases' in df.columns:
            summary["conversion_metrics"] = {
                "total_purchases": int(df['purchases'].sum()),
                "avg_cpa": float(df[df['cpa'] > 0]['cpa'].mean()) if (df['cpa'] > 0).any() else 0,
                "avg_cvr": float(df['cvr'].mean())
            }
        
        if 'revenue' in df.columns:
            summary["revenue_metrics"] = {
                "total_revenue": float(df['revenue'].sum()),
                "avg_roas": float(df[df['roas'] > 0]['roas'].mean()) if (df['roas'] > 0).any() else 0
            }
        
        return summary
    
    def _get_campaign_performance(self, df):
        """Get top and bottom performing campaigns."""
        campaign_summary = df.groupby('campaign_id').agg({
            'spend': 'sum',
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean',
            'cpc': 'mean'
        }).reset_index()
        
        # Sort by spend to get top campaigns
        top_campaigns = campaign_summary.nlargest(5, 'spend').to_dict('records')
        
        # Sort by CTR to get best performing
        best_ctr = campaign_summary.nlargest(3, 'ctr').to_dict('records')
        worst_ctr = campaign_summary.nsmallest(3, 'ctr').to_dict('records')
        
        return {
            "top_spending": top_campaigns,
            "best_ctr": best_ctr,
            "worst_ctr": worst_ctr
        }
    
    def _get_time_trends(self, df):
        """Get performance trends over time."""
        daily_summary = df.groupby('date').agg({
            'spend': 'sum',
            'clicks': 'sum',
            'impressions': 'sum',
            'ctr': 'mean'
        }).reset_index()
        
        # Calculate week-over-week changes if enough data
        if len(daily_summary) >= 7:
            recent_week = daily_summary.tail(7)
            previous_week = daily_summary.iloc[-14:-7] if len(daily_summary) >= 14 else daily_summary.head(7)
            
            wow_spend_change = ((recent_week['spend'].sum() - previous_week['spend'].sum()) / 
                              previous_week['spend'].sum() * 100) if previous_week['spend'].sum() > 0 else 0
            
            wow_ctr_change = ((recent_week['ctr'].mean() - previous_week['ctr'].mean()) / 
                             previous_week['ctr'].mean() * 100) if previous_week['ctr'].mean() > 0 else 0
            
            return {
                "wow_spend_change": float(wow_spend_change),
                "wow_ctr_change": float(wow_ctr_change),
                "trend_data": daily_summary.tail(14).to_dict('records')
            }
        
        return {"trend_data": daily_summary.to_dict('records')}
    
    def _call_relevance_api(self, data_summary):
        """Make API call to Relevance AI."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Construct the prompt for insight generation
        prompt = self._construct_insight_prompt(data_summary)
        
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a digital marketing expert analyzing campaign performance data. Provide actionable insights and recommendations based on the data provided."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.7
        }
        
        # Note: This is a simplified API call structure
        # The actual Relevance AI API structure may differ
        response = requests.post(
            f"{self.base_url}/completion",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('choices', [{}])[0].get('message', {}).get('content', 'No insights generated')
        else:
            st.warning(f"API call failed with status {response.status_code}")
            return self._generate_fallback_insights_from_summary(data_summary)
    
    def _construct_insight_prompt(self, data_summary):
        """Construct a detailed prompt for insight generation."""
        prompt = f"""
        Analyze the following digital advertising campaign performance data and provide actionable insights:

        CAMPAIGN OVERVIEW:
        - Total Campaigns: {data_summary['campaign_overview']['total_campaigns']}
        - Date Range: {data_summary['campaign_overview']['date_range']['start']} to {data_summary['campaign_overview']['date_range']['end']}
        - Total Spend: ${data_summary['campaign_overview']['total_spend']:,.2f}
        - Total Impressions: {data_summary['campaign_overview']['total_impressions']:,}
        - Total Clicks: {data_summary['campaign_overview']['total_clicks']:,}

        PERFORMANCE METRICS:
        - Average CPC: ${data_summary['performance_metrics']['avg_cpc']:.2f}
        - Average CPM: ${data_summary['performance_metrics']['avg_cpm']:.2f}
        - Average CTR: {data_summary['performance_metrics']['avg_ctr']:.2%}
        - Overall CTR: {data_summary['performance_metrics']['overall_ctr']:.2%}
        """
        
        if 'conversion_metrics' in data_summary:
            prompt += f"""
        CONVERSION METRICS:
        - Total Purchases: {data_summary['conversion_metrics']['total_purchases']:,}
        - Average CPA: ${data_summary['conversion_metrics']['avg_cpa']:.2f}
        - Average CVR: {data_summary['conversion_metrics']['avg_cvr']:.2%}
            """
        
        if 'revenue_metrics' in data_summary:
            prompt += f"""
        REVENUE METRICS:
        - Total Revenue: ${data_summary['revenue_metrics']['total_revenue']:,.2f}
        - Average ROAS: {data_summary['revenue_metrics']['avg_roas']:.2f}x
            """
        
        prompt += """
        
        Please provide:
        1. Key Performance Insights (3-4 bullet points)
        2. Areas of Concern (if any)
        3. Optimization Recommendations (3-5 actionable suggestions)
        4. Budget Allocation Suggestions
        5. Overall Campaign Health Assessment
        
        Focus on practical, data-driven recommendations that can improve campaign performance.
        """
        
        return prompt
    
    def _generate_fallback_insights(self, df):
        """Generate basic insights when API is unavailable."""
        # Still print the JSON data even when using fallback
        data_summary = self._prepare_data_summary(df)
        import json
        print("=" * 50)
        print("JSON DATA THAT WOULD BE SENT TO RELEVANCE API (using fallback):")
        print("=" * 50)
        print(json.dumps(data_summary, indent=2, default=str))
        print("=" * 50)
        
        return self._generate_fallback_insights_from_summary(data_summary)
    
    def _generate_fallback_insights_from_summary(self, summary):
        """Generate fallback insights from data summary."""
        insights = []
        
        # Header
        insights.append("# Campaign Performance Analysis\n")
        
        # Overview
        insights.append("## Campaign Overview")
        insights.append(f"- **Campaigns Analyzed:** {summary['campaign_overview']['total_campaigns']}")
        insights.append(f"- **Date Range:** {summary['campaign_overview']['date_range']['start']} to {summary['campaign_overview']['date_range']['end']}")
        insights.append(f"- **Total Investment:** ${summary['campaign_overview']['total_spend']:,.2f}")
        insights.append(f"- **Total Reach:** {summary['campaign_overview']['total_impressions']:,} impressions")
        insights.append(f"- **Total Engagement:** {summary['campaign_overview']['total_clicks']:,} clicks\n")
        
        # Performance Analysis
        insights.append("## Key Performance Insights")
        
        avg_ctr = summary['performance_metrics']['avg_ctr']
        if avg_ctr > 0.02:  # 2%
            insights.append(f"✅ **Strong CTR Performance:** Average CTR of {avg_ctr:.2%} is above industry benchmarks")
        elif avg_ctr < 0.01:  # 1%
            insights.append(f"⚠️ **CTR Needs Improvement:** Average CTR of {avg_ctr:.2%} is below optimal levels")
        else:
            insights.append(f"📊 **Moderate CTR Performance:** Average CTR of {avg_ctr:.2%} shows room for optimization")
        
        avg_cpc = summary['performance_metrics']['avg_cpc']
        insights.append(f"💰 **Cost Efficiency:** Average CPC of ${avg_cpc:.2f}")
        
        # Conversion insights if available
        if 'conversion_metrics' in summary:
            total_purchases = summary['conversion_metrics']['total_purchases']
            avg_cvr = summary['conversion_metrics']['avg_cvr']
            insights.append(f"🎯 **Conversion Performance:** {total_purchases:,} total conversions with {avg_cvr:.2%} conversion rate")
        
        # Revenue insights if available
        if 'revenue_metrics' in summary:
            total_revenue = summary['revenue_metrics']['total_revenue']
            avg_roas = summary['revenue_metrics']['avg_roas']
            insights.append(f"💸 **Revenue Impact:** ${total_revenue:,.2f} generated with {avg_roas:.2f}x ROAS")
        
        insights.append("")
        
        # Recommendations
        insights.append("## Optimization Recommendations")
        
        if avg_ctr < 0.015:
            insights.append("🔧 **Improve Ad Creative:** Low CTR suggests need for more compelling ad copy and visuals")
        
        if avg_cpc > 2.00:
            insights.append("🎯 **Refine Targeting:** High CPC indicates potential for better audience targeting")
        
        if 'conversion_metrics' in summary and summary['conversion_metrics']['avg_cvr'] < 0.02:
            insights.append("🔄 **Optimize Landing Pages:** Low conversion rate suggests landing page improvements needed")
        
        insights.append("📊 **A/B Testing:** Implement systematic testing of ad variations")
        insights.append("⏰ **Timing Optimization:** Analyze performance by time of day and day of week")
        insights.append("📱 **Device Optimization:** Review performance across different device types")
        
        insights.append("")
        insights.append("## Next Steps")
        insights.append("1. Focus budget on top-performing campaigns")
        insights.append("2. Pause or optimize underperforming campaigns")
        insights.append("3. Scale successful creative and targeting combinations")
        insights.append("4. Implement continuous monitoring and optimization")
        
        return "\n".join(insights)
