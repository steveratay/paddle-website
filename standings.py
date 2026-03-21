import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import json
import sys
from pathlib import Path
from jinja2 import Template

# Google Sheets setup
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


def get_site_config(config, site_id):
    """Get configuration for a specific site by its ID."""
    for site in config.get('sites', []):
        if site.get('name') == site_id:
            return site
    return None


def get_credentials_file(config):
    """Get the credentials file path from config."""
    return config.get('default_credentials_file', 'service-account-credentials.json')

def fetch_standings(site_config):
    """Fetch standings data from Google Sheets using site configuration."""
    creds_file = get_credentials_file({'default_credentials_file': 'service-account-credentials.json'})
    
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, SCOPES)
        client = gspread.authorize(creds)
        
        # Open spreadsheet
        spreadsheet_url = site_config.get('spreadsheet_url', '')
        sheet = client.open_by_url(spreadsheet_url)
        
        # Get standings worksheet (default to 'Standings')
        standings_worksheet = site_config.get('standings_worksheet', 'Standings')
        worksheet = sheet.worksheet(standings_worksheet)
        data = worksheet.get_all_values()
        
        if not data or len(data) < 2:
            return None
        
        # Extract headers from first row
        headers = data[0]
        
        # Extract rows (skip header)
        rows = data[1:]
        
        # Convert to DataFrame
        standings = pd.DataFrame(rows, columns=headers)
        return standings
        
    except Exception as e:
        print(f"Error fetching standings: {e}")
        return None

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Standings</title>
    <style>
        table { width: 100%; border-collapse: collapse; }
        th, td { border: 1px solid black; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>Standings</h1>
    <table>
        <tr>
            {% for column in headers %}
                <th>{{ column }}</th>
            {% endfor %}
        </tr>
        {% for row in standings %}
        <tr>
            {% for cell in row %}
                <td>{{ cell }}</td>
            {% endfor %}
        </tr>
        {% endfor %}
    </table>
</body>
</html>
"""

def generate_html(standings):
    template = Template(HTML_TEMPLATE)
    html_content = template.render(headers=standings.columns, standings=standings.values.tolist())
    with open("standings.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("standings.html has been created!")

def main():
    """Main function to run the standings generator."""
    # Load configuration
    config = load_config()
    if not config:
        print("Failed to load configuration.")
        sys.exit(1)
    
    # Get default site or site from command line argument
    site_id = sys.argv[1] if len(sys.argv) > 1 else None
    site_config = None
    
    if site_id:
        site_config = get_site_config(config, site_id)
        if not site_config:
            print(f"Error: Site '{site_id}' not found in configuration.")
            print(f"Available sites: {', '.join([s.get('name', 'unnamed') for s in config.get('sites', [])])}")
            sys.exit(1)
    else:
        # Use default site if available
        default_site = config.get('default_site')
        if default_site:
            site_config = get_site_config(config, default_site)
        else:
            # Use first site if available
            sites = config.get('sites', [])
            if sites:
                site_config = sites[0]
            else:
                print("Error: No sites defined in configuration.")
                sys.exit(1)
    
    # Fetch standings data
    standings = fetch_standings(site_config)
    if standings is None:
        print("Failed to fetch standings data.")
        sys.exit(1)
    
    # Get output directory
    docs_dir = config.get('docs_dir', 'docs')
    output_dir = Path(docs_dir) / site_config.get('output_folder', site_id)
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate HTML
    html_content = generate_html(standings)
    output_file = output_dir / "standings.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"{output_file} has been created!")


def generate_html(standings):
    """Generate HTML content from standings data."""
    template = Template(HTML_TEMPLATE)
    html_content = template.render(headers=standings.columns, standings=standings.values.tolist())
    return html_content


if __name__ == "__main__":
    main()
