import json
import os
import streamlit as st
from openai import OpenAI
from constants import GPT_PROMPT


class GPTClient:
    """Client for generating insights using OpenAI GPT API."""

    def __init__(self, api_key=None):
        self.api_key = os.environ['GPT_API_KEY']
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key)

    def generate_insights(self, kpi_data):
        """
        Generate AI insights from campaign KPI data using GPT.
        
        Args:
            kpi_data: pandas.DataFrame with calculated KPIs
            
        Returns:
            str: AI-generated insights text
        """
        try:
            # Convert DataFrame to JSON format
            json_data = kpi_data.to_dict('records')

            # Construct the full prompt with data
            full_prompt = GPT_PROMPT + "\n\n" + json.dumps(
                json_data, indent=2, default=str)

            # Print the data being sent to GPT (for debugging)
            print("=" * 50)
            print("DATA BEING SENT TO GPT API:")
            print("=" * 50)
            print(json.dumps(json_data, indent=2, default=str))
            print("=" * 50)

            # Call GPT API
            response = self.client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for better analysis
                messages=[{
                    "role":
                    "system",
                    "content":
                    "You are a digital marketing expert specializing in campaign performance analysis and optimization."
                }, {
                    "role": "user",
                    "content": full_prompt
                }],
                max_tokens=2000,
                temperature=0.7)

            insights = response.choices[0].message.content

            return insights

        except Exception as e:
            st.error(f"Error generating GPT insights: {str(e)}")
            return self._generate_fallback_insights(kpi_data)

    def _generate_fallback_insights(self, df):
        """Generate basic insights when GPT API is unavailable."""
        # Still print the JSON data even when using fallback
        json_data = df.to_dict('records')
        print("=" * 50)
        print("JSON DATA THAT WOULD BE SENT TO GPT API (using fallback):")
        print("=" * 50)
        print(json.dumps(json_data, indent=2, default=str))
        print("=" * 50)

        return self._generate_basic_insights(df)

    def _generate_basic_insights(self, df):
        """Generate basic insights from data when API is unavailable."""
        insights = []

        # Header
        insights.append("# Campaign Performance Analysis (Basic Insights)\n")

        # Overview
        insights.append("## Campaign Overview")
        insights.append(
            f"- **Total Campaigns:** {df['campaign_name'].nunique()}")
        insights.append(f"- **Total Records:** {len(df)}")
        insights.append(
            f"- **Date Range:** {df['date'].min().date()} to {df['date'].max().date()}"
        )
        insights.append(f"- **Total Spend:** ₹{df['spend'].sum():,.2f}")
        insights.append(
            f"- **Total Impressions:** {df['impressions'].sum():,}")
        insights.append(f"- **Total Clicks:** {df['clicks'].sum():,}")

        if 'purchases' in df.columns:
            insights.append(
                f"- **Total Conversions:** {df['purchases'].sum():,}")

        insights.append("")

        # Performance Analysis
        insights.append("## Key Performance Metrics")

        avg_ctr = df['ctr'].mean()
        avg_cpc = df['cpc'].mean()
        avg_cpm = df['cpm'].mean()

        insights.append(
            f"- **Average CTR (Click-Through Rate):** {avg_ctr:.2%}")
        insights.append(f"- **Average CPC (Cost Per Click):** ₹{avg_cpc:.2f}")
        insights.append(
            f"- **Average CPM (Cost Per 1000 Impressions):** ₹{avg_cpm:.2f}")

        if 'purchases' in df.columns:
            avg_cvr = df['cvr'].mean() if 'cvr' in df.columns else 0
            avg_cpa = df['cpa'].mean() if 'cpa' in df.columns else 0
            insights.append(
                f"- **Average CVR (Conversion Rate):** {avg_cvr:.2%}")
            insights.append(
                f"- **Average CPA (Cost Per Acquisition):** ₹{avg_cpa:.2f}")
        else:
            avg_cvr = 0

        insights.append("")

        # Top Campaigns
        insights.append("## Top Performing Campaigns by Spend")
        top_campaigns = df.groupby('campaign_name')['spend'].sum().nlargest(5)
        for i, (campaign, spend) in enumerate(top_campaigns.items(), 1):
            insights.append(f"{i}. **{campaign}**: ₹{spend:,.2f}")

        insights.append("")

        # Recommendations
        insights.append("## Basic Recommendations")

        if avg_ctr < 0.01:  # Less than 1%
            insights.append(
                "- **Improve Ad Creative**: CTR is below 1%, consider testing new visuals and copy"
            )

        if avg_cpc > 50:  # High CPC for INR
            insights.append(
                "- **Optimize Targeting**: High CPC suggests need for better audience targeting"
            )

        if 'purchases' in df.columns:
            if df['purchases'].sum() == 0:
                insights.append(
                    "- **Conversion Tracking**: No conversions detected, verify tracking setup"
                )
            elif avg_cvr < 0.01:
                insights.append(
                    "- **Landing Page Optimization**: Low conversion rate suggests landing page improvements needed"
                )

        insights.append(
            "- **Budget Optimization**: Focus budget on top-performing campaigns"
        )
        insights.append(
            "- **A/B Testing**: Implement systematic testing of ad variations")
        insights.append(
            "- **Performance Monitoring**: Set up regular performance review cycles"
        )

        return "\n".join(insights)
