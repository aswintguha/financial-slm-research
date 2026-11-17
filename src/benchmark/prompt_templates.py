"""
Prompt templates for Phase 05: Zero-Shot SLM Financial Time-Series Forecasting.

Definitions:
- Template A (Primary Benchmark Standard):
  Prompts the model with the sequence of historical closing prices over the past
  W=20 trading days up to origin_date t and solicits a 5-day ahead cumulative log return.
  Format constraint: [FORECAST: <return>]

- Template B (Price Level Wording Ablation - Development Split Only):
  Prompts the model with the exact same historical prices and current price, but solicits
  a nominal price level forecast P_{t+5}.
  Format constraint: [FORECAST: <price>]

- Template C (Daily Returns Sequence Input Ablation - Development Split Only):
  Prompts the model with past daily log returns inside the context window and solicits
  a cumulative return forecast.
  Format constraint: [FORECAST: <return>]
"""

from typing import List, Dict, Any

def format_template_a(
    ticker: str,
    country: str,
    sector: str,
    origin_date: str,
    target_date: str,
    past_prices: List[float]
) -> str:
    """
    Primary benchmark prompt. Formats past prices to 2 decimal places and requests
    the cumulative 5-day log return.
    """
    price_str = ", ".join(f"{p:.2f}" for p in past_prices)
    prompt = (
        f"You are an expert quantitative financial analyst.\n"
        f"Analyze the following historical closing price sequence for {ticker} ({country}, {sector}) "
        f"over the past 20 trading days up to {origin_date}:\n"
        f"Prices: [{price_str}]\n\n"
        f"Task: Predict the cumulative 5-trading-day ahead log return from {origin_date} to {target_date}.\n"
        f"Format your output strictly as: [FORECAST: <return>]\n"
        f"Example: [FORECAST: +0.0125]\n"
        f"Do not explain or add commentary. Output only the bracketed tag."
    )
    return prompt

def format_template_b(
    ticker: str,
    country: str,
    sector: str,
    origin_date: str,
    target_date: str,
    past_prices: List[float]
) -> str:
    """
    Price-level wording sensitivity prompt.
    """
    price_str = ", ".join(f"{p:.2f}" for p in past_prices)
    current_price = past_prices[-1]
    prompt = (
        f"You are an expert quantitative financial analyst.\n"
        f"Historical closing prices for {ticker} ({country}, {sector}) over the past 20 trading days up to {origin_date}:\n"
        f"Prices: [{price_str}]\n"
        f"The current closing price on {origin_date} is {current_price:.2f}.\n\n"
        f"Task: Predict the exact closing price 5 trading days ahead on {target_date}.\n"
        f"Format your output strictly as: [FORECAST: <price>]\n"
        f"Example: [FORECAST: {current_price:.2f}]\n"
        f"Do not explain or add commentary. Output only the bracketed tag."
    )
    return prompt

def format_template_c(
    ticker: str,
    country: str,
    sector: str,
    origin_date: str,
    target_date: str,
    past_daily_returns: List[float]
) -> str:
    """
    Input representation sensitivity prompt: daily log returns input context.
    """
    ret_str = ", ".join(f"{r:+.4f}" for r in past_daily_returns)
    prompt = (
        f"You are an expert quantitative financial analyst.\n"
        f"The sequence of daily percentage returns for {ticker} ({country}, {sector}) "
        f"over the past 19 trading sessions up to {origin_date} is:\n"
        f"Daily Returns: [{ret_str}]\n\n"
        f"Task: Predict the cumulative percentage return over the next 5 trading days up to {target_date}.\n"
        f"Format your output strictly as: [FORECAST: <return>]\n"
        f"Example: [FORECAST: +0.0125]\n"
        f"Do not explain or add commentary. Output only the bracketed tag."
    )
    return prompt

