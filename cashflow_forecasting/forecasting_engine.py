import pandas as pd
import torch
import matplotlib.pyplot as plt
from transformers import (
    EarlyStoppingCallback,
    PatchTSTConfig,
    PatchTSTForPrediction,
    Trainer,
    TrainingArguments,
    set_seed
)

from tsfm_public import TimeSeriesPreprocessor
from config.settings import HUGGING_FACE_TOKEN
from utils.granite import summarize_with_granite

set_seed(42)

from huggingface_hub import login
import os

login(token=HUGGING_FACE_TOKEN)


class CashFlowForecaster:
    def __init__(self, context_length: int = 128, forecast_length: int = 30):
        self.context_length = context_length
        self.forecast_length = forecast_length

        # ✅ Load pretrained IBM PatchTSMixer model (CPU only)
        self.config = PatchTSTConfig(
            do_mask_input=False,
            context_length=128,
            patch_length=8,
            num_input_channels=1,
            patch_stride=8,
            prediction_length=30,
            d_model=64,
            num_attention_heads=4,
            num_hidden_layers=2,
            ffn_dim=256,
            dropout=0.15,
            head_dropout=0.1,
            pooling_type=None,
            channel_attention=False,
            scaling="std",
            loss="mse",
            pre_norm=True,
            norm_type="batchnorm",
        )

        self.model = PatchTSTForPrediction(config=self.config)

    def forecast(self, raw_df: pd.DataFrame, days: int = 30) -> pd.DataFrame:
        df = raw_df[['Date', 'Credit', 'Debit']].copy()
        df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%y', errors='coerce')
        df = df.dropna(subset=['Date'])
        df['cashflow'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0) - pd.to_numeric(df['Debit'], errors='coerce').fillna(0)
        df = df.groupby('Date').agg({'cashflow': 'sum'}).reset_index().rename(columns={'Date': 'date'})
        df = df.sort_values('date')
        df['cashflow'] = df['cashflow'].interpolate()

        if len(df) < self.context_length:
            raise ValueError(f"Need ≥{self.context_length} days; got {len(df)}.")

        context = df.iloc[-self.context_length:].copy()

        # ✅ Use IBM TimeSeriesPreprocessor
        tsp = TimeSeriesPreprocessor(
            timestamp_column="date",
            target_columns=["cashflow"],
            observable_columns=[],
            context_length=self.context_length,
            prediction_length=days,
            scaling=True,
            encode_categorical=False,
            scaler_type="standard"
        )
        tsp.train(context)
        proc = tsp.preprocess(context)

        tensor = torch.tensor(proc["cashflow"].values.reshape(1, -1, 1), dtype=torch.float32).to("cpu")

        self.model.eval()
        with torch.no_grad():
            output = self.model(past_values=tensor).prediction_outputs.cpu()

        scaler = tsp.target_scaler_dict["0"]
        yhat_real = scaler.inverse_transform(output.squeeze().numpy().reshape(-1, 1)).flatten()

        forecast_dates = pd.date_range(context['date'].iloc[-1] + pd.Timedelta(days=1), periods=days)
        df = pd.DataFrame({
            "ds": forecast_dates,
            "yhat": yhat_real
        })

        return df

    def forecast_summary(self, raw_df: pd.DataFrame, days: int = 30) -> dict:
        df = self.forecast(raw_df, days)
        summary = {
            "min": round(df['yhat'].min(), 2),
            "max": round(df['yhat'].max(), 2),
            "mean": round(df['yhat'].mean(), 2),
            "neg": int((df['yhat'] < 0).sum())
        }
        return summary


class ForecastExplainer:
    def __init__(self, granite_client):
        self.granite_client = granite_client

    def explain_forecast(self, forecast_df: pd.DataFrame, horizon_days: int = 30) -> str:
        df = forecast_df.tail(horizon_days)
        df['ds'] = df['ds'].dt.strftime('%b %d')
        summary = {
            "min": round(df['yhat'].min(), 2),
            "max": round(df['yhat'].max(), 2),
            "mean": round(df['yhat'].mean(), 2),
            "neg": int((df['yhat'] < 0).sum())
        }
        prompt = (
            f"Forecast for next {horizon_days} days:\n{df.to_string(index=False)}\n\n"
            f"Summary:\n- Min: ${summary['min']}\n- Max: ${summary['max']}\n"
            f"- Avg: ${summary['mean']}\n- Days negative: {summary['neg']}\n\n"
            f"Provide 2–4 sentence financial advice."
        )
        print("We came here", prompt)
        return summarize_with_granite(prompt, temperature=0.3, max_new_tokens=750)


if __name__ == "__main__":
    import sys

    class DummyClient:
        def generate_text(self, prompt: str) -> str:
            print("\n📤 Prompt to Granite:\n", prompt[:500], "\n")
            return "Maintain buffer on surplus days. Smooth out outflows using high-cashflow periods."

    if len(sys.argv) < 2:
        print("Usage: python forecasting_engine.py <path_to_csv>")
        sys.exit(1)

    df_in = pd.read_csv(sys.argv[1])
    forecaster = CashFlowForecaster()
    forecast_df = forecaster.forecast(df_in, days=30)

    print("\n📈 Forecast:")
    print(forecast_df)

    explainer = ForecastExplainer(DummyClient())
    print("\n🧠 Explanation:")
    print(explainer.explain_forecast(forecast_df))

    plt.figure(figsize=(12, 5))
    plt.plot(forecast_df['ds'], forecast_df['yhat'], marker='o')
    plt.title("🔮 Cash Flow Forecast (Next 30 Days)")
    plt.xlabel("Date")
    plt.ylabel("Predicted Cashflow")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
