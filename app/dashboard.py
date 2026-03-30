import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import os

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(page_title="Quant Strategy Dashboard", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #1E1E1E;
        border: 1px solid #333333;
        padding: 5% 5% 5% 10%;
        border-radius: 10px;
        color: white;
    }
    .disclaimer {
        font-size: 0.85rem;
        color: #aaaaaa;
        margin-top: -10px;
        margin-bottom: 20px;
    }
    .withdrawal-box {
        padding: 15px;
        border: 1px solid #ffcc00;
        border-radius: 5px;
        background-color: rgba(255, 204, 0, 0.1);
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Quantitative Strategy Performance")

# ==========================================
# 2. DATA LOADING & SESSION STATE
# ==========================================
@st.cache_data
def load_data():
    try:
        # Get the absolute path of the directory containing dashboard.py (the 'app' folder)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Navigate up one level to the root, then into data/processed/
        st01_path = os.path.join(current_dir, '..', 'data', 'processed', 'ST01.csv')
        st02_path = os.path.join(current_dir, '..', 'data', 'processed', 'ST02.csv')
        
        # Load the data using the absolute paths
        st01_df = pd.read_csv(st01_path, parse_dates=['entry_time', 'exit_time'])
        st02_df = pd.read_csv(st02_path, parse_dates=['entry_time', 'exit_time'])
        
        return st01_df, st02_df
        
    except FileNotFoundError as e:
        st.error("❌ Data files not found. Ensure ST01.csv and ST02.csv are in data/processed/")
        return pd.DataFrame(), pd.DataFrame()

st01_data, st02_data = load_data()

# Initialize Session State for the Simulator
if 'sim_rounds' not in st.session_state:
    st.session_state.sim_rounds = []
if 'sim_capital' not in st.session_state:
    st.session_state.sim_capital = 1000.0 # Default starting capital
if 'pending_withdrawal' not in st.session_state:
    st.session_state.pending_withdrawal = 0.0 # Tracks withdrawals made before executing a round

if st01_data.empty or st02_data.empty:
    st.stop()

# ==========================================
# 3. SIDEBAR (Global Filters for Dashboard)
# ==========================================
st.sidebar.header("⚙️ Dashboard Parameters")

strategy_choice = st.sidebar.radio("Strategy", ["ST01", "ST02"])
df_main = st01_data if "ST01" in strategy_choice else st02_data
default_start_cap = 500.0 if "ST01" in strategy_choice else 2700.0

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filters")

min_date = df_main['exit_time'].min().date()
max_date = df_main['exit_time'].max().date()
date_range = st.sidebar.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

assets = sorted(df_main['asset_name'].unique().tolist())
selected_assets = st.sidebar.multiselect("Select Assets", assets, default=assets)

trade_types = df_main['type'].unique().tolist()
selected_types = st.sidebar.multiselect("Trade Direction", trade_types, default=trade_types)

# Apply Filters
mask = (
    (df_main['exit_time'].dt.date >= date_range[0]) & 
    (df_main['exit_time'].dt.date <= date_range[1]) &
    (df_main['asset_name'].isin(selected_assets)) &
    (df_main['type'].isin(selected_types))
)
filtered_df = df_main[mask].copy()


# ==========================================
# 4. METRICS CALCULATION ENGINE
# ==========================================
def calculate_dynamic_metrics(data, start_capital):
    if data.empty:
        return {"profit": 0, "win_rate": 0, "pf": 0, "expectancy": 0, "max_dd": 0, "sharpe": 0, "end_cap": start_capital}
    
    wins = data[data['profit'] > 0]
    losses = data[data['profit'] < 0]
    
    total_profit = data['profit'].sum()
    end_cap = start_capital + total_profit
    win_rate = len(wins) / len(data) if len(data) > 0 else 0
    
    gross_win = wins['profit'].sum()
    gross_loss = abs(losses['profit'].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else np.inf
    
    avg_win_r = wins['r_multiple'].mean() if not wins.empty else 0
    avg_loss_r = abs(losses['r_multiple'].mean()) if not losses.empty else 0
    expectancy = (win_rate * avg_win_r) - ((1 - win_rate) * avg_loss_r)
    
    temp_equity = [start_capital]
    current_eq = start_capital
    for p in data['profit']:
        current_eq += p
        temp_equity.append(current_eq)
        
    equity_s = pd.Series(temp_equity)
    rolling_max = equity_s.cummax()
    drawdown = (equity_s - rolling_max) / rolling_max
    max_dd = abs(drawdown.min())
    
    data['date'] = data['exit_time'].dt.date
    daily_pnl = data.groupby('date')['profit'].sum()
    if len(daily_pnl) > 1 and daily_pnl.std() != 0:
        avg_equity = equity_s.mean()
        daily_pct = daily_pnl / avg_equity
        sharpe = (daily_pct.mean() / daily_pct.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    return {
        "profit": total_profit, "win_rate": win_rate, "pf": pf, 
        "expectancy": expectancy, "max_dd": max_dd, "sharpe": sharpe,
        "equity_curve": equity_s, "drawdown_curve": drawdown, "end_cap": end_cap
    }

metrics = calculate_dynamic_metrics(filtered_df, default_start_cap)


# ==========================================
# 5. TABS SETUP
# ==========================================
tab_dash, tab_sim = st.tabs(["📊 Performance Dashboard", "🧪 Risk Simulator"])


# ==========================================
# 6. TAB 1: PERFORMANCE DASHBOARD
# ==========================================
with tab_dash:
    bal_col1, bal_col2 = st.columns(2)
    bal_col1.markdown(f"### **Starting Balance:** £{default_start_cap:,.2f}")
    bal_col2.markdown(f"### **Final Balance:** £{metrics['end_cap']:,.2f}")
    st.markdown("---")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        p_val = metrics['profit']
        p_str = f"-£{abs(p_val):,.2f}" if p_val < 0 else f"£{p_val:,.2f}"
        st.metric("Net Profit", p_str)
    with col2:
        st.metric("Win Rate", f"{metrics['win_rate']*100:.1f}%")
    with col3:
        st.metric("Profit Factor", f"{metrics['pf']:.2f}")
    with col4:
        st.metric("Expectancy (R)", f"{metrics['expectancy']:+.2f}R")
    with col5:
        st.metric("Max Drawdown", f"{metrics['max_dd']*100:.2f}%")
    with col6:
        st.metric("Sharpe Ratio", f"{metrics['sharpe']:.2f}")

    st.markdown("<div class='disclaimer'><b>Data Engineering Note:</b> The Cumulative Equity Curve and Final Balance metrics displayed here represent Gross Trade Equity (Starting Capital + Closed Trade P/L). This isolates and proves the mathematical edge of the strategy. It intentionally excludes non-trade broker cash flows such as overnight swaps, dividends, and rebates, which cause minor deviations from the final MT5 broker statement.</div>", unsafe_allow_html=True)

    if not filtered_df.empty:
        col_chart1, col_chart2 = st.columns(2)
        dates = [filtered_df['entry_time'].iloc[0]] + filtered_df['exit_time'].tolist()
        
        with col_chart1:
            fig_equity = px.line(x=dates, y=metrics['equity_curve'], labels={'x': 'Date', 'y': 'Account Balance (£)'}, title="Cumulative Equity Curve")
            fig_equity.update_traces(line_color='#00ff88', line_width=3)
            st.plotly_chart(fig_equity, use_container_width=True)

        with col_chart2:
            # Drawdown fix: Native negative plotting (removed autorange="reversed")
            fig_dd = px.area(x=dates, y=metrics['drawdown_curve'] * 100, labels={'x': 'Date', 'y': 'Drawdown (%)'}, title="Underwater Drawdown")
            fig_dd.update_traces(line_color='#ff3333', fillcolor='rgba(255, 51, 51, 0.3)')
            fig_dd.update_layout(margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig_dd, use_container_width=True)

        st.markdown("---")
        
        # Monthly P/L Bar Chart added here
        st.subheader("📅 Monthly P/L")
        monthly_df = filtered_df.copy()
        monthly_df['month'] = monthly_df['exit_time'].dt.strftime('%Y-%m')
        monthly_pnl = monthly_df.groupby('month')['profit'].sum().reset_index()
        colors = ['#ff3333' if val < 0 else '#00ff88' for val in monthly_pnl['profit']]
        
        fig_monthly = px.bar(monthly_pnl, x='month', y='profit', 
                             labels={'month': 'Month', 'profit': 'Net Profit (£)'},
                             title="")
        fig_monthly.update_traces(marker_color=colors)
        st.plotly_chart(fig_monthly, use_container_width=True)

        col_chart3, col_chart4 = st.columns(2)
        with col_chart3:
            r_data = filtered_df[filtered_df['r_multiple'] != 0]
            fig_r = px.histogram(r_data, x='r_multiple', nbins=30, color_discrete_sequence=['#3399ff'], title="R-Multiple Distribution")
            fig_r.add_vline(x=0, line_dash="dash", line_color="white")
            st.plotly_chart(fig_r, use_container_width=True)

        with col_chart4:
            asset_pnl = filtered_df.groupby('asset_name')['profit'].sum().reset_index().sort_values(by='profit', ascending=True)
            colors = ['#ff3333' if val < 0 else '#00ff88' for val in asset_pnl['profit']]
            fig_asset = px.bar(asset_pnl, y='asset_name', x='profit', orientation='h', title="Net Profit by Asset")
            fig_asset.update_traces(marker_color=colors)
            st.plotly_chart(fig_asset, use_container_width=True)

        st.subheader("📋 Execution Log")
        display_df = filtered_df[['exit_time', 'asset_name', 'type', 'volume', 'profit', 'return_label', 'capital_at_exit']].copy()
        display_df.columns = ['Close Time', 'Asset', 'Type', 'Volume', 'Profit (£)', 'R-Multiple', 'Balance (£)']
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No trades found for the selected filters.")


# ==========================================
# 7. TAB 2: RISK SIMULATOR
# ==========================================
with tab_sim:
    st.markdown("### 🧪 Compounding Risk Simulator")
    st.markdown("Simulate what would happen to this exact historical sequence of R-Multiples if you changed your risk profile and capital base.")
    
    is_new_run = len(st.session_state.sim_rounds) == 0
    
    # ----------------------------------------------------
    # CAPITAL MANAGEMENT & WITHDRAWAL SECTION
    # ----------------------------------------------------
    if not is_new_run:
        current_avail = st.session_state.sim_rounds[-1]["Forward Capital"]
        
        st.info(f"💰 **Available Capital for Next Round:** £{current_avail:,.2f}")
        
        with st.expander("💸 Make a Withdrawal"):
            with st.form("withdraw_form"):
                w_amt = st.number_input("Amount to Withdraw (£)", min_value=0.0, max_value=float(current_avail), step=50.0)
                w_submit = st.form_submit_button("Apply Withdrawal")
                
                if w_submit:
                    if 0 < w_amt <= current_avail:
                        st.session_state.sim_rounds[-1]['Withdrawn'] += w_amt
                        st.session_state.sim_rounds[-1]['Forward Capital'] -= w_amt
                        
                        st.session_state.sim_capital = st.session_state.sim_rounds[-1]['Forward Capital']
                        st.rerun() 
                    elif w_amt > current_avail:
                        st.error("Cannot withdraw more than available capital.")

    # ----------------------------------------------------
    # EXECUTION FORM
    # ----------------------------------------------------
    if is_new_run:
        sim_start_cap = st.number_input("Initial Starting Capital (£)", min_value=100.0, value=1000.0, step=100.0)
    else:
        sim_start_cap = st.session_state.sim_rounds[-1]['Forward Capital']

    with st.form("simulator_form"):
        sc1, sc2 = st.columns(2)
        with sc1:
            sim_strat = st.selectbox("Strategy to Simulate", ["Account ST01", "Account ST02"])
        with sc2:
            sim_risk = st.slider("Risk Per Trade (%)", min_value=1.0, max_value=25.0, value=5.0, step=0.5)
            
        sd1, sd2 = st.columns(2)
        with sd1:
            sim_df_source = st01_data if "ST01" in sim_strat else st02_data
            s_min_date = sim_df_source['exit_time'].min().date()
            s_max_date = sim_df_source['exit_time'].max().date()
            sim_dates = st.date_input("Simulation Period", [s_min_date, s_max_date], min_value=s_min_date, max_value=s_max_date)
            
        execute_button = st.form_submit_button("🚀 Execute Round")

    if not is_new_run:
        if st.button("🗑️ Reset Simulator completely"):
            st.session_state.sim_rounds = []
            st.session_state.sim_capital = 1000.0
            st.session_state.pending_withdrawal = 0.0
            st.rerun()

    # ----------------------------------------------------
    # EXECUTION LOGIC
    # ----------------------------------------------------
    if execute_button:
        if len(sim_dates) != 2:
            st.warning("Please select a valid start and end date.")
        else:
            sim_mask = (sim_df_source['exit_time'].dt.date >= sim_dates[0]) & (sim_df_source['exit_time'].dt.date <= sim_dates[1])
            sim_data = sim_df_source[sim_mask].copy()
            
            if sim_data.empty:
                st.warning("No trades found in this period to simulate.")
            else:
                start_cap = sim_start_cap
                
                sim_equity = [start_cap]
                sim_profits = []
                current_cap = start_cap
                
                for r in sim_data['r_multiple']:
                    trade_risk = current_cap * (sim_risk / 100.0)
                    trade_profit = trade_risk * r
                    current_cap += trade_profit
                    
                    sim_profits.append(trade_profit)
                    sim_equity.append(current_cap)
                
                eq_series = pd.Series(sim_equity)
                roll_max = eq_series.cummax()
                dd = (eq_series - roll_max) / roll_max
                max_dd = abs(dd.min())
                
                sim_data['sim_profit'] = sim_profits
                sim_data['date'] = sim_data['exit_time'].dt.date
                daily_p = sim_data.groupby('date')['sim_profit'].sum()
                sim_sharpe = 0
                if len(daily_p) > 1 and daily_p.std() != 0:
                    daily_pct = daily_p / eq_series.mean()
                    sim_sharpe = (daily_pct.mean() / daily_pct.std()) * np.sqrt(252)

                round_number = len(st.session_state.sim_rounds) + 1
                
                round_result = {
                    "Round": round_number,
                    "Strategy": sim_strat,
                    "Period": f"{sim_dates[0]} to {sim_dates[1]}",
                    "Risk %": f"{sim_risk}%",
                    "Start Capital": start_cap,
                    "Net Profit": current_cap - start_cap,
                    "End Capital": current_cap,
                    "Withdrawn": 0.0,
                    "Forward Capital": current_cap,
                    "Max Drawdown": max_dd,
                    "Sharpe Ratio": sim_sharpe,
                    "Equity Curve": sim_equity,
                    "Drawdown Curve": dd.tolist(),
                    "Dates": [sim_data['entry_time'].iloc[0]] + sim_data['exit_time'].tolist(),
                    "Profits": sim_profits # Added to support the Monthly P/L in the simulator
                }
                
                st.session_state.sim_rounds.append(round_result)
                st.session_state.sim_capital = current_cap 
                st.rerun()

    # ----------------------------------------------------
    # HISTORY TABLE & CHARTS
    # ----------------------------------------------------
    if st.session_state.sim_rounds:
        st.markdown("---")
        st.markdown("### 🏆 Simulation Rounds History")
        
        history_df = pd.DataFrame(st.session_state.sim_rounds)
        
        display_hist = history_df[['Round', 'Strategy', 'Period', 'Risk %', 'Start Capital', 'Net Profit', 'End Capital', 'Withdrawn', 'Forward Capital', 'Max Drawdown', 'Sharpe Ratio']].copy()
        
        for col in ['Start Capital', 'Net Profit', 'End Capital', 'Withdrawn', 'Forward Capital']:
            display_hist[col] = display_hist[col].apply(lambda x: f"-£{abs(x):,.2f}" if x < 0 else f"£{x:,.2f}")
            
        display_hist['Max Drawdown'] = display_hist['Max Drawdown'].apply(lambda x: f"{x*100:.2f}%")
        display_hist['Sharpe Ratio'] = display_hist['Sharpe Ratio'].apply(lambda x: f"{x:.2f}")
        
        st.dataframe(display_hist, hide_index=True, use_container_width=True)
        
        for r in reversed(st.session_state.sim_rounds):
            with st.expander(f"Detailed Results: Round {r['Round']} (Risk: {r['Risk %']})", expanded=(r['Round'] == len(st.session_state.sim_rounds))):
                
                rc1, rc2, rc3, rc4 = st.columns(4)
                rc1.metric("Start Capital", f"£{r['Start Capital']:,.2f}")
                
                profit_val = r['Net Profit']
                delta_str = f"-£{abs(profit_val):,.2f}" if profit_val < 0 else f"£{profit_val:,.2f}"
                
                rc2.metric("End Capital", f"£{r['End Capital']:,.2f}", delta_str)
                
                rc3.metric("Sharpe Ratio", f"{r['Sharpe Ratio']:.2f}")
                rc4.metric("Max Drawdown", f"{r['Max Drawdown']*100:.2f}%")
                
                c_ch1, c_ch2, c_ch3 = st.columns(3)
                
                with c_ch1:
                    f_eq = px.line(x=r['Dates'], y=r['Equity Curve'], title=f"Round {r['Round']} Equity")
                    f_eq.update_traces(line_color='#00ff88')
                    f_eq.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(f_eq, use_container_width=True)
                    
                with c_ch2:
                    # Native negative plotting for Drawdown
                    f_dd = px.area(x=r['Dates'], y=np.array(r['Drawdown Curve']) * 100, title=f"Round {r['Round']} Drawdown")
                    f_dd.update_traces(line_color='#ff3333', fillcolor='rgba(255, 51, 51, 0.3)')
                    f_dd.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(f_dd, use_container_width=True)

                with c_ch3:
                    # Simulator Monthly P/L
                    sim_df_temp = pd.DataFrame({'Date': pd.to_datetime(r['Dates'][1:]), 'Profit': r['Profits']})
                    sim_df_temp['month'] = sim_df_temp['Date'].dt.strftime('%Y-%m')
                    sim_monthly = sim_df_temp.groupby('month')['Profit'].sum().reset_index()
                    sim_colors = ['#ff3333' if val < 0 else '#00ff88' for val in sim_monthly['Profit']]
                    
                    f_mo = px.bar(sim_monthly, x='month', y='Profit', title=f"Round {r['Round']} Monthly P/L")
                    f_mo.update_traces(marker_color=sim_colors)
                    f_mo.update_layout(margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(f_mo, use_container_width=True)