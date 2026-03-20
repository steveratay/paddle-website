#!/usr/bin/env python3
"""
Google Sheets Results Fetcher

Reads match results and standings from a Google Sheet and updates
results.html and standings.html with the data.
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
from pathlib import Path

# Google Sheets configuration
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1D8euOXUaqpxDVJM0vFwlZZSgW5lyZDfSv7zv49YmkmQ/edit"
WORKSHEET_NAME = "Results"
STANDINGS_WORKSHEET_NAME = "Standings"

# File paths
SCRIPT_DIR = Path(__file__).parent
RESULTS_HTML = SCRIPT_DIR / "docs" / "results.html"
STANDINGS_HTML = SCRIPT_DIR / "docs" / "standings.html"


def fetch_results():
    """Fetch match results from Google Sheets."""
    # Note: You need to set up service account credentials
    # For development, you might want to use gspread-pandas or other methods
    # that don't require a service account file
    
    # The script needs service account credentials to authenticate
    # Create a service account in Google Cloud Console and download credentials
    # CREDENTIALS_FILE = "path/to/service-account-credentials.json"
    
    # For now, this function shows what would be done
    print("Google Sheets Configuration:")
    print(f"  Spreadsheet URL: {SPREADSHEET_URL}")
    print(f"  Worksheet Name: {WORKSHEET_NAME}")
    print()
    print("To use this script, you need to:")
    print("  1. Create a service account in Google Cloud Console")
    print("  2. Download the credentials JSON file")
    print("  3. Share the Google Sheet with the service account email")
    print("  4. Update CREDENTIALS_FILE path in this script")
    print()
    print("Alternatively, for local testing without service account:")
    print("  pip install gspread-pandas")
    print("  Then use: gspread.authorize(gspread.service_account())")
    
    return None


def is_match_header_row(row):
    """
    Check if a row is a match header row (with team names) vs individual match row.
    
    Match header rows have:
    - Non-empty home team name in column C
    - Date in column D  
    - Non-empty guest team name in column E
    
    Individual match rows have:
    - " / " in home players column
    - " / " in guest players column
    """
    if not row or len(row) < 5:
        return False
    
    home_team = row[2].strip() if len(row) > 2 else ""
    guest_team = row[4].strip() if len(row) > 4 else ""
    date = row[3].strip() if len(row) > 3 else ""
    
    # Match header: has team names and date
    # Check if it looks like a match header (has "Team" or meaningful team name)
    is_match_header = (
        len(home_team) > 0 and 
        " / " not in home_team and  # Not a player name
        len(guest_team) > 0 and
        "Team" in guest_team and
        len(date) > 0 and
        "Week" in date
    )
    
    return is_match_header

def is_individual_match_row(row):
    """
    Check if a row is an individual match row (with player names).
    
    Individual match rows have "/" in player columns.
    """
    if not row or len(row) < 5:
        return False
    
    home_players = row[2].strip() if len(row) > 2 else ""
    guest_players = row[4].strip() if len(row) > 4 else ""
    
    # Individual match: has "/" indicating multiple players
    has_player_delimiter = "/" in home_players or "/" in guest_players
    
    return has_player_delimiter

def parse_sheet_data(data):
    """
    Parse Google Sheet data into structured match results.
    
    The sheet has the following structure:
    - Row 2: Header with total team points
    - Next 4 rows: Individual match results (players, set scores)
    - Blank row separator
    - Pattern repeats for each match
    
    Column mapping (1-indexed):
    B (col 2): Home team points / individual match points
    ceC (col 3): Home team name / home team players
    D (col 4): Match date / set-by-set score
    E (col 5): Guest team name / guest team players
    F (col 6): Guest team points / guest team points
    """
    if not data or len(data) < 2:
        return []
    
    matches = []
    current_week_matches = []
    
    # Skip header row (index 0)
    for i, row in enumerate(data[1:], start=2):
        # Check if this is a blank row (separator)
        # A row is blank if it's empty or all cells are empty/whitespace
        is_blank = False
        if not row:
            is_blank = True
        elif all(cell.strip() == "" for cell in row):
            is_blank = True
        elif len(row) == 1 and row[0].strip() == "":
            is_blank = True
        
        if is_blank:
            if current_week_matches:
                matches.append(current_week_matches)
                current_week_matches = []
            continue
        
        # Parse the match data
        # Check if this is a match header row or individual match row
        if is_match_header_row(row):
            # Match header row: B=total home points, C=home team, D=date, E=guest team, F=total guest points
            match = {
                "date": row[3].strip() if len(row) > 3 else "",
                "home_team": row[2].strip() if len(row) > 2 else "",
                "guest_team": row[4].strip() if len(row) > 4 else "",
                "home_total_points": row[1].strip() if len(row) > 1 else "",
                "guest_total_points": row[5].strip() if len(row) > 5 else "",
                "individual_matches": []
            }
            current_week_matches.append(match)
        elif is_individual_match_row(row):
            # Individual match row: B=home points, C=home players, D=set score, E=guest players, F=guest points
            if current_week_matches:
                match = current_week_matches[-1]
                individual_match = {
                    "home_points": row[1].strip() if len(row) > 1 else "",
                    "home_players": row[2].strip() if len(row) > 2 else "",
                    "set_score": row[3].strip() if len(row) > 3 else "",
                    "guest_players": row[4].strip() if len(row) > 4 else "",
                    "guest_points": row[5].strip() if len(row) > 5 else ""
                }
                match["individual_matches"].append(individual_match)
        else:
            pass  # Row doesn't match expected format, skip silently
    
    # Don't forget the last group if no trailing blank row
    if current_week_matches:
        matches.append(current_week_matches)
    
    return matches


def load_html_template():
    """Load the base HTML template from existing results.html file."""
    template_path = SCRIPT_DIR / "docs" / "results.html"
    
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    
    # Fallback template if file doesn't exist
    return None


def extract_style_content(html_content):
    """Extract the <style> content from existing HTML."""
    if not html_content:
        return ""
    
    # Try to extract styles from the existing template
    style_match = re.search(r'<style>(.*?)</style>', html_content, re.DOTALL)
    if style_match:
        return style_match.group(1)
    
    return ""


def generate_main_content(matches):
    """Generate the main content HTML from match data."""
    main_content = []
    week_num = 0
    
    for week_matches in matches:
        if not week_matches:
            continue
        
        week_num += 1
        
        # Extract date from first match (assuming all matches in a week are on same date)
        date_str = week_matches[0].get("date", "TBD")
        
        main_content.append(f'    <!-- Week {week_num} -->')
        main_content.append(f'    <div class="results-section">')
        main_content.append(f'      <h3>{date_str}</h3>')
        
        for match_idx, match in enumerate(week_matches):
            home_team = match.get("home_team", "TBD")
            guest_team = match.get("guest_team", "TBD")
            home_total = match.get("home_total_points", "0")
            guest_total = match.get("guest_total_points", "0")
            
            main_content.append(f'      <table class="match-table">')
            main_content.append(f'        <thead>')
            main_content.append(f'          <tr class="match-header-row">')
            main_content.append(f'            <th class="team-cell team-left" colspan="2" style="padding-bottom: 0.3rem;">{home_team}</th>')
            main_content.append(f'            <th class="center-cell" colspan="1" style="border-left: 2px solid var(--green-primary); border-right: 2px solid var(--green-primary); vertical-align: bottom; width: 100px;">')
            main_content.append(f'              <span class="vs-text">vs.</span>')
            main_content.append(f'              <div class="match-score" style="display: inline-block; font-size: 1.1rem; background: var(--white); padding: 0.35rem 0.9rem; border-radius: 4px; color: var(--green-dark);">{home_total} - {guest_total}</div>')
            main_content.append(f'            </th>')
            main_content.append(f'            <th class="team-cell team-right" colspan="2" style="padding-bottom: 0.3rem;">{guest_team}</th>')
            main_content.append(f'          </tr>')
            main_content.append(f'          <tr class="match-header-row">')
            main_content.append(f'            <th class="team-cell team-left" colspan="2" style="font-size: 0.78rem; color: #4a6a55; padding-top: 0;">')
            main_content.append(f'              <span class="match-date">{date_str}</span>')
            main_content.append(f'            </th>')
            main_content.append(f'            <th class="center-cell" colspan="1" style="font-size: 0.7rem; color: var(--green-primary); border-left: 2px solid var(--green-primary); border-right: 2px solid var(--green-primary); width: 100px;">')
            main_content.append(f'              <span class="set-score">Total Score</span>')
            main_content.append(f'            </th>')
            main_content.append(f'            <th class="team-cell team-right" colspan="2" style="font-size: 0.78rem; color: #4a6a55; padding-top: 0;">')
            main_content.append(f'              <span class="match-date">{date_str}</span>')
            main_content.append(f'            </th>')
            main_content.append(f'          </tr>')
            main_content.append(f'        </thead>')
            main_content.append(f'        <tbody>')
            
            # Add individual match rows (4 matches per week)
            for ind_match in match.get("individual_matches", []):
                home_players = ind_match.get("home_players", "")
                guest_players = ind_match.get("guest_players", "")
                home_pts = ind_match.get("home_points", "")
                guest_pts = ind_match.get("guest_points", "")
                set_score = ind_match.get("set_score", "")
                
                main_content.append(f'          <tr class="match-row">')
                main_content.append(f'            <td class="team-cell team-left">')
                if home_players:
                    main_content.append(f'              <div class="team-players">{home_players}</div>')
                main_content.append(f'            </td>')
                main_content.append(f'            <td class="score-cell score-left">{home_pts}</td>')
                
                # Set score display (center column)
                main_content.append(f'            <td class="center-cell" style="width: 100px;">')
                main_content.append(f'              <span class="vs-text">vs.</span>')
                if set_score:
                    main_content.append(f'              <span class="set-score">{set_score}</span>')
                main_content.append(f'            </td>')
                
                main_content.append(f'            <td class="score-cell score-right">{guest_pts}</td>')
                main_content.append(f'            <td class="team-cell team-right">')
                if guest_players:
                    main_content.append(f'              <div class="team-players">{guest_players}</div>')
                main_content.append(f'            </td>')
                main_content.append(f'          </tr>')
            
            main_content.append(f'        </tbody>')
            main_content.append(f'      </table>')
        
        main_content.append(f'    </div>')
    
    return "\n".join(main_content)


def replace_main_content(html_content, new_main_content):
    """Replace the content inside the <main> tag with new content."""
    # Pattern to match everything between <main> and </main> tags
    pattern = r'<main>.*?</main>'
    
    replacement = f'<main>\n{new_main_content}\n  </main>'
    
    # Use DOTALL flag to match across newlines
    result = re.sub(pattern, replacement, html_content, flags=re.DOTALL)
    
    return result


def generate_results_html(matches):
    """Generate the complete results.html content from match data."""
    # Load the existing template
    template = load_html_template()
    
    if template is None:
        # If no template exists, create a minimal one
        return generate_minimal_html(matches)
    
    # Generate the main content
    main_content = generate_main_content(matches)
    
    # Replace the <main> section content
    html_content = replace_main_content(template, main_content)
    
    # Ensure the style section exists (safety check)
    if '<style>' not in html_content:
        # Extract styles from minimal HTML and add them
        minimal_html = generate_minimal_html(matches)
        style_content = extract_style_content(minimal_html)
        if style_content:
            # Find </head> and insert style before it
            style_tag = f'  <style>\n{style_content}\n  </style>'
            html_content = html_content.replace('</head>', f'{style_tag}\n  </head>', 1)
    
    return html_content


def generate_minimal_html(matches):
    """Generate a minimal HTML template when no existing template exists."""
    main_content = generate_main_content(matches)
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Winter Club – Results | Men's Spring Paddle League 2026</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --green-dark:    #1a4a2e;
      --green-primary: #2d6a4f;
      --green-mid:     #40916c;
      --green-light:   #74c69d;
      --green-pale:    #d8f3dc;
      --white:         #ffffff;
      --text-dark:     #1b2e22;
      --shadow:        0 4px 16px rgba(0,0,0,0.15);
      --radius:        10px;
    }}

    body {{
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: #f0f7f2;
      color: var(--text-dark);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    nav {{
      background: var(--green-dark);
      display: flex;
      align-items: center;
      padding: 0 1.5rem;
      height: 56px;
      gap: 0.25rem;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }}

    .nav-brand {{
      color: var(--white);
      font-weight: 800;
      font-size: 1rem;
      letter-spacing: 0.02em;
      text-decoration: none;
      margin-right: auto;
      white-space: nowrap;
    }}

    .nav-brand span {{ opacity: 0.6; font-weight: 400; }}

    nav a.nav-link {{
      color: rgba(255,255,255,0.75);
      text-decoration: none;
      font-size: 0.88rem;
      font-weight: 500;
      padding: 0.4rem 0.85rem;
      border-radius: 6px;
      transition: background 0.15s, color 0.15s;
      white-space: nowrap;
    }}

    nav a.nav-link:hover,
    nav a.nav-link.active {{
      background: rgba(255,255,255,0.12);
      color: var(--white);
    }}

    header {{
      background: linear-gradient(135deg, var(--green-dark) 0%, var(--green-primary) 60%, var(--green-mid) 100%);
      color: var(--white);
      text-align: center;
      padding: 3rem 1.5rem 2.5rem;
      position: relative;
      overflow: hidden;
    }}

    .header-badge {{
      display: inline-block;
      background: rgba(255,255,255,0.15);
      border: 1px solid rgba(255,255,255,0.3);
      border-radius: 50px;
      padding: 0.35rem 1.1rem;
      font-size: 0.78rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 1rem;
      position: relative;
    }}

    header h1 {{
      font-size: clamp(1.6rem, 4vw, 2.8rem);
      font-weight: 800;
      letter-spacing: -0.01em;
      line-height: 1.2;
      text-shadow: 0 2px 8px rgba(0,0,0,0.25);
      position: relative;
    }}

    header h1 span {{
      display: block;
      font-size: clamp(1rem, 2.5vw, 1.5rem);
      font-weight: 400;
      opacity: 0.9;
      margin-top: 0.35rem;
    }}

    main {{
      max-width: 860px;
      margin: 0 auto;
      width: 100%;
      padding: 3.5rem 1.25rem 4rem;
      flex: 1;
      text-align: center;
    }}

    .results-section {{
      background: var(--white);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 2rem;
      margin-bottom: 2rem;
      text-align: left;
    }}

    .results-section h3 {{
      font-size: 1.1rem;
      font-weight: 700;
      color: var(--green-dark);
      margin-bottom: 1.5rem;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid var(--green-pale);
      text-align: center;
    }}

    .match-table {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 1.5rem;
      font-size: 0.9rem;
      border: 2px solid var(--green-primary);
    }}

    .match-table thead {{
      background: var(--green-primary);
      color: var(--white);
    }}

    .match-header-row {{
      background: var(--green-primary);
      color: var(--white);
    }}

    .match-header-cell {{
      padding: 0.75rem 1rem;
      text-align: center;
      border: 1px solid var(--white);
    }}

    .match-date {{
      font-weight: 600;
      margin-right: 1rem;
    }}

    .match-score {{
      background: var(--white);
      padding: 0.35rem 0.9rem;
      border-radius: 4px;
      font-weight: 700;
      color: var(--green-dark);
      display: inline-block;
      font-size: 1.1rem;
    }}

    .match-row {{
      background: var(--white);
    }}

    .team-cell {{
      padding: 0.6rem 0.75rem;
      text-align: left;
      border: 1px solid var(--green-primary);
    }}

    .team-left {{
      border-right: 2px solid var(--green-primary);
    }}

    .team-right {{
      border-left: 2px solid var(--green-primary);
    }}

    .team-name {{
      font-weight: 700;
      color: var(--green-dark);
      display: block;
    }}

    .team-players {{
      font-size: 0.78rem;
      color: #4a6a55;
      display: block;
    }}

    .score-cell {{
      width: 60px;
      text-align: center;
      font-weight: 700;
      font-size: 1.05rem;
      padding: 0.5rem 0;
      border: 1px solid var(--green-primary);
    }}

    .score-left {{
      border-right: 2px solid var(--green-primary);
    }}

    .score-right {{
      border-left: 2px solid var(--green-primary);
    }}

    .center-cell {{
      text-align: center;
      padding: 0.5rem 0.5rem;
      border: 1px solid var(--green-primary);
      background: var(--green-pale);
    }}

    .vs-text {{
      font-size: 0.65rem;
      color: var(--green-primary);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      display: block;
      margin-bottom: 0.25rem;
    }}

    .set-score {{
      font-size: 0.7rem;
      color: var(--green-primary);
      font-style: italic;
      display: block;
    }}

    footer {{
      text-align: center;
      padding: 1.5rem;
      background: var(--green-dark);
      color: rgba(255,255,255,0.6);
      font-size: 0.82rem;
    }}

    footer strong {{ color: rgba(255,255,255,0.85); }}
  </style>
</head>
<body>
    <nav>
    <a class="nav-brand" href="index.html">Winter Club <span>Paddle League</span></a>
    <a class="nav-link" href="index.html">Home</a>
    <a class="nav-link" href="rosters.html">Rosters</a>
    <a class="nav-link" href="schedule.html">Schedule</a>
    <a class="nav-link active" href="results.html">Results</a>
    <a class="nav-link" href="standings.html">Standings</a>
  </nav>
  <header>
    <div class="header-badge">Winter Club</div>
    <h1>
      Results
      <span>Men's Spring Paddle League 2026</span>
    </h1>
  </header>
  <main>
{main_content}
  </main>
  <footer>
    <strong>Winter Club</strong> &nbsp;·&nbsp; Men's Spring Paddle League 2026 &nbsp;·&nbsp; All rights reserved
  </footer>
</body>
</html>'''


def fetch_standings():
    """Fetch standings data from Google Sheets."""
    import os
    
    creds_file = "service-account-credentials.json"
    if not os.path.exists(creds_file):
        print("Service account credentials file not found. Skipping standings fetch.")
        print("To enable standings, create 'service-account-credentials.json' in the project root.")
        return None
    
    try:
        # Initialize Google Sheets client
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, SCOPES)
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        sheet = client.open_by_url(SPREADSHEET_URL)
        
        # Get the standings worksheet
        worksheet = sheet.worksheet(STANDINGS_WORKSHEET_NAME)
        
        # Fetch all data
        data = worksheet.get_all_values()
        
        if not data or len(data) < 2:
            print("No standings data found in the sheet.")
            return None
        
        # Extract headers from first row
        headers = data[0]
        
        # Extract rows (skip header)
        rows = data[1:]
        
        # Convert to list of dicts for easier processing
        standings = []
        for row in rows:
            entry = {}
            for i, header in enumerate(headers):
                value = row[i].strip() if i < len(row) else ""
                entry[header] = value
            standings.append(entry)
        
        return standings
    
    except Exception as e:
        print(f"Error fetching standings: {e}")
        return None


def generate_standings_html(standings):
    """Generate the standings.html content from standings data."""
    # Load the existing standings.html template
    standings_template_path = SCRIPT_DIR / "docs" / "standings.html"
    template = None
    
    if standings_template_path.exists():
        template = standings_template_path.read_text(encoding="utf-8")
    
    if template is None:
        return generate_minimal_standings_html(standings)
    
    # Generate the main content for standings
    main_content = generate_standings_main_content(standings)
    
    # Replace the <main> section content
    html_content = replace_main_content(template, main_content)
    
    return html_content


def generate_standings_main_content(standings):
    """Generate the main content HTML for standings page."""
    if not standings:
        return "    <p>No standings data available.</p>"
    
    # Get headers from the first entry, filtering out empty column headers
    headers = list(standings[0].keys())
    # Filter out empty/whitespace-only column names
    headers = [h for h in headers if h.strip()]
    
    # Skip the first column if it's numbered rank (#)
    # Check if first header is a rank/number column (commonly "#", "Rank", "Position", etc.)
    if headers and (headers[0] == "#" or headers[0].lower() in ["rank", "position", "num", "no"]):
        headers = headers[1:]
    
    main_content = []
    
    # Table header - use standings-table class to match the existing template
    main_content.append('      <table class="standings-table">')
    main_content.append('        <thead>')
    main_content.append('          <tr>')
    
    for header in headers:
        main_content.append(f'          <th style="text-align: center;">{header}</th>')
    
    main_content.append('          </tr>')
    main_content.append('        </thead>')
    main_content.append('        <tbody>')
    
    # Table rows
    for entry in standings:
        main_content.append('            <tr>')
        for header in headers:
            value = entry.get(header, "")
            main_content.append(f'              <td style="text-align: center;">{value}</td>')
        main_content.append('            </tr>')
    
    main_content.append('        </tbody>')
    main_content.append('      </table>')
    
    return "\n".join(main_content)


def generate_minimal_standings_html(standings):
    """Generate a minimal HTML template for standings when no template exists."""
    main_content = generate_standings_main_content(standings)
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Winter Club – Standings | Men's Spring Paddle League 2026</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --green-dark:    #1a4a2e;
      --green-primary: #2d6a4f;
      --green-mid:     #40916c;
      --green-light:   #74c69d;
      --green-pale:    #d8f3dc;
      --white:         #ffffff;
      --text-dark:     #1b2e22;
      --shadow:        0 4px 16px rgba(0,0,0,0.15);
      --radius:        10px;
    }}

    body {{
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: #f0f7f2;
      color: var(--text-dark);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    nav {{
      background: var(--green-dark);
      display: flex;
      align-items: center;
      padding: 0 1.5rem;
      height: 56px;
      gap: 0.25rem;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    }}

    .nav-brand {{
      color: var(--white);
      font-weight: 800;
      font-size: 1rem;
      letter-spacing: 0.02em;
      text-decoration: none;
      margin-right: auto;
      white-space: nowrap;
    }}

    .nav-brand span {{ opacity: 0.6; font-weight: 400; }}

    nav a.nav-link {{
      color: rgba(255,255,255,0.75);
      text-decoration: none;
      font-size: 0.88rem;
      font-weight: 500;
      padding: 0.4rem 0.85rem;
      border-radius: 6px;
      transition: background 0.15s, color 0.15s;
      white-space: nowrap;
    }}

    nav a.nav-link:hover,
    nav a.nav-link.active {{
      background: rgba(255,255,255,0.12);
      color: var(--white);
    }}

    header {{
      background: linear-gradient(135deg, var(--green-dark) 0%, var(--green-primary) 60%, var(--green-mid) 100%);
      color: var(--white);
      text-align: center;
      padding: 3rem 1.5rem 2.5rem;
      position: relative;
      overflow: hidden;
    }}

    .header-badge {{
      display: inline-block;
      background: rgba(255,255,255,0.15);
      border: 1px solid rgba(255,255,255,0.3);
      border-radius: 50px;
      padding: 0.35rem 1.1rem;
      font-size: 0.78rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      margin-bottom: 1rem;
      position: relative;
    }}

    header h1 {{
      font-size: clamp(1.6rem, 4vw, 2.8rem);
      font-weight: 800;
      letter-spacing: -0.01em;
      line-height: 1.2;
      text-shadow: 0 2px 8px rgba(0,0,0,0.25);
      position: relative;
    }}

    header h1 span {{
      display: block;
      font-size: clamp(1rem, 2.5vw, 1.5rem);
      font-weight: 400;
      opacity: 0.9;
      margin-top: 0.35rem;
    }}

    main {{
      max-width: 860px;
      margin: 0 auto;
      width: 100%;
      padding: 3.5rem 1.25rem 4rem;
      flex: 1;
      text-align: center;
    }}

    .standings-table-container {{
      background: var(--white);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
    }}

    .standings-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
    }}

    .standings-table thead {{
      background: var(--green-primary);
      color: var(--white);
    }}

    .standings-table th {{
      padding: 0.75rem 1rem;
      text-align: left;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.05em;
    }}

    .standings-table tbody tr {{
      border-bottom: 1px solid var(--green-pale);
    }}

    .standings-table tbody tr:hover {{
      background: var(--green-pale);
      opacity: 0.6;
    }}

    .standings-table td {{
      padding: 0.75rem 1rem;
      border: 1px solid var(--green-primary);
    }}

    .standings-table td:first-child {{
      font-weight: 600;
      color: var(--green-dark);
    }}

    footer {{
      text-align: center;
      padding: 1.5rem;
      background: var(--green-dark);
      color: rgba(255,255,255,0.6);
      font-size: 0.82rem;
    }}

    footer strong {{ color: rgba(255,255,255,0.85); }}
  </style>
</head>
<body>
  <nav>
    <a class="nav-brand" href="index.html">Winter Club <span>Paddle League</span></a>
    <a class="nav-link" href="index.html">Home</a>
    <a class="nav-link" href="rosters.html">Rosters</a>
    <a class="nav-link" href="schedule.html">Schedule</a>
    <a class="nav-link" href="results.html">Results</a>
    <a class="nav-link active" href="standings.html">Standings</a>
  </nav>
  <header>
    <div class="header-badge">Winter Club</div>
    <h1>
      Standings
      <span>Men's Spring Paddle League 2026</span>
    </h1>
  </header>
  <main>
{main_content}
  </main>
  <footer>
    <strong>Winter Club</strong> &nbsp;·&nbsp; Men's Spring Paddle League 2026 &nbsp;·&nbsp; All rights reserved
  </footer>
</body>
</html>'''


def main():
    """Main function to fetch and process results."""
    print("=" * 60)
    print("Google Sheets Results Fetcher")
    print("=" * 60)
    print()
    
    # Check for credentials file
    import os
    creds_file = "service-account-credentials.json"
    
    if not os.path.exists(creds_file):
        print(f"Service account credentials file not found: {creds_file}")
        print()
        print("To set up authentication, you have two options:")
        print()
        print("Option 1: Use Service Account (Recommended for production)")
        print("  1. Go to https://console.cloud.google.com/")
        print("  2. Create a new project or select existing one")
        print("  3. Go to API & Services > Credentials")
        print("  4. Click 'Create Credentials' > 'Service Account'")
        print("  5. Follow the wizard to create the service account")
        print("  6. Click 'Create Key' > 'JSON' and download the file")
        print("  7. Save it as 'service-account-credentials.json' in this directory")
        print("  8. Share your Google Sheet with the service account email")
        print()
        print("Option 2: Use OAuth (For local development)")
        print("  1. Run: pip install gspread oauth2client")
        print("  2. Run: python3 -m gspread.cli")
        print("  3. Follow the instructions to authenticate")
        print()
        print("Once credentials are set up, update the script to use them.")
        print()
        return
    
    try:
        # Initialize Google Sheets client
        print("Connecting to Google Sheets...")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, SCOPES)
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        print(f"Opening spreadsheet: {SPREADSHEET_URL}")
        sheet = client.open_by_url(SPREADSHEET_URL)
        
        # Get the worksheet
        print(f"Accessing worksheet: {WORKSHEET_NAME}")
        worksheet = sheet.worksheet(WORKSHEET_NAME)
        
        # Fetch all data
        print("Fetching data from sheet...")
        data = worksheet.get_all_values()
        
        if not data:
            print("No data found in the sheet.")
            return
        
        print(f"Retrieved {len(data)} rows")
        print()
        
        # Parse the data
        print("Parsing match results...")
        matches = parse_sheet_data(data)
        print(f"Found {len(matches)} week(s) of matches")
        print()
        
        # Generate HTML
        print("Generating results.html...")
        html_content = generate_results_html(matches)
        
        # Write to file
        RESULTS_HTML.write_text(html_content, encoding="utf-8")
        print(f"✓ Results written to: {RESULTS_HTML}")
        print()
        
        # Fetch and generate standings
        print("Fetching standings data...")
        standings = fetch_standings()
        
        if standings:
            print(f"Found {len(standings)} team(s) in standings")
            print("Generating standings.html...")
            standings_html = generate_standings_html(standings)
            STANDINGS_HTML.write_text(standings_html, encoding="utf-8")
            print(f"✓ Standings written to: {STANDINGS_HTML}")
            print()
        else:
            print("Standings data not available. Skipping standings generation.")
            print()
        
        print("Done! The results.html and standings.html files have been updated.")
        
    except Exception as e:
        print(f"Error: {e}")
        print()
        print("Common issues:")
        print("  - Sheet not shared with service account email")
        print("  - Incorrect worksheet name")
        print("  - Network connectivity issues")
        print("  - Invalid credentials file")


if __name__ == "__main__":
    main()