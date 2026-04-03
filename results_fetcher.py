#!/usr/bin/env python3
"""
Google Sheets Results Fetcher

Reads match results and standings from a Google Sheet and updates
results.html and standings.html with the data.

Supports multiple sites by loading configuration from config.json
Usage:
  python3 results_fetcher.py           # Process all sites from config
  python3 results_fetcher.py <site_id> # Process a specific site
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import json
import sys
from pathlib import Path

# Google Sheets configuration
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# File paths
SCRIPT_DIR = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "config.json"


def load_config():
    """Load configuration from config.json file."""
    if not CONFIG_FILE.exists():
        print(f"Error: Configuration file not found: {CONFIG_FILE}")
        return None
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config file: {e}")
        return None
    except Exception as e:
        print(f"Error reading config file: {e}")
        return None


def get_site_config(config, site_id):
    """Get configuration for a specific site by its ID."""
    for site in config.get('sites', []):
        if site.get('name') == site_id:
            return site
    return None


def get_credentials_file(config):
    """Get the credentials file path from config."""
    return config.get('default_credentials_file', 'service-account-credentials.json')


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


def load_html_template(output_folder=None):
    """Load the base HTML template from existing results.html file.
    
    Args:
        output_folder: The output folder path. If it's a league subfolder 
                       (not the root docs), returns None to avoid loading 
                       redirect content from docs/results.html
    """
    # If output folder is specified and is a league subfolder (contains wc-),
    # don't load the template with redirects
    if output_folder:
        folder_name = Path(output_folder).name
        # Check if this is a league subfolder (e.g., wc-mens-spring-26)
        if folder_name.startswith("wc-"):
            # For league subfolders, we don't want to load the redirect template
            return None
    
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


def remove_redirect_content(html_content):
    """Remove redirect meta tags and scripts from HTML content."""
    if not html_content:
        return html_content
    
    # Remove meta refresh tag
    html_content = re.sub(r'<meta\s+http-equiv="refresh"[^>]*>', '', html_content, flags=re.IGNORECASE)
    
    # Remove redirect script (look for window.location.href patterns)
    html_content = re.sub(r'<script>.*?window\.location\.href.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove "Redirecting..." title if present
    html_content = re.sub(r'<title>Redirecting\.\.\.</title>', '', html_content, flags=re.IGNORECASE)
    
    # Remove any remaining redirect paragraph
    html_content = re.sub(r'<p>If you are not redirected automatically.*?</p>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    return html_content


def replace_main_content(html_content, new_main_content):
    """Replace the content inside the <main> tag with new content."""
    # Pattern to match everything between <main> and </main> tags
    pattern = r'<main>.*?</main>'
    
    replacement = f'<main>\n{new_main_content}\n  </main>'
    
    # Use DOTALL flag to match across newlines
    result = re.sub(pattern, replacement, html_content, flags=re.DOTALL)
    
    return result


def generate_results_html(matches, league_name, output_folder=None):
    """Generate the complete results.html content from match data."""
    # Load the existing template
    template = load_html_template(output_folder)
    
    if template is None:
        # If no template exists, create a minimal one
        return generate_minimal_html(matches, league_name)
    
    # Generate the main content
    main_content = generate_main_content(matches)
    
    # Replace the <main> section content
    html_content = replace_main_content(template, main_content)
    
    # Ensure the style section exists (safety check)
    if '<style>' not in html_content:
        # Extract styles from minimal HTML and add them
        minimal_html = generate_minimal_html(matches, league_name)
        style_content = extract_style_content(minimal_html)
        if style_content:
            # Find </head> and insert style before it
            style_tag = f'  <style>\n{style_content}\n  </style>'
            html_content = html_content.replace('</head>', f'{style_tag}\n  </head>', 1)
    
    return html_content


def generate_minimal_html(matches, league_name):
    """Generate a minimal HTML template when no existing template exists."""
    main_content = generate_main_content(matches)
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Winter Club – Results | {league_name}</title>
  <link rel="stylesheet" href="../common.css" />
</head>
<body>
    <nav>
    <a class="nav-brand" href="../index.html">Winter Club <span>Paddle League</span></a>
    <a class="nav-link" href="index.html">Home</a>
    <a class="nav-link" href="schedule.html">Schedule</a>
    <a class="nav-link active" href="results.html">Results</a>
    <a class="nav-link" href="standings.html">Standings</a>
  </nav>
  <header>
    <div class="header-badge">Winter Club</div>
    <h1>
      Results
      <span>{league_name}</span>
    </h1>
  </header>
  <main>
{main_content}
  </main>
  <footer>
    <strong>Winter Club</strong> &nbsp;·&nbsp; {league_name} &nbsp;·&nbsp; All rights reserved
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


def generate_standings_html(standings, league_name, output_folder=None):
    """Generate the standings.html content from standings data."""
    # Load the existing standings.html template
    standings_template_path = SCRIPT_DIR / "docs" / "standings.html"
    template = None

    # Don't use the redirect template for league subfolders
    if output_folder and Path(output_folder).name.startswith("wc-"):
        template = None
    elif standings_template_path.exists():
        template = standings_template_path.read_text(encoding="utf-8")

    if template is None:
        return generate_minimal_standings_html(standings, league_name)
    
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
    first_col = headers[0] if headers else None
    for entry in standings:
        main_content.append('            <tr>')
        for header in headers:
            value = entry.get(header, "")
            if header == first_col and value:
                slug = value.lower().replace(' ', '-')
                cell = f'<a href="{slug}.html">{value}</a>'
            else:
                cell = value
            main_content.append(f'              <td style="text-align: center;">{cell}</td>')
        main_content.append('            </tr>')
    
    main_content.append('        </tbody>')
    main_content.append('      </table>')
    
    return "\n".join(main_content)


def generate_minimal_standings_html(standings, league_name):
    """Generate a minimal HTML template for standings when no template exists."""
    main_content = generate_standings_main_content(standings)
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Winter Club – Standings | {league_name}</title>
  <link rel="stylesheet" href="../common.css" />
</head>
<body>
  <nav>
    <a class="nav-brand" href="../index.html">Winter Club <span>Paddle League</span></a>
    <a class="nav-link" href="index.html">Home</a>
    <a class="nav-link" href="schedule.html">Schedule</a>
    <a class="nav-link" href="results.html">Results</a>
    <a class="nav-link active" href="standings.html">Standings</a>
  </nav>
  <header>
    <div class="header-badge">Winter Club</div>
    <h1>
      Standings
      <span>{league_name}</span>
    </h1>
  </header>
  <main>
{main_content}
  </main>
  <footer>
    <strong>Winter Club</strong> &nbsp;·&nbsp; {league_name} &nbsp;·&nbsp; All rights reserved
  </footer>
</body>
</html>'''


def generate_team_left_column(rows):
    """Generate HTML for the left column (columns A-D) of a team page."""
    if not rows:
        return ''

    parts = []
    in_table = False

    for row in rows[1:2] + rows[3:]:
        cells = [row[i].strip() if i < len(row) else '' for i in range(4)]

        if not any(cells):
            continue

        # Label row: only column A has content
        is_label = bool(cells[0]) and not any(cells[1:])

        if is_label:
            if in_table:
                parts.append(f'  <tr class="team-sub-label"><td colspan="4">{cells[0]}</td></tr>')
            else:
                parts.append(f'<h3 class="team-section-label">{cells[0]}</h3>')
        else:
            if not in_table:
                # First data row after a section label becomes the table header
                parts.append('<table class="team-table"><thead><tr>')
                for cell in cells:
                    parts.append(f'  <th>{cell}</th>')
                parts.append('</tr></thead><tbody>')
                in_table = True
            else:
                parts.append('<tr>')
                for cell in cells:
                    parts.append(f'  <td>{cell}</td>')
                parts.append('</tr>')

    if in_table:
        parts.append('</tbody></table>')

    return '\n'.join(parts)


def generate_team_right_column(rows):
    """Generate HTML for the right column (columns F-H, rows 3-10) of a team page."""
    # Rows 3-10 (1-indexed) = indices 2-9; columns F-H = indices 5-7
    if len(rows) < 3:
        return ''

    right_rows = rows[2:10]
    col_indices = [5, 6, 7]

    parts = ['<table class="team-table">']
    for i, row in enumerate(right_rows):
        cells = [row[j].strip() if j < len(row) else '' for j in col_indices]
        if i == 0:
            parts.append('<thead><tr>')
            for cell in cells:
                parts.append(f'  <th>{cell}</th>')
            parts.append('</tr></thead><tbody>')
        else:
            parts.append('<tr>')
            for cell in cells:
                parts.append(f'  <td>{cell}</td>')
            parts.append('</tr>')
    parts.append('</tbody></table>')

    return '\n'.join(parts)


def generate_team_html(tab_name, title_html, left_html, right_html, league_name):
    """Generate the full HTML page for a team."""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{tab_name} | {league_name}</title>
  <link rel="stylesheet" href="../common.css" />
  <style>
    .team-page {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 2rem;
      align-items: start;
    }}
    .team-title-row {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 1.5rem;
      padding-bottom: 0.75rem;
      border-bottom: 2px solid var(--green-pale);
    }}
    .team-title {{
      font-size: 1.3rem;
      font-weight: 700;
      color: var(--green-dark);
    }}
    .team-pts {{
      font-size: 1rem;
      font-weight: 600;
      color: var(--green-primary);
    }}
    .team-section-label {{
      font-size: 1rem;
      font-weight: 700;
      color: var(--green-dark);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin: 1.25rem 0 0.5rem;
    }}
    .team-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.9rem;
      background: var(--white);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow: hidden;
    }}
    .team-table thead {{
      background: var(--green-primary);
      color: var(--white);
    }}
    .team-table th {{
      padding: 0.65rem 0.9rem;
      text-align: left;
      font-weight: 600;
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .team-table td {{
      padding: 0.55rem 0.9rem;
      border-bottom: 1px solid var(--green-pale);
      color: var(--text-dark);
    }}
    .team-table tbody tr:last-child td {{ border-bottom: none; }}
    .team-table tbody tr:hover {{ background: var(--green-pale); }}
    .team-sub-label td {{
      background: var(--green-pale);
      font-weight: 600;
      color: var(--green-dark);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: 0.4rem 0.9rem;
    }}
    @media (max-width: 700px) {{
      .team-page {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <nav>
    <a class="nav-brand" href="../index.html">Winter Club <span>Paddle League</span></a>
    <a class="nav-link" href="index.html">Home</a>
    <a class="nav-link" href="schedule.html">Schedule</a>
    <a class="nav-link" href="results.html">Results</a>
    <a class="nav-link" href="standings.html">Standings</a>
  </nav>
  <header>
    <div class="header-badge">Winter Club</div>
    <h1>
      {tab_name}
      <span>{league_name}</span>
    </h1>
  </header>
  <main>
{title_html}
    <div class="team-page">
      <div class="team-left-col">
{left_html}
      </div>
      <div class="team-right-col">
{right_html}
      </div>
    </div>
  </main>
  <footer>
    <strong>Winter Club</strong> &nbsp;·&nbsp; {league_name} &nbsp;·&nbsp; All rights reserved
  </footer>
</body>
</html>'''


def process_team_sheets(sheet, league_name, output_path):
    """Find all Team* worksheets and generate individual team HTML pages."""
    worksheets = sheet.worksheets()
    team_sheets = [ws for ws in worksheets if ws.title.startswith('Team')]

    if not team_sheets:
        print("  No team worksheets found.")
        return

    print(f"  Found {len(team_sheets)} team worksheet(s)")

    for ws in team_sheets:
        tab_name = ws.title
        slug = tab_name.lower().replace(' ', '-')
        output_file = output_path / f"{slug}.html"

        print(f"  Processing: {tab_name}")
        data = ws.get_all_values()

        if not data:
            print(f"    No data found, skipping.")
            continue

        # Find last non-empty row in columns A-D
        last_row_idx = 0
        for i, row in enumerate(data):
            if any(cell.strip() for cell in row[:4]):
                last_row_idx = i

        # Build title HTML from row 1 (spans both columns)
        row1 = data[0] if data else []
        team_name = row1[0].strip() if len(row1) > 0 else ''
        pts_label = row1[2].strip() if len(row1) > 2 else ''
        pts_value = row1[3].strip() if len(row1) > 3 else ''
        pts_display = f'{pts_label} {pts_value}'.strip()
        pts_span = f'  <span class="team-pts">{pts_display}</span>' if pts_display else ''
        title_html = f'    <div class="team-title-row">\n  <span class="team-title">{team_name}</span>\n{pts_span}\n    </div>'

        left_rows = data[:last_row_idx + 1]
        left_html = generate_team_left_column(left_rows)
        right_html = generate_team_right_column(data)

        html = generate_team_html(tab_name, title_html, left_html, right_html, league_name)
        output_file.write_text(html, encoding='utf-8')
        print(f"    ✓ Written to: {output_file}")


def process_site(site_config, creds_file):
    """Process a single site using its configuration."""
    import os
    
    site_name = site_config.get('name', 'unknown')
    league_name = site_config.get('league_name', '')
    spreadsheet_url = site_config.get('spreadsheet_url', '')
    output_folder = site_config.get('output_folder', 'docs')
    results_worksheet = site_config.get('results_worksheet', 'Results')
    standings_worksheet = site_config.get('standings_worksheet', 'Standings')
    
    # Set up output paths
    output_path = SCRIPT_DIR / output_folder
    results_html_path = output_path / "results.html"
    standings_html_path = output_path / "standings.html"
    
    print(f"\nProcessing site: {site_name}")
    print("-" * 40)
    
    # Check if output directory exists
    if not output_path.exists():
        print(f"Error: Output directory does not exist: {output_path}")
        return False
    
    # Verify credentials file exists
    if not os.path.exists(creds_file):
        print(f"Warning: Credentials file not found: {creds_file}")
        print("Skipping this site. Please set up credentials first.")
        return False
    
    try:
        # Initialize Google Sheets client
        print(f"Connecting to Google Sheets...")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, SCOPES)
        client = gspread.authorize(creds)
        
        # Open the spreadsheet
        print(f"Opening spreadsheet: {spreadsheet_url}")
        sheet = client.open_by_url(spreadsheet_url)
        
        # Get the results worksheet
        print(f"Accessing worksheet: {results_worksheet}")
        worksheet = sheet.worksheet(results_worksheet)
        
        # Fetch all data
        print("Fetching data from sheet...")
        data = worksheet.get_all_values()
        
        if not data:
            print("No data found in the sheet.")
            return False
        
        print(f"Retrieved {len(data)} rows")
        
        # Parse the data
        print("Parsing match results...")
        matches = parse_sheet_data(data)
        print(f"Found {len(matches)} week(s) of matches")
        
        # Generate HTML
        print("Generating results.html...")
        html_content = generate_results_html(matches, league_name, output_folder)
        
        # Write to file
        results_html_path.write_text(html_content, encoding="utf-8")
        print(f"✓ Results written to: {results_html_path}")
        
        # Fetch and generate standings
        print("Fetching standings data...")
        
        try:
            standings_sheet = sheet.worksheet(standings_worksheet)
            standings_data = standings_sheet.get_all_values()
            
            if standings_data and len(standings_data) >= 2:
                # Extract headers from first row
                headers = standings_data[0]
                
                # Extract rows (skip header)
                rows = standings_data[1:]
                
                # Convert to list of dicts for easier processing
                standings = []
                for row in rows:
                    entry = {}
                    for i, header in enumerate(headers):
                        value = row[i].strip() if i < len(row) else ""
                        entry[header] = value
                    standings.append(entry)
                
                if standings:
                    print(f"Found {len(standings)} team(s) in standings")
                    print("Generating standings.html...")
                    standings_html = generate_standings_html(standings, league_name, output_folder)
                    standings_html_path.write_text(standings_html, encoding="utf-8")
                    print(f"✓ Standings written to: {standings_html_path}")
                else:
                    print("No standings data available.")
            else:
                print("No standings data found in the sheet.")
        except Exception as e:
            print(f"Standings processing skipped: {e}")
        
        # Process team sheets
        print("Processing team sheets...")
        try:
            process_team_sheets(sheet, league_name, output_path)
        except Exception as e:
            print(f"Team sheet processing skipped: {e}")

        print(f"✓ Site '{site_name}' processed successfully!")
        return True
        
    except Exception as e:
        print(f"Error processing site '{site_name}': {e}")
        print("Common issues:")
        print("  - Sheet not shared with service account email")
        print("  - Incorrect worksheet name")
        print("  - Network connectivity issues")
        print("  - Invalid credentials file")
        return False


def main():
    """Main function to fetch and process results."""
    import os
    
    print("=" * 60)
    print("Google Sheets Results Fetcher")
    print("=" * 60)
    
    # Load configuration
    config = load_config()
    if config is None:
        return
    
    # Get credentials file from config
    creds_file = get_credentials_file(config)
    creds_file_path = SCRIPT_DIR / creds_file
    
    # Determine which sites to process
    site_arg = None
    if len(sys.argv) > 1:
        site_arg = sys.argv[1]
    
    # Process sites
    if site_arg:
        # Process a specific site
        site_config = get_site_config(config, site_arg)
        if site_config is None:
            print(f"\nError: Site '{site_arg}' not found in config.")
            print(f"\nAvailable sites:")
            for site in config.get('sites', []):
                print(f"  - {site.get('name', 'unknown')}")
            return
        
        # Check credentials file
        if not creds_file_path.exists():
            print(f"Credentials file not found: {creds_file_path}")
            return
        
        process_site(site_config, str(creds_file_path))
    else:
        # Process all sites
        print("\nLoading configuration...")
        sites = config.get('sites', [])
        
        if not sites:
            print("No sites found in configuration file.")
            return
        
        print(f"Found {len(sites)} site(s) to process")
        
        # Check credentials file
        if not creds_file_path.exists():
            print(f"\nCredentials file not found: {creds_file_path}")
            print("\nTo set up authentication, you have two options:")
            print("\nOption 1: Use Service Account (Recommended for production)")
            print("  1. Go to https://console.cloud.google.com/")
            print("  2. Create a new project or select existing one")
            print("  3. Go to API & Services > Credentials")
            print("  4. Click 'Create Credentials' > 'Service Account'")
            print("  5. Follow the wizard to create the service account")
            print("  6. Click 'Create Key' > 'JSON' and download the file")
            print(f"  7. Save it as '{creds_file}' in this directory")
            print("  8. Share your Google Sheet with the service account email")
            print("\nOption 2: Use OAuth (For local development)")
            print("  1. Run: pip install gspread oauth2client")
            print("  2. Run: python3 -m gspread.cli")
            print("  3. Follow the instructions to authenticate")
            return
        
        success_count = 0
        for site in sites:
            if process_site(site, str(creds_file_path)):
                success_count += 1
        
        print("\n" + "=" * 60)
        print(f"Completed processing {success_count}/{len(sites)} site(s)")
        print("=" * 60)


if __name__ == "__main__":
    main()
