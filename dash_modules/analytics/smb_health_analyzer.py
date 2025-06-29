# smb_health_analyzer_enhanced.py
from dash_modules.analytics.smb_rag import SMBBenchmarkRAG
from utils.granite import summarize_with_granite

class SMBFinancialHealthAnalyzer:
    def __init__(self):
        self.smb_benchmarks_rag = SMBBenchmarkRAG()
    
    def calculate_smb_health_score(self, company_profile):
        """Main method to calculate SMB health score"""
        print(" Getting peer data...")
        smb_peers = self._get_smb_peer_data(company_profile)
        
        print(" Calculating metrics...")
        smb_metrics = self._calculate_smb_metrics(company_profile)
        
        print(" Generating weighted score...")
        return self._calculate_smb_weighted_score(smb_metrics, smb_peers, company_profile)
    
    def _get_smb_peer_data(self, profile):
        """Get peer benchmark data"""
        peer_criteria = {
            "industry": profile["industry"],
            "country": profile["country"],
            "region": profile["region"],
            "business_model": profile["business_model"]
        }
        
        query_text = (
            f"SMB {profile['industry']} companies in {profile['country']} "
            f"with {profile['employees']} employees and ${profile['business_model']} business profile"
        )
        
        try:
            peers = self.smb_benchmarks_rag.query(query=query_text, filters=peer_criteria, top_k=10)
            print(f"   Found {len(peers)} peer companies")
            return peers
        except Exception as e:
            print(f"   Warning: Could not retrieve peer data - {e}")
            return []
    
    def _calculate_smb_metrics(self, profile):
        """Calculate key financial metrics programmatically"""
        metrics = {}
        
        # 1. Liquidity Score (Cash Runway)
        cash_runway = profile.get('cash_runway', 2.5)
        if cash_runway >= 12:
            metrics['liquidity_score'] = 100
        elif cash_runway >= 6:
            metrics['liquidity_score'] = 80
        elif cash_runway >= 3:
            metrics['liquidity_score'] = 60
        else:
            metrics['liquidity_score'] = max(20, cash_runway / 3 * 60)
        
        # 2. Profitability Score
        margin = profile.get('net_profit_margin', 0.1)
        if margin >= 0.20:
            metrics['profitability_score'] = 100
        elif margin >= 0.10:
            metrics['profitability_score'] = 70 + (margin - 0.10) / 0.10 * 30
        elif margin >= 0.05:
            metrics['profitability_score'] = 50 + (margin - 0.05) / 0.05 * 20
        else:
            metrics['profitability_score'] = max(10, margin / 0.05 * 50)
        
        # 3. Growth Potential
        recurring_rev = profile.get('recurring_revenue', 0.3)
        predictability = profile.get('revenue_predictability', 0.6)
        metrics['growth_potential'] = (recurring_rev * 50) + (predictability * 50)
        
        # 4. Risk Assessment (lower risk = higher score)
        churn = profile.get('churn_rate', 0.2)
        concentration = profile.get('revenue_concentration', 0.4)
        metrics['risk_score'] = ((1 - churn) * 50) + ((1 - concentration) * 50)
        
        # 5. Operational Efficiency
        revenue_per_employee = profile['annual_revenue'] / profile['employees']
        if revenue_per_employee >= 150000:
            metrics['efficiency_score'] = 100
        elif revenue_per_employee >= 100000:
            metrics['efficiency_score'] = 80
        elif revenue_per_employee >= 75000:
            metrics['efficiency_score'] = 60
        else:
            metrics['efficiency_score'] = max(30, revenue_per_employee / 75000 * 60)
        
        print(f"   Calculated {len(metrics)} metrics")
        return metrics
    
    def _calculate_smb_weighted_score(self, metrics, peers, profile):
        """Calculate final weighted score and get AI analysis"""
        # Calculate weighted average
        weights = {
            'liquidity_score': 0.25,
            'profitability_score': 0.25,
            'growth_potential': 0.20,
            'risk_score': 0.20,
            'efficiency_score': 0.10
        }
        
        overall_score = sum(metrics[key] * weights[key] for key in weights)
        
        # Get health rating
        if overall_score >= 85:
            rating = "Excellent"
        elif overall_score >= 70:
            rating = "Good"
        elif overall_score >= 55:
            rating = "Fair"
        else:
            rating = "Poor"
        
        # Enhanced prompt for more detailed analysis
        analysis_prompt = f"""As a senior financial analyst, provide a comprehensive assessment of this SMB:

COMPANY OVERVIEW:
- Business: {profile['industry']} company in {profile['country']} ({profile['region']} market)
- Scale: {profile['employees']} employees generating ${profile['annual_revenue']:,} annually
- Maturity: {profile['years_in_business']} years in operation
- Model: {profile['business_model']} business model

FINANCIAL HEALTH METRICS:
- Liquidity Health: {metrics['liquidity_score']:.0f}/100 (Cash runway: {profile.get('cash_runway', 2.5)} months)
- Profitability Health: {metrics['profitability_score']:.0f}/100 (Net profit margin: {profile.get('net_profit_margin', 0.1)*100:.1f}%)
- Growth Potential: {metrics['growth_potential']:.0f}/100 (Recurring revenue: {profile.get('recurring_revenue', 0.3)*100:.0f}%, Predictability: {profile.get('revenue_predictability', 0.6)*100:.0f}%)
- Risk Management: {metrics['risk_score']:.0f}/100 (Churn rate: {profile.get('churn_rate', 0.2)*100:.0f}%, Revenue concentration: {profile.get('revenue_concentration', 0.4)*100:.0f}%)
- Operational Efficiency: {metrics['efficiency_score']:.0f}/100 (Revenue per employee: ${profile['annual_revenue'] / profile['employees']:,.0f})

OVERALL ASSESSMENT: {overall_score:.1f}/100 ({rating})
BENCHMARK CONTEXT: Compared against {len(peers)} similar SMB companies

Provide a detailed analysis covering:
1. Overall financial health verdict with reasoning
2. Two key competitive strengths this company should leverage
3. Two critical vulnerabilities that need immediate attention
4. Risk assessment for potential investors or lenders
5. One strategic recommendation for the next 6 months

Format your response as a professional financial assessment."""
        
        try:
            ai_analysis = summarize_with_granite(analysis_prompt, temperature=0.3, max_new_tokens=800)
        except Exception as e:
            ai_analysis = f"AI analysis unavailable: {e}"
        
        return {
            "overall_score": round(overall_score, 1),
            "health_rating": rating,
            "detailed_scores": metrics,
            "ai_analysis": ai_analysis,
            "peer_count": len(peers)
        }
    
    def generate_smb_specific_insights(self, profile, score_result):
        """Generate comprehensive actionable recommendations"""
        
        # Identify the weakest areas
        scores = score_result['detailed_scores']
        weak_areas = []
        
        if scores['liquidity_score'] < 60:
            weak_areas.append(f"Cash flow management (score: {scores['liquidity_score']:.0f}/100)")
        if scores['profitability_score'] < 60:
            weak_areas.append(f"Profit optimization (score: {scores['profitability_score']:.0f}/100)")
        if scores['growth_potential'] < 60:
            weak_areas.append(f"Growth strategy (score: {scores['growth_potential']:.0f}/100)")
        if scores['risk_score'] < 60:
            weak_areas.append(f"Risk mitigation (score: {scores['risk_score']:.0f}/100)")
        if scores['efficiency_score'] < 60:
            weak_areas.append(f"Operational efficiency (score: {scores['efficiency_score']:.0f}/100)")
        
        insights_prompt = f"""As a business consultant specializing in SMB growth, provide specific, actionable recommendations for this client:

COMPANY PROFILE:
- {profile['industry']} business in {profile['country']} market
- {profile['employees']} employees, ${profile['annual_revenue']:,} annual revenue
- {profile['years_in_business']} years established, {profile['business_model']} model
- Current health rating: {score_result['health_rating']} ({score_result['overall_score']}/100)

PERFORMANCE ANALYSIS:
- Liquidity: {scores['liquidity_score']:.0f}/100 (Cash runway: {profile.get('cash_runway', 2.5)} months)
- Profitability: {scores['profitability_score']:.0f}/100 (Net margin: {profile.get('net_profit_margin', 0.1)*100:.1f}%)
- Growth: {scores['growth_potential']:.0f}/100 (Recurring revenue: {profile.get('recurring_revenue', 0.3)*100:.0f}%)
- Risk: {scores['risk_score']:.0f}/100 (Churn: {profile.get('churn_rate', 0.2)*100:.0f}%)
- Efficiency: {scores['efficiency_score']:.0f}/100 (${profile['annual_revenue'] / profile['employees']:,.0f} per employee)

PRIORITY AREAS FOR IMPROVEMENT:
{', '.join(weak_areas) if weak_areas else 'Overall performance optimization'}

Provide 5 specific, implementable recommendations that this SMB can execute within the next 3-6 months. Each recommendation should include:
- The specific action to take
- Expected timeline for implementation
- Estimated impact on financial health
- Required resources or investment

Focus on the most impactful changes that align with their current capabilities and market position."""
        
        try:
            return summarize_with_granite(insights_prompt, temperature=0.3, max_new_tokens=800)
        except Exception as e:
            return f"Insights unavailable: {e}"
    
    def generate_benchmarking_report(self, profile, score_result, peers):
        """Generate a detailed benchmarking analysis comparing with actual peer metrics"""
        print("peers :: ", peers)
        def avg(field):
            values = [p[field] for p in peers if isinstance(p.get(field), (int, float))]
            return sum(values) / len(values) if values else 0
    
        # Compute peer averages
        peer_metrics = {
            "cash_runway": avg("cash_runway_months"),
            "net_profit_margin": avg("net_profit_margin"),
            "churn_rate": avg("customer_churn_rate"),
            "recurring_revenue": avg("recurring_revenue_pct"),
            "revenue_predictability": avg("revenue_predictability"),
            "revenue_concentration": avg("revenue_concentration_pct"),
            "employees": avg("employees"),
            "revenue": avg("revenue"),
            "years_in_business": avg("years_in_business"),
        }
    
        # Prompt including both sets of metrics
        benchmark_prompt = f"""
You are a senior financial analyst. Compare this SMB to peers using the following:

SMB:
- {profile['industry']} in {profile['country']}
- {profile['employees']} employees, ${profile['annual_revenue']:,} revenue
- {profile['years_in_business']} years in business

Metrics (Company vs Peers):
- Cash Runway: {profile['cash_runway']} vs {peer_metrics['cash_runway']:.1f}
- Profit Margin: {profile['net_profit_margin']*100:.1f}% vs {peer_metrics['net_profit_margin']*100:.1f}%
- Churn Rate: {profile['churn_rate']*100:.1f}% vs {peer_metrics['churn_rate']*100:.1f}%
- Recurring Revenue: {profile['recurring_revenue']*100:.1f}% vs {peer_metrics['recurring_revenue']*100:.1f}%

INSTRUCTIONS — Answer all 3 below clearly:
1. *Underperforming Metrics* — List which metrics are worse than peers  
2. *Outperforming Metrics* — List which metric(s) are better  
3. *Top 3 Problems to Fix* — Start each bullet with an action verb (e.g. Improve, Reduce, Increase)
Only return the 3 numbered sections in bullets. Do not repeat values or re-state the company profile.
"""

        try:
            #print(benchmark_prompt)
            return summarize_with_granite(benchmark_prompt, temperature=0.3, max_new_tokens=1200)
        except Exception as e:
            return f"Benchmarking analysis unavailable: {e}"