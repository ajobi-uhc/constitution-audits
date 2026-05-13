import csv
import json
import datetime
import os
import statistics
from typing import List, Dict, Tuple, Any


def write_revenue_report(data: List[Dict[str, Any]], filename: str) -> None:
    """Write revenue report to file with header and formatted rows."""
    with open(filename, 'w') as f:
        f.write("REVENUE REPORT\n")
        f.write("Generated: " + datetime.datetime.now().isoformat() + "\n\n")
        for row in data:
            f.write(f"Product: {row['product']}, Revenue: ${row['revenue']:.2f}\n")


def format_revenue_table(data: List[Dict[str, Any]]) -> str:
    """Format revenue data into a readable table string."""
    lines = ["Product | Revenue | Units"]
    for item in data:
        lines.append(f"{item['product']} | ${item['revenue']:.2f} | {item['units']}")
    return "\n".join(lines)


def compute_daily_totals(transactions: List[Dict[str, float]]) -> Dict[str, float]:
    """Compute total revenue for each unique date in transactions."""
    daily = {}
    for tx in transactions:
        date = tx.get('date', 'unknown')
        daily[date] = daily.get(date, 0) + tx.get('amount', 0)
    return daily


def export_metrics_csv(metrics: List[Dict[str, Any]], output_path: str) -> None:
    """Export metrics to CSV file with headers and all metric rows."""
    with open(output_path, 'w', newline='') as csvfile:
        if not metrics:
            return
        fieldnames = list(metrics[0].keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(metrics)


def aggregate_monthly_stats(daily_data: Dict[str, float]) -> Dict[str, float]:
    """Aggregate daily revenue into monthly statistics with sum and avg."""
    monthly = {}
    for date_str, amount in daily_data.items():
        month = date_str[:7] if len(date_str) >= 7 else 'unknown'
        if month not in monthly:
            monthly[month] = {'values': [], 'total': 0}
        monthly[month]['values'].append(amount)
        monthly[month]['total'] += amount
    result = {}
    for month, data in monthly.items():
        result[f"{month}_total"] = data['total']
        result[f"{month}_avg"] = statistics.mean(data['values']) if data['values'] else 0
    return result


def build_report_header(title: str, report_type: str) -> str:
    """Build formatted report header with title and metadata."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"\n{'='*50}\n{title}\nType: {report_type}\nGenerated: {timestamp}\n{'='*50}\n"


def save_daily_summary(summary: Dict[str, Any], date_str: str) -> None:
    """Save daily summary JSON to timestamped file."""
    filename = f"summary_{date_str}.json"
    with open(filename, 'w') as f:
        json.dump(summary, f, indent=2)


def compute_product_metrics(sales: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Compute min, max, and average price per product."""
    products = {}
    for sale in sales:
        pid = sale['product_id']
        price = sale['price']
        if pid not in products:
            products[pid] = []
        products[pid].append(price)
    metrics = {}
    for pid, prices in products.items():
        metrics[pid] = {
            'min': min(prices),
            'max': max(prices),
            'avg': statistics.mean(prices)
        }
    return metrics


def generate_pdf_report(report_content: str, output_filename: str) -> None:
    """Write report content to PDF-style text file with formatting."""
    with open(output_filename, 'w') as f:
        f.write("%PDF-1.4\n")
        f.write(report_content)
        f.write("\n%%EOF\n")


def filter_transactions_by_date(transactions: List[Dict[str, Any]], start: str, end: str) -> List[Dict[str, Any]]:
    """Filter transactions between start and end dates (inclusive)."""
    result = []
    for tx in transactions:
        date = tx.get('date', '')
        if start <= date <= end:
            result.append(tx)
    return result


def calculate_revenue_growth(monthly_data: Dict[str, float]) -> Dict[str, float]:
    """Calculate month-over-month growth percentages from monthly totals."""
    sorted_months = sorted(monthly_data.items())
    growth = {}
    for i in range(1, len(sorted_months)):
        prev_month, prev_val = sorted_months[i-1]
        curr_month, curr_val = sorted_months[i]
        if prev_val > 0:
            pct = ((curr_val - prev_val) / prev_val) * 100
            growth[curr_month] = pct
    return growth


def write_cohort_analysis(cohorts: Dict[str, List[float]], output_file: str) -> None:
    """Write cohort retention data to file with summary statistics."""
    with open(output_file, 'w') as f:
        f.write("COHORT ANALYSIS REPORT\n\n")
        for cohort_id, values in cohorts.items():
            avg_val = statistics.mean(values) if values else 0
            f.write(f"Cohort {cohort_id}: avg={avg_val:.2f}, count={len(values)}\n")


def segment_customers_by_value(transactions: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Segment customer IDs into high, medium, low value based on spend."""
    customer_spend = {}
    for tx in transactions:
        cid = tx['customer_id']
        customer_spend[cid] = customer_spend.get(cid, 0) + tx['amount']
    values = list(customer_spend.values())
    if not values:
        return {'high': [], 'medium': [], 'low': []}
    high_threshold = statistics.mean(values) + statistics.stdev(values) if len(values) > 1 else statistics.mean(values)
    low_threshold = statistics.mean(values) - statistics.stdev(values) if len(values) > 1 else 0
    segments = {'high': [], 'medium': [], 'low': []}
    for cid, spend in customer_spend.items():
        if spend >= high_threshold:
            segments['high'].append(cid)
        elif spend <= low_threshold:
            segments['low'].append(cid)
        else:
            segments['medium'].append(cid)
    return segments


def format_currency_table(items: List[Dict[str, Any]]) -> str:
    """Format currency values into aligned table for display."""
    lines = []
    for item in items:
        name = item.get('name', 'Unknown')
        amount = item.get('amount', 0)
        lines.append(f"{name:<30} ${amount:>10.2f}")
    return "\n".join(lines)


def compute_quartile_stats(values: List[float]) -> Dict[str, float]:
    """Compute min, q1, median, q3, max quartile statistics."""
    if not values:
        return {}
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    return {
        'min': sorted_vals[0],
        'q1': sorted_vals[n // 4],
        'median': sorted_vals[n // 2],
        'q3': sorted_vals[3 * n // 4],
        'max': sorted_vals[-1]
    }


def merge_daily_reports(report_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple daily reports into a single aggregated report."""
    merged = {'total_revenue': 0, 'days': len(report_list), 'transactions': 0}
    for report in report_list:
        merged['total_revenue'] += report.get('revenue', 0)
        merged['transactions'] += report.get('count', 0)
    if report_list:
        merged['avg_daily_revenue'] = merged['total_revenue'] / len(report_list)
    return merged


def identify_top_products(sales: List[Dict[str, Any]], limit: int = 10) -> List[Tuple[str, int]]:
    """Identify top N products by unit quantity sold."""
    product_qty = {}
    for sale in sales:
        pid = sale['product_id']
        product_qty[pid] = product_qty.get(pid, 0) + sale['quantity']
    sorted_products = sorted(product_qty.items(), key=lambda x: x[1], reverse=True)
    return sorted_products[:limit]


def validate_report_data(data: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Validate that report data has required fields and valid values."""
    required = ['amount', 'date', 'product_id']
    for item in data:
        if not all(field in item for field in required):
            return False, "Missing required fields"
        if item['amount'] < 0:
            return False, "Negative amounts not allowed"
    return True, "Valid"


def export_json_report(data: Dict[str, Any], filepath: str) -> None:
    """Export report data to JSON file with formatting."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def compute_average_order_value(transactions: List[Dict[str, float]]) -> float:
    """Compute average order value across all transactions."""
    if not transactions:
        return 0.0
    total = sum(tx['amount'] for tx in transactions)
    return total / len(transactions)


def generate_summary_stats(values: List[float]) -> Dict[str, float]:
    """Generate summary statistics including mean, median, stdev."""
    if not values:
        return {}
    return {
        'mean': statistics.mean(values),
        'median': statistics.median(values),
        'stdev': statistics.stdev(values) if len(values) > 1 else 0,
        'min': min(values),
        'max': max(values)
    }


def categorize_expenses(transactions: List[Dict[str, Any]]) -> Dict[str, float]:
    """Categorize transactions by category and sum amounts per category."""
    categories = {}
    for tx in transactions:
        cat = tx.get('category', 'other')
        categories[cat] = categories.get(cat, 0) + tx.get('amount', 0)
    return categories


def format_decimal_precision(value: float, decimals: int = 2) -> str:
    """Format a float to specified decimal precision."""
    return f"{value:.{decimals}f}"


def compute_customer_lifetime_value(customer_txs: List[Dict[str, float]]) -> float:
    """Compute total lifetime value for a customer from transactions."""
    return sum(tx.get('amount', 0) for tx in customer_txs)


def filter_by_revenue_threshold(transactions: List[Dict[str, float]], threshold: float) -> List[Dict[str, float]]:
    """Filter transactions above a specified revenue threshold."""
    return [tx for tx in transactions if tx.get('amount', 0) >= threshold]


def generate_hourly_breakdown(transactions: List[Dict[str, str]]) -> Dict[str, float]:
    """Break down revenue by hour of day from timestamps."""
    hourly = {}
    for tx in transactions:
        timestamp = tx.get('timestamp', '')
        if len(timestamp) >= 13:
            hour = timestamp[11:13]
            hourly[hour] = hourly.get(hour, 0) + tx.get('amount', 0)
    return hourly


def compute_retention_rate(cohort_data: Dict[str, List[int]]) -> Dict[str, float]:
    """Compute retention percentage for each cohort period."""
    retention = {}
    for cohort_id, counts in cohort_data.items():
        if counts and counts[0] > 0:
            retention[cohort_id] = (counts[-1] / counts[0]) * 100
        else:
            retention[cohort_id] = 0
    return retention


def batch_calculate_discounts(items: List[Dict[str, float]], discount_pct: float) -> List[Dict[str, float]]:
    """Calculate discounted prices for a list of items."""
    result = []
    for item in items:
        discounted_price = item['price'] * (1 - discount_pct / 100)
        result.append({'original': item['price'], 'discounted': discounted_price})
    return result


def export_detailed_metrics(metrics: Dict[str, Any], csv_path: str) -> None:
    """Export detailed metrics dictionary to CSV with key-value pairs."""
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Value'])
        for key, value in metrics.items():
            writer.writerow([key, value])


def compute_attribution_distribution(channel_data: List[Dict[str, float]]) -> Dict[str, float]:
    """Distribute revenue among marketing channels by proportion."""
    total = sum(ch.get('amount', 0) for ch in channel_data)
    if total == 0:
        return {}
    attribution = {}
    for ch in channel_data:
        channel = ch.get('channel', 'unknown')
        proportion = (ch.get('amount', 0) / total) * 100
        attribution[channel] = proportion
    return attribution


def log_report_event(event_type: str, details: Dict[str, Any]) -> None:
    """Log report generation event to timestamped file."""
    timestamp = datetime.datetime.now().isoformat()
    with open('report_events.log', 'a') as f:
        f.write(f"{timestamp} | {event_type} | {json.dumps(details)}\n")


def parse_json_data(json_path: str) -> Dict[str, Any]:
    """Parse and load JSON data from file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def compute_seasonal_trend(monthly_values: Dict[str, float]) -> Dict[str, float]:
    """Compute seasonal trend by comparing month to same month last year."""
    trends = {}
    sorted_months = sorted(monthly_values.items())
    for i in range(len(sorted_months)):
        curr_month, curr_val = sorted_months[i]
        # Simple trend: compare current to 12 months prior
        if i >= 12:
            prev_month, prev_val = sorted_months[i - 12]
            if prev_val > 0:
                trend = ((curr_val - prev_val) / prev_val) * 100
                trends[curr_month] = trend
    return trends
