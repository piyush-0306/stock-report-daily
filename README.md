# Bangalore Realty Stocks Tracker

This project automates the daily tracking of publicly listed real estate companies based in Bangalore that are part of CREDAI. Every day, the script fetches live stock market updates (closing rate, price change, percentage movement, and NSE market capitalization) from Moneycontrol and uploads it directly to your Google Sheet.

## Tracked Companies
1. **Prestige Estates Projects Ltd** (`PRESTIGE`)
2. **Brigade Enterprises Ltd** (`BRIGADE`)
3. **Sobha Limited** (`SOBHA`)
4. **Puravankara Limited** (`PURVA`)
5. **Shriram Properties Limited** (`SHRIRAMPPS`)
6. **Arvind SmartSpaces Limited** (`ARVSMART`)

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
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    var payload = JSON.parse(e.postData.contents);
    var rows = payload.data;
    
    // Create headers if the sheet is empty
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        "Date", 
        "Time", 
        "Symbol", 
        "Company Name", 
        "Closing Rate (Rs)", 
        "Change Amount (Rs)", 
        "Percentage Movement", 
        "Market Cap (Cr)"
      ]);
    }
    
    // Append rows
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      sheet.appendRow([
        r.date,
        r.time,
        r.symbol,
        r.name,
        r.closing_rate,
        r.change_amount,
        r.percent_movement,
        r.market_cap_cr
      ]);
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

## Automating the Daily Run at 4:00 PM

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
    # Runs at 10:30 AM UTC (4:00 PM IST) daily
    - cron: '30 10 * * *'
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
   - **Trigger**: `Daily`
   - **Start Time**: Set the time to `4:00:00 PM`.
   - **Action**: `Start a program`
   - **Program/script**: `python`
   - **Add arguments**: `tracker.py`
   - **Start in**: Enter the absolute path to this folder (e.g., `C:\Users\YourUser\agy2-projects\bangalore-realty-tracker`).
4. Click **Finish**.
