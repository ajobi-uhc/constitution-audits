"""E-commerce analytics metrics computation module."""

import math
from statistics import mean, median, stdev, quantiles
from datetime import datetime, timedelta
from collections import defaultdict
from itertools import groupby


def conversion_rate(total_visitors: int, total_conversions: int) -> float:
    """Calculate conversion rate as percentage (0-100)."""
    if total_visitors == 0:
        return 0.0
    return (total_conversions / total_visitors) * 100


def average_order_value(order_totals: list[float]) -> float:
    """Calculate mean value across all orders."""
    if not order_totals:
        return 0.0
    return mean(order_totals)


def revenue_per_visitor(total_revenue: float, total_visitors: int) -> float:
    """Calculate revenue generated per visitor."""
    if total_visitors == 0:
        return 0.0
    return total_revenue / total_visitors


def purchase_frequency(total_purchases: int, unique_customers: int) -> float:
    """Calculate average purchases per customer."""
    if unique_customers == 0:
        return 0.0
    return total_purchases / unique_customers


def customer_lifetime_value(
    total_revenue: float, unique_customers: int, avg_customer_lifespan_days: int
) -> float:
    """Estimate CLV as total revenue divided by customer count and lifespan factor."""
    if unique_customers == 0 or avg_customer_lifespan_days == 0:
        return 0.0
    return total_revenue / (unique_customers * (avg_customer_lifespan_days / 365))


def churn_rate(customers_lost: int, starting_customers: int) -> float:
    """Calculate percentage of customers lost in period."""
    if starting_customers == 0:
        return 0.0
    return (customers_lost / starting_customers) * 100


def retention_rate(customers_retained: int, starting_customers: int) -> float:
    """Calculate percentage of customers retained."""
    if starting_customers == 0:
        return 0.0
    return (customers_retained / starting_customers) * 100


def repeat_purchase_rate(repeat_customers: int, total_customers: int) -> float:
    """Calculate percentage of customers who made multiple purchases."""
    if total_customers == 0:
        return 0.0
    return (repeat_customers / total_customers) * 100


def cart_abandonment_rate(abandoned_carts: int, total_carts: int) -> float:
    """Calculate percentage of abandoned shopping carts."""
    if total_carts == 0:
        return 0.0
    return (abandoned_carts / total_carts) * 100


def revenue_growth_rate(previous_revenue: float, current_revenue: float) -> float:
    """Calculate period-over-period revenue growth percentage."""
    if previous_revenue == 0:
        return 0.0 if current_revenue == 0 else 100.0
    return ((current_revenue - previous_revenue) / previous_revenue) * 100


def customer_acquisition_cost(marketing_spend: float, new_customers: int) -> float:
    """Calculate cost to acquire each new customer."""
    if new_customers == 0:
        return 0.0
    return marketing_spend / new_customers


def return_on_ad_spend(revenue_from_ads: float, ad_spend: float) -> float:
    """Calculate ROAS: revenue generated per dollar spent."""
    if ad_spend == 0:
        return 0.0
    return revenue_from_ads / ad_spend


def inventory_turnover(cogs: float, average_inventory_value: float) -> float:
    """Calculate how many times inventory sells and is replaced."""
    if average_inventory_value == 0:
        return 0.0
    return cogs / average_inventory_value


def gross_margin(revenue: float, cost_of_goods: float) -> float:
    """Calculate gross margin percentage."""
    if revenue == 0:
        return 0.0
    return ((revenue - cost_of_goods) / revenue) * 100


def net_margin(revenue: float, net_income: float) -> float:
    """Calculate net profit margin percentage."""
    if revenue == 0:
        return 0.0
    return (net_income / revenue) * 100


def operating_margin(revenue: float, operating_income: float) -> float:
    """Calculate operating margin percentage."""
    if revenue == 0:
        return 0.0
    return (operating_income / revenue) * 100


def return_rate(total_returned_items: int, total_sold_items: int) -> float:
    """Calculate percentage of sold items that were returned."""
    if total_sold_items == 0:
        return 0.0
    return (total_returned_items / total_sold_items) * 100


def sessions_per_visitor(total_sessions: int, unique_visitors: int) -> float:
    """Calculate average sessions per unique visitor."""
    if unique_visitors == 0:
        return 0.0
    return total_sessions / unique_visitors


def bounce_rate(bounced_sessions: int, total_sessions: int) -> float:
    """Calculate percentage of sessions with single pageview."""
    if total_sessions == 0:
        return 0.0
    return (bounced_sessions / total_sessions) * 100


def pages_per_session(total_pageviews: int, total_sessions: int) -> float:
    """Calculate average pages viewed per session."""
    if total_sessions == 0:
        return 0.0
    return total_pageviews / total_sessions


def average_session_duration(total_duration_seconds: int, total_sessions: int) -> float:
    """Calculate mean session duration in minutes."""
    if total_sessions == 0:
        return 0.0
    return (total_duration_seconds / total_sessions) / 60


def cohort_retention(cohort_size: int, current_cohort_users: int) -> float:
    """Calculate percentage of original cohort still active."""
    if cohort_size == 0:
        return 0.0
    return (current_cohort_users / cohort_size) * 100


def cohort_revenue_per_user(cohort_revenue: float, cohort_size: int) -> float:
    """Calculate average revenue generated per cohort member."""
    if cohort_size == 0:
        return 0.0
    return cohort_revenue / cohort_size


def funnel_conversion_step(users_entering: int, users_completing: int) -> float:
    """Calculate conversion for single funnel step."""
    if users_entering == 0:
        return 0.0
    return (users_completing / users_entering) * 100


def funnel_drop_rate(users_previous_step: int, users_current_step: int) -> float:
    """Calculate percentage dropoff between consecutive funnel steps."""
    if users_previous_step == 0:
        return 0.0
    return ((users_previous_step - users_current_step) / users_previous_step) * 100


def funnel_completion_rate(users_start: int, users_end: int) -> float:
    """Calculate percentage completing entire funnel."""
    if users_start == 0:
        return 0.0
    return (users_end / users_start) * 100


def moving_average(values: list[float], window_size: int) -> list[float]:
    """Calculate simple moving average with given window size."""
    if window_size <= 0 or len(values) < window_size:
        return []
    return [mean(values[i : i + window_size]) for i in range(len(values) - window_size + 1)]


def exponential_moving_average(values: list[float], alpha: float) -> list[float]:
    """Calculate EMA with smoothing factor alpha (0-1)."""
    if not values:
        return []
    ema = [values[0]]
    for val in values[1:]:
        ema.append(alpha * val + (1 - alpha) * ema[-1])
    return ema


def percentile_value(values: list[float], percentile: int) -> float:
    """Calculate value at nth percentile."""
    if not values or percentile < 0 or percentile > 100:
        return 0.0
    sorted_vals = sorted(values)
    idx = int((percentile / 100) * len(sorted_vals))
    return sorted_vals[min(idx, len(sorted_vals) - 1)]


def quartile_range(values: list[float]) -> tuple[float, float, float, float]:
    """Calculate Q1, median, Q3, and IQR."""
    if len(values) < 4:
        return (0.0, 0.0, 0.0, 0.0)
    sorted_vals = sorted(values)
    q1 = sorted_vals[len(sorted_vals) // 4]
    q2 = median(sorted_vals)
    q3 = sorted_vals[3 * len(sorted_vals) // 4]
    return (q1, q2, q3, q3 - q1)


def percentile_rank(value: float, values: list[float]) -> float:
    """Calculate percentile rank of value within dataset."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    count = sum(1 for v in sorted_vals if v <= value)
    return (count / len(sorted_vals)) * 100


def growth_rate(start_value: float, end_value: float, periods: int) -> float:
    """Calculate compound annual growth rate."""
    if start_value <= 0 or periods <= 0:
        return 0.0
    return (pow(end_value / start_value, 1 / periods) - 1) * 100


def year_over_year_growth(current_year: float, previous_year: float) -> float:
    """Calculate YoY growth percentage."""
    if previous_year == 0:
        return 0.0 if current_year == 0 else 100.0
    return ((current_year - previous_year) / previous_year) * 100


def month_over_month_growth(current_month: float, previous_month: float) -> float:
    """Calculate MoM growth percentage."""
    if previous_month == 0:
        return 0.0 if current_month == 0 else 100.0
    return ((current_month - previous_month) / previous_month) * 100


def roi(gain: float, cost: float) -> float:
    """Calculate return on investment percentage."""
    if cost == 0:
        return 0.0
    return ((gain - cost) / cost) * 100


def payback_period(monthly_profit: float, initial_investment: float) -> float:
    """Calculate months to recover initial investment."""
    if monthly_profit <= 0:
        return float('inf')
    return initial_investment / monthly_profit


def break_even_units(fixed_costs: float, price_per_unit: float, variable_cost_per_unit: float) -> float:
    """Calculate units needed to break even."""
    contribution_margin = price_per_unit - variable_cost_per_unit
    if contribution_margin <= 0:
        return float('inf')
    return fixed_costs / contribution_margin


def profit_margin_per_unit(price: float, cost: float) -> float:
    """Calculate profit margin per unit."""
    if price == 0:
        return 0.0
    return ((price - cost) / price) * 100


def weighted_average_price(quantities: list[float], prices: list[float]) -> float:
    """Calculate weighted average price across quantities."""
    if not quantities or not prices or len(quantities) != len(prices):
        return 0.0
    total_value = sum(q * p for q, p in zip(quantities, prices))
    total_quantity = sum(quantities)
    if total_quantity == 0:
        return 0.0
    return total_value / total_quantity


def variance_in_revenue(revenues: list[float]) -> float:
    """Calculate variance in revenue data."""
    if len(revenues) < 2:
        return 0.0
    return pow(stdev(revenues), 2)


def coefficient_of_variation(revenues: list[float]) -> float:
    """Calculate CV: ratio of std dev to mean."""
    if not revenues or mean(revenues) == 0:
        return 0.0
    return (stdev(revenues) / mean(revenues)) * 100 if len(revenues) > 1 else 0.0


def days_sales_outstanding(accounts_receivable: float, daily_revenue: float) -> float:
    """Calculate average days to collect payment."""
    if daily_revenue == 0:
        return 0.0
    return accounts_receivable / daily_revenue


def inventory_days_outstanding(inventory_value: float, daily_cogs: float) -> float:
    """Calculate average days inventory is held."""
    if daily_cogs == 0:
        return 0.0
    return inventory_value / daily_cogs


def days_payable_outstanding(accounts_payable: float, daily_cogs: float) -> float:
    """Calculate average days to pay suppliers."""
    if daily_cogs == 0:
        return 0.0
    return accounts_payable / daily_cogs


def cash_conversion_cycle(dso: float, dio: float, dpo: float) -> float:
    """Calculate days from outlay to cash collection."""
    return dso + dio - dpo


def product_mix_index(product_revenue: float, total_revenue: float) -> float:
    """Calculate product's percentage of total revenue."""
    if total_revenue == 0:
        return 0.0
    return (product_revenue / total_revenue) * 100


def seasonal_index(month_value: float, average_value: float) -> float:
    """Calculate seasonal index for month."""
    if average_value == 0:
        return 0.0
    return (month_value / average_value) * 100


def forecast_with_trend(historical_values: list[float], periods_ahead: int) -> list[float]:
    """Forecast future values using linear trend."""
    if len(historical_values) < 2 or periods_ahead <= 0:
        return []
    n = len(historical_values)
    x_mean = (n + 1) / 2
    y_mean = mean(historical_values)
    numerator = sum((i + 1 - x_mean) * (historical_values[i] - y_mean) for i in range(n))
    denominator = sum(pow(i + 1 - x_mean, 2) for i in range(n))
    slope = numerator / denominator if denominator != 0 else 0
    intercept = y_mean - slope * x_mean
    return [intercept + slope * (n + j + 1) for j in range(periods_ahead)]


def customer_segment_value(segment_customers: int, segment_revenue: float, total_customers: int) -> dict:
    """Calculate value metrics for customer segment."""
    avg_value = segment_revenue / segment_customers if segment_customers > 0 else 0
    pct_customers = (segment_customers / total_customers * 100) if total_customers > 0 else 0
    return {
        "avg_customer_value": avg_value,
        "pct_of_customer_base": pct_customers,
        "total_segment_value": segment_revenue,
    }


def market_penetration(customers_acquired: int, total_market_size: int) -> float:
    """Calculate percentage of addressable market acquired."""
    if total_market_size == 0:
        return 0.0
    return (customers_acquired / total_market_size) * 100


def market_expansion_potential(current_penetration: float, realistic_max_penetration: float) -> float:
    """Calculate untapped market opportunity."""
    if realistic_max_penetration < current_penetration:
        return 0.0
    return realistic_max_penetration - current_penetration
