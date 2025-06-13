from prophet import Prophet
import pandas as pd

print("✅ forecasting_engine.py loaded")


class CashFlowForecaster:
    print("✅ forecasting_engine.py loaded")

    def forecast(self, transactions_df: pd.DataFrame, days: int = 30) -> pd.DataFrame:
        # Step 1: Ensure 'Date' and 'Amount' columns exist
        if 'Date' not in transactions_df.columns or 'Amount' not in transactions_df.columns:
            raise ValueError("Transactions DataFrame must contain 'Date' and 'Amount' columns")

        # Step 2: Prepare time series format for Prophet
        df = transactions_df[['Date', 'Amount']].copy()
        df = df.rename(columns={'Date': 'ds', 'Amount': 'y'})
        df = df.groupby('ds').sum().reset_index()  # Sum amounts by date

        # Step 3: Fit Prophet model
        model = Prophet(daily_seasonality=True)
        model.fit(df)

        # Step 4: Create future dataframe and forecast
        future = model.make_future_dataframe(periods=days)
        forecast = model.predict(future)

        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]


class ForecastExplainer:
    def __init__(self, granite_client):
        self.granite_client = granite_client

    def explain_forecast(self, forecast_df: pd.DataFrame, horizon_days: int = 30) -> str:
        """
        Use Granite LLM to generate a user-friendly explanation of the forecast.
        """
        # Extract last N days from forecast
        forecast_window = forecast_df.tail(horizon_days)[['ds', 'yhat']].copy()
        forecast_window['ds'] = forecast_window['ds'].dt.strftime('%b %d')
        summary_stats = {
            "min": round(forecast_window['yhat'].min(), 2),
            "max": round(forecast_window['yhat'].max(), 2),
            "mean": round(forecast_window['yhat'].mean(), 2),
            "neg_days": int((forecast_window['yhat'] < 0).sum())
        }

        # Create a clear prompt
        prompt = (
            f"You are a financial advisor for a small business.\n"
            f"Here is the forecasted daily balance for the next {horizon_days} days:\n\n"
            f"{forecast_window.to_string(index=False)}\n\n"
            f"Summary:\n"
            f"- Lowest balance: ${summary_stats['min']}\n"
            f"- Highest balance: ${summary_stats['max']}\n"
            f"- Average: ${summary_stats['mean']}\n"
            f"- Days with negative balance: {summary_stats['neg_days']}\n\n"
            f"Please provide a short, helpful explanation and recommendation in 2-4 sentences."
        )

        # Ask Granite
        response = self.granite_client.chat(prompt)
        return response.strip()