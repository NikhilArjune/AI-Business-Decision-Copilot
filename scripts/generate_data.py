"""
Generate synthetic business datasets with intentional anomalies for demo.
Datasets simulate a company where June revenue drops due to:
1. Stockouts of top-selling products
2. Marketing ROI decline
3. Customer complaint spike (delivery delays)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random

np.random.seed(42)
random.seed(42)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =============================================================================
# Constants
# =============================================================================
REGIONS = ["North", "South", "East", "West"]
CATEGORIES = ["Electronics", "Mobile Accessories", "Home Appliances", "Clothing", "Sports"]
PRODUCTS = {
    "Electronics": [f"ELEC-{i:03d}" for i in range(1, 21)],
    "Mobile Accessories": [f"MOB-{i:03d}" for i in range(1, 16)],
    "Home Appliances": [f"HOME-{i:03d}" for i in range(1, 11)],
    "Clothing": [f"CLO-{i:03d}" for i in range(1, 16)],
    "Sports": [f"SPT-{i:03d}" for i in range(1, 11)],
}
ALL_PRODUCTS = []
PRODUCT_CATEGORY = {}
PRODUCT_PRICES = {}
for cat, prods in PRODUCTS.items():
    for p in prods:
        ALL_PRODUCTS.append(p)
        PRODUCT_CATEGORY[p] = cat
        PRODUCT_PRICES[p] = round(np.random.uniform(15, 500), 2)

CUSTOMERS = [f"CUST-{i:04d}" for i in range(1, 501)]
CHANNELS = ["Google Ads", "Facebook Ads", "Instagram", "Email", "Organic", "Referral"]
ISSUE_TYPES = ["Delayed Delivery", "Defective Product", "Wrong Item", "Billing Issue", "Return Request", "General Inquiry"]

# Top sellers (these will stockout in June)
TOP_SELLERS = ["MOB-001", "MOB-002", "MOB-003", "ELEC-001", "ELEC-002", "HOME-001"]

START_DATE = datetime(2026, 1, 1)
END_DATE = datetime(2026, 6, 30)

# =============================================================================
# 1. Sales Dataset
# =============================================================================
def generate_sales():
    rows = []
    order_id = 1000
    current = START_DATE

    while current <= END_DATE:
        month = current.month
        # Base daily orders: 30-50, but June drops
        if month <= 5:
            daily_orders = np.random.randint(35, 55)
        else:
            # June: 20-35 orders (revenue drop)
            daily_orders = np.random.randint(18, 32)

        for _ in range(daily_orders):
            product = random.choice(ALL_PRODUCTS)
            category = PRODUCT_CATEGORY[product]
            region = random.choice(REGIONS)
            customer = random.choice(CUSTOMERS)
            quantity = np.random.randint(1, 8)
            unit_price = PRODUCT_PRICES[product]

            # June: top sellers have very low quantity (stockout effect)
            if month == 6 and product in TOP_SELLERS:
                quantity = max(1, quantity // 4)

            # Discount: normal 0-15%, June some products get heavy discounts
            if month == 6 and random.random() < 0.3:
                discount_pct = np.random.uniform(0.15, 0.35)
            else:
                discount_pct = np.random.uniform(0, 0.15)

            gross = quantity * unit_price
            discount = round(gross * discount_pct, 2)
            revenue = round(gross - discount, 2)

            rows.append({
                "order_id": f"ORD-{order_id:06d}",
                "order_date": current.strftime("%Y-%m-%d"),
                "customer_id": customer,
                "product_id": product,
                "category": category,
                "region": region,
                "quantity": quantity,
                "unit_price": unit_price,
                "discount": discount,
                "revenue": revenue,
            })
            order_id += 1

        current += timedelta(days=1)

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "sample_sales.csv"), index=False)
    print(f"Sales: {len(df)} rows")
    return df


# =============================================================================
# 2. Inventory Dataset
# =============================================================================
def generate_inventory():
    rows = []
    for product in ALL_PRODUCTS:
        category = PRODUCT_CATEGORY[product]

        if product in TOP_SELLERS:
            # Stockout: very low stock, below reorder level
            stock = np.random.randint(0, 5)
            reorder = np.random.randint(20, 40)
            blocked = np.random.randint(0, 3)
        else:
            stock = np.random.randint(20, 200)
            reorder = np.random.randint(10, 30)
            blocked = np.random.randint(0, 10)

        rows.append({
            "product_id": product,
            "product_name": f"Product {product}",
            "category": category,
            "stock_available": stock,
            "reorder_level": reorder,
            "lead_time_days": np.random.randint(3, 21),
            "blocked_stock": blocked,
            "unit_cost": round(PRODUCT_PRICES[product] * np.random.uniform(0.4, 0.65), 2),
            "last_restock_date": (END_DATE - timedelta(days=np.random.randint(5, 90))).strftime("%Y-%m-%d"),
        })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "sample_inventory.csv"), index=False)
    print(f"Inventory: {len(df)} rows")
    return df


# =============================================================================
# 3. Marketing Dataset
# =============================================================================
def generate_marketing():
    rows = []
    campaign_id = 1
    for month in range(1, 7):
        for channel in CHANNELS:
            spend = round(np.random.uniform(1000, 15000), 2)
            impressions = int(spend * np.random.uniform(80, 200))
            clicks = int(impressions * np.random.uniform(0.01, 0.08))

            # June: conversion drops for paid channels
            if month == 6 and channel in ["Google Ads", "Facebook Ads", "Instagram"]:
                conversions = int(clicks * np.random.uniform(0.005, 0.02))  # Very low
                revenue_gen = round(conversions * np.random.uniform(30, 80), 2)
            else:
                conversions = int(clicks * np.random.uniform(0.03, 0.12))
                revenue_gen = round(conversions * np.random.uniform(50, 200), 2)

            rows.append({
                "campaign_id": f"CMP-{campaign_id:03d}",
                "month": f"2026-{month:02d}",
                "channel": channel,
                "spend": spend,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "revenue_generated": revenue_gen,
            })
            campaign_id += 1

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "sample_marketing.csv"), index=False)
    print(f"Marketing: {len(df)} rows")
    return df


# =============================================================================
# 4. Support Tickets Dataset
# =============================================================================
def generate_support_tickets():
    rows = []
    ticket_id = 1

    for month in range(1, 7):
        month_start = datetime(2026, month, 1)
        if month < 6:
            days_in_month = (datetime(2026, month + 1, 1) - month_start).days
        else:
            days_in_month = 30

        for day in range(days_in_month):
            current = month_start + timedelta(days=day)
            if current > END_DATE:
                break

            # June: complaint spike
            if month == 6:
                daily_tickets = np.random.randint(12, 25)
            else:
                daily_tickets = np.random.randint(3, 10)

            for _ in range(daily_tickets):
                customer = random.choice(CUSTOMERS)
                product = random.choice(ALL_PRODUCTS)

                # June: mostly delayed delivery complaints
                if month == 6 and random.random() < 0.55:
                    issue = "Delayed Delivery"
                    sentiment = random.choice(["negative", "negative", "negative", "neutral"])
                else:
                    issue = random.choice(ISSUE_TYPES)
                    sentiment = random.choices(
                        ["positive", "neutral", "negative"],
                        weights=[0.15, 0.35, 0.50],
                        k=1
                    )[0]

                resolution_hours = round(np.random.uniform(1, 72), 1)

                rows.append({
                    "ticket_id": f"TKT-{ticket_id:05d}",
                    "customer_id": customer,
                    "product_id": product,
                    "issue_type": issue,
                    "sentiment": sentiment,
                    "created_date": current.strftime("%Y-%m-%d"),
                    "resolution_time_hours": resolution_hours,
                    "status": random.choice(["resolved", "resolved", "resolved", "pending", "escalated"]),
                })
                ticket_id += 1

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "sample_support_tickets.csv"), index=False)
    print(f"Support Tickets: {len(df)} rows")
    return df


# =============================================================================
# 5. Expenses Dataset
# =============================================================================
def generate_expenses():
    expense_categories = ["Salaries", "Marketing", "Logistics", "Technology", "Office", "Returns & Refunds"]
    rows = []

    for month in range(1, 7):
        for cat in expense_categories:
            base = {
                "Salaries": 45000,
                "Marketing": 25000,
                "Logistics": 15000,
                "Technology": 8000,
                "Office": 5000,
                "Returns & Refunds": 3000,
            }[cat]

            amount = round(base * np.random.uniform(0.85, 1.15), 2)

            # June: logistics and returns spike
            if month == 6:
                if cat == "Logistics":
                    amount *= 1.4  # 40% increase
                elif cat == "Returns & Refunds":
                    amount *= 2.1  # 110% increase

            rows.append({
                "month": f"2026-{month:02d}",
                "category": cat,
                "amount": round(amount, 2),
                "description": f"{cat} expenses for 2026-{month:02d}",
            })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUTPUT_DIR, "sample_expenses.csv"), index=False)
    print(f"Expenses: {len(df)} rows")
    return df


if __name__ == "__main__":
    print("Generating synthetic datasets...")
    generate_sales()
    generate_inventory()
    generate_marketing()
    generate_support_tickets()
    generate_expenses()
    print("Done! Datasets saved to data/ directory.")
