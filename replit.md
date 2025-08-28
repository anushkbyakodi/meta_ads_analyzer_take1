# Overview

AdSummarizer is a comprehensive Streamlit-based web application designed to process and analyze digital advertising campaign data from multiple sources. The application supports both Meta (Facebook/Instagram) Ads API integration and Excel file uploads, providing a unified workflow for campaign analysis. It generates AI-powered insights along with comprehensive KPI calculations, offering marketers and analysts automated reporting capabilities to understand campaign performance through visualizations and intelligent recommendations.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit for web interface
- **UI Components**: Multi-column layouts with sidebar configuration panel
- **Visualization**: Plotly Express and Plotly Graph Objects for interactive charts and graphs
- **State Management**: Streamlit session state for maintaining processed data, insights, and KPIs across user interactions

## Backend Architecture
- **Modular Design**: Separated into specialized classes for different responsibilities
  - `DataProcessor`: Handles Excel file loading, data cleaning, and normalization
  - `KPICalculator`: Computes marketing metrics (CPC, CPM, CTR, CPA, ROAS, CVR)
  - `RelevanceClient`: Manages AI insights generation through external API
  - `ExcelValidator`: Validates file structure and data quality
  - `MetaAdsClient`: Handles Meta Marketing API integration for Facebook/Instagram data
- **Dual Input Processing**: Unified pipeline supporting both Meta API and Excel data sources
- **Data Processing Pipeline**: Sequential processing from raw data to cleaned datasets with calculated KPIs
- **Error Handling**: Comprehensive validation and fallback mechanisms for data processing failures

## Data Architecture
- **Input Sources**: 
  - Meta Marketing API (Facebook/Instagram Ads)
  - Excel files with predefined schema
- **Required Fields**: account_id, campaign_id, date, spend, impressions, clicks
- **Optional Fields**: purchases, revenue, ad_id, ad_name, campaign_name, objective, creative_id
- **Data Types**: Pandas DataFrames for in-memory data manipulation and analysis
- **Column Mapping**: Flexible mapping system to handle variations in input column names
- **API Integration**: Direct data fetching from Meta with automatic schema normalization

## Configuration Management
- **API Key Management**: Secure handling of Relevance API credentials through environment variables or user input
- **Validation Rules**: Configurable data validation with required and optional column specifications
- **KPI Definitions**: Centralized configuration of marketing metric calculations and definitions

# External Dependencies

## AI Services
- **Relevance AI API**: External service for generating automated insights and recommendations from campaign data
- **API Endpoint**: https://api.relevanceai.com/latest
- **Authentication**: API key-based authentication

## Core Libraries
- **Streamlit**: Web application framework for the user interface
- **Pandas**: Data manipulation and analysis
- **NumPy**: Numerical computing for KPI calculations
- **Plotly**: Interactive data visualization components

## File Processing
- **Excel Support**: Built-in pandas Excel reading capabilities for .xlsx and .xls files
- **BytesIO**: In-memory file handling for uploaded Excel files

## Development Tools
- **Error Tracking**: Python traceback module for debugging and error reporting
- **Environment Variables**: OS module for secure configuration management