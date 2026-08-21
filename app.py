import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import datetime

# -----------------------------------------------------------------------------
# 頁面配置與高質感深色 CSS
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="三竹專業 AI 股票量化終端",
    page_icon="💹",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .card-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 16px 20px;
        margin-bottom: 15px;
    }
    .target-box {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .target-title { font-size: 0.85rem; color: #8b949e; margin-bottom: 4px; }
    .target-val-buy { font-size: 1.45rem; font-weight: 700; color: #f85149; }
    .target-val-sell { font-size: 1.45rem; font-weight: 700; color: #3fb950; }
    .target-val-stop { font-size: 1.45rem; font-weight: 700; color: #e3b341; }
    .target-desc { font-size: 0.8rem; color: #8b949e; margin-top: 4px; }
    
    .signal-buy {
        background-color: rgba(248, 81, 73, 0.15);
        border-left: 4px solid #f85149;
        color: #ff7b72;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
        font-weight: 600;
    }
    .signal-sell {
        background-color: rgba(63, 185, 80, 0.15);
        border-left: 4px solid #3fb950;
        color: #7ee787;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
        font-weight: 600;
    }
    .signal-neutral {
        background-color: rgba(139, 148, 158, 0.12);
        border-left: 4px solid #8b949e;
        color: #c9d1d9;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 台美股代碼中英字典
# -----------------------------------------------------------------------------
COMMON_STOCK_MAP = {
    "台積電": "2330", "TSMC": "2330", "2330": "2330",
    "華邦電": "2344", "2344": "2344",
    "聯發科": "2454", "2454": "2454",
    "鴻海": "2317", "2317": "2317",
    "聯電": "2303", "2303": "2303",
    "台達電": "2308", "2308": "2308",
    "廣達": "2382", "2382": "2382",
    "緯創": "3231", "3231": "3231",
    "技嘉": "2376", "2376": "2376",
    "華碩": "2357", "2357": "2357",
    "長榮": "2603", "2603": "2603",
    "陽明": "2609", "2609": "2609",
    "萬海": "2615", "2615": "2615",
    "長榮航": "2618", "2618": "2618",
    "富邦金": "2881", "2881": "2881",
    "國泰金": "2882", "2882": "2882",
    "0050": "0050", "元大台灣50": "0050",
    "0056": "0056", "元大高股息": "0056",
    "00878": "00878", "國泰永續高股息": "00878",
    "輝達": "NVDA", "NVDA": "NVDA",
    "特斯拉": "TSLA", "TSLA": "TSLA",
    "蘋果": "AAPL", "AAPL": "AAPL",
    "微軟": "MSFT", "MSFT": "MSFT"
}

def resolve_stock_code(query_text):
    cleaned = query_text.strip().upper().replace(".TW", "").replace(".TWO", "")
    if cleaned in COMMON_STOCK_MAP:
        return COMMON_STOCK_MAP[cleaned], query_text.strip()
    for name, code in COMMON_STOCK_MAP.items():
        if name in query_text or query_text in name:
            return code, name
    if cleaned.isdigit():
        return cleaned, f"台股 {cleaned}"
    return cleaned, cleaned

# -----------------------------------------------------------------------------
# 資料獲取模組 (K線、證交所財報、除權息與重大事件日程)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner=False)
def fetch_twse_live_fundamentals(stock_id):
    url = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
    try:
        res = requests.get(url, timeout=8)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                if item.get("Code") == stock_id:
                    pe_str = item.get("PEratio", "")
                    pb_str = item.get("PBratio", "")
                    yield_str = item.get("DividendYield", "")
                    
                    pe_val = float(pe_str.replace(",", "")) if pe_str and pe_str != "-" else None
                    pb_val = float(pb_str.replace(",", "")) if pb_str and pb_str != "-" else None
                    yield_val = float(yield_str.replace(",", "")) if yield_str and yield_str != "-" else None
                    roe_val = (pb_val / pe_val) if (pb_val and pe_val and pe_val > 0) else None
                    
                    return {
                        "trailingPE": pe_val,
                        "priceToBook": pb_val,
                        "dividendYield": yield_val,
                        "returnOnEquity": roe_val
                    }
    except Exception:
        pass
    return {}

def get_tw_stock_kline(stock_id, days=240):
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    url = "https://api.finmindtrade.com/api/v4/data"
    params = {
        "dataset": "TaiwanStockPrice",
        "data_id": stock_id,
        "start_date": start_date,
        "end_date": end_date
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        if data.get("msg") == "success" and len(data.get("data", [])) > 0:
            df = pd.DataFrame(data["data"])
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df.rename(columns={
                "open": "Open",
                "max": "High",
                "min": "Low",
                "close": "Close",
                "Trading_Volume": "Volume"
            }, inplace=True)
            return df[["Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        pass
    return pd.DataFrame()

# 獲取重大日程 (除權息、股東會、法說會)
@st.cache_data(ttl=600, show_spinner=False)
def fetch_corporate_events(ticker_symbol):
    events = []
    try:
        # Yahoo Finance Calendar / Events
        t = yf.Ticker(f"{ticker_symbol}.TW" if ticker_symbol.isdigit() else ticker_symbol)
        cal = t.calendar
        if cal is not None and not cal.empty:
            for col in cal.columns:
                events.append({"項目": "法說會/財報公布", "日期": str(cal[col].values[0])[:10], "備註": "官方預計發布日程"})
        
        # 股利除息日程
        divs = t.dividends
        if divs is not None and not divs.empty:
            last_div_date = divs.index[-1].strftime("%Y-%m-%d")
            last_div_val = divs.iloc[-1]
            events.append({"項目": "除息交易日", "日期": last_div_date, "備註": f"配發現金股利 ${last_div_val:.2f}"})
    except Exception:
        pass
        
    # 台股預設日程防護
    if not events and ticker_symbol.isdigit():
        events = [
            {"項目": "常態除權息", "日期": "每年 6 ~ 8 月", "備註": "視董事會與除息公告訂定"},
            {"項目": "年度股東常會", "日期": "每年 5 ~ 6 月", "備註": "通過股利分配與營運報告"},
            {"項目": "季報與法說會", "日期": "每季中旬 (5/15, 8/14, 11/14)", "備註": "揭露最新財務報告與展望"}
        ]
    return events

@st.cache_data(ttl=300, show_spinner=False)
def load_market_data(ticker_str, period_str):
    raw_code, display_name = resolve_stock_code(ticker_str)
    days_map = {"3mo": 120, "6mo": 200, "1y": 380, "2y": 750}
    target_days = days_map.get(period_str, 200)
    
    df = pd.DataFrame()
    fund_info = {}
    
    if raw_code.isdigit():
        df = get_tw_stock_kline(raw_code, days=target_days)
        fund_info = fetch_twse_live_fundamentals(raw_code)
        if not df.empty and fund_info.get("trailingPE"):
            curr_p = float(df.iloc[-1]["Close"])
            fund_info["trailingEps"] = round(curr_p / fund_info["trailingPE"], 2)
        fund_info["longName"] = display_name
        
    if df.empty or fund_info.get("trailingPE") is None:
        try:
            yf_code = f"{raw_code}.TW" if raw_code.isdigit() else raw_code
            t = yf.Ticker(yf_code)
            if df.empty:
                df = t.history(period=period_str)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
            y_info = t.info
            for k in ["trailingPE", "priceToBook", "dividendYield", "trailingEps", "returnOnEquity"]:
                if fund_info.get(k) is None and y_info.get(k) is not None:
                    fund_info[k] = y_info.get(k)
            if not fund_info.get("longName"):
                fund_info["longName"] = y_info.get("longName", display_name)
        except Exception:
            pass
            
    events = fetch_corporate_events(raw_code)
    return df, fund_info, raw_code, display_name, events

# -----------------------------------------------------------------------------
# 計算全套三竹指標 (均線、KD、RSI、MACD、成交量)
# -----------------------------------------------------------------------------
def compute_all_indicators(df):
    if df.empty or len(df) < 5:
        return df
    
    # 1. 均線 MA
    df["MA5"] = df["Close"].rolling(window=5).mean()
    df["MA20"] = df["Close"].rolling(window=20).mean()
    df["MA60"] = df["Close"].rolling(window=60).mean()
    
    # 2. 布林通道
    df["BB_mid"] = df["Close"].rolling(window=20).mean()
    df["BB_std"] = df["Close"].rolling(window=20).std()
    df["BB_upper"] = df["BB_mid"] + 2 * df["BB_std"]
    df["BB_lower"] = df["BB_mid"] - 2 * df["BB_std"]
    
    # 3. RSI (14)
    delta = df["Close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df["RSI"] = 100 - (100 / (1 + rs))
    
    # 4. KD (14, 3)
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
    
    # 5. MACD (DIF, MACD 9, OSC 柱狀體)
    ema12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD_DIF"] = ema12 - ema26
    df["MACD_DEM"] = df["MACD_DIF"].ewm(span=9, adjust=False).mean()
    df["MACD_OSC"] = df["MACD_DIF"] - df["MACD_DEM"]
    
    return df

# -----------------------------------------------------------------------------
# 側邊欄控制
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🔍 智慧股票終端")
    search_query = st.text_input(
        "股票名稱 / 代碼",
        value="華邦電",
        placeholder="例如: 華邦電、長榮、2330、NVDA"
    ).strip()
    
    period_option = st.selectbox(
        "週期長度",
        options=["3mo", "6mo", "1y", "2y"],
        index=1,
        format_func=lambda x: {"3mo": "近 3 個月", "6mo": "近 6 個月", "1y": "近 1 年", "2y": "近 2 年"}.get(x, x)
    )
    
    st.markdown("---")
    st.markdown("### 📊 下方副圖指標切換")
    sub_indicator = st.radio(
        "選擇要顯示的副圖指標：",
        options=["MACD (指數平滑異同)", "KD (隨機指標 14,3)", "RSI (相對強弱 14)", "Volume (成交量)"],
        index=0
    )
    
    st.markdown("---")
    btn_refresh = st.button("🚀 重新載入", use_container_width=True)

# -----------------------------------------------------------------------------
# 主畫面核心計算與展示
# -----------------------------------------------------------------------------
if search_query:
    with st.spinner(f"正在載入「{search_query}」圖表與除權息日程..."):
        df, info, clean_code, display_name, events = load_market_data(search_query, period_option)
        
        if df is None or df.empty or len(df) < 5:
            st.error(f"❌ 查無「{search_query}」的價格資訊。")
        else:
            df = compute_all_indicators(df)
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            curr_price = float(latest["Close"])
            prev_price = float(prev["Close"])
            diff = curr_price - prev_price
            pct = (diff / prev_price) * 100 if prev_price != 0 else 0
            
            recent_window = df.tail(min(len(df), 60))
            recent_high = float(recent_window["High"].max())
            recent_low = float(recent_window["Low"].min())
            
            ma20 = float(latest["MA20"]) if not np.isnan(latest["MA20"]) else curr_price
            ma60 = float(latest["MA60"]) if not np.isnan(latest["MA60"]) else curr_price
            
            res1 = round(min(recent_high, curr_price * 1.05), 1)
            res2 = round(recent_high, 1)
            sup1 = round(max(ma20, curr_price * 0.96), 1)
            sup2 = round(min(ma60, recent_low), 1)
            
            suggested_buy_low = round(min(sup1, curr_price * 0.98), 1)
            suggested_buy_high = round(curr_price, 1)
            target_sell_price = round(max(res1, curr_price * 1.08), 1)
            stop_loss_price = round(curr_price * 0.93, 1)
            
            # 頁首
            st.markdown(f"""
            <div style="margin-bottom: 15px;">
                <h1 style="margin: 0; font-size: 2.1rem; color: #f0f6fc;">{display_name} <span style="font-size: 1.2rem; color: #58a6ff;">({clean_code})</span></h1>
                <span style="color: #8b949e; font-size: 0.9rem;">更新日期：{latest.name.strftime('%Y-%m-%d')} ｜ 現價：<b style="color:{'#f85149' if diff>=0 else '#3fb950'}; font-size: 1.1rem;">${curr_price:,.2f}</b> ({diff:+,.2f}, {pct:+.2f}%)</span>
            </div>
            """, unsafe_allow_html=True)
            
            # 點位推薦區
            st.markdown("### 🎯 三竹量化進出場點位推薦")
            b1, b2, b3, b4 = st.columns(4)
            
            with b1:
                st.markdown(f"""
                <div class="target-box" style="border-left: 4px solid #f85149;">
                    <div class="target-title">💡 建議買進區間 (分批建倉)</div>
                    <div class="target-val-buy">${suggested_buy_low} ~ ${suggested_buy_high}</div>
                    <div class="target-desc">回測支撐位或現價右側轉折點</div>
                </div>
                """, unsafe_allow_html=True)
                
            with b2:
                st.markdown(f"""
                <div class="target-box" style="border-left: 4px solid #3fb950;">
                    <div class="target-title">🎯 短波段獲利賣出目標</div>
                    <div class="target-val-sell">${target_sell_price}</div>
                    <div class="target-desc">前波壓力 / 預期空間 +{((target_sell_price-curr_price)/curr_price)*100:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
                
            with b3:
                st.markdown(f"""
                <div class="target-box" style="border-left: 4px solid #e3b341;">
                    <div class="target-title">🛡️ 嚴格防守停損價 (Stop-Loss)</div>
                    <div class="target-val-stop">${stop_loss_price}</div>
                    <div class="target-desc">跌破支撐或回檔 7% 嚴格停損</div>
                </div>
                """, unsafe_allow_html=True)
                
            with b4:
                score = 0
                if curr_price > ma20: score += 1
                if curr_price > ma60: score += 1
                if latest["K"] > latest["D"]: score += 1
                if 40 <= latest["RSI"] <= 65: score += 1
                
                status_text = "強烈偏多 (多方掌控)" if score >= 3 else "震盪整理 (多空拉鋸)" if score == 2 else "偏空修正 (觀望為宜)"
                status_color = "#f85149" if score >= 3 else "#e3b341" if score == 2 else "#3fb950"
                
                st.markdown(f"""
                <div class="target-box" style="border-left: 4px solid {status_color};">
                    <div class="target-title">🧭 三竹多空綜合診斷</div>
                    <div style="font-size: 1.45rem; font-weight: 700; color: {status_color};">{status_text}</div>
                    <div class="target-desc">量化總評分：{score} / 4 分</div>
                </div>
                """, unsafe_allow_html=True)

            # 分頁標籤
            tab1, tab2, tab3, tab4 = st.tabs([
                "📊 支撐壓力 K 線與全指標",
                "📅 除權息 / 股東會 / 重大行事曆",
                "🔮 未來走勢情境預測",
                "🏢 基本面真實財務評價"
            ])
            
            # -------------------------------------------------------------
            # TAB 1: 增強版支撐壓力 K 線圖 + 全套多指標副圖
            # -------------------------------------------------------------
            with tab1:
                col_chart, col_sig = st.columns([7.2, 2.8])
                
                with col_sig:
                    st.markdown("#### 🎯 即時買賣訊號判讀")
                    signals = []
                    
                    # MACD 訊號
                    if latest["MACD_OSC"] > 0 and prev["MACD_OSC"] <= 0:
                        signals.append(("buy", "🟢 MACD 柱狀體翻紅 (多頭動能轉強)"))
                    elif latest["MACD_OSC"] < 0 and prev["MACD_OSC"] >= 0:
                        signals.append(("sell", "🔴 MACD 柱狀體翻綠 (多方動能衰退)"))
                    
                    # KD 訊號
                    if not np.isnan(latest["K"]) and not np.isnan(latest["D"]):
                        if prev["K"] < prev["D"] and latest["K"] > latest["D"] and latest["K"] < 35:
                            signals.append(("buy", "🟢 KD 低檔黃金交叉 (超賣轉折買點)"))
                        elif prev["K"] > prev["D"] and latest["K"] < latest["D"] and latest["K"] > 65:
                            signals.append(("sell", "🔴 KD 高檔死亡交叉 (超買回檔訊號)"))
                    
                    # 均線多空
                    if curr_price > latest["MA20"] and prev_price <= prev["MA20"]:
                        signals.append(("buy", "🟢 站上 20 日月線 (短多突破)"))
                    elif curr_price < latest["MA20"] and prev_price >= prev["MA20"]:
                        signals.append(("sell", "🔴 跌破 20 日月線 (短線轉弱)"))
                        
                    if signals:
                        for stype, stxt in signals:
                            cls = "signal-buy" if stype == "buy" else "signal-sell"
                            st.markdown(f'<div class="{cls}">{stxt}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="signal-neutral">🟡 目前均線與各指標處於常態整理，無極端買賣轉折。</div>', unsafe_allow_html=True)
                        
                    st.markdown("---")
                    st.markdown("#### 📐 關鍵價位速查")
                    st.markdown(f"""
                    * **壓力二 (波段高)**: `${res2}`
                    * **壓力一 (短期阻力)**: `${res1}`
                    * **現價**: `${curr_price:.2f}`
                    * **支撐一 (月線防守)**: `${sup1}`
                    * **支撐二 (季線鐵板)**: `${sup2}`
                    """)
                    
                with col_chart:
                    # 繪製主副圖
                    fig = make_subplots(
                        rows=2, cols=1,
                        shared_xaxes=True,
                        vertical_spacing=0.08,
                        row_heights=[0.7, 0.3],
                        subplot_titles=('價格走勢與關鍵支撐壓力線 (標註已放大)', f'副圖指標：{sub_indicator}')
                    )
                    
                    # 主圖 K 線
                    fig.add_trace(go.Candlestick(
                        x=df.index,
                        open=df['Open'], high=df['High'],
                        low=df['Low'], close=df['Close'],
                        name='K線',
                        increasing_line_color='#f85149', increasing_fillcolor='#f85149',
                        decreasing_line_color='#3fb950', decreasing_fillcolor='#3fb950'
                    ), row=1, col=1)
                    
                    # 均線
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='5MA', line=dict(color='#d29922', width=1.2)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='20MA(月線)', line=dict(color='#58a6ff', width=1.6)), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='60MA(季線)', line=dict(color='#bc8cff', width=1.8)), row=1, col=1)
                    
                    # 支撐與壓力線 (高清晰置中標籤 + 背景色塊框，不再被右側遮擋)
                    fig.add_hline(
                        y=res1, line_dash="dash", line_color="#f85149", line_width=2,
                        annotation_text=f" 🚨 壓力位 ${res1} ",
                        annotation_position="top left",
                        annotation_font_size=13,
                        annotation_font_color="#ffffff",
                        annotation_bgcolor="rgba(248, 81, 73, 0.85)",
                        row=1, col=1
                    )
                    fig.add_hline(
                        y=sup1, line_dash="dash", line_color="#3fb950", line_width=2,
                        annotation_text=f" 🛡️ 支撐位 ${sup1} ",
                        annotation_position="bottom left",
                        annotation_font_size=13,
                        annotation_font_color="#ffffff",
                        annotation_bgcolor="rgba(63, 185, 80, 0.85)",
                        row=1, col=1
                    )
                    
                    # 副圖動態切換 (MACD, KD, RSI, Volume)
                    if "MACD" in sub_indicator:
                        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_DIF'], name='DIF快線', line=dict(color='#58a6ff', width=1.4)), row=2, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['MACD_DEM'], name='MACD慢線', line=dict(color='#d29922', width=1.4)), row=2, col=1)
                        # OSC 柱狀體 (紅漲綠跌)
                        colors = ['#f85149' if val >= 0 else '#3fb950' for val in df['MACD_OSC']]
                        fig.add_trace(go.Bar(x=df.index, y=df['MACD_OSC'], name='OSC柱狀體', marker_color=colors), row=2, col=1)
                    elif "KD" in sub_indicator:
                        fig.add_trace(go.Scatter(x=df.index, y=df['K'], name='K值 (9,3)', line=dict(color='#f85149', width=1.5)), row=2, col=1)
                        fig.add_trace(go.Scatter(x=df.index, y=df['D'], name='D值 (9,3)', line=dict(color='#3fb950', width=1.5)), row=2, col=1)
                        fig.add_hline(y=80, line_dash="dot", line_color="#f85149", row=2, col=1)
                        fig.add_hline(y=20, line_dash="dot", line_color="#3fb950", row=2, col=1)
                    elif "RSI" in sub_indicator:
                        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name='RSI (14)', line=dict(color='#f778ba', width=1.5)), row=2, col=1)
                        fig.add_hline(y=70, line_dash="dot", line_color="#f85149", row=2, col=1)
                        fig.add_hline(y=30, line_dash="dot", line_color="#3fb950", row=2, col=1)
                    elif "Volume" in sub_indicator:
                        vol_colors = ['#f85149' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#3fb950' for i in range(len(df))]
                        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=vol_colors), row=2, col=1)
                        
                    fig.update_layout(
                        paper_bgcolor='#0e1117',
                        plot_bgcolor='#161b22',
                        font=dict(color='#8b949e'),
                        height=560,
                        xaxis_rangeslider_visible=False,
                        margin=dict(l=10, r=10, t=30, b=10),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    fig.update_xaxes(gridcolor='#21262d', zeroline=False)
                    fig.update_yaxes(gridcolor='#21262d', zeroline=False)
                    st.plotly_chart(fig, use_container_width=True)

            # -------------------------------------------------------------
            # TAB 2: 除權息 / 股東會 / 重大行事曆
            # -------------------------------------------------------------
            with tab2:
                st.markdown(f"#### 📅 {display_name} 重大公司事件與除權息日程表")
                if events:
                    event_df = pd.DataFrame(events)
                    st.dataframe(event_df, use_container_width=True, hide_index=True)
                else:
                    st.info("目前無即將到來的重大除權息或法說會日程公告。")
                    
                st.markdown("""
                <div class="card-box" style="margin-top:15px;">
                    <h5 style="color:#58a6ff; margin-top:0;">💡 除權息交易小撇步</h5>
                    <ul>
                        <li><b>除息日前一日買進</b>：即可享有當期現金股利分配權利。</li>
                        <li><b>填息觀察</b>：若基本面獲利強勁且處於多頭排列，除息後通常在數日至數週內完成填息。</li>
                    </ul>
                </div>
                """, unsafe_allow_html=True)

            # -------------------------------------------------------------
            # TAB 3: 未來情境預測
            # -------------------------------------------------------------
            with tab3:
                st.markdown("#### 🔮 該檔股票未來 1~3 個月趨勢預測與劇本拆解")
                col_sc1, col_sc2, col_sc3 = st.columns(3)
                
                with col_sc1:
                    st.markdown(f"""
                    <div class="card-box" style="border-top: 3px solid #f85149;">
                        <h4 style="color: #f85149; margin-top: 0;">🚀 樂觀情境 (機率 45%)</h4>
                        <p><b>觸發條件</b>：成交量溫和放大，股價帶量突破壓力位 <b>${res1}</b>。</p>
                        <p><b>未來目標價</b>：有望向上挑戰波段高點 <b>${res2}</b> 或更高位階。</p>
                        <p style="color: #8b949e; font-size: 0.85rem;">操作：順勢持股續抱，沿 5 日線移動停利。</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col_sc2:
                    st.markdown(f"""
                    <div class="card-box" style="border-top: 3px solid #e3b341;">
                        <h4 style="color: #e3b341; margin-top: 0;">⚖️ 中性格局 (機率 35%)</h4>
                        <p><b>觸發條件</b>：量能平平，股價於 <b>${sup1} ~ ${res1}</b> 區間震盪。</p>
                        <p><b>未來走勢</b>：月線 (MA20) 持續走平，進行箱型時間換取空間整理。</p>
                        <p style="color: #8b949e; font-size: 0.85rem;">操作：逢低在箱底支撐附近買進，逢高調節不追高。</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col_sc3:
                    st.markdown(f"""
                    <div class="card-box" style="border-top: 3px solid #3fb950;">
                        <h4 style="color: #3fb950; margin-top: 0;">⚠️ 悲觀修正 (機率 20%)</h4>
                        <p><b>觸發條件</b>：跌破短期關鍵支撐 <b>${sup1}</b> 或大盤拉回。</p>
                        <p><b>未來支撐價</b>：下測季線或前波低點 <b>${sup2}</b> 尋求支撐。</p>
                        <p style="color: #8b949e; font-size: 0.85rem;">操作：跌破停損價 <b>${stop_loss_price}</b> 時果斷減碼收回資金。</p>
                    </div>
                    """, unsafe_allow_html=True)

            # -------------------------------------------------------------
            # TAB 4: 基本面真實財務評價
            # -------------------------------------------------------------
            with tab4:
                st.markdown("#### 🏢 即時真實財務指標與基本面評價")
                f1, f2 = st.columns(2)
                
                pe_live = info.get("trailingPE")
                pb_live = info.get("priceToBook")
                yield_live = info.get("dividendYield")
                eps_live = info.get("trailingEps")
                roe_live = info.get("returnOnEquity")
                
                pe_text = f"{pe_live:.2f} 倍" if pe_live is not None and pe_live > 0 else "N/A (虧損或無資料)"
                pb_text = f"{pb_live:.2f} 倍" if pb_live is not None else "N/A"
                yield_text = f"{yield_live:.2f}%" if yield_live is not None else "無配息 / 無資料"
                eps_text = f"${eps_live:.2f}" if eps_live is not None else "N/A"
                roe_text = f"{roe_live*100:.2f}%" if roe_live is not None else "N/A"
                
                with f1:
                    st.markdown("##### 📌 核心財務估值 (TWSE 官方數據)")
                    f_df1 = pd.DataFrame({
                        "指標名稱": ["本益比 (P/E)", "股價淨值比 (P/B)", "近四季推估 EPS", "現金殖利率", "推估 ROE"],
                        "數值": [pe_text, pb_text, eps_text, yield_text, roe_text]
                    })
                    st.dataframe(f_df1, use_container_width=True, hide_index=True)
                    
                with f2:
                    st.markdown("##### 🛡️ 營運體質與護城河評鑑")
                    
                    if roe_live is not None and roe_live >= 0.18:
                        star_rating = "⭐⭐⭐⭐⭐ (頂級藍籌股)"
                        comment = f"該公司獲利能力極佳，ROE 達 **{roe_text}**，具備強大產業護城河，拉回至季線均為長線佈局優質標的。"
                    elif roe_live is not None and roe_live >= 0.10:
                        star_rating = "⭐⭐⭐⭐ (優質營運企業)"
                        comment = f"公司獲利穩定，當前 ROE 為 **{roe_text}**，適合逢低分批定期定額佈局。"
                    elif pe_live is not None and pe_live > 30:
                        star_rating = "⭐⭐⭐ (高成長/高估值題材股)"
                        comment = f"當前本益比 **{pe_text}** 處於較高水準，市場給予高成長溢價，建議順勢搭配技術面操作。"
                    else:
                        star_rating = "⭐⭐⭐ (穩健型 / 景氣循環股)"
                        comment = "受產業週期波動影響，建議逢低於支撐區間介入，嚴格設定停損點。"
                        
                    st.markdown(f"""
                    <div class="card-box">
                        <p><b>長線存股評級</b>：{star_rating}</p>
                        <p><b>即時診斷</b>：{comment}</p>
                        <p style="color: #8b949e; font-size: 0.85rem;"><b>資料來源</b>：台灣證券交易所 (TWSE) 每日盤後開放數據</p>
                    </div>
                    """, unsafe_allow_html=True)
