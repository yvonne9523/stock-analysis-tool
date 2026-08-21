import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 頁面配置
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI 股票量化與指標分析終端",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 輕量俐落深色 CSS (提高文字對比度，不刺眼)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* 調整字體與背景對比度 */
    .stApp {
        background-color: #0e1117;
        color: #e2e8f0;
    }
    
    /* 頂部指標卡片 */
    .metric-box {
        background-color: #1a1f2c;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 16px 18px;
        margin-bottom: 12px;
    }
    .metric-title {
        font-size: 0.85rem;
        color: #a0aec0;
        margin-bottom: 4px;
        font-weight: 500;
    }
    .metric-num {
        font-size: 1.6rem;
        font-weight: 700;
        color: #ffffff;
    }
    .metric-pos {
        color: #f87171; /* 紅漲 */
        font-weight: 600;
        font-size: 0.85rem;
    }
    .metric-neg {
        color: #4ade80; /* 綠跌 */
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    /* 買賣訊號盒 */
    .signal-buy {
        background-color: rgba(239, 68, 68, 0.15);
        border-left: 4px solid #ef4444;
        color: #fca5a5;
        padding: 12px 14px;
        border-radius: 6px;
        margin-bottom: 8px;
        font-weight: 500;
    }
    .signal-sell {
        background-color: rgba(34, 197, 94, 0.15);
        border-left: 4px solid #22c55e;
        color: #86efac;
        padding: 12px 14px;
        border-radius: 6px;
        margin-bottom: 8px;
        font-weight: 500;
    }
    .signal-neutral {
        background-color: rgba(148, 163, 184, 0.1);
        border-left: 4px solid #64748b;
        color: #cbd5e1;
        padding: 12px 14px;
        border-radius: 6px;
        margin-bottom: 8px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 修正 Pickle 序列化問題的快取抓取函式
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_stock_history(ticker_symbol, period_choice):
    """只快取歷史價格 DataFrame (100% 支援 pickle 序列化)"""
    stock_obj = yf.Ticker(ticker_symbol)
    df = stock_obj.history(period=period_choice)
    return df

def fetch_stock_info(ticker_symbol):
    """安全獲取公司基本面字典"""
    stock_obj = yf.Ticker(ticker_symbol)
    try:
        raw_info = stock_obj.info
        clean_info = {
            "longName": raw_info.get("longName") or raw_info.get("shortName") or ticker_symbol,
            "sector": raw_info.get("sector", "主要產業"),
            "currency": raw_info.get("currency", "TWD" if ".TW" in ticker_symbol else "USD"),
            "trailingPE": raw_info.get("trailingPE"),
            "priceToBook": raw_info.get("priceToBook"),
            "trailingEps": raw_info.get("trailingEps"),
            "returnOnEquity": raw_info.get("returnOnEquity"),
            "returnOnAssets": raw_info.get("returnOnAssets"),
            "operatingMargins": raw_info.get("operatingMargins"),
            "currentRatio": raw_info.get("currentRatio"),
            "quickRatio": raw_info.get("quickRatio"),
            "debtToEquity": raw_info.get("debtToEquity"),
            "revenueGrowth": raw_info.get("revenueGrowth"),
            "grossMargins": raw_info.get("grossMargins"),
            "dividendYield": raw_info.get("dividendYield"),
            "marketCap": raw_info.get("marketCap"),
            "longBusinessSummary": raw_info.get("longBusinessSummary", "目前無詳細公司業務簡介。")
        }
        return clean_info
    except Exception:
        return {"longName": ticker_symbol, "longBusinessSummary": "基本面資料獲取逾時，請稍後重試。"}

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
# 側邊欄控制
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ 股票搜尋與設定")
    ticker_input = st.text_input(
        "股票代號",
        value="2330.TW",
        help="台股請加 .TW (例: 2330.TW, 2454.TW)；美股直接輸入代號 (例: NVDA, AAPL)"
    ).strip().upper()
    
    period_option = st.selectbox(
        "時間週期",
        options=["3m", "6m", "1y", "2y"],
        index=1,
        format_func=lambda x: {"3m": "近 3 個月", "6m": "近 6 個月", "1y": "近 1 年", "2y": "近 2 年"}.get(x, x)
    )
    st.caption("💡 資料已啟用自動快取防護，避免頻繁查詢限流。")

# -----------------------------------------------------------------------------
# 主畫面資料載入與呈現
# -----------------------------------------------------------------------------
if ticker_input:
    with st.spinner("正在加載最新數據..."):
        try:
            hist = fetch_stock_history(ticker_input, period_option)
            info = fetch_stock_info(ticker_input)
            
            if hist is None or hist.empty:
                st.warning(f"⚠️ 找不到 `{ticker_input}` 的價格資訊，請確認代號是否正確。")
            else:
                hist = calculate_technical_indicators(hist)
                latest = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else latest
                
                curr_price = float(latest["Close"])
                prev_price = float(prev["Close"])
                price_diff = curr_price - prev_price
                pct_diff = (price_diff / prev_price) * 100 if prev_price != 0 else 0
                
                company_name = info.get("longName", ticker_input)
                
                # 標題
                st.markdown(f"## {company_name} (`{ticker_input}`)")
                
                # 四大關鍵指標卡片
                c1, c2, c3, c4 = st.columns(4)
                delta_color = "metric-pos" if price_diff >= 0 else "metric-neg"
                arrow = "▲" if price_diff >= 0 else "▼"
                
                with c1:
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-title">最新收盤價</div>
                        <div class="metric-num">{curr_price:,.2f}</div>
                        <div class="{delta_color}">{arrow} {price_diff:+,.2f} ({pct_diff:+.2f}%)</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with c2:
                    pe_val = info.get("trailingPE")
                    pe_txt = f"{pe_val:.2f} 倍" if isinstance(pe_val, (int, float)) else "無資料"
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-title">本益比 (P/E)</div>
                        <div class="metric-num">{pe_txt}</div>
                        <div style="font-size:0.8rem; color:#718096; margin-top:3px;">估值倍數</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with c3:
                    roe_val = info.get("returnOnEquity")
                    roe_txt = f"{roe_val*100:.2f}%" if isinstance(roe_val, (int, float)) else "無資料"
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-title">股東權益報酬率 (ROE)</div>
                        <div class="metric-num">{roe_txt}</div>
                        <div style="font-size:0.8rem; color:#718096; margin-top:3px;">巴菲特選股指標</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with c4:
                    mc = info.get("marketCap")
                    if isinstance(mc, (int, float)):
                        mc_txt = f"{mc/1e12:.2f} 兆" if mc >= 1e12 else f"{mc/1e8:.2f} 億" if mc >= 1e8 else f"{mc:,.0f}"
                    else:
                        mc_txt = "無資料"
                    st.markdown(f"""
                    <div class="metric-box">
                        <div class="metric-title">總市值</div>
                        <div class="metric-num">{mc_txt}</div>
                        <div style="font-size:0.8rem; color:#718096; margin-top:3px;">企業資本規模</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                # 分頁
                tab1, tab2, tab3 = st.tabs(["📊 技術分析與訊號", "🏢 基本面財務指標", "🤖 量化分析診斷"])
                
                # Tab 1: 技術指標
                with tab1:
                    col_chart, col_sig = st.columns([7, 3])
                    
                    with col_sig:
                        st.markdown("#### 🎯 即時指標買賣點判讀")
                        signals = []
                        
                        # KD
                        if not np.isnan(latest["K"]) and not np.isnan(latest["D"]):
                            if prev["K"] < prev["D"] and latest["K"] > latest["D"] and latest["K"] < 35:
                                signals.append(("buy", "🟢 KD 低檔黃金交叉（超賣反彈買點）"))
                            elif prev["K"] > prev["D"] and latest["K"] < latest["D"] and latest["K"] > 65:
                                signals.append(("sell", "🔴 KD 高檔死亡交叉（超買回檔訊號）"))
                                
                        # 均線
                        if curr_price > latest["MA20"] and prev_price <= prev["MA20"]:
                            signals.append(("buy", "🟢 股價向上突破 20 日月線（短多轉強）"))
                        elif curr_price < latest["MA20"] and prev_price >= prev["MA20"]:
                            signals.append(("sell", "🔴 股價向下跌破 20 日月線（短線走弱）"))
                            
                        # RSI
                        if latest["RSI"] < 30:
                            signals.append(("buy", f"🟢 RSI 處於超賣區 ({latest['RSI']:.1f})"))
                        elif latest["RSI"] > 70:
                            signals.append(("sell", f"🔴 RSI 處於過熱區 ({latest['RSI']:.1f})"))
                            
                        if signals:
                            for stype, stxt in signals:
                                cls_name = "signal-buy" if stype == "buy" else "signal-sell"
                                st.markdown(f'<div class="{cls_name}">{stxt}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="signal-neutral">🟡 目前均線與震盪指標處於常態盤整，無顯著轉折訊號。</div>', unsafe_allow_html=True)
                            
                        st.markdown("---")
                        st.markdown(f"""
                        **即時指標數值：**
                        * 5MA: `{latest['MA5']:.2f}` | 20MA: `{latest['MA20']:.2f}`
                        * RSI (14): `{latest['RSI']:.2f}`
                        * KD: `K {latest['K']:.2f}` / `D {latest['D']:.2f}`
                        """)
                    
                    with col_chart:
                        fig = make_subplots(
                            rows=2, cols=1,
                            shared_xaxes=True,
                            vertical_spacing=0.06,
                            row_heights=[0.72, 0.28],
                            subplot_titles=('K 線與移動平均線', 'RSI 相對強弱指標')
                        )
                        
                        # K線 (紅漲綠跌)
                        fig.add_trace(go.Candlestick(
                            x=hist.index,
                            open=hist['Open'], high=hist['High'],
                            low=hist['Low'], close=hist['Close'],
                            name='K線',
                            increasing_line_color='#ef4444', increasing_fillcolor='#ef4444',
                            decreasing_line_color='#22c55e', decreasing_fillcolor='#22c55e'
                        ), row=1, col=1)
                        
                        # 均線
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA5'], name='5MA', line=dict(color='#fbbf24', width=1.2)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], name='20MA(月線)', line=dict(color='#38bdf8', width=1.5)), row=1, col=1)
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['MA60'], name='60MA(季線)', line=dict(color='#c084fc', width=1.8)), row=1, col=1)
                        
                        # RSI
                        fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], name='RSI', line=dict(color='#f472b6', width=1.5)), row=2, col=1)
                        fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=2, col=1)
                        fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", row=2, col=1)
                        
                        fig.update_layout(
                            paper_bgcolor='#0e1117',
                            plot_bgcolor='#161b22',
                            font=dict(color='#94a3b8'),
                            height=520,
                            xaxis_rangeslider_visible=False,
                            margin=dict(l=10, r=10, t=30, b=10),
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                        )
                        fig.update_xaxes(gridcolor='#21262d', zeroline=False)
                        fig.update_yaxes(gridcolor='#21262d', zeroline=False)
                        st.plotly_chart(fig, use_container_width=True)
                        
                # Tab 2: 基本面
                with tab2:
                    st.markdown("#### 📊 公司價值與財務健全度")
                    col_f1, col_f2 = st.columns(2)
                    
                    with col_f1:
                        st.markdown("##### 📌 獲利與估值指標")
                        f_df1 = pd.DataFrame({
                            "指標名稱": ["本益比 (P/E)", "股價淨值比 (P/B)", "近四季 EPS", "股東權益報酬率 (ROE)", "總資產報酬率 (ROA)", "營業利益率"],
                            "數值": [
                                f"{info.get('trailingPE', 'N/A')}",
                                f"{info.get('priceToBook', 'N/A')}",
                                f"${info.get('trailingEps', 'N/A')}",
                                f"{info.get('returnOnEquity', 0)*100:.2f}%" if isinstance(info.get('returnOnEquity'), (int, float)) else "N/A",
                                f"{info.get('returnOnAssets', 0)*100:.2f}%" if isinstance(info.get('returnOnAssets'), (int, float)) else "N/A",
                                f"{info.get('operatingMargins', 0)*100:.2f}%" if isinstance(info.get('operatingMargins'), (int, float)) else "N/A",
                            ]
                        })
                        st.dataframe(f_df1, use_container_width=True, hide_index=True)
                        
                    with col_f2:
                        st.markdown("##### 🛡️ 安全性與營運成長")
                        f_df2 = pd.DataFrame({
                            "指標名稱": ["流動比率", "速動比率", "負債股本比 (Debt/Equity)", "營收年成長率 (YoY)", "毛利率", "股息殖利率"],
                            "數值": [
                                f"{info.get('currentRatio', 'N/A')}",
                                f"{info.get('quickRatio', 'N/A')}",
                                f"{info.get('debtToEquity', 'N/A')}",
                                f"{info.get('revenueGrowth', 0)*100:.2f}%" if isinstance(info.get('revenueGrowth'), (int, float)) else "N/A",
                                f"{info.get('grossMargins', 0)*100:.2f}%" if isinstance(info.get('grossMargins'), (int, float)) else "N/A",
                                f"{info.get('dividendYield', 0)*100:.2f}%" if isinstance(info.get('dividendYield'), (int, float)) else "無配息/無資料",
                            ]
                        })
                        st.dataframe(f_df2, use_container_width=True, hide_index=True)
                        
                    st.markdown("##### 🏢 業務簡介")
                    st.info(info.get("longBusinessSummary", "無提供詳細公司簡介。"))
                    
                # Tab 3: 量化報告
                with tab3:
                    st.markdown("#### 🤖 量化綜合投資決策報告")
                    roe_num = info.get('returnOnEquity', 0) if isinstance(info.get('returnOnEquity'), (int, float)) else 0
                    pe_num = info.get('trailingPE', 0) if isinstance(info.get('trailingPE'), (int, float)) else 0
                    
                    st.markdown(f"""
                    * **基本面體質評鑑**：ROE 為 **{roe_num*100:.2f}%**（{'⭐⭐⭐⭐⭐ 頂尖水準' if roe_num > 0.2 else '⭐⭐⭐⭐ 體質良好' if roe_num > 0.15 else '⭐⭐⭐ 表現普通'}），靜態本益比 **{pe_num if pe_num else 'N/A'}** 倍。
                    * **趨勢位階判定**：當前股價 **${curr_price:.2f}**，處於 **{'月線 (MA20) 之上（短多格局）' if curr_price > latest['MA20'] else '月線 (MA20) 之下（短空格局）'}**。
                    * **策略操作建議**：
                        * **波段交易者**：以月線 `${latest['MA20']:.2f}` 作為多空防守停損點；KD 低檔 (<35) 出現黃金交叉為右側進場機會。
                        * **長期價值投資者**：好公司若拉回至季線 `${latest['MA60']:.2f}` 附近且 RSI 未過熱，均為合適分批佈局點位。
                    """)
                    
        except Exception as e:
            st.error(f"讀取異常: {e}")
