# Results Fetcher Setup Guide

## Quick Start

1. Install required packages:
```bash
pip install gspread oauth2client
```

2. Get Google Sheets credentials:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a project
   - Enable Google Sheets API
   - Create Service Account credentials
   - Download JSON key file

3. Share your Google Sheet with the service account email (found in JSON file)

4. Save the credentials as `service-account-credentials.json` in this directory

5. Run the script:
```bash
python3 results_fetcher.py
```

## Sheet Structure (as provided)

| Column | Description |
|--------|-------------|
| B | Home team points (row 2) / Individual home points (rows 3-5) |
| C | Home team name (row 2) / Home team players (rows 3-5) |
| D | Match date (row 2) / Set score (rows 3-5) |
| E | Guest team name (row 2) / Guest team players (rows 3-5) |
| F | Guest team points (row 2) / Guest team points (rows 3-5) |

## Output

The script generates `docs/results.html` with match results displayed in a responsive grid layout.