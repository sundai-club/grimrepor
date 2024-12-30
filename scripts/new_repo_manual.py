import os
import subprocess
import shutil
import requests
from dotenv import load_dotenv
import pandas as pd
import yaml
import tempfile
from tqdm import tqdm
from github import Github
import instructor
from pydantic import BaseModel
from openai import OpenAI
from typing import Callable

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

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
g = Github(GITHUB_TOKEN)
client = instructor.from_openai(OpenAI(api_key=OPENAI_API_KEY))

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

def fix_requirements(requirements_content):
    """Fix common issues in requirements files."""
    # Split requirements into lines
    requirements = requirements_content.strip().split('\n')
    fixed_requirements = []
    
    # Known replacements for common issues
    replacements = {
        'pprint': None,  # None means remove it as it's built-in
        'PIL': 'Pillow',  # Example of package rename
        'sklearn': 'scikit-learn',
    }
    
    # Built-in modules that shouldn't be in requirements
    builtin_modules = {
        'pprint', 'json', 'os', 'sys', 'time', 'datetime', 
        'random', 'math', 'collections', 're', 'subprocess'
    }
    
    for req in requirements:
        req = req.strip()
        if not req or req.startswith('#'):
            continue
            
        # Extract package name (handle cases like package==version or package>=version)
        package_name = req.split('==')[0].split('>=')[0].split('<=')[0].split('[')[0].strip()
        
        # Skip if it's a built-in module
        if package_name.lower() in builtin_modules:
            print(f"Removing built-in module from requirements: {package_name}")
            continue
            
        # Apply known replacements
        if package_name in replacements:
            if replacements[package_name] is None:
                print(f"Removing unnecessary requirement: {package_name}")
                continue
            new_req = req.replace(package_name, replacements[package_name], 1)
            print(f"Replacing {package_name} with {replacements[package_name]}")
            fixed_requirements.append(new_req)
        else:
            fixed_requirements.append(req)
    
    return '\n'.join(fixed_requirements)

def install_requirements(requirements_content):
    try:
        # Fix requirements before installation
        fixed_requirements = fix_requirements(requirements_content)
        
        # Save original and fixed requirements for comparison
        with open("requirements.txt.original", "w") as f:
            f.write(requirements_content)
        with open("requirements.txt", "w") as f:
            f.write(fixed_requirements)
            
        with tempfile.TemporaryDirectory() as env_dir:
            # First try with current Python version
            try:
                subprocess.run(["python3", "-m", "venv", env_dir], check=True)
                pip_executable = os.path.join(env_dir, "bin", "pip")

                # Upgrade pip first
                subprocess.run([pip_executable, "install", "--upgrade", "pip"], check=True)

                with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_req_file:
                    temp_req_file.write(fixed_requirements)
                    temp_req_file.flush()

                    result = subprocess.run([pip_executable, "install", "-r", temp_req_file.name], 
                                         capture_output=True, text=True)

                    if result.returncode != 0 and ("Requires-Python" in result.stderr or 
                        "different python version" in result.stderr):
                        raise ValueError("Python version compatibility issue")
                    
                    if result.returncode != 0:
                        return False, result.stderr
                    return True, None

            except Exception as e:
                print(f"Trying with Python 3.10 due to: {str(e)}")
                # Clean up the environment directory
                shutil.rmtree(env_dir, ignore_errors=True)
                os.makedirs(env_dir, exist_ok=True)

                # Try with Python 3.10
                subprocess.run(["python3.10", "-m", "venv", env_dir], check=True)
                pip_executable = os.path.join(env_dir, "bin", "pip")

                # Upgrade pip in the new environment
                subprocess.run([pip_executable, "install", "--upgrade", "pip"], check=True)

                with tempfile.NamedTemporaryFile(delete=False, mode='w') as temp_req_file:
                    temp_req_file.write(fixed_requirements)
                    temp_req_file.flush()

                    result = subprocess.run([pip_executable, "install", "-r", temp_req_file.name], 
                                         capture_output=True, text=True)

                    if result.returncode != 0:
                        return False, f"Failed with Python 3.10: {result.stderr}"
                    return True, None

    except Exception as e:
        return False, str(e)

def parse_setup_py(setup_content):
    install_requires = []
    for line in setup_content.split('\n'):
        if 'install_requires' in line:
            requirements = line.split('=')[-1].strip()[1:-1].replace("'", "").replace('"', '')
            install_requires = [req.strip() for req in requirements.split(',')]
            break
    return '\n'.join(install_requires)

def parse_conda_env(conda_content):
    try:
        env_dict = yaml.safe_load(conda_content)
        dependencies = env_dict.get('dependencies', [])
        pip_requirements = [dep for dep in dependencies if isinstance(dep, str)]
        pip_dict = next((item for item in dependencies if isinstance(item, dict) and 'pip' in item), None)
        if pip_dict:
            pip_requirements.extend(pip_dict['pip'])
        return '\n'.join(pip_requirements)
    except yaml.YAMLError:
        return None

def build_check():
    try:
        requirements = None
        
        # Check for requirements.txt
        if os.path.exists("requirements.txt"):
            with open("requirements.txt", 'r') as f:
                requirements = f.read()
        # Check for setup.py
        elif os.path.exists("setup.py"):
            with open("setup.py", 'r') as f:
                requirements = parse_setup_py(f.read())
        # Check for conda environment files
        elif os.path.exists("environment.yml") or os.path.exists("environment.yaml"):
            env_file = "environment.yml" if os.path.exists("environment.yml") else "environment.yaml"
            with open(env_file, 'r') as f:
                requirements = parse_conda_env(f.read())

        if not requirements:
            print("No requirements found")
            return False, False, {}

        success, error = install_requirements(requirements)
        if success:
            print("Requirements installation successful")
            return True, True, {"status": "Success"}
        else:
            print(f"Requirements installation failed: {error}")
            return False, False, {"status": f"Failed: {error}"}

    except Exception as e:
        print(f"Build check error: {str(e)}")
        return False, False, {"status": f"Error: {str(e)}"}

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

class UpdateSuggestion(BaseModel):
    file_name: str
    suggestion: str

def has_versions(requirements_content):
    for line in requirements_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if any(operator in stripped for operator in ["==", ">=", "<=", ">"]):
            return True
    return False

def get_version_at_date(package_name, commit_date):
    pypi_url = f'https://pypi.org/pypi/{package_name}/json'
    try:
        response = requests.get(pypi_url)
        if response.status_code == 200:
            data = response.json()
            releases = data.get('releases', {})
            for version, release_data in sorted(releases.items(), reverse=True):
                for release in release_data:
                    release_date = release.get('upload_time')
                    if release_date and release_date <= commit_date:
                        return version
    except Exception as e:
        print(f"Error getting version for {package_name}: {str(e)}")
    return None

def process_requirements(requirements_content, commit_date):
    updated_requirements = []
    for line in requirements_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "==" not in stripped:
            package_name = stripped.split()[0]
            version = get_version_at_date(package_name, commit_date)
            if version:
                updated_requirements.append(f"{package_name}=={version}")
            else:
                updated_requirements.append(package_name)
        else:
            updated_requirements.append(stripped)
    return updated_requirements

def check_and_update_requirements(requirements_text):
    prompt = f"This is the requirement.txt : {requirements_text}, see if the packages work together and return the updated requirement.txt with fixed versions"
    system_prompt = """
    You are a senior software engineer reviewing the following repository files.
    Please analyze the following requirement.txt and make sure all the packages work together - Try to use the versions already used and only change if you think it won't work together else just clean the requirement.txt file. Return the list of packages along with their version in this format "
    package_1==version_no_for_package_1_that_works_with_the_other
    package_2==version_no_for_package_2_that_works_with_the_other
    package_3==version_no_for_package_3_that_works_with_the_other
    "
    """
    full_prompt = system_prompt + "\n\n" + prompt
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": full_prompt}],
        response_model=UpdateSuggestion
    )
    return response.suggestion

def process_with_status_callback(message: str, callback: Callable[[str], None] = None):
    """Wrapper to handle status messages with optional callback."""
    if callback:
        callback(message)
    print(message)

def process_repository(repo_url, status_callback: Callable[[str], None] = None):
    try:
        # Clean up the URL
        repo_url = repo_url.rstrip('/')
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]

        # Extract the repository name from the URL
        repo_name = os.path.basename(repo_url)
        username = repo_url.split("/")[-2]
        new_repo_name = f"{username}_{repo_name}"

        process_with_status_callback(f"Processing repository: {repo_url}", status_callback)
        
        # Create a new directory for the repo
        repo_dir = os.path.join(ROOT, "output", f"{repo_name}_dir")
        
        # Remove the directory if it exists
        if os.path.exists(repo_dir):
            process_with_status_callback(f"Removing existing directory: {repo_dir}", status_callback)
            shutil.rmtree(repo_dir)
        
        # Create fresh directory
        os.makedirs(repo_dir, exist_ok=True)
        os.chdir(repo_dir)

        # Clone the repository
        clone_url = f"{repo_url}.git"
        process_with_status_callback(f"Cloning from: {clone_url}", status_callback)
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

        # Create virtual environment - try Python 3.10 first if available
        try:
            subprocess.run(["python3.10", "-m", "venv", "venv"], check=True)
            process_with_status_callback("Created virtual environment with Python 3.10", status_callback)
        except (subprocess.CalledProcessError, FileNotFoundError):
            subprocess.run(["python3", "-m", "venv", "venv"], check=True)
            process_with_status_callback("Created virtual environment with default Python", status_callback)

        # After cloning and before build check, add GPT analysis
        repo_name = repo_url.split('github.com/')[-1].strip('/')
        try:
            github_repo = g.get_repo(repo_name)
            contents = github_repo.get_contents("")
            requirements_file = None
            
            # Find requirements file
            for content_file in contents:
                if "requirement" in content_file.name.lower() and ".txt" in content_file.name:
                    requirements_file = content_file
                    break

            if requirements_file:
                # Get commit history and date
                commits = github_repo.get_commits(path=requirements_file.path)
                commit_date = commits[0].commit.author.date.isoformat()

                # Get requirements content
                requirements_text = requirements_file.decoded_content.decode()

                # Process requirements with versions
                updated_requirements = process_requirements(requirements_text, commit_date)
                updated_requirements_str = "\n".join(updated_requirements)

                # Get GPT suggestions
                gpt_output = check_and_update_requirements(updated_requirements_str)
                
                # Write the GPT suggestions to a new file
                with open("requirements.txt.gpt", "w") as f:
                    f.write(gpt_output)
                
                process_with_status_callback("GPT analysis completed and saved to requirements.txt.gpt", status_callback)

        except Exception as e:
            process_with_status_callback("Error in GPT analysis: {str(e)}", status_callback)

        # Run build check
        success, fixed, json_data = build_check()

        if success and fixed:
            if os.path.exists("requirements.txt.gpt"):
                shutil.move("requirements.txt.gpt", "requirements.txt")
            elif os.path.exists("requirements_fixed.txt"):
                shutil.move("requirements_fixed.txt", "requirements.txt")

            subprocess.run(["git", "add", "*"], check=True)
            
            # Make the commit and capture its hash
            commit_process = subprocess.run(
                ["git", "commit", "-m", "repo fixed your env file"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Get the commit hash
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True
            ).strip()

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
            process_with_status_callback(f"Pushing to branch: {branch_name}", status_callback)
            subprocess.run(["git", "push", "-f", "origin", branch_name], check=True)
            
            # Clean up
            subprocess.run(["pip", "cache", "purge"], check=True)
            os.chdir(ROOT)
            
            # Create the commit URL
            commit_url = f"https://github.com/grimrepor/{new_repo_name}/commit/{commit_hash}"
            return True, commit_url
            
        return False, None

    except Exception as e:
        process_with_status_callback(f"Error processing repository: {str(e)}", status_callback)
        return False, None 