import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from jinja2 import Template

# Google Sheets setup
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = "path/to/your/service-account-file.json"  # Update with your credentials file
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1fzSLekV44ejYraB4hySVQNS4n0HLCNh44RCEUneZoWs/edit"

def fetch_standings():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    client = gspread.authorize(creds)
    
    # Open spreadsheet
    sheet = client.open_by_url(SPREADSHEET_URL)
    worksheet = sheet.worksheet("Standings")
    data = worksheet.get_all_values()
    
    # Convert to DataFrame
    headers = data[0]
    standings = pd.DataFrame(data[1:], columns=headers)
    return standings

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

if __name__ == "__main__":
    standings = fetch_standings()
    generate_html(standings)
