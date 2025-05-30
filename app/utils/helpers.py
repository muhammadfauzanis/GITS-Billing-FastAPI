import locale

try:
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

def format_currency(amount: float) -> str:
    try:
        formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"Rp {formatted}"
    except Exception:
        return f"Rp {amount:.2f}".replace(".", ",")


def calculate_projection_moving_average(
    current_amount: float,
    current_day: int,
    days_in_month: int,
    historical_data: list[float],
    num_months_for_average: int = 3
) -> float:
    if current_day == 0:
        return 0.0

    daily_avg_current_month = current_amount / current_day

    if historical_data:
        recent_historical_data = historical_data[:num_months_for_average] 
        if recent_historical_data:
            historical_average = sum(recent_historical_data) / len(recent_historical_data)
            weight_current = current_day / days_in_month
            weight_historical = 1 - weight_current
            combined_daily_avg = (daily_avg_current_month * weight_current) + \
                                 ((historical_average / days_in_month) * weight_historical)
        else:
            combined_daily_avg = daily_avg_current_month 
    else:
        combined_daily_avg = daily_avg_current_month

    return combined_daily_avg * days_in_month

def group_by(array: list[dict], key: str) -> dict[str, list[dict]]:
    result = {}
    for item in array:
        group_key = str(item.get(key, 'unknown'))
        if group_key not in result:
            result[group_key] = []
        result[group_key].append(item)
    return result
