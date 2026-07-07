"""
=================================================

Bangalore Realty Market Intelligence Agent

Architecture

Market Intelligence Agent
        │
        ├── Configuration Loader
        ├── Stock Fetch Tool
        ├── Market Data Parser
        └── Google Sheets Tool

The agent autonomously coordinates the
daily workflow to collect, process,
and persist stock market information.

Developed using Google Antigravity IDE.

=================================================
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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}")
        sys.exit(1)
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def market_data_parser(html, symbol):
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Closing Price (NSE preferred, BSE fallback)
    price_elem = soup.find(class_="nsecp")
    if not price_elem:
        price_elem = soup.find(class_="bsecp")
    
    if not price_elem:
        raise ValueError(f"Could not find stock price element (class 'nsecp'/'bsecp')")
    
    price_val = float(price_elem.text.strip().replace(",", ""))
    
    # 2. Change and Percent Change (NSE preferred, BSE fallback)
    change_elem = soup.find(id="nsechange")
    if not change_elem:
        change_elem = soup.find(class_="nsechange")
    if not change_elem:
        change_elem = soup.find(id="bsechange")
    if not change_elem:
        change_elem = soup.find(class_="bsechange")
        
    if not change_elem:
        raise ValueError(f"Could not find price change element (id/class 'nsechange'/'bsechange')")
        
    change_text = change_elem.text.strip()
    # Match: change_amount (percent_change%)
    # E.g., "48.80 (3.00%)" or "-12.50 (-0.80%)"
    match = re.search(r"([+-]?[0-9,.]+)\s*\(\s*([+-]?[0-9,.]+)%\s*\)", change_text)
    if not match:
        raise ValueError(f"Could not parse change text format '{change_text}'")
        
    change_amt = float(match.group(1).replace(",", ""))
    change_pct = float(match.group(2).replace(",", ""))
    
    # 3. Market Cap in Rs. Cr. (NSE preferred, BSE fallback)
    mkt_cap_elem = soup.find(class_="nsemktcap")
    if not mkt_cap_elem:
        mkt_cap_elem = soup.find(class_="bsemktcap")
        
    if not mkt_cap_elem:
        raise ValueError(f"Could not find market cap element (class 'nsemktcap'/'bsemktcap')")
        
    mkt_cap_val = float(mkt_cap_elem.text.strip().replace(",", ""))
    
    return {
        "price": price_val,
        "change_amount": change_amt,
        "change_percent": change_pct,
        "market_cap_cr": mkt_cap_val
    }

def fetch_stock_data(session, stock):
    symbol = stock["symbol"]
    url = stock["moneycontrol_url"]
    
    print(f"Fetching data for {symbol} ({stock['name']})...")
    
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
            
            data = market_data_parser(response.text, symbol)
            print(f"  Success: Price={data['price']}, Change={data['change_amount']} ({data['change_percent']}%), Market Cap={data['market_cap_cr']} Cr")
            return data
        except Exception as e:
            print(f"  [Attempt {attempt}/{max_retries}] Error fetching/parsing {symbol}: {e}")
            if attempt == max_retries:
                return None
            time.sleep(2)

def google_sheets_tool(url, rows):
    print(f"\nSending data to Google Sheets Web App...")
    payload = {
        "data": rows
    }
    try:
        response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=30)
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
        
        rows_to_append = []
        for r in rows:
            rows_to_append.append([
                r["date"],
                r["time"],
                r["symbol"],
                r["name"],
                r["closing_rate"],
                r["change_amount"],
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
    # Force alignment to Indian Standard Time (IST) regardless of host runtime architecture (like GitHub Actions)
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    ist_offset = datetime.timedelta(hours=5, minutes=30)
    ist_now = utc_now + ist_offset

    print(f"=== Bangalore Realty Stocks Tracker - Run started at {ist_now.strftime('%Y-%m-%d %H:%M:%S')} IST ===")
    config = load_config()
    
    today_date = ist_now.strftime('%Y-%m-%d')
    fetch_time = ist_now.strftime('%H:%M:%S')
    
    # Setup HTTP Session to reuse TCP connection (increases speed and resilience)
    session = requests.Session()
    session.headers.update(HEADERS)
    
    results = []
    for stock in config["stocks"]:
        data = fetch_stock_data(session, stock)
        if data:
            results.append({
                "date": today_date,
                "time": fetch_time,
                "symbol": stock["symbol"],
                "name": stock["name"],
                "closing_rate": data["price"],
                "change_amount": data["change_amount"],
                # Passing as a raw decimal value instead of a text string allows 
                # native mathematical/graph formatting configurations inside Google Sheets.
                "percent_movement": data["change_percent"] / 100.0,
                "market_cap_cr": data["market_cap_cr"]
            })
        time.sleep(1.5) # Politeness delay between requests
            
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
            print("\nFetched Stock Data:")
            print(json.dumps(results, indent=2))
            sys.exit(0)
        google_sheets_tool(url, results)
    elif method == "service_account":
        write_to_google_sheet_service_account(sheets_config, results)
    else:
        print(f"Error: Unknown Google Sheets integration method: {method}")
        sys.exit(1)

if __name__ == "__main__":
    run_market_intelligence_agent()
