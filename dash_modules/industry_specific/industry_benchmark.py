import streamlit as st
import pandas as pd
import json
from pathlib import Path
from utils.granite import summarize_with_granite
from utils.business_profile import load_profile
import plotly.express as px
import plotly.graph_objects as go
from dash_modules.analytics.run_smb_analysis import load_ledger
from dash_modules.analytics.run_smb_analysis import derive_metrics

def render_industry_benchmark():
    st.title("Industry Benchmark Analysis")
    
    # Load business profile and peer data
    business_profile = load_profile()
    peer_data = load_peer_benchmark_data()
    
    if not business_profile:
        st.warning("Please complete your business profile to enable industry benchmarking.")
        return
    
    # Extract relevant information
    industry = business_profile.get('industry')
    country = business_profile.get('country')
    region = business_profile.get('region', 'Urban')  # Default to Urban if not specified
    
    if not industry or not country:
        st.warning("Industry and country information is required for benchmarking. Please update your business profile.")
        return
    
    # Filter relevant peers
    peers_df = filter_relevant_peers(peer_data, business_profile)
    
    if len(peers_df) == 0:
        st.warning(f"Not enough peer data available for {industry} in {region}, {country}. Showing general industry data instead.")
        # Fall back to just industry + country match
        peers_df = peer_data[(peer_data['industry'] == industry) & (peer_data['country'] == country)]
    
    # Extract company metrics from profile/data
    company_metrics = extract_company_metrics(business_profile)
    
    # Calculate percentiles
    percentiles = calculate_percentiles(peers_df, company_metrics)
    
    # Create benchmark visualization section
    st.subheader("Performance Benchmarking")
    
    # 1. Benchmark comparison table
    benchmark_table = create_benchmark_table(peers_df, company_metrics, percentiles)
    
    # Apply conditional formatting to the table
    styled_table = style_benchmark_table(benchmark_table)
    st.dataframe(styled_table, use_container_width=True)
    
    # 2. Radar chart for visual comparison
    st.subheader("🎯 Performance Radar")
    fig = create_radar_chart(peers_df, company_metrics)
    st.plotly_chart(fig, use_container_width=True)
    
    # 3. Industry trends from Granite
    st.markdown("---")
    st.subheader("🔮 Industry Trends & Outlook")
    
    # Get industry trends using Granite
    with st.spinner("Analyzing industry trends..."):
        industry_trends = get_industry_trends(industry, country, region, peers_df)
    
    # Display the trends in a clean format
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Current Industry Trends")
        for i, trend in enumerate(industry_trends['trends'], 1):
            st.markdown(f"**{i}.** {trend}")
        
        st.markdown("### Industry Forecast")
        st.markdown(f"*{industry_trends['forecast']}*")
    
    with col2:
        st.markdown("### Key Metrics to Monitor")
        for metric in industry_trends['metrics_to_watch']:
            st.markdown(f"• {metric}")
        
        if 'action_items' in industry_trends:
            st.markdown("### Recommended Actions")
            for item in industry_trends['action_items']:
                st.markdown(f"• {item}")


def load_peer_benchmark_data():
    """Load peer benchmark data from file or API"""
    # Replace with actual data loading logic
    try:
        # Path would be adjusted to your actual data location
        peer_data_path = Path("data/global_smb_benchmark_dataset_5000.csv")
        if peer_data_path.exists():
            return pd.read_csv(peer_data_path)
        else:
            # Fallback to API or other source
            # Return empty DataFrame with expected columns if data not available
            return pd.DataFrame(columns=['company_id', 'industry', 'country', 'region', 
                                         'revenue', 'employees', 'years_in_business',
                                         'business_model', 'revenue_predictability', 
                                         'cash_runway_months', 'revenue_concentration_pct',
                                         'cash_flow_rating', 'customer_churn_rate',
                                         'net_profit_margin', 'recurring_revenue_pct'])
    except Exception as e:
        st.error(f"Error loading peer benchmark data: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error


def filter_relevant_peers(df, company_info):
    """Filter peer companies based on same industry, country, region"""
    return df[
        (df['industry'] == company_info.get('industry')) & 
        (df['country'] == company_info.get('country')) & 
        (df['region'] == company_info.get('region', 'Urban'))
    ]


def extract_company_metrics(business_profile):
    """Extract metrics from business profile to use for comparison"""
    # This would extract relevant metrics from your business profile
    # Adjust according to your actual data structure
    df = load_ledger()
    derived = derive_metrics(df)
    metrics = {
        'revenue': derived["annual_revenue"],
        'employees': business_profile.get('employee_count', 0),
        'revenue_predictability': business_profile.get('revenue_predictability', 0.5),
        'cash_runway_months': derived["cash_runway"],
        'revenue_concentration_pct': business_profile.get('revenue_concentration', 0.5),
        'cash_flow_rating': business_profile.get('cash_flow_rating', 'adequate'),
        'customer_churn_rate': business_profile.get('churn_rate', 0.15),
        'net_profit_margin': derived["net_profit_margin"],
        'recurring_revenue_pct': business_profile.get('recurring_revenue', 0.4),
    }
    return metrics


def calculate_percentiles(peers_df, company_metrics):
    """Calculate where the company stands in percentiles against peers"""
    percentiles = {}
    metrics_to_compare = [
        'revenue', 'employees', 'revenue_predictability', 
        'cash_runway_months', 'customer_churn_rate',
        'net_profit_margin', 'recurring_revenue_pct'
    ]
    
    for metric in metrics_to_compare:
        if metric in company_metrics and metric in peers_df.columns and not peers_df.empty:
            # For metrics where lower is better (like churn), invert the percentile
            if metric in ['customer_churn_rate', 'revenue_concentration_pct']:
                percentiles[metric] = round(
                    sum(peers_df[metric] > company_metrics[metric]) / len(peers_df) * 100
                )
            else:
                percentiles[metric] = round(
                    sum(peers_df[metric] < company_metrics[metric]) / len(peers_df) * 100
                )
            
    return percentiles


def create_benchmark_table(peers_df, company_metrics, percentiles):
    """Create a comparison table of company vs industry averages"""
    metrics_to_display = {
        'revenue': ('Revenue', '\$'),
        'revenue_predictability': ('Revenue Predictability', ''),
        'cash_runway_months': ('Cash Runway', 'months'),
        'customer_churn_rate': ('Customer Churn', '%'),
        'net_profit_margin': ('Net Profit Margin', '%'),
        'recurring_revenue_pct': ('Recurring Revenue', '%')
    }
    
    # Prepare data for table
    table_data = []
    
    for metric, (display_name, unit) in metrics_to_display.items():
        row = {'Metric': display_name}
        
        # Your company value
        if metric in company_metrics:
            value = company_metrics[metric]
            if unit == '\$':
                row['Your Company'] = f"\${value:,.2f}"
            elif unit == '%':
                row['Your Company'] = f"{value*100:.1f}%"
            else:
                row['Your Company'] = f"{value}{unit}"
        else:
            row['Your Company'] = "N/A"
        
        # Industry average
        if metric in peers_df.columns and not peers_df.empty:
            avg_value = peers_df[metric].mean()
            if unit == '\$':
                row['Industry Average'] = f"\${avg_value:,.2f}"
            elif unit == '%':
                row['Industry Average'] = f"{avg_value*100:.1f}%"
            else:
                row['Industry Average'] = f"{avg_value:.2f}{unit}"
        else:
            row['Industry Average'] = "N/A"
        
        # Percentile
        if metric in percentiles:
            row['Percentile'] = f"{percentiles[metric]}%"
            
            # Determine performance status
            if metric in ['revenue', 'revenue_predictability', 'cash_runway_months', 'net_profit_margin', 'recurring_revenue_pct']:
                # Higher is better
                if percentiles[metric] >= 75:
                    row['Status'] = "Excellent"
                elif percentiles[metric] >= 50:
                    row['Status'] = "Good"
                elif percentiles[metric] >= 25:
                    row['Status'] = "Fair"
                else:
                    row['Status'] = "Poor"
            else:
                # Lower is better (e.g., churn)
                if percentiles[metric] <= 25:
                    row['Status'] = "Excellent"
                elif percentiles[metric] <= 50:
                    row['Status'] = "Good"
                elif percentiles[metric] <= 75:
                    row['Status'] = "Fair"
                else:
                    row['Status'] = "Poor"
        else:
            row['Percentile'] = "N/A"
            row['Status'] = "N/A"
            
        table_data.append(row)
    
    return pd.DataFrame(table_data)


def style_benchmark_table(df):
    """Apply styling to the benchmark table"""
    # This is a placeholder - in Streamlit you might need to use different 
    # styling approaches depending on the version and methods available
    
    # For Streamlit's st.dataframe, we can use pandas styling
    styled_df = df.style.apply(lambda x: [
        f"background-color: {'#c6efce' if v == 'Excellent' else '#ffeb9c' if v == 'Good' else '#ffc7ce' if v == 'Poor' else '#ffffff'}" 
        for v in x
    ], axis=1, subset=['Status'])
    
    return styled_df


def create_radar_chart(peers_df, company_metrics):
    """Create a radar chart comparing company to industry averages with proper scaling"""
    # Select metrics to display in radar chart
    metrics = ['revenue_predictability', 'cash_runway_months', 
               'net_profit_margin', 'recurring_revenue_pct']
    
    # For customer_churn_rate, we invert it (lower is better)
    if 'customer_churn_rate' in peers_df.columns and 'customer_churn_rate' in company_metrics:
        metrics.append('customer_churn_rate')
    
    # Prepare data with user-friendly labels
    categories = [
        'Revenue Predictability', 
        'Cash Runway (months)', 
        'Net Profit Margin', 
        'Recurring Revenue %'
    ]
    
    if 'customer_churn_rate' in metrics:
        categories.append('Customer Retention')  # Inverted from churn
    
    # Calculate industry averages and normalize values
    normalized_industry = []
    normalized_company = []
    
    # Typical ranges for normalization (min, max)
    # This helps set appropriate scales for each metric
    metric_scales = {
        'revenue_predictability': (0, 1),      # 0-1 scale
        'cash_runway_months': (0, 12),         # 0-12 months
        'net_profit_margin': (-0.1, 0.3),      # -10% to 30%
        'recurring_revenue_pct': (0, 1),       # 0-100%
        'customer_churn_rate': (0, 1)          # 0-100% (inverted in calculation)
    }
    
    for metric in metrics:
        if metric in peers_df.columns and not peers_df.empty:
            min_val, max_val = metric_scales.get(metric, (0, 1))
            
            # Get raw values
            industry_val = peers_df[metric].mean()
            company_val = company_metrics.get(metric, 0)
            
            # Handle special cases
            if metric == 'customer_churn_rate':
                # Invert churn to retention (1 - churn)
                industry_val = 1 - industry_val
                if metric in company_metrics:
                    company_val = 1 - company_val
            
            # Normalize to 0-1 scale
            norm_industry = max(0, min(1, (industry_val - min_val) / (max_val - min_val)))
            norm_company = max(0, min(1, (company_val - min_val) / (max_val - min_val)))
            
            normalized_industry.append(norm_industry)
            normalized_company.append(norm_company)
    
    # Create radar chart with normalized values
    fig = go.Figure()
    
    # Add industry trace
    fig.add_trace(go.Scatterpolar(
        r=normalized_industry,
        theta=categories,
        fill='toself',
        name='Industry Average',
        line_color='rgba(31, 119, 180, 0.8)',
        hoverinfo='text',
        text=[f"{cat}: {val:.2f}" for cat, val in zip(categories, normalized_industry)]
    ))
    
    # Add company trace
    fig.add_trace(go.Scatterpolar(
        r=normalized_company,
        theta=categories,
        fill='toself',
        name='Your Company',
        line_color='rgba(255, 127, 14, 0.8)',
        hoverinfo='text',
        text=[f"{cat}: {val:.2f}" for cat, val in zip(categories, normalized_company)]
    ))
    
    # Configure the layout for better readability
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],  # Normalized scale
                tickvals=[0, 0.25, 0.5, 0.75, 1],
                ticktext=['0%', '25%', '50%', '75%', '100%'],
                tickfont=dict(size=10),
                gridcolor='rgba(0,0,0,0.1)',
                linecolor='rgba(0,0,0,0.1)',
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color='rgb(68, 68, 68)'),
                linecolor='rgba(0,0,0,0.2)',
            )
        ),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=1.1,
            xanchor="left",
            x=0.01
        ),
        margin=dict(l=80, r=80, t=50, b=50),
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    
    # Add annotation explaining the chart
    fig.add_annotation(
        text="Metrics normalized to percentage scale",
        xref="paper", yref="paper",
        x=0.5, y=-0.15,
        showarrow=False,
        font=dict(size=11, color="gray")
    )
    
    return fig


def get_industry_trends(industry, country, region, peers_df):
    """
    Get real-time industry trends analysis using IBM Granite with robust parsing
    and error handling.
    """
    # Summarize peer data for context
    metrics_summary = {
        "avg_revenue": peers_df['revenue'].mean() if not peers_df.empty else 0,
        "avg_profit_margin": peers_df['net_profit_margin'].mean() if not peers_df.empty else 0,
        "avg_churn": peers_df['customer_churn_rate'].mean() if not peers_df.empty else 0,
        "avg_cash_runway": peers_df['cash_runway_months'].mean() if not peers_df.empty else 0,
        "avg_recurring_revenue": peers_df['recurring_revenue_pct'].mean() if not peers_df.empty else 0
    }
    
    # Construct the prompt for Granite - asking for JSON format explicitly
    prompt = f"""
    Based on the following financial metrics for {industry} companies in {region} {country}:
    
    Average Revenue: \${metrics_summary['avg_revenue']:,.2f}
    Average Profit Margin: {metrics_summary['avg_profit_margin']*100:.1f}%
    Average Customer Churn: {metrics_summary['avg_churn']*100:.1f}%
    Average Cash Runway: {metrics_summary['avg_cash_runway']:.1f} months
    Average Recurring Revenue: {metrics_summary['avg_recurring_revenue']*100:.1f}%
    
    Please analyze current {industry} industry conditions in {region} {country} and provide:
    
    1. Three specific current industry trends affecting {industry} businesses
    2. Three key financial metrics these businesses should closely monitor
    3. A brief forecast for this industry in the next fiscal year
    4. Two actionable recommendations for businesses in this sector
    
    IMPORTANT: Return your analysis as a valid JSON object with the following structure:
    {{
        "trends": ["trend1", "trend2", "trend3"],
        "metrics_to_watch": ["metric1", "metric2", "metric3"],
        "forecast": "Your forecast text here",
        "action_items": ["action1", "action2"]
    }}
    
    Ensure your JSON is properly formatted with all quotes and commas.
    """
    
    # Call Granite for analysis
    try:
        # Get response from Granite
        raw_response = summarize_with_granite(prompt)
        
        # Parse the JSON response with multiple fallback methods
        trends_data = parse_granite_response(raw_response, industry, country, region)
        
        # Validate the parsed data and ensure all required fields exist
        trends_data = validate_and_complete_trends_data(trends_data, industry, country, region)
        
        return trends_data
        
    except Exception as e:
        st.error(f"Error retrieving industry trends: {str(e)}")
        # Return fallback data in case of any errors
        return generate_fallback_trends(industry, country, region)


def parse_granite_response(response, industry, country, region):
    """
    Parse the response from Granite with multiple parsing strategies
    and robust error handling.
    """
    # First attempt: Direct JSON parsing
    try:
        # Try to find JSON content within the response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        
        if json_start >= 0 and json_end > 0:
            json_content = response[json_start:json_end]
            return json.loads(json_content)
    except json.JSONDecodeError:
        pass  # Continue to next parsing strategy
    
    # Second attempt: Look for code blocks that might contain JSON
    try:
        import re
        code_block_pattern = r"```(?:json)?(.*?)```"
        code_blocks = re.findall(code_block_pattern, response, re.DOTALL)
        
        for block in code_blocks:
            try:
                return json.loads(block.strip())
            except json.JSONDecodeError:
                continue
    except:
        pass  # Continue to next parsing strategy
    
    # Third attempt: Structured text parsing if JSON parsing fails
    try:
        trends = []
        metrics = []
        forecast = ""
        actions = []
        
        # Look for trends section
        trends_section = re.search(r"(?:trends|industry trends):?(.*?)(?:metrics|key metrics|financial metrics|forecast)", 
                                  response, re.IGNORECASE | re.DOTALL)
        if trends_section:
            trend_lines = [line.strip() for line in trends_section.group(1).split('\n') if line.strip()]
            # Look for numbered or bullet points
            for line in trend_lines:
                # Remove numbers, bullets, etc.
                cleaned_line = re.sub(r'^[•\-\d\.\s]+', '', line).strip()
                if cleaned_line and len(cleaned_line) > 10:  # Arbitrary min length
                    trends.append(cleaned_line)
        
        metrics_section = re.search(r"(?:metrics|key metrics|financial metrics):?(.*?)(?:forecast|outlook|prediction)", 
                                   response, re.IGNORECASE | re.DOTALL)
        if metrics_section:
            metric_lines = [line.strip() for line in metrics_section.group(1).split('\n') if line.strip()]
            for line in metric_lines:
                cleaned_line = re.sub(r'^[•\-\d\.\s]+', '', line).strip()
                if cleaned_line and len(cleaned_line) > 3:  # Metrics can be shorter
                    metrics.append(cleaned_line)
        
        # Look for forecast section
        forecast_section = re.search(r"(?:forecast|outlook|prediction):?(.*?)(?:action|recommendation|\$)", 
                                    response, re.IGNORECASE | re.DOTALL)
        if forecast_section:
            forecast = forecast_section.group(1).strip()
        
        # Look for action items
        actions_section = re.search(r"(?:action|recommendation).*?:?(.*?)\$", 
                                   response, re.IGNORECASE | re.DOTALL)
        if actions_section:
            action_lines = [line.strip() for line in actions_section.group(1).split('\n') if line.strip()]
            for line in action_lines:
                cleaned_line = re.sub(r'^[•\-\d\.\s]+', '', line).strip()
                if cleaned_line and len(cleaned_line) > 10:
                    actions.append(cleaned_line)
        
        # Construct and return the structured data
        parsed_data = {
            "trends": trends[:3] if trends else [],  # Limit to 3
            "metrics_to_watch": metrics[:3] if metrics else [],
            "forecast": forecast,
            "action_items": actions[:2] if actions else []  # Limit to 2
        }
        
        # Only return this if we have at least some valid content
        if (parsed_data["trends"] or parsed_data["metrics_to_watch"] or 
            parsed_data["forecast"] or parsed_data["action_items"]):
            return parsed_data
    except:
        pass  # Continue to fallback strategy
    
    # If all parsing methods fail, extract any useful information
    try:
        # Simple extraction of sentences that might contain useful information
        sentences = [s.strip() for s in response.split('.') if len(s.strip()) > 20]
        forecast_candidates = [s for s in sentences if any(word in s.lower() for word in 
                             ['forecast', 'predict', 'future', 'expect', 'outlook', 'next year'])]
        
        trend_candidates = [s for s in sentences if any(word in s.lower() for word in 
                          ['trend', 'movement', 'shift', 'change', 'growing', 'increasing', 'decreasing'])]
        
        metric_candidates = [s for s in sentences if any(word in s.lower() for word in 
                           ['metric', 'measure', 'monitor', 'track', 'kpi', 'indicator'])]
        
        action_candidates = [s for s in sentences if any(word in s.lower() for word in 
                            ['action', 'recommend', 'should', 'must', 'consider', 'implement'])]
        
        return {
            "trends": trend_candidates[:3] if trend_candidates else [],
            "metrics_to_watch": metric_candidates[:3] if metric_candidates else [],
            "forecast": forecast_candidates[0] + '.' if forecast_candidates else "",
            "action_items": action_candidates[:2] if action_candidates else []
        }
    except:
        # If everything fails, return empty structure
        # The validation function will fill it with fallbacks
        return {
            "trends": [],
            "metrics_to_watch": [],
            "forecast": "",
            "action_items": []
        }


def validate_and_complete_trends_data(data, industry, country, region):
    """
    Ensure all required fields exist in the trends data and are properly formatted.
    Fill in any missing data with reasonable defaults.
    """
    validated = {
        "trends": [],
        "metrics_to_watch": [],
        "forecast": "",
        "action_items": []
    }
    
    # Validate trends
    if "trends" in data and isinstance(data["trends"], list) and data["trends"]:
        validated["trends"] = [str(trend) for trend in data["trends"][:3]]
    
    # If trends are empty or less than 3, add generic ones
    while len(validated["trends"]) < 3:
        generic_trends = [
            f"Increasing digital transformation across {industry} businesses",
            f"Growing focus on sustainability practices in {industry}",
            f"Rising operational costs affecting profit margins in {region} {industry}"
        ]
        for trend in generic_trends:
            if trend not in validated["trends"]:
                validated["trends"].append(trend)
                if len(validated["trends"]) >= 3:
                    break
    
    # Validate metrics to watch
    if "metrics_to_watch" in data and isinstance(data["metrics_to_watch"], list) and data["metrics_to_watch"]:
        validated["metrics_to_watch"] = [str(metric) for metric in data["metrics_to_watch"][:3]]
    
    # If metrics are empty or less than 3, add generic ones
    while len(validated["metrics_to_watch"]) < 3:
        generic_metrics = [
            "Cash Flow",
            "Customer Retention Rate",
            "Operating Profit Margin"
        ]
        for metric in generic_metrics:
            if metric not in validated["metrics_to_watch"]:
                validated["metrics_to_watch"].append(metric)
                if len(validated["metrics_to_watch"]) >= 3:
                    break
    
    # Validate forecast
    if "forecast" in data and data["forecast"] and isinstance(data["forecast"], str):
        validated["forecast"] = data["forecast"]
    else:
        validated["forecast"] = f"The {industry} industry in {region} {country} is expected to face moderate growth with increased competition and evolving customer demands in the next fiscal year."
    
    # Validate action items
    if "action_items" in data and isinstance(data["action_items"], list) and data["action_items"]:
        validated["action_items"] = [str(item) for item in data["action_items"][:2]]
    
    # If action items are empty or less than 2, add generic ones
    while len(validated["action_items"]) < 2:
        generic_actions = [
            f"Invest in technology to improve operational efficiency",
            f"Develop customer retention strategies to reduce churn"
        ]
        for action in generic_actions:
            if action not in validated["action_items"]:
                validated["action_items"].append(action)
                if len(validated["action_items"]) >= 2:
                    break
    
    return validated


def generate_fallback_trends(industry, country, region):
    """Generate fallback trend data if Granite API call fails"""
    industry_specific_data = {
        "Retail": {
            "trends": [
                "Omnichannel integration becoming essential for customer retention",
                "Increased adoption of AI for inventory and demand forecasting",
                "Growing emphasis on experiential retail to combat e-commerce pressure"
            ],
            "metrics": ["Inventory turnover", "Customer acquisition cost", "Same-store sales growth"],
            "forecast": "The retail sector faces moderate growth challenges amid digital transformation pressures and changing consumer behaviors."
        },
        "Medical": {
            "trends": [
                "Telehealth services expanding beyond pandemic-driven adoption",
                "Value-based care models reshaping reimbursement structures",
                "Integration of AI and ML in diagnostic and administrative processes"
            ],
            "metrics": ["Patient retention rate", "Average reimbursement time", "Operating margin"],
            "forecast": "The healthcare sector continues to show resilience with steady growth projections despite regulatory challenges."
        },
        "Hospitality": {
            "trends": [
                "Experience-driven offerings commanding premium prices",
                "Contactless service options becoming standard expectations",
                "Sustainability initiatives increasingly influencing customer choices"
            ],
            "metrics": ["Revenue per available room (RevPAR)", "Customer satisfaction score", "Labor cost percentage"],
            "forecast": "Recovery continues in the hospitality sector with cautious optimism for growth in leisure travel segments."
        },
        "Shipping/Freight": {
            "trends": [
                "Supply chain visibility solutions seeing increased adoption",
                "Last-mile optimization becoming key competitive advantage",
                "Alternative fuel adoption accelerating amid environmental regulations"
            ],
            "metrics": ["Asset utilization rate", "Fuel efficiency", "On-time delivery percentage"],
            "forecast": "The shipping industry faces mixed growth prospects with opportunities in technology integration offsetting fuel cost challenges."
        }
    }
    
    # Get industry specific data or use generic if industry not found
    industry_data = industry_specific_data.get(industry, {
        "trends": [
            f"Digital transformation accelerating across {industry}",
            f"Customer retention becoming priority focus in {industry}",
            f"Operational efficiency initiatives gaining traction"
        ],
        "metrics": ["Cash flow", "Customer retention rate", "Operating margin"],
        "forecast": f"The {industry} industry shows cautious growth potential amid evolving market conditions."
    })
    
    return {
        "trends": industry_data["trends"],
        "metrics_to_watch": industry_data["metrics"],
        "forecast": industry_data["forecast"],
        "action_items": [
            f"Invest in digital capabilities to enhance customer experience",
            f"Implement data analytics for improved decision-making"
        ]
    }