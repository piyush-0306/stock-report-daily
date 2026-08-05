"""
===========================================================
Bangalore Realty Market Intelligence Agent

Overview
--------
This autonomous agent monitors Bangalore-based real estate
stocks by coordinating the complete data collection workflow.

Responsibilities
----------------
• Load project configuration
• Retrieve daily stock prices from Moneycontrol
• Parse and validate market data
• Store processed information in Google Sheets
• Log execution status

Architecture
------------
GitHub Actions
        │
        ▼
Market Intelligence Agent
        │
 ┌──────┴──────────┐
 │                 │
Configuration   Stock Fetch Tool
                    │
                    ▼
            Market Data Parser
                    │
                    ▼
          Google Sheets Tool
                    │
                    ▼
             Google Sheets

Developed using:
- Google Antigravity IDE
- Google Antigravity Web
- Python
- GitHub Actions
===========================================================
"""

import os
import sys
import json
import re
import datetime
import requests
import time
from bs4 import BeautifulSoup

# Ensure stdout uses UTF-8 to prevent encoding errors on Windows when printing currency symbols or logs
sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'DNT': '1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Sec-Fetch-User': '?1',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
}

# ----------------------------------------------------------
# Configuration Loader
# Loads application settings from config.json
# ----------------------------------------------------------

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# ----------------------------------------------------------
# Indices Fetch Tool
# Retrieves NIFTY 50, SENSEX, NIFTY REALTY data
# ----------------------------------------------------------

def fetch_indices_tool(session):
    print("Fetching NIFTY 50, SENSEX, and NIFTY REALTY indices...")
    indices = {}
    
    # 1. Fetch NIFTY 50 & NIFTY REALTY from NSE
    try:
        url = "https://www.nseindia.com/api/allIndices"
        r = session.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json().get('data', [])
            for idx in data:
                iname = idx.get('index')
                if iname in ['NIFTY 50', 'NIFTY REALTY']:
                    last_val = round(float(idx.get('last', 0.0)), 2)
                    var_val = round(float(idx.get('variation', 0.0)), 2)
                    pct_val = round(float(idx.get('percentChange', 0.0)), 2)
                    indices[iname] = {
                        "name": iname,
                        "closing_value": last_val,
                        "points_change": var_val,
                        "percent_movement": f"{pct_val}%"
                    }
    except Exception as e:
        print(f"  Warning: Failed to fetch NSE indices: {e}")

    # 2. Fetch SENSEX from Yahoo Finance
    try:
        import yfinance as yf
        ticker = yf.Ticker("^BSESN")
        fast_info = ticker.fast_info
        last_price = fast_info.last_price
        prev_close = fast_info.previous_close
        if last_price and prev_close:
            change_pts = last_price - prev_close
            p_change = (change_pts / prev_close) * 100
            indices['SENSEX'] = {
                "name": "SENSEX",
                "closing_value": round(float(last_price), 2),
                "points_change": round(float(change_pts), 2),
                "percent_movement": f"{round(float(p_change), 2)}%"
            }
    except Exception as e:
        print(f"  Warning: Failed to fetch SENSEX: {e}")

    order = ['NIFTY 50', 'SENSEX', 'NIFTY REALTY']
    return [indices[k] for k in order if k in indices]

# ----------------------------------------------------------
# Stock Fetch Tool
# Retrieves stock data directly from NSE India API
# ----------------------------------------------------------

def stock_data_tool(session, stock):
    symbol = stock["symbol"]
    name = stock["name"]
    
    print(f"Fetching data for {symbol} ({name})...")
    
    url = f"https://www.nseindia.com/api/NextApi/apiClient/GetQuoteApi?functionName=getSymbolData&marketType=N&series=EQ&symbol={symbol}"
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, timeout=30)
            if response.status_code != 200:
                print(f"  [Attempt {attempt}/{max_retries}] Error: Received status code {response.status_code} for {symbol}")
                if attempt == max_retries:
                    return None
                time.sleep(2)
                continue
            
            data = response.json()
            eq_resp = data.get('equityResponse', [{}])[0]
            if not eq_resp:
                raise ValueError(f"No equityResponse data found in response for {symbol}")
                
            meta = eq_resp.get('metaData', {})
            trade = eq_resp.get('tradeInfo', {})
            
            # If market is closed, closePrice is preferred. If open, lastPrice.
            price = meta.get('closePrice') or meta.get('lastPrice') or meta.get('iep') or 0.0
            change = meta.get('change', 0.0)
            pChange = meta.get('pChange', 0.0)
            
            # Market Cap in Cr directly from NSE tradeInfo.totalMarketCap
            raw_mkt_cap = trade.get('totalMarketCap', 0.0)
            mkt_cap_cr = round(raw_mkt_cap / 10_000_000, 2) if raw_mkt_cap else 0.0
            
            print(f"  Success: Price={price:.2f}, Change={change:.2f} ({pChange:.2f}%), Market Cap={mkt_cap_cr:.2f} Cr")
            
            return {
                "price": price,
                "change_amount": change,
                "change_percent": pChange,
                "market_cap_cr": mkt_cap_cr
            }
        except Exception as e:
            print(f"  [Attempt {attempt}/{max_retries}] Error fetching/parsing {symbol}: {e}")
            if attempt == max_retries:
                return None
            time.sleep(2)

# ----------------------------------------------------------
# Google Sheets Tool
# Stores processed stock information
# ----------------------------------------------------------

def google_sheets_tool(url, rows, indices=None, sheet_name=None):
    print(f"\nSending data to Google Sheets Web App...")
    payload = {
        "sheet_name": sheet_name or datetime.datetime.now().strftime('%d-%m-%Y'),
        "data": rows,
        "indices": indices or []
    }
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"Web App Response Status: {response.status_code}")
        print(f"Web App Response Body: {response.text}")
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get("status") == "success":
                    print("Data successfully written to Google Sheet!")
                    return True
                else:
                    print(f"Google Sheets API Error: {result.get('message')}")
            except Exception:
                # Handle plain text response
                if "success" in response.text.lower():
                    print("Data successfully written to Google Sheet!")
                    return True
                print("Failed to parse Web App JSON response, check sheet if data was written.")
        return False
    except Exception as e:
        print(f"Error calling Web App: {e}")
        return False

def write_to_google_sheet_service_account(sheets_config, rows):
    print("\nAuthenticating with Google Sheets API via Service Account...")
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
    except ImportError:
        print("Error: gspread and oauth2client libraries are required for the service_account method.")
        print("Run: pip install gspread oauth2client")
        return False

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_path = sheets_config["service_account_json_path"]
        
        # Resolve path relative to tracker.py if it's a relative path
        if not os.path.isabs(creds_path):
            creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), creds_path)
            
        if not os.path.exists(creds_path):
            print(f"Error: Service account credentials JSON not found at {creds_path}")
            return False
            
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        client = gspread.authorize(creds)
        
        spreadsheet_name = sheets_config["spreadsheet_name"]
        sheet_name = sheets_config["sheet_name"]
        
        print(f"Opening spreadsheet '{spreadsheet_name}', worksheet '{sheet_name}'...")
        sheet = client.open(spreadsheet_name).worksheet(sheet_name)
        
        # Prepare rows to append (convert dicts to lists in the correct column order)
        # Columns: Company, Closing Price, % Change, Market cap (Rs. Cr.)
        rows_to_append = []
        for r in rows:
            rows_to_append.append([
                r["name"],
                r["closing_rate"],
                r["percent_movement"],
                r["market_cap_cr"]
            ])
            
        print(f"Appending {len(rows_to_append)} rows to Google Sheet...")
        sheet.append_rows(rows_to_append)
        print("Data successfully appended to Google Sheet!")
        return True
    except Exception as e:
        print(f"Error writing to Google Sheets via Service Account: {e}")
        return False

def run_market_intelligence_agent():
    print(f"=== Bangalore Realty Stocks Tracker - Run started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    config = load_config()
    
    today_date = datetime.datetime.now().strftime('%Y-%m-%d')
    fetch_time = datetime.datetime.now().strftime('%H:%M:%S')
    
    # Setup HTTP Session to reuse TCP connection (increases speed and resilience)
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # Initialize cookies on nseindia.com to avoid 403 blocks
    print("Initializing session on nseindia.com...")
    try:
        session.get("https://www.nseindia.com", timeout=15)
        time.sleep(2)  # Delay to let cookies settle
    except Exception as e:
        print(f"Warning: Failed to initialize session cookies: {e}")
        
    results = []
    
    # 1. Fetch Market Indices (NIFTY 50, SENSEX, NIFTY REALTY)
    indices_data = fetch_indices_tool(session)
    
    # 2. Fetch 12 Realty Stocks
    results = []
    for stock in config["stocks"]:
        data = stock_data_tool(session, stock)
        if data:
            results.append({
                "name": stock["name"],
                "closing_rate": data["price"],
                "percent_movement": f"{data['change_percent']}%",
                "market_cap_cr": data["market_cap_cr"]
            })
        time.sleep(2.0) # Politeness delay between requests
            
    if not results:
        print("No stock data was successfully fetched. Exiting.")
        return
        
    sheets_config = config["google_sheets"]
    method = sheets_config.get("method", "web_app").lower()
    
    if method == "web_app":
        url = sheets_config.get("web_app_url")
        if not url or "YOUR_GOOGLE_APPS_SCRIPT_WEB_APP_URL_HERE" in url:
            print("\n[Warning] Google Sheets Web App URL is not configured in config.json")
            print("Please configure 'web_app_url' in config.json to upload data automatically.")
            # Still output the results to stdout so they can see them
            print("\nFetched Stock Data:")
            print(json.dumps(results, indent=2))
            sys.exit(0)
        today_sheet_name = datetime.datetime.now().strftime('%d-%m-%Y')
        google_sheets_tool(url, results, indices=indices_data, sheet_name=today_sheet_name)
    elif method == "service_account":
        write_to_google_sheet_service_account(sheets_config, results)
    else:
        print(f"Error: Unknown Google Sheets integration method: {method}")
        sys.exit(1)

if __name__ == "__main__":
    run_market_intelligence_agent()
