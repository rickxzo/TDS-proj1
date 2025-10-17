from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import json
import time
import base64
import threading

import replicate


# Load environment variables from a .env file (if present)
load_dotenv()

# Read tokens from environment; functions will re-check env if needed
AIPIPE_TOKEN = os.getenv("AIPIPE_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

class TextAgent():
    def __init__(self, model_name, system_prompt):
        self.model_name = model_name
        self.system_prompt = system_prompt
    def gen(self, prompt):
        input = {
            "prompt": prompt,
            "system_prompt": self.system_prompt
        }
        x = ''
        for event in replicate.stream(
            self.model_name,
            input=input
        ):
            x+=str(event)
        return x
    
Init_Model = TextAgent(
    "openai/gpt-5",
    '''
    Provided an json body, consisting of project requirements and checks, 
    generate a json payload that can be used to create a GitHub repository via the GitHub API.
    The JSON payload should include relevant fields such as:
    - name: The name of the repository
    - description: A brief description of the repository
    - private: Set to false
    - auto_init: Set to true
    - license_template: according to checks

    Return the answer in JSON format only.
    '''
)

Coder_Model = TextAgent(
    "openai/gpt-5",
    '''
    You are a coding assistant. Given a project brief, write a python program to implement the project.
    Return only the code, no explanations.
    '''
)

app = Flask(__name__)


def get_init(req):
    """Call the external AI service. Returns a parsed JSON or an error dict."""
    token = os.getenv("AIPIPE_KEY") or AIPIPE_TOKEN
    if not token:
        return {"error": "AIPIPE_KEY not set"}

    print("\n\nAbout to sent request to AI service.")

    resp = Init_Model.gen(f"{req}")
from flask import Flask, request, jsonify
import requests
import os
from dotenv import load_dotenv
import json
import base64

import replicate


# Load environment variables from a .env file (if present)
load_dotenv()

# Read tokens from environment; functions will re-check env if needed
AIPIPE_TOKEN = os.getenv("AIPIPE_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SECRET_KEY = os.getenv("SECRET_KEY")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")


class TextAgent():
    def __init__(self, model_name, system_prompt):
        self.model_name = model_name
        self.system_prompt = system_prompt

    def gen(self, prompt):
        input = {
            "prompt": prompt,
            "system_prompt": self.system_prompt
        }
        x = ''
        for event in replicate.stream(self.model_name, input=input):
            x += str(event)
        return x

    
Init_Model = TextAgent(
    "openai/gpt-5",
    '''
    Provided an json body, consisting of project requirements and checks, 
    generate a json payload that can be used to create a GitHub repository via the GitHub API.
    The JSON payload should include relevant fields such as:
    - name: The name of the repository
    - description: A brief description of the repository
    - private: Set to false
    - auto_init: Set to false
    - license_template: according to checks

    Return the answer in JSON format only.
    Note: 
    - To the name, add a 4 letter hash suffix to ensure uniqueness.
    - The description is the readme of the project. Make sure it is well written and professional. Abide by the checks in case any additional requirements are specified.
    The description should not be more than 300 characters.
    '''
)

Coder_Model = TextAgent(
    "openai/gpt-5",
    '''
    You are a coding assistant. Given a project brief, write a html + js file to implement the project.
    Return only the code, no explanations.
    Pay special attention to the checks as they are the evaluation metric.
    Example:
    - If a check states "Page displays captcha URL passed at ?url=... as well as the solved text", 
    ensure the code includes logic to read the URL parameter and display the output.
    The web page depending on input fields would not pass the checks in this scenario.

    '''
)

Readme_Model = TextAgent(
    "openai/gpt-5",
    '''
    You are a coding assistant. Given a project brief, write a professional README.md file for the project.
    Return only the markdown content, no explanations.
    '''
)

app = Flask(__name__)


def get_init(req):
    """Call the external AI service. Returns a parsed JSON or an error dict."""
    token = os.getenv("AIPIPE_KEY") or AIPIPE_TOKEN
    if not token:
        return {"error": "AIPIPE_KEY not set"}

    print("\n\nAbout to send request to AI service.")

    resp = Init_Model.gen(f"{req}")

    print(resp)
    return resp


def make_repo(payload):
    """Create a GitHub repository using provided payload. Returns (status_code, json_or_text)."""
    token = os.getenv("GITHUB_TOKEN") or GITHUB_TOKEN
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    resp = requests.post("https://api.github.com/user/repos", json=payload, headers=headers)
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, {"text": resp.text}

def commit_readme(repo_full_name, code):
    token = os.getenv("GITHUB_TOKEN") or GITHUB_TOKEN
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    url = f"https://api.github.com/repos/{repo_full_name}/contents/README.md"
    # GitHub expects the file content to be base64 encoded
    content_b64 = base64.b64encode(code.encode("utf-8")).decode("utf-8")

    payload = {
        "message": "Initial commit with generated README",
        "content": content_b64
    }
    resp = requests.put(url, json=payload, headers=headers)
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, {"text": resp.text}

def commit_code(repo_full_name, code):
    token = os.getenv("GITHUB_TOKEN") or GITHUB_TOKEN
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if token:
        headers["Authorization"] = f"token {token}"

    url = f"https://api.github.com/repos/{repo_full_name}/contents/index.html"
    # GitHub expects the file content to be base64 encoded
    if isinstance(code, str):
        content_b64 = base64.b64encode(code.encode("utf-8")).decode("utf-8")
    else:
        # fallback: convert to string then encode
        content_b64 = base64.b64encode(str(code).encode("utf-8")).decode("utf-8")

    payload = {
        "message": "Initial commit with generated code",
        "content": content_b64
    }
    resp = requests.put(url, json=payload, headers=headers)
    try:
        return resp.status_code, resp.json()
    except ValueError:
        return resp.status_code, {"text": resp.text}


def build(data):
    

    resp = get_init(data)
    print("AI Response:", resp)

    # Try to parse AI response as JSON for repo creation
    repo_payload = None
    try:
        if isinstance(resp, dict):
            repo_payload = resp
        else:
            repo_payload = json.loads(resp)
    except Exception as e:
        print('Could not parse AI response as JSON:', e)
        return jsonify({"error": "AI response not valid JSON", "ai_response": str(resp)}), 500

    make_repo_status, make_repo_resp = make_repo(repo_payload)
    print("Make Repo Response:", make_repo_status, make_repo_resp)

    readme = Readme_Model.gen(f"Write a professional README.md for the project with brief: {data.get('brief')} and checks: {data.get('checks')}")
    print("Generated README:")
    print(readme)

    code = Coder_Model.gen(f"Write a html + js file to implement the project with brief: {data.get('brief')} and checks: {data.get('checks')}")
    print("Generated code:")
    print(code)

    repo_full_name = make_repo_resp.get("full_name") if isinstance(make_repo_resp, dict) else None
    if not repo_full_name:
        print('No repo full_name returned; skipping commit')
        commit_status, commit_resp = None, {"error": "no repo created"}
    else:
        commit_status, commit_resp = commit_code(repo_full_name, code)
        readme_status, readme_resp = commit_readme(repo_full_name, readme)
        print("Commit README Response:", readme_status, readme_resp)
    print("Commit Code Response:", commit_status, commit_resp)

    OWNER = "rickxzo"
    REPO = repo_payload.get("name")
    BRANCH = "main"
    PATH = "/"

    url = f"https://api.github.com/repos/{OWNER}/{REPO}/pages"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json"
    }
    data2 = {
        "source": {
            "branch": BRANCH,
            "path": PATH
        }
    }

    print("requesting gh pages")
    # === Send request ===
    response = requests.post(url, headers=headers, json=data2)
    print("GitHub Pages Response:", response.status_code, response.json())

    if response.status_code == 201:
        print("GitHub Pages created successfully")

    email = data.get("email")
    task = data.get("task")
    round = data.get("round")
    nonce = data.get("nonce")
    repo_url = f"https://github.com/{OWNER}/{REPO}"
    pages_url = f"https://{OWNER}.github.io/{REPO}/"
    commit_sha = commit_resp["content"]["sha"]

    payload = {
        "email": email,
        "secret": SECRET_KEY,
        "task": task,
        "round": round,
        "nonce": nonce,
        "repo_url": repo_url,
        "pages_url": pages_url,
        "commit_sha": commit_sha
    }
    evaluation_url = data.get("evaluation_url")
    print(data)
    print(payload)
    time.sleep(180)
    max_attempts = 5
    delay = 1  # start with 1 second

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.post(
                evaluation_url,
                headers=headers,
                data=json.dumps(payload),
                timeout=10
            )

            if response.status_code == 200:
                print(f"✅ Success on attempt {attempt}")
                print("Response:", response.text)
                break  # exit loop on success
            else:
                print(f"⚠️ Attempt {attempt} failed with status {response.status_code}")
                print("Response body:", response.text)

        except requests.RequestException as e:
            print(f"❌ Attempt {attempt} error: {e}")

        if attempt < max_attempts:
            print(f"Retrying in {delay} second(s)...")
            time.sleep(delay)
            delay *= 2  # double the delay each time
    else:
        print("🚫 All attempts failed after backoff retries.")

    return jsonify({"status": "ok", "ai_response": repo_payload, "make_repo": make_repo_resp, "commit": commit_resp}), 200

@app.route("/verify", methods=['GET', 'POST'])
def verify():
    if request.method == 'GET':
        return jsonify({"message": "POST JSON to this endpoint. Expecting 'secret', 'checks', and 'brief' fields."}), 200

    # POST handling
    data = request.get_json(silent=True)
    print('--- /build request received ---')
    print('Headers:')
    # print relevant headers for debugging (avoid printing very large secrets)
    try:
        headers = dict(request.headers)
        print(headers)
    except Exception:
        print('Could not read headers')

    print('JSON body:')
    print(data)

    if not data:
        return jsonify({"error": "Missing or invalid JSON body"}), 400

    # Validate secret
    if SECRET_KEY and data.get("secret") != SECRET_KEY:
        print('Invalid secret provided:', data.get('secret'))
        return jsonify({"error": "Invalid secret"}), 403

    thread = threading.Thread(target=build, args=(data,), daemon=True)
    thread.start()
    return jsonify({"status": "ok", "message": "Verification endpoint reached"}), 200

if __name__ == '__main__':
    # Use PORT env if provided (useful for deployments); bind to 0.0.0.0 for container friendliness
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)