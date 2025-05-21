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


def calculate_projection(current_amount: float, current_day: int, days_in_month: int) -> float:
    if current_day == 0:
        return 0.0
    daily_avg = current_amount / current_day
    return daily_avg * days_in_month

def group_by(array: list[dict], key: str) -> dict[str, list[dict]]:
    result = {}
    for item in array:
        group_key = str(item.get(key, 'unknown'))
        if group_key not in result:
            result[group_key] = []
        result[group_key].append(item)
    return result
