import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # For more control if needed later

# --- Page Configuration (optional) ---
st.set_page_config(
    page_title="Stock Price Comparison (GOOGL vs NVDA)",
    layout="wide",
    initial_sidebar_state="auto"
)

st.title("📊 Stock Price Comparison: GOOGL vs NVDA")

# --- Sidebar Controls ---
st.sidebar.header("📈 Plot Controls")

# Option to show 200-day moving average
show_ma = st.sidebar.checkbox("Show 200-Day Moving Average", value=False)

# Year Range Input (single control)
current_year = pd.Timestamp.now().year
year_range = st.sidebar.slider(
    "Select Year Range",
    min_value=1990,
    max_value=current_year,
    value=(current_year - 5, current_year),
    step=1
)
start_year, end_year = year_range

# Time Interval Selection
interval_options = {
    "Day": "1d",
    "Week": "1wk",
    "Month": "1mo",
    "Quarter": "3mo", # yfinance uses 3mo for quarter, but we'll resample for exact quarter end
    "Year": "1y"
}
selected_interval_name = st.sidebar.selectbox(
    "Select Interval",
    options=list(interval_options.keys())
)
yfinance_interval_code = interval_options[selected_interval_name] # Interval for yfinance fetch
# Resampling code will be based on selected_interval_name, as yfinance's '3mo' is not quarter-end specific

# --- Data Fetching and Resampling Function ---
@st.cache_data(ttl=3600) # Cache data for 1 hour to avoid re-downloading on every rerun
def fetch_and_resample_data(symbol, start_date, interval_name):
    """
    Fetches historical stock data for a given symbol and resamples it based on the interval.
    Returns a DataFrame with the 'Close' price or an empty DataFrame if an error occurs.
    """
    try:
        # yfinance often requires a 'period' or 'start/end' for history.
        # Fetching a broad period and then filtering/resampling is safer.
        # For long histories, 'max' is good, then filter by start_date
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="max")

        if df.empty:
            st.warning(f"No historical data found for {symbol}.")
            return pd.DataFrame()

        # Filter data by start date
        df = df[df.index >= start_date]

        if df.empty:
            st.warning(f"No data found for {symbol} from {start_date[:4]} onwards. Try an earlier year.")
            return pd.DataFrame()

        # Resample data based on interval name
        if interval_name == "Day":
            # No resampling needed, use daily data
            pass
        elif interval_name == "Week":
            # Resample to weekly data: take the last close of the week
            df = df['Close'].resample('W').last().to_frame()
        elif interval_name == "Month":
            # Resample to monthly data: take the last close of the month
            df = df['Close'].resample('M').last().to_frame()
        elif interval_name == "Quarter":
            # Resample to quarterly data: take the last close of the quarter
            df = df['Close'].resample('Q').last().to_frame()
        elif interval_name == "Year":
            # Resample to yearly data: take the last close of the year
            df = df['Close'].resample('Y').last().to_frame()

        # Ensure 'Close' column exists after resampling
        if 'Close' not in df.columns:
            df.rename(columns={df.columns[0]: 'Close'}, inplace=True) # If resample returned a series
        
        # Add a symbol column for Plotly
        df['Symbol'] = symbol
        return df
    except Exception as e:
        st.error(f"An error occurred while fetching {symbol} data: {e}\n"
                 "Please check your internet connection or try again later.")
        return pd.DataFrame()

# --- Main Plotting Logic ---
start_date_str = f"{start_year}-01-01"
end_date_str = f"{end_year}-12-31"

# Fetch data for GOOGL
df_googl = fetch_and_resample_data("GOOGL", start_date_str, selected_interval_name)
# Fetch data for NVDA
df_nvda = fetch_and_resample_data("NVDA", start_date_str, selected_interval_name)
# Fetch data for TSLA
df_tsla = fetch_and_resample_data("TSLA", start_date_str, selected_interval_name)

# Combine DataFrames if any are not empty
combined_df = pd.DataFrame()
if not df_googl.empty:
    combined_df = pd.concat([combined_df, df_googl])
if not df_nvda.empty:
    combined_df = pd.concat([combined_df, df_nvda])
if not df_tsla.empty:
    combined_df = pd.concat([combined_df, df_tsla])

# Filter combined_df by end date
if not combined_df.empty:
    combined_df = combined_df[(combined_df.index >= start_date_str) & (combined_df.index <= end_date_str)]

# Calculate 200-day moving average if option is selected and interval is daily
if show_ma and selected_interval_name == "Day" and not combined_df.empty:
    for symbol in ["GOOGL", "NVDA", "TSLA"]:
        symbol_mask = combined_df['Symbol'] == symbol
        combined_df.loc[symbol_mask, 'MA200'] = combined_df.loc[symbol_mask, 'Close'].rolling(window=200).mean()

if not combined_df.empty:
    # Use Plotly Express for plotting
    fig = px.line(
        combined_df.reset_index(), # Reset index to make 'Date' a column for Plotly
        x='Date',
        y='Close',
        color='Symbol',
        line_dash='Symbol', # Optional: different dash types for symbols
        title=f'GOOGL vs NVDA vs TSLA Stock Price ({selected_interval_name}ly) from {start_year}',
        labels={
            "Date": "Date",
            "Close": "Close Price (USD)"
        },
        hover_data={
            "Date": "|%Y-%m-%d", # Format date on hover
            "Close": ":$.2f",    # Format price on hover
            "Symbol": True       # Show symbol on hover
        }
    )

    # Add 200-day moving average traces if selected
    if show_ma and selected_interval_name == "Day":
        for symbol, color in zip(["GOOGL", "NVDA", "TSLA"], ["steelblue", "firebrick", "green"]):
            ma_data = combined_df[combined_df['Symbol'] == symbol].reset_index()
            if 'MA200' in ma_data.columns:
                fig.add_scatter(x=ma_data['Date'], y=ma_data['MA200'], mode='lines',
                                name=f"{symbol} 200D MA", line=dict(dash='dot', color=color, width=2),
                                showlegend=True)

    # Customize trace colors for consistency with previous Matplotlib example if desired
    fig.update_traces(
        selector=dict(name="GOOGL"),
        line=dict(color='steelblue')
    )
    fig.update_traces(
        selector=dict(name="NVDA"),
        line=dict(color='firebrick')
    )
    fig.update_traces(
        selector=dict(name="TSLA"),
        line=dict(color='green')
    )

    fig.update_layout(
        hovermode="x unified", # Shows all traces' values at a given x-coordinate
        legend_title_text='Stock',
        xaxis_title="Date",
        yaxis_title="Close Price (USD)",
        xaxis_tickformat='%Y-%m-%d', # Ensure date format on x-axis
        # Improve interactivity
        hoverlabel=dict(
            bgcolor="white",
            font_size=12,
            font_family="Arial"
        ),
        margin=dict(l=0, r=0, t=50, b=0) # Adjust margins for better fit
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Please select valid parameters and ensure stock data is available.")
    st.image("https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExYTgyY2FkYWV0MzdkNGQ2YTliYjcyZjUyMGNiZmQ3ZmU4ZTYwNzI2YiZlcD12MV9pbnRlcm5hbF9naWZzX2dpZklkJmN0PWc/3o7aCSPyUNsfdDvpro/giphy.gif", caption="Loading data...", use_column_width=True)

st.markdown("---")
st.markdown("Developed with ❤️ using Streamlit, yfinance, and Plotly.")