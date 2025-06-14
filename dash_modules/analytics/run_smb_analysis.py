# run_comprehensive_smb_analysis.py
from dash_modules.analytics.smb_health_analyzer import SMBFinancialHealthAnalyzer
import json

def print_section(title, content):
    """Helper function to print formatted sections"""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print('='*60)
    print(content)

if __name__ == "__main__":
    analyzer = SMBFinancialHealthAnalyzer()
    
    # Test with different company profiles
    company_profile = {
            "name": "RetailCorp India",
            "industry": "Retail",
            "country": "India",
            "region": "Urban",
            "employees": 25,
            "annual_revenue": 2_000_000,
            "years_in_business": 5,
            "business_model": "B2C",
            "cash_runway": 2.5,
            "net_profit_margin": 0.08,
            "churn_rate": 0.18,
            "recurring_revenue": 0.4,
            "revenue_predictability": 0.6,
            "revenue_concentration": 0.3
        }
    print(f"\n{'#'*80}")
    print(f"ANALYSIS: {company_profile['name']}")
    print('#'*80)
        
    print(f"\n🏢 Company Overview:")
    print(f"   Industry: {company_profile['industry']}")
    print(f"   Location: {company_profile['country']}, {company_profile['region']}")
    print(f"   Size: {company_profile['employees']} employees")
    print(f"   Revenue: ${company_profile['annual_revenue']:,}")
    print(f"   Experience: {company_profile['years_in_business']} years")
    print(f"   Model: {company_profile['business_model']}")
        
    print(f"\n📊 Calculating comprehensive health assessment...")
    score_result = analyzer.calculate_smb_health_score(company_profile)
        
        # Main Results
    print_section("FINANCIAL HEALTH SCORE", f"""
Overall Score: {score_result['overall_score']}/100
Health Rating: {score_result['health_rating']}
Peer Comparisons: {score_result['peer_count']} similar companies

Detailed Breakdown:
  • Liquidity Score: {score_result['detailed_scores']['liquidity_score']:.1f}/100
  • Profitability Score: {score_result['detailed_scores']['profitability_score']:.1f}/100
  • Growth Potential: {score_result['detailed_scores']['growth_potential']:.1f}/100
  • Risk Management: {score_result['detailed_scores']['risk_score']:.1f}/100
  • Operational Efficiency: {score_result['detailed_scores']['efficiency_score']:.1f}/100
        """)
        
        # AI Analysis
    print_section("AI FINANCIAL ANALYSIS", score_result['ai_analysis'])
        
        # Actionable Insights
    print(f"\n💡 Generating actionable recommendations...")
    insights = analyzer.generate_smb_specific_insights(company_profile, score_result)
    print_section("ACTIONABLE RECOMMENDATIONS", insights)
        
        # Benchmarking Report
    print(f"\n📈 Generating benchmarking report...")
    peers = analyzer._get_smb_peer_data(company_profile)  # Get peers for benchmarking
    benchmarking = analyzer.generate_benchmarking_report(company_profile, score_result, peers)
    print_section("COMPETITIVE BENCHMARKING", benchmarking)
        
        # Summary
    print_section("EXECUTIVE SUMMARY", f"""
Company: {company_profile['name']}
Industry: {company_profile['industry']} ({company_profile['country']})
Financial Health: {score_result['overall_score']}/100 ({score_result['health_rating']})

Key Metrics:
- Cash Runway: {company_profile['cash_runway']} months
- Profit Margin: {company_profile['net_profit_margin']*100:.1f}%
- Customer Churn: {company_profile['churn_rate']*100:.1f}%
- Revenue Predictability: {company_profile['revenue_predictability']*100:.1f}%

Recommendation: {"Immediate attention required" if score_result['overall_score'] < 60 else "Monitor and optimize" if score_result['overall_score'] < 80 else "Strong position, focus on growth"}
        """)
        
