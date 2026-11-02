import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Forex Analysis Dashboard", page_icon="📊", layout="wide")
st.title("📊 Forex Analysis Dashboard")
st.caption("Analisis edukasi XAUUSD dari data publik Yahoo Finance. Sinyal bersifat simulasi, bukan rekomendasi transaksi.")

@st.cache_data(ttl=60)
def load_data(interval):
    ticker = "XAUUSD=X"
    period = "5d" if interval in ("5m", "15m", "30m") else "1mo"
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.title)
    needed = ["Open", "High", "Low", "Close"]
    if not all(c in df.columns for c in needed):
        return pd.DataFrame()
    return df.dropna(subset=needed).copy()

def indicators(df):
    x = df.copy()
    x["EMA20"] = x["Close"].ewm(span=20, adjust=False).mean()
    x["EMA50"] = x["Close"].ewm(span=50, adjust=False).mean()
    delta = x["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    x["RSI"] = 100 - (100 / (1 + rs))
    ema12 = x["Close"].ewm(span=12, adjust=False).mean()
    ema26 = x["Close"].ewm(span=26, adjust=False).mean()
    x["MACD"] = ema12 - ema26
    x["MACD_Signal"] = x["MACD"].ewm(span=9, adjust=False).mean()
    return x.dropna()

interval_label = st.selectbox("Timeframe", ["5m", "15m", "30m", "1h"], index=1)
if interval_label == "1h":
    interval = "1h"
else:
    interval = interval_label

with st.spinner("Mengambil data XAUUSD..."):
    raw = load_data(interval)

if raw.empty or len(raw) < 55:
    st.error("Data XAUUSD belum tersedia dari sumber publik. Coba beberapa saat lagi atau ganti timeframe.")
    st.stop()

df = indicators(raw)
last = df.iloc[-1]
prev = df.iloc[-2]

bull = last["EMA20"] > last["EMA50"] and last["MACD"] > last["MACD_Signal"] and 50 <= last["RSI"] < 70
bear = last["EMA20"] < last["EMA50"] and last["MACD"] < last["MACD_Signal"] and 30 < last["RSI"] <= 50
if bull:
    state, explanation = "SIMULASI BUY", "EMA20 di atas EMA50, MACD di atas garis sinyal, dan RSI berada pada rentang konfirmasi naik."
elif bear:
    state, explanation = "SIMULASI SELL", "EMA20 di bawah EMA50, MACD di bawah garis sinyal, dan RSI berada pada rentang konfirmasi turun."
else:
    state, explanation = "WAIT / NETRAL", "Syarat indikator belum selaras. Tunggu data candle berikutnya."

c1, c2, c3, c4 = st.columns(4)
c1.metric("Harga terakhir", f'{last["Close"]:.3f}')
c2.metric("RSI 14", f'{last["RSI"]:.2f}')
c3.metric("EMA 20", f'{last["EMA20"]:.3f}')
c4.metric("EMA 50", f'{last["EMA50"]:.3f}')

st.subheader(state)
st.write(explanation)
st.caption(f"Update data: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} | Refresh otomatis melalui cache 60 detik.")

fig = go.Figure()
fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="XAUUSD"))
fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"], name="EMA 20", line=dict(width=1.5)))
fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], name="EMA 50", line=dict(width=1.5)))
fig.update_layout(height=520, xaxis_rangeslider_visible=False, title="XAUUSD Candlestick + EMA")
st.plotly_chart(fig, use_container_width=True)

rsi_fig = go.Figure()
rsi_fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI 14"))
rsi_fig.add_hline(y=70, line_dash="dash")
rsi_fig.add_hline(y=50, line_dash="dot")
rsi_fig.add_hline(y=30, line_dash="dash")
rsi_fig.update_layout(height=260, title="RSI 14", yaxis_range=[0, 100])
st.plotly_chart(rsi_fig, use_container_width=True)

st.subheader("Rincian indikator")
st.dataframe(pd.DataFrame({
    "Indikator": ["EMA 20 vs EMA 50", "MACD vs Signal", "RSI 14"],
    "Nilai terakhir": [
        "EMA20 > EMA50" if last["EMA20"] > last["EMA50"] else "EMA20 < EMA50",
        "MACD > Signal" if last["MACD"] > last["MACD_Signal"] else "MACD < Signal",
        f'{last["RSI"]:.2f}'
    ],
    "Interpretasi": [
        "Kecenderungan naik" if last["EMA20"] > last["EMA50"] else "Kecenderungan turun",
        "Momentum positif" if last["MACD"] > last["MACD_Signal"] else "Momentum negatif",
        "Kuat" if last["RSI"] >= 70 else "Lemah" if last["RSI"] <= 30 else "Rentang tengah"
    ]
}), hide_index=True, use_container_width=True)

st.download_button("Unduh data CSV", df.to_csv().encode("utf-8"), "xauusd_analysis.csv", "text/csv")
st.caption("Catatan: XAUUSD=X adalah simbol data publik Yahoo Finance, bukan feed broker MT5. Data dapat terlambat/tidak lengkap. Dashboard hanya untuk latihan analisis; bukan instruksi transaksi.")
