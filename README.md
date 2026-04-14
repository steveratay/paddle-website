# paddle-website

Website for paddle tennis leagues. Match results and standings are pulled from Google Sheets and committed as static HTML files.

## How results are updated

Editing a Google Sheet triggers a GitHub Actions workflow that runs `results_fetcher.py` and commits the updated HTML files automatically.

### Flow

```
Edit Google Sheet → Apps Script (debounced 30s) → GitHub Actions workflow_dispatch →
  results_fetcher.py runs → updated HTML committed to docs/
```

---

## Setup

### 1. GitHub repository secret

Add the contents of `service-account-credentials.json` as a repository secret:

- Go to **Settings > Secrets and variables > Actions**
- Name: `GOOGLE_CREDENTIALS`
- Value: paste the full JSON contents of the service account credentials file

### 2. GitHub Personal Access Token (PAT)

The Apps Script needs a PAT to trigger the workflow:

- Go to `github.com/settings/tokens` → **Generate new token (classic)**
- Scopes: check only `workflow`
- Copy the token — you'll paste it into the Apps Script below

### 3. Apps Script (add to each Google Sheet)

For each spreadsheet, open **Extensions > Apps Script** and paste this script. Set `GITHUB_TOKEN` to your PAT.

```javascript
const GITHUB_TOKEN = "ghp_YOUR_TOKEN_HERE";
const REPO = "steveratay/paddle-website";
const WORKFLOW = "update-results.yml";
const BRANCH = "main";
const DEBOUNCE_SECONDS = 30;

function onSheetEdit(e) {
  // Delete any pending trigger
  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (trigger.getHandlerFunction() === "triggerGitHubWorkflow") {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  // Schedule a new one 30 seconds from now
  ScriptApp.newTrigger("triggerGitHubWorkflow")
    .timeBased()
    .after(DEBOUNCE_SECONDS * 1000)
    .create();
}

function triggerGitHubWorkflow() {
  // Clean up this trigger before firing
  ScriptApp.getProjectTriggers().forEach(trigger => {
    if (trigger.getHandlerFunction() === "triggerGitHubWorkflow") {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  const url = `https://api.github.com/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`;
  const options = {
    method: "post",
    headers: {
      "Authorization": "Bearer " + GITHUB_TOKEN,
      "Accept": "application/vnd.github+json",
      "Content-Type": "application/json"
    },
    payload: JSON.stringify({ ref: BRANCH }),
    muteHttpExceptions: true
  };

  const response = UrlFetchApp.fetch(url, options);
  console.log("GitHub response: " + response.getResponseCode());
}
```

After saving the script, update the `appsscript.json` manifest (enable it via **Project Settings > Show "appsscript.json" manifest file in editor**):

```json
{
  "timeZone": "America/New_York",
  "dependencies": {},
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "oauthScopes": [
    "https://www.googleapis.com/auth/script.scriptapp",
    "https://www.googleapis.com/auth/spreadsheets.currentonly",
    "https://www.googleapis.com/auth/script.external_request"
  ]
}
```

Then set up an installable trigger:

- Click the **Triggers** icon (clock) in the left sidebar
- **Add Trigger** → function: `onSheetEdit`, event source: `From spreadsheet`, event type: `On edit`
- Save and authorize when prompted (you'll see an "unverified app" warning — click **Advanced > Go to [project] (unsafe) > Allow**)

> **Note:** The function is named `onSheetEdit` rather than `onEdit` intentionally. Google's built-in simple trigger (`onEdit`) runs in a restricted sandbox that blocks `ScriptApp` calls. An installable trigger pointing to any other function name runs with full authorization and works correctly.

The debounce means the workflow only fires once editing stops for 30 seconds, preventing a flood of jobs during data entry.

### 4. GitHub Actions workflow

The workflow file is at `.github/workflows/update-results.yml`. It runs `results_fetcher.py`, then commits any changed files in `docs/`. Concurrent runs are cancelled so only the latest sheet data wins.

---

## Running locally

```bash
pip install -r requirements.txt
python3 results_fetcher.py
```

Credentials file `service-account-credentials.json` must be present in the project root (not committed to git).
