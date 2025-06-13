from typing import List
import pandas as pd
from cashflow_forecasting.models import Alert

def generate_cashflow_alerts(forecast_df: pd.DataFrame, threshold: float = 0.0) -> List[Alert]:
    """
    Scans a forecast DataFrame and returns a list of Alerts for days
    where projected cash flow drops below the specified threshold.
    """
    alerts = []
    low_cash_days = forecast_df[forecast_df['yhat'] < threshold]

    for _, row in low_cash_days.iterrows():
        severity = "high" if row['yhat'] < -100 else "medium" if row['yhat'] < 0 else "low"
        message = (
            f"⚠️ Projected balance of ${row['yhat']:.2f} on {row['ds'].strftime('%b %d')} "
            f"is below threshold (${threshold:.2f})."
        )
        alerts.append(Alert(date=row['ds'], message=message, severity=severity))

    return alerts
