/**
 * Google Apps Script for Bangalore Realty Tracker (Realty Pulse - Oct)
 * 
 * Web App deployment endpoint to handle POST requests from Python scripts.
 * Populates market indices (NIFTY 50, SENSEX, NIFTY REALTY) and 12 realty stocks.
 */

function doPost(e) {
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var payload = JSON.parse(e.postData.contents);
    
    // Determine target sheet name (default: date string e.g. "05-10-2026" or custom sheet_name)
    var targetSheetName = payload.sheet_name || "Sheet1";
    var sheet = ss.getSheetByName(targetSheetName);
    
    // If sheet doesn't exist, create it
    if (!sheet) {
      sheet = ss.insertSheet(targetSheetName);
    }
    
    sheet.clear();
    
    var rows = payload.data || [];
    var indices = payload.indices || [];
    
    // -----------------------------------------------------------------
    // Section 1: Market Indices Table
    // -----------------------------------------------------------------
    if (indices && indices.length > 0) {
      sheet.appendRow(["MARKET INDICES SUMMARY"]);
      sheet.getRange(sheet.getLastRow(), 1).setFontWeight("bold").setFontSize(11);
      
      sheet.appendRow(["Index Name", "Closing Value", "Points Change", "% Movement"]);
      var idxHeaderRange = sheet.getRange(sheet.getLastRow(), 1, 1, 4);
      idxHeaderRange.setFontWeight("bold");
      idxHeaderRange.setBackground("#D9E1F2");
      
      for (var j = 0; j < indices.length; j++) {
        var idx = indices[j];
        sheet.appendRow([
          idx.name,
          idx.closing_value,
          idx.points_change,
          idx.percent_movement
        ]);
      }
      sheet.appendRow([""]); // Spacer row
    }
    
    // -----------------------------------------------------------------
    // Section 2: Realty Stocks Table
    // -----------------------------------------------------------------
    sheet.appendRow(["REALTY STOCKS DATA"]);
    sheet.getRange(sheet.getLastRow(), 1).setFontWeight("bold").setFontSize(11);
    
    var stockHeaders = ["Company Name", "Closing Rate (Rs)", "% Movement", "Market Cap (Rs. Cr)"];
    sheet.appendRow(stockHeaders);
    var stockHeaderRange = sheet.getRange(sheet.getLastRow(), 1, 1, stockHeaders.length);
    stockHeaderRange.setFontWeight("bold");
    stockHeaderRange.setBackground("#1F4E79");
    stockHeaderRange.setFontColor("#FFFFFF");
    
    for (var k = 0; k < rows.length; k++) {
      var st = rows[k];
      sheet.appendRow([
        st.name || st.company || "",
        st.closing_rate || st.price || 0,
        st.percent_movement || st.change_percent || 0,
        st.market_cap_cr || 0
      ]);
    }
    
    // Auto resize columns for a clean look
    for (var c = 1; c <= 4; c++) {
      sheet.autoResizeColumn(c);
    }
    
    return ContentService.createTextOutput(JSON.stringify({
      "status": "success",
      "message": "Appended " + rows.length + " stock rows to sheet '" + targetSheetName + "'."
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      "status": "error",
      "message": error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}
