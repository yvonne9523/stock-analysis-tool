import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 頁面配置與暗黑交易終端風格 CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI 量化投資與技術分析終端",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    /* 全域暗黑科技風 */
    .stApp {
        background-color: #0b0f19;
        color: #f1f5f9;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    }
    
    /* 側邊欄樣式 */
    section[data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
    
    /* 卡片式容器 */
    .metric-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-bottom: 12px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        font-weight: 500;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #f8fafc;
        font-family: 'SF Pro Display', Roboto, sans-serif;
    }
    .metric-delta-pos {
        font-size: 0.85rem;
        color: #ef4444; /* 台灣股市習慣：紅漲 */
        font-weight: 600;
        margin-top: 4px;
    }
    .metric-delta-neg {
        font-size: 0.85rem;
        color: #22c55e; /* 綠跌 */
        font-weight: 600;
        margin-top: 4px;
    }
    
    /* 訊號卡片 */
    .signal-box-buy {
        background: rgba(239, 68, 68, 0.12);
        border-left: 4px solid #ef4444;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 8px;
        color: #fca5a5;
        font-weight: 500;
    }
    .signal-box-sell {
        background: rgba(34, 197, 94, 0.12);
        border-left: 4px solid #22c55e;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 8px;
        color: #86efac;
        font-weight: 500;
    }
    .signal-box-neutral {
        background: rgba(148, 163, 184, 0.08);
        border-left: 4px solid #64748b;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 8px;
        color: #cbd5e1;
    }
    
    /* Tab 樣式客製 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #1e293b;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #94a3b8;
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e293b !important;
        color: #38bdf8 !important;
        border-bottom: 2px solid #38bdf8 !important;
    }
    
    /* 按鈕樣式 */
    .stButton>button {
        background: linear-gradient(135deg, #0284c7, #2563eb);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #0369a1, #1d4ed8);
        box-shadow: 0 6px 16px rgba(37, 99, 235, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 資料快取與防限流機制 (Streamlit Cache)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_stock_data(ticker_symbol, period_choice):
    """快取股價與基本面資料，有效防止 Yahoo Finance Rate Limit"""
    stock_obj = yf.Ticker(ticker_symbol)
    
    # 抓取歷史 K 線
    df = stock_obj.history(period=period_choice)
    
    # 安全取得 info 資料
    info_dict = {}
    try:
        info_dict = stock_obj.get_info()
    except Exception:
        try:
            info_dict = stock_obj.fast_info
        except Exception:
            info_dict = {}
            
    return df, info_dict

def calculate_technical_indicators(df):
    """計算技術指標 (MA, RSI, KD)"""
    if df.empty:
        return df
    
    # 均線
    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA60"] = df["Close"].rolling(window=60).mean()
    
    # RSI (14)
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # KD (14, 3)
    low_min = df["Low"].rolling(window=14).min()
    high_max = df["High"].rolling(window=14).max()
    rsv = 100 * ((df["Close"] - low_min) / (high_max - low_min + 1e-9))
    
    k_list, d_list = [], []
    k_prev, d_prev = 50.0, 50.0
    for val in rsv:
        if np.isnan(val):
            k_list.append(np.nan)
            d_list.append(np.nan)
        else:
            k_curr = (2/3) * k_prev + (1/3) * val
            d_curr = (2/3) * d_prev + (1/3) * k_curr
            k_list.append(k_curr)
            d_list.append(d_curr)
            k_prev, d_prev = k_curr, d_curr
    df["K"] = k_list
    df["D"] = d_list
    return df

# -----------------------------------------------------------------------------
# 側邊欄控制項
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ 交易終端控制台")
    ticker_input = st.text_input(
        "股票代號",
        value="2330.TW",
        help="台股請加上代尾綴 (如: 2330.TW, 2454.TW, 0050.TW)；美股直接填寫代碼 (如: NVDA, TSLA, AAPL)"
    ).strip().upper()
    
    period_option = st.selectbox(
        "時間週期",
        options=["3m", "6m", "1y", "2y", "5y"],
        index=1,
        format_func=lambda x: {"3m": "近 3 個月", "6m": "近 6 個月", "1y": "近 1 年", "2y": "近 2 年", "5y": "近 5 年"}.get(x, x)
    )
    
    st.markdown("---")
    st.caption("💡 **防限流機制已啟用**：資料具備 10 分鐘本地快取保護，大幅減少 Yahoo Finance 頻繁查詢封鎖。")
    btn_search = st.button("🚀 重新整理分析", use_container_width=True)

# -----------------------------------------------------------------------------
# 主畫面核心呈現
# -----------------------------------------------------------------------------
if ticker_input:
    with st.spinner(f"正在連線量化終端載入 {ticker_input} 最新數據..."):
        try:
            hist, info = fetch_stock_data(ticker_input, period_option)
            
            if hist is None or hist.empty:
                st.error(f"⚠️ 無法取得代碼 `{ticker_input}` 的價格資訊。請檢查代號是否正確，或稍後再試。")
            else:
                hist = calculate_technical_indicators(hist)
                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest
                
                curr_price = float(latest["Close"])
                prev_price = float(prev["Close"])
                price_diff = curr_price - prev_price
                pct_diff = (price_diff / prev_price) * 100 if prev_price != 0 else 0
                
                # 公司名稱提取
                company_name = info.get("longName") or info.get("shortName") or ticker_input
                sector = info.get("sector", "主要產業")
                currency = info.get("currency", "TWD" if ".TW" in ticker_input else "USD")
                
                # 頁首標題區
                st.markdown(f"""
                <div style="display: flex; align-items: baseline; gap: 15px; margin-bottom: 5px;">
                    <h1 style="margin: 0; font-size: 2.2rem; color: #ffffff;">{company_name}</h1>
                    <span style="font-size: 1.2rem; color: #38bdf8; font-weight: 600; background: rgba(56, 189, 248, 0.1); padding: 2px 10px; border-radius: 6px;">{ticker_input}</span>
                    <span style="color: #64748b; font-size: 0.95rem;">{sector} | 計價幣別: {currency}</span>
                </div>
                """, unsafe_allow_html=True)
                
                # 精緻指標卡片 (4 列)
                col1, col2, col3, col4 = st.columns(4)
                
                delta_class = "metric-delta-pos" if price_diff >= 0 else "metric-delta-neg"
                delta_arrow = "▲" if price_diff >= 0 else "▼"
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">最新收盤價</div>
                        <div class="metric-value">{curr_price:,.2f}</div>
                        <div class="{delta_class}">{delta_arrow} {price_diff:+,.2f} ({pct_diff:+.2f}%)</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col2:
                    pe_val = info.get("trailingPE") or info.get("forwardPE")
                    pe_str = f"{pe_val:.2f} 倍" if isinstance(pe_val, (int, float)) else "無資料"
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">本益比 (P/E Ratio)</div>
                        <div class="metric-value">{pe_str}</div>
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">歷史估值參考</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col3:
                    roe_val = info.get("returnOnEquity")
                    roe_str = f"{roe_val*100:.2f}%" if isinstance(roe_val, (int, float)) else "無資料"
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">股東權益報酬率 (ROE)</div>
                        <div class="metric-value">{roe_str}</div>
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">巴菲特核心選股指標</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col4:
                    market_cap = info.get("marketCap")
                    if isinstance(market_cap, (int, float)):
                        if market_cap >= 1e12:
                            mc_str = f"{market_cap/1e12:.2f} 兆"
                        elif market_cap >= 1e8:
                            mc_str = f"{market_cap/1e8:.2f} 億"
                        else:
                            mc_str = f"{market_cap:,.0f}"
                    else:
                        mc_str = "無資料"
                    st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-label">總市值 (Market Cap)</div>
                        <div class="metric-value">{mc_str}</div>
                        <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 4px;">企業規模實力</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                
                # 導航分頁
                tab1, tab2, tab3 = st.tabs(["📊 技術面指標與即時買賣點", "🏢 基本面與財務體質分析", "🤖 量化綜合投資診斷"])
                
                # -------------------------------------------------------------
                # TAB 1: 技術分析
                # -------------------------------------------------------------
                with tab1:
                    col_chart, col_signal = st.columns([7, 3])
                    
                    with col_signal:
                        st.markdown("#### 🎯 即時買賣點判讀")
                        
                        signals = []
                        # KD 判斷
                        if not np.isnan(latest["K"]) and not np.isnan(latest["D"]):
                            k_curr, d_curr = latest["K"], latest["D"]
                            k_prev, d_prev = prev["K"], prev["D"]
                            if k_prev < d_prev and k_curr > d_curr and k_curr < 35:
                                signals.append(("buy", "🟢 KD 低檔黃金交叉 (超賣反彈訊號)"))
                            elif k_prev > d_prev and k_curr < d_curr and k_curr > 65:
                                signals.append(("sell", "🔴 KD 高檔死亡交叉 (超買回檔訊號)"))
                        
                        # 均線判定
                        if curr_price > latest["MA20"] and prev_price <= prev["MA20"]:
                            signals.append(("buy", "🟢 股價突破 20 日月線 (短多確立)"))
                        elif curr_price < latest["MA20"] and prev_price >= prev["MA20"]:
                            signals.append(("sell", "🔴 股價跌破 20 日月線 (短多轉弱)"))
                            
                        # RSI 判定
                        if latest["RSI"] < 30:
                            signals.append(("buy", f"🟢 RSI 指標處於超賣區 ({latest['RSI']:.1f})"))
                        elif latest["RSI"] > 70:
                            signals.append(("sell", f"🔴 RSI 指標處於過熱區 ({latest['RSI']:.1f})"))
                            
                        if signals:
                            for sig_type, text in signals:
                                box_class = "signal-box-buy" if sig_type == "buy" else "signal-box-sell"
                                st.markdown(f'<div class="{box_class}">{text}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="signal-box-neutral">🟡 目前均線與震盪指標處於常態盤整，無顯著極端轉折買賣訊號。</div>', unsafe_allow_html=True)
                            
                        st.markdown("---")
                        st.markdown("#### 📐 指標現值速覽")
                        st.markdown(f"""
                        * **5日均線 (MA5)**: `{latest['MA5']:.2f}`
                        * **20日月線 (MA20)**: `{latest['MA20']:.2f}`
                        * **60日季線 (MA60)**: `{latest['MA60']:.2f}`
                        * **RSI (14)**: `{latest['RSI']:.2f}`
                        * **KD (14, 3)**: `K: {latest['K']:.2f}` / `D: {latest['D']:.2f}`
                        """)
                    
                    with col_chart:
                        # 專業深色 Plotly K 線圖
                        fig = make_subplots(
                            rows=2, cols=1,
                            shared_xaxes=True,
                            vertical_spacing=0.05,
                            row_heights=[0.7, 0.3],
                            subplot_titles=('價格走勢與移動平均線', 'RSI 相對強弱指標')
                        )
                        
                        # K 線
                        fig.add_trace(go.Candlestick(
                            x=hist.index,
                            open=hist['Open'], high=hist['High'],
                            low=hist['Low'], close=hist['Close'],
                            name='K線',
                            increasing_line_color='#ef4444', increasing_fillcolor='#ef4444', # 台股紅漲
                            decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e'  # 綠跌
                        ), row=1, col=1)
                        
                        # 均線
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA5'], name='5MA', line=dict(color='#f59e0b', width=1.2)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], name='20MA (月線)', line=dict(color='#38bdf8', width=1.5)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA60'], name='60MA (季線)', line=dict(color='#a855f7', width=1.8)), row=1, col=1)
                        
                        # RSI
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], name='RSI', line=dict(color='#ec4899', width=1.5)), row=2, col=1)
                        fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=2, col=1)
                        fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", row=2, col=1)
                        
                        fig.update_layout(
                            paper_bgcolor='#0b0f19',
                            plot_bgcolor='#111827',
                            font=dict(color='#94a3b8'),
                            height=550,
                            xaxis_rangeslider_visible=False,
                            margin=dict(l=10, r=10, t=30, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        fig.update_xaxes(gridcolor='#1e293b', zeroline=False)
                        fig.update_yaxes(gridcolor='#1e293b', zeroline=False)
                        
                        st.plotly_chart(fig, use_container_width=True)

                # -------------------------------------------------------------
                # TAB 2: 基本面分析
                # -------------------------------------------------------------
                with tab2:
                    st.markdown("#### 📊 公司基本面與價值體質健檢")
                    col_fund1, col_fund2 = st.columns(2)
                    
                    with col_fund1:
                        st.markdown("##### 📌 獲利與估值指標")
                        f_data_1 = {
                            "指標": ["本益比 (P/E)", "股價淨值比 (P/B)", "近四季每股盈餘 (EPS)", "股東權益報酬率 (ROE)", "總資產報酬率 (ROA)", "營業利益率"],
                            "數值": [
                                f"{info.get('trailingPE', 'N/A')}",
                                f"{info.get('priceToBook', 'N/A')}",
                                f"${info.get('trailingEps', 'N/A')}",
                                f"{info.get('returnOnEquity', 0)*100:.2f}%" if isinstance(info.get('returnOnEquity'), (int, float)) else "N/A",
                                f"{info.get('returnOnAssets', 0)*100:.2f}%" if isinstance(info.get('returnOnAssets'), (int, float)) else "N/A",
                                f"{info.get('operatingMargins', 0)*100:.2f}%" if isinstance(info.get('operatingMargins'), (int, float)) else "N/A",
                            ]
                        }
                        st.dataframe(pd.DataFrame(f_data_1), use_container_width=True, hide_index=True)
                        
                    with col_fund2:
                        st.markdown("##### 🛡️ 財務結構與營運成長")
                        f_data_2 = {
                            "指標": ["流動比率", "速動比率", "負債股本比 (Debt/Equity)", "營收年成長率 (YoY)", "毛利率 (Gross Margins)", "股利殖利率 (Dividend Yield)"],
                            "數值": [
                                f"{info.get('currentRatio', 'N/A')}",
                                f"{info.get('quickRatio', 'N/A')}",
                                f"{info.get('debtToEquity', 'N/A')}",
                                f"{info.get('revenueGrowth', 0)*100:.2f}%" if isinstance(info.get('revenueGrowth'), (int, float)) else "N/A",
                                f"{info.get('grossMargins', 0)*100:.2f}%" if isinstance(info.get('grossMargins'), (int, float)) else "N/A",
                                f"{info.get('dividendYield', 0)*100:.2f}%" if isinstance(info.get('dividendYield'), (int, float)) else "無配息/無資料",
                            ]
                        }
                        st.dataframe(pd.DataFrame(f_data_2), use_container_width=True, hide_index=True)

                    st.markdown("##### 🏢 公司主要業務概況")
                    st.info(info.get("longBusinessSummary", "目前暫無提供該公司的詳細營運描述。"))

                # -------------------------------------------------------------
                # TAB 3: 綜合量化報告
                # -------------------------------------------------------------
                with tab3:
                    st.markdown("#### 🤖 量化策略與投資價值評定")
                    
                    roe = info.get('returnOnEquity', 0) if isinstance(info.get('returnOnEquity'), (int, float)) else 0
                    pe = info.get('trailingPE', 0) if isinstance(info.get('trailingPE'), (int, float)) else 0
                    
                    roe_grade = "⭐⭐⭐⭐⭐ (頂尖企業)" if roe >= 0.20 else "⭐⭐⭐⭐ (體質良好)" if roe >= 0.15 else "⭐⭐⭐ (表現中規中矩)" if roe >= 0.08 else "⭐⭐ (體質偏弱)"
                    
                    trend_status = "多頭排列 (股價 > 月線)" if curr_price > latest['MA20'] else "空頭回檔 (股價 < 月線)"
                    
                    st.markdown(f"""
                    <div style="background-color: #111827; border: 1px solid #1e293b; border-radius: 10px; padding: 20px; line-height: 1.8;">
                        <h4 style="color: #38bdf8; margin-top: 0;">📋 核心體質評鑑</h4>
                        <ul>
                            <li><b>基本面評分</b>：{roe_grade}，近四季 ROE 為 <b>{roe*100:.2f}%</b>。</li>
                            <li><b>估值水平</b>：當前靜態本益比為 <b>{pe if pe else 'N/A'}</b> 倍。</li>
                            <li><b>波段動能</b>：現階段處於 <b>{trend_status}</b>，最新收盤價 <b>${curr_price:.2f}</b>。</li>
                        </ul>
                        <hr style="border-color: #1e293b;">
                        <h4 style="color: #f59e0b; margin-top: 0;">💡 投資策略決策建議</h4>
                        <ul>
                            <li><b>長線存股/價值投資</b>：若 ROE 長期高於 15% 且現金流穩健，拉回至季線 (MA60) 附近皆為合適的分批建倉點位。</li>
                            <li><b>波段與短線交易</b>：當前 RSI 處於 <b>{latest['RSI']:.1f}</b>，建議嚴格配合 20MA (月線 ${latest['MA20']:.2f}) 設立防守停損點。</li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
        except Exception as e:
            if "Too Many Requests" in str(e) or "Rate limited" in str(e):
                st.warning("⚠️ **觸發 Yahoo Finance 流量限制**：目前公共伺服器請求過於頻繁。請稍候 1~2 分鐘後重新點擊「重新整理」，或嘗試切換至不同的時間週期。")
            else:
                st.error(f"讀取資料發生異常: {e}")
