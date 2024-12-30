import os
import subprocess
import shutil
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_project_root():
    result = subprocess.check_output("git rev-parse --show-toplevel", shell=True).decode('utf-8')
    return result.strip()

ROOT = get_project_root()
GITHUB_API_URL = "https://api.github.com/user/repos"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN not found in .env file")

def create_new_github_repo(new_repo_name):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "name": new_repo_name,
        "description": "We have fixed your repository!",
        "private": False,
        "auto_init": True
    }
    response = requests.post(GITHUB_API_URL, json=data, headers=headers)
    if response.status_code == 201:
        print(f"Repository '{new_repo_name}' created successfully.")
        return True
    else:
        print(f"Failed to create repository: {response.status_code}")
        print(response.json())
        return False

def build_check():
    # FIXME: Replace with actual function logic
    success = True
    fixed = True
    json_data = {}
    return success, fixed, json_data

def check_if_repo_exists(repo_name):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.get(f"https://api.github.com/repos/grimrepor/{repo_name}", headers=headers)
    return response.status_code == 200

def get_default_branch(repo_path):
    try:
        # Get the current branch name
        result = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=repo_path
        ).decode('utf-8').strip()
        print(f"Current branch is: {result}")
        return result
    except Exception as e:
        print(f"Error getting branch name: {e}")
        return "master"  # fallback to master if command fails

def process_repository(repo_url):
    try:
        # Clean up the URL
        repo_url = repo_url.rstrip('/')
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]

        # Extract the repository name from the URL
        repo_name = os.path.basename(repo_url)
        username = repo_url.split("/")[-2]
        new_repo_name = f"{username}_{repo_name}"

        # Create a new directory for the repo
        repo_dir = os.path.join(ROOT, "output", f"{repo_name}_dir")
        
        # Remove the directory if it exists
        if os.path.exists(repo_dir):
            print(f"Removing existing directory: {repo_dir}")
            shutil.rmtree(repo_dir)
        
        # Create fresh directory
        os.makedirs(repo_dir, exist_ok=True)
        os.chdir(repo_dir)

        # Clone the repository
        clone_url = f"{repo_url}.git"
        print(f"Cloning from: {clone_url}")
        subprocess.run(["git", "clone", clone_url], check=True)

        # Navigate into the cloned repository
        os.chdir(repo_name)
        
        # Get the current branch name
        branch_name = get_default_branch(os.getcwd())

        # Setup gitignore
        if not os.path.exists(".gitignore"):
            os.system("touch .gitignore && echo 'venv/' >> .gitignore")
        else:
            os.system("echo 'venv/' >> .gitignore")

        # Create virtual environment
        subprocess.run(["python3", "-m", "venv", "venv"], check=True)

        # Run build check
        success, fixed, json_data = build_check()

        if success and fixed:
            if os.path.exists("requirements_fixed.txt"):
                shutil.move("requirements_fixed.txt", "requirements.txt")

            subprocess.run(["git", "add", "*"], check=True)
            subprocess.run(["git", "commit", "-m", "repo fixed your env file"], check=True)

            # Check if repository already exists
            if not check_if_repo_exists(new_repo_name):
                create_new_github_repo(new_repo_name)
            
            new_repo_url = f"git@github.com:grimrepor/{new_repo_name}.git"
            
            try:
                subprocess.run(["git", "remote", "remove", "origin"], check=True)
            except:
                pass
            
            subprocess.run(["git", "remote", "add", "origin", new_repo_url], check=True)
            
            # Push to the correct branch
            print(f"Pushing to branch: {branch_name}")
            subprocess.run(["git", "push", "-f", "origin", branch_name], check=True)
            
            # Clean up
            subprocess.run(["pip", "cache", "purge"], check=True)
            os.chdir(ROOT)
            return True, new_repo_url
            
        return False, None

    except Exception as e:
        print(f"Error processing repository: {str(e)}")
        return False, None 