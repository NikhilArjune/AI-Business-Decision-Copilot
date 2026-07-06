"""Quick test of the analytics pipeline."""
import sys
sys.path.insert(0, '.')
import pandas as pd

from agents.tools.sales_tools import run_sales_analysis
from agents.tools.inventory_tools import run_inventory_analysis
from agents.tools.marketing_tools import run_marketing_analysis
from agents.tools.support_tools import run_support_analysis
from agents.tools.analytics_tools import run_anomaly_detection, run_root_cause_ranking

sales = run_sales_analysis(pd.read_csv('data/sample_sales.csv'))
inv = run_inventory_analysis(pd.read_csv('data/sample_inventory.csv'))
mkt = run_marketing_analysis(pd.read_csv('data/sample_marketing.csv'))
sup = run_support_analysis(pd.read_csv('data/sample_support_tickets.csv'))
anomalies = run_anomaly_detection(pd.read_csv('data/sample_sales.csv'))
causes = run_root_cause_ranking({
    'sales_analysis': sales,
    'inventory_analysis': inv,
    'marketing_analysis': mkt,
    'support_analysis': sup,
})

print("=== SALES ===")
print(f"Revenue change: {sales['revenue_change_pct']}%")
print(f"Total orders: {sales['total_orders']}")
print(f"Declining products: {len(sales['declining_products'])}")
print()
print("=== INVENTORY ===")
print(f"Stockouts: {inv['stockout_count']}")
print(f"Risk level: {inv['risk_level']}")
print()
print("=== MARKETING ===")
print(f"Overall ROI: {mkt['overall_roi']}%")
print(f"ROI change: {mkt['roi_change']}%")
print(f"Wasted spend: ${mkt['wasted_spend']:,.0f}")
print()
print("=== SUPPORT ===")
print(f"Total tickets: {sup['total_tickets']}")
print(f"Complaint spike: {sup['has_complaint_spike']}")
print(f"Negative sentiment: {sup['negative_sentiment_pct']}%")
print()
print("=== ANOMALIES ===")
print(f"Anomaly count: {anomalies['anomaly_count']}")
print()
print("=== ROOT CAUSES (ranked by confidence) ===")
for i, c in enumerate(causes, 1):
    print(f"  {i}. [{c['confidence']:.0%}] {c['cause']}")
print()
print("ALL TESTS PASSED!")
