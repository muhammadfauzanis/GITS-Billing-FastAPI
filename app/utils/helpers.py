import locale
from fastapi import Request, HTTPException
from typing import Optional

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

def _get_target_client_id(request: Request, provided_client_id: Optional[str]) -> str:
    user_details = request.state.user
    user_role = user_details.get("role")
    user_client_id = user_details.get("clientId")

    if user_role == "admin":
        if provided_client_id:
            return provided_client_id
        else:
            raise HTTPException(status_code=400, detail="Admin must specify a clientId for this operation.")
    else: # Role 'client'
        if not user_client_id:
            raise HTTPException(status_code=401, detail="Unauthorized: Client ID not found in token.")
        if provided_client_id and provided_client_id != str(user_client_id):
            raise HTTPException(status_code=403, detail="Forbidden: Clients can only access their own data.")
        return str(user_client_id)

def format_usage(usage: float, unit: str) -> str:
    """
    Buat format usage sku biar kaya di GCP
    """
    if usage is None:
        usage = 0.0

    unit = unit.lower()

    if "byte-seconds" in unit:
        # Konversi byte-seconds ke gibibyte-hours, unit yang umum untuk storage-time
        # 1 GiB = 1024^3 bytes, 1 hour = 3600 seconds
        gibibyte_hours = usage / (1024**3 * 3600)
        return f"{gibibyte_hours:,.2f} gibibyte hour"
    
    if "seconds" in unit:
        if usage >= 3600:
            hours = usage / 3600
            return f"{hours:,.2f} hour"
        elif usage >= 60:
            minutes = usage / 60
            return f"{minutes:,.2f} minute"
        return f"{usage:,.2f} second"

    if "bytes" in unit:
        if usage >= 1024**4:
            terabytes = usage / 1024**4
            return f"{terabytes:,.2f} TiB"
        elif usage >= 1024**3:
            gigabytes = usage / 1024**3
            return f"{gigabytes:,.2f} GiB"
        elif usage >= 1024**2:
            megabytes = usage / 1024**2
            return f"{megabytes:,.2f} MiB"
        elif usage >= 1024:
            kilobytes = usage / 1024
            return f"{kilobytes:,.2f} KiB"
        return f"{usage:,.0f} bytes"

    if "requests" in unit:
        return f"{usage:,.0f} requests"

    return f"{usage:,.2f} {unit}"