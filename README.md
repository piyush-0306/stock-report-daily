# Bangalore Realty Market Intelligence Agent
Automated monitoring of Bangalore real estate stocks using Python, Google Antigravity and GitHub Actions.

## Problem

Tracking Bangalore real estate stocks every day requires visiting multiple financial websites, manually recording prices and maintaining historical records.

## Solution

The Bangalore Realty Market Intelligence Agent automates the complete workflow.

The agent:

- Retrieves live stock data from Moneycontrol
- Parses daily market information
- Structures the data
- Automatically stores the results in Google Sheets
- Runs daily through GitHub Actions

This eliminates manual data collection and creates a continuously growing historical dataset.

## Architecture

```text
                 GitHub Actions
                        │
                        ▼
        Market Intelligence Agent
                        │
        ┌───────────────┴───────────────┐
        │                               │
 Configuration Loader           Stock Fetch Tool
                                        │
                                        ▼
                             Market Data Parser
                                        │
                                        ▼
                               Google Sheets Tool
                                        │
                                        ▼
                                 Google Sheets
```
## Technologies

- Python
- Requests
- BeautifulSoup
- Google Apps Script
- Google Sheets
- GitHub Actions
- Google Antigravity IDE
- Google Antigravity Web

## Features

- Daily automated execution
- Cloud deployment through GitHub Actions
- Moneycontrol stock data extraction
- Automatic Google Sheets updates
- Configurable stock list (currently 12 stocks)
- Retry logic for failed requests
- Error handling and execution logging

## Tracked Companies
1. **Ajmera Realty & Infra India Ltd** (`AJMERA`)
2. **Brigade Enterprises Ltd** (`BRIGADE`)
3. **Godrej Properties Ltd** (`GODREJPROP`)
4. **Kolte-Patil Developers Ltd** (`KOLTEPATIL`)
5. **Mahindra Lifespace Developers Ltd** (`MAHLIFE`)
6. **NCC Ltd** (`NCC`)
7. **The Phoenix Mills Ltd** (`PHOENIXLTD`)
8. **Prestige Estates Projects Ltd** (`PRESTIGE`)
9. **Puravankara Limited** (`PURVA`)
10. **Ramky Infrastructure Ltd** (`RAMKY`)
11. **Shriram Properties Limited** (`SHRIRAMPPS`)
12. **Sobha Limited** (`SOBHA`)

---

## Getting Started

### 1. Installation
Ensure you have Python 3.11+ installed on your system.

Clone or download this folder and install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configuration
Open `config.json` and configure how you want to connect to Google Sheets. There are two supported methods:

---

## Google Sheets Integration Method 1: Google Apps Script (Recommended)

This method is the simplest because it **does not require creating a Google Cloud Project** or generating complex API credentials.

### Step-by-Step Setup:
1. Open your target **Google Sheet**.
2. Click on **Extensions** in the top menu, then select **Apps Script**.
3. Clear any existing code in the editor and paste the following code:

```javascript
function doPost(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var payload = JSON.parse(e.postData.contents);
    
    var targetSheetName = payload.sheet_name || "Sheet1";
    var sheet = ss.getSheetByName(targetSheetName);
    if (!sheet) {
      sheet = ss.insertSheet(targetSheetName);
    }
    sheet.clear();
    
    var rows = payload.data || [];
    var indices = payload.indices || [];
    
    if (indices && indices.length > 0) {
      sheet.appendRow(["MARKET INDICES SUMMARY"]);
      sheet.getRange(sheet.getLastRow(), 1).setFontWeight("bold").setFontSize(11);
      sheet.appendRow(["Index Name", "Closing Value", "Points Change", "% Movement"]);
      var idxHeaderRange = sheet.getRange(sheet.getLastRow(), 1, 1, 4);
      idxHeaderRange.setFontWeight("bold").setBackground("#D9E1F2");
      for (var j = 0; j < indices.length; j++) {
        var idx = indices[j];
        sheet.appendRow([idx.name, idx.closing_value, idx.points_change, idx.percent_movement]);
      }
      sheet.appendRow([""]);
    }
    
    sheet.appendRow(["REALTY STOCKS DATA"]);
    sheet.getRange(sheet.getLastRow(), 1).setFontWeight("bold").setFontSize(11);
    var stockHeaders = ["Company Name", "Closing Rate (Rs)", "% Movement", "Market Cap (Rs. Cr)"];
    sheet.appendRow(stockHeaders);
    var stockHeaderRange = sheet.getRange(sheet.getLastRow(), 1, 1, stockHeaders.length);
    stockHeaderRange.setFontWeight("bold").setBackground("#1F4E79").setFontColor("#FFFFFF");
    
    for (var k = 0; k < rows.length; k++) {
      var st = rows[k];
      sheet.appendRow([
        st.name || st.company || "",
        st.closing_rate || st.price || 0,
        st.percent_movement || st.change_percent || 0,
        st.market_cap_cr || 0
      ]);
    }
    
    for (var c = 1; c <= 4; c++) {
      sheet.autoResizeColumn(c);
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success", 
      "message": "Appended " + rows.length + " rows."
    })).setMimeType(ContentService.MimeType.JSON);
    
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      "status": "error", 
      "message": error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
```

4. Click the **Save** (disk) icon.
5. Click the **Deploy** button at the top-right and select **New deployment**.
6. Click the gear icon next to "Select type" and select **Web app**.
7. Configure the settings:
   - **Description**: `Realty Stock Tracker`
   - **Execute as**: `Me (your-email@gmail.com)`
   - **Who has access**: `Anyone` (This is crucial to allow the Python script to post data)
8. Click **Deploy**.
9. You will be prompted to authorize access. Click **Authorize access**, choose your Google account, click **Advanced**, and then click **Go to Untitled project (unsafe)**. Click **Allow**.
10. Once deployed, copy the **Web app URL** from the screen.
11. Paste this URL into `config.json` under `google_sheets` -> `web_app_url`:
```json
  "google_sheets": {
    "method": "web_app",
    "web_app_url": "https://script.google.com/macros/s/YOUR_DEPLOYED_URL_HERE/exec",
    ...
  }
```

---

## Google Sheets Integration Method 2: Google Sheets API v4 (Service Account)

If you already have a Google Cloud project or prefer standard API access:
1. Create a service account in your Google Cloud Console.
2. Enable the **Google Sheets API** and **Google Drive API**.
3. Generate a JSON credentials key, download it, and rename it to `credentials.json` (place it in this directory).
4. Share your Google Sheet with the service account email (found in your `credentials.json` file as `client_email`) with **Editor** permissions.
5. Update your `config.json` to use `service_account`:
```json
  "google_sheets": {
    "method": "service_account",
    "service_account_json_path": "credentials.json",
    "spreadsheet_name": "Bangalore Realty Stocks Tracker",
    "sheet_name": "Sheet1"
  }
```

---

## How to Run Locally

You can manually trigger the tracking script at any time:
```bash
python tracker.py
```

---

## Automating the Daily Run at 4:00 PM (Monday to Friday)

Since Indian stock markets close at 3:30 PM, running this at **4:00 PM** ensures the final closing rates and market capitalizations are correctly logged.

### Option A: GitHub Actions (Free Cloud Scheduler - Recommended)
You can run this completely in the cloud without keeping your PC turned on:
1. Create a private GitHub repository for this project.
2. In your repository, create a directory structure: `.github/workflows/`
3. Add a file named `daily_run.yml` with the following contents:

```yaml
name: Daily Realty Stocks Tracker

on:
  schedule:
    # Runs at 10:30 AM UTC (4:00 PM IST) Monday to Friday
    - cron: '30 10 * * 1-5'
  workflow_dispatch: # Allows manual trigger

jobs:
  run-tracker:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run Tracker Script
        run: python tracker.py
```

### Option B: Windows Task Scheduler (Local Run)
If you prefer running it locally on your Windows PC:
1. Open **Task Scheduler** on your computer.
2. Click **Create Basic Task...** on the right side.
3. Set the details:
   - **Name**: `Bangalore Realty Stocks Tracker`
   - **Trigger**: `Weekly`
   - **Start Time**: Set the time to `4:00:00 PM` and check **Monday, Tuesday, Wednesday, Thursday, and Friday**.
   - **Action**: `Start a program`
   - **Program/script**: `python`
   - **Add arguments**: `tracker.py`
   - **Start in**: Enter the absolute path to this folder (e.g., `C:\Users\YourUser\agy2-projects\bangalore-realty-tracker`).
4. Click **Finish**.
