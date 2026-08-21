import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------------------------------------------------------
# 頁面基本設定
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI 股票基本面與技術面分析工具",
    page_icon="📈",
    layout="wide"
)

st.title("📈 股票雙模組分析小工具 (基本面 + 技術面)")
st.caption("結合基本面價值評估與技術面即時指標買賣點訊號")

# -----------------------------------------------------------------------------
# 指標計算函式 (原生 Pandas 實作，免外部相依套件)
# -----------------------------------------------------------------------------
def calculate_indicators(df):
    # 均線 MA
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
    
    # 計算 K 與 D
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
# 側邊欄輸入設定
# -----------------------------------------------------------------------------
st.sidebar.header("🔍 股票搜尋設定")
ticker_input = st.sidebar.text_input("請輸入股票代號", value="2330.TW", help="台股請加 .TW (例: 2330.TW, 2454.TW)，美股直接輸入代號 (例: AAPL, TSLA)")
period_option = st.sidebar.selectbox("歷史資料時間跨度", options=["3m", "6m", "1y", "2y"], index=1)

btn_analyze = st.sidebar.button("開始分析", type="primary")

# -----------------------------------------------------------------------------
# 核心處理邏輯
# -----------------------------------------------------------------------------
if ticker_input:
    try:
        stock = yf.Ticker(ticker_input)
        info = stock.info
        hist = stock.history(period=period_option)
        
        if hist.empty:
            st.error(f"找不到代號 '{ticker_input}' 的股價資料，請確認輸入是否正確。")
        else:
            hist = calculate_indicators(hist)
            latest = hist.iloc[-1]
            prev = hist.iloc[-2]
            
            company_name = info.get("longName", info.get("shortName", ticker_input))
            st.header(f"{company_name} ({ticker_input.upper()})")
            
            # 頂部指標卡片
            col1, col2, col3, col4 = st.columns(4)
            curr_price = latest["Close"]
            price_change = curr_price - prev["Close"]
            pct_change = (price_change / prev["Close"]) * 100
            
            col1.metric("最新收盤價", f"${curr_price:.2f}", f"{price_change:+.2f} ({pct_change:+.2f}%)")
            col2.metric("本益比 (P/E)", f"{info.get('trailingPE', 'N/A')}")
            col3.metric("股東權益報酬率 (ROE)", f"{info.get('returnOnEquity', 0)*100:.2f}%" if isinstance(info.get('returnOnEquity'), (int, float)) else "N/A")
            col4.metric("市值", f"${info.get('marketCap', 0):,}" if info.get('marketCap') else "N/A")
            
            st.markdown("---")
            
            tab1, tab2, tab3 = st.tabs(["📊 技術面圖表與買賣訊號", "🏢 基本面與財務數據", "🤖 AI 綜合分析診斷"])
            
            # TAB 1: 技術面
            with tab1:
                st.subheader("買賣訊號偵測")
                signals = []
                
                # KD 訊號
                if prev["K"] < prev["D"] and latest["K"] > latest["D"]:
                    if latest["K"] < 30:
                        signals.append("🟢 **【買進訊號】KD 在低檔 (<30) 出現黃金交叉！**")
                elif prev["K"] > prev["D"] and latest["K"] < latest["D"]:
                    if latest["K"] > 70:
                        signals.append("🔴 **【賣出訊號】KD 在高檔 (>70) 出現死亡交叉！**")
                
                # 均線訊號
                if curr_price > latest["MA20"] and prev["Close"] <= prev["MA20"]:
                    signals.append("🟢 **【買進訊號】股價向上突破 20 日均線 (月線)！**")
                elif curr_price < latest["MA20"] and prev["Close"] >= prev["MA20"]:
                    signals.append("🔴 **【賣出訊號】股價跌破 20 日均線 (月線)！**")
                    
                # RSI 訊號
                if latest["RSI"] < 30:
                    signals.append("🟢 **【買進訊號】RSI 低於 30，處於超賣區！**")
                elif latest["RSI"] > 70:
                    signals.append("🔴 **【賣出訊號】RSI 高於 70，處於超買區！**")
                    
                if signals:
                    for sig in signals:
                        st.write(sig)
                else:
                    st.info("🟡 目前各技術指標維持正常區間震盪，無顯著極端買賣轉折訊號。")
                
                # 繪製圖表
                fig = make_subplots(
                    rows=2, cols=1, 
                    shared_xaxes=True, 
                    vertical_spacing=0.08, 
                    subplot_titles=('K線圖與移動平均線', 'RSI 相對強弱指標'),
                    row_width=[0.3, 0.7]
                )
                
                fig.add_trace(go.Candlestick(
                    x=hist.index,
                    open=hist['Open'], high=hist['High'],
                    low=hist['Low'], close=hist['Close'],
                    name='K線'
                ), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=hist.index, y=hist['MA5'], name='5日線', line=dict(color='orange', width=1)), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=hist['MA20'], name='20日線 (月線)', line=dict(color='blue', width=1.5)), row=1, col=1)
                fig.add_trace(go.Scatter(x=hist.index, y=hist['MA60'], name='60日線 (季線)', line=dict(color='purple', width=2)), row=1, col=1)
                
                fig.add_trace(go.Scatter(x=hist.index, y=hist['RSI'], name='RSI (14)', line=dict(color='brown', width=1.5)), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                
                fig.update_layout(
                    height=600,
                    xaxis_rangeslider_visible=False,
                    template="plotly_white",
                    margin=dict(l=20, r=20, t=40, b=20)
                )
                st.plotly_chart(fig, use_container_width=True)

            # TAB 2: 基本面
            with tab2:
                st.subheader("公司基本面與體質檢視")
                col_f1, col_f2 = st.columns(2)
                
                with col_f1:
                    st.write("#### 📌 關鍵財務估值指標")
                    financial_data = {
                        "指標名稱": ["本益比 (P/E)", "股價淨值比 (P/B)", "近四季 EPS", "股東權益報酬率 (ROE)", "總資產報酬率 (ROA)", "營業利益率"],
                        "數值": [
                            f"{info.get('trailingPE', 'N/A')}",
                            f"{info.get('priceToBook', 'N/A')}",
                            f"${info.get('trailingEps', 'N/A')}",
                            f"{info.get('returnOnEquity', 0)*100:.2f}%" if isinstance(info.get('returnOnEquity'), (int, float)) else "N/A",
                            f"{info.get('returnOnAssets', 0)*100:.2f}%" if isinstance(info.get('returnOnAssets'), (int, float)) else "N/A",
                            f"{info.get('operatingMargins', 0)*100:.2f}%" if isinstance(info.get('operatingMargins'), (int, float)) else "N/A",
                        ]
                    }
                    st.table(pd.DataFrame(financial_data))

                with col_f2:
                    st.write("#### 🛡️ 安全性與營運指標")
                    safety_data = {
                        "指標名稱": ["速動比率", "流動比率", "負債比率 (Debt to Equity)", "營收年增率 (Revenue Growth)"],
                        "數值": [
                            f"{info.get('quickRatio', 'N/A')}",
                            f"{info.get('currentRatio', 'N/A')}",
                            f"{info.get('debtToEquity', 'N/A')}",
                            f"{info.get('revenueGrowth', 0)*100:.2f}%" if isinstance(info.get('revenueGrowth'), (int, float)) else "N/A",
                        ]
                    }
                    st.table(pd.DataFrame(safety_data))

                st.write("#### 📄 公司業務簡介")
                st.write(info.get("longBusinessSummary", "無提供詳細公司簡介資訊。"))

            # TAB 3: AI 綜合診斷
            with tab3:
                st.subheader("🤖 自動化綜合量化診斷報告")
                roe_val = info.get('returnOnEquity', 0) if isinstance(info.get('returnOnEquity'), (int, float)) else 0
                pe_val = info.get('trailingPE', 0) if isinstance(info.get('trailingPE'), (int, float)) else 0
                
                st.markdown(f"""
                ### 📋 綜合評估摘要
                * **基本面體質**：
                    * ROE 為 **{roe_val*100:.2f}%** ({'體質優異 (>15%)' if roe_val > 0.15 else '表現一般'})。
                    * 當前本益比 **{pe_val}** 倍。
                * **技術面走勢**：
                    * 當前股價 **${curr_price:.2f}**，與月線 (MA20 ${latest['MA20']:.2f}) 相比處於 **{'多頭上方' if curr_price > latest['MA20'] else '空頭下方'}**。
                    * RSI 指標為 **{latest['RSI']:.2f}** ({'過熱' if latest['RSI']>70 else '過冷' if latest['RSI']<30 else '中性'})。
                
                ---
                ### 💡 操作建議提示
                * **價值投資者**：若基本面 ROE 穩定且具產業龍頭地位，可關注股價回檔至季線 (MA60) 附近進行分批佈局。
                * **短線交易者**：留意短期技術指標 (如 KD 與 RSI) 轉折，嚴格執行 Stop-Loss (例如跌破月線或 -5% 停損)。
                """)

    except Exception as e:
        st.error(f"讀取資料發生錯誤: {e}")
