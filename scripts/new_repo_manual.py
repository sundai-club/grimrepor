import os
import subprocess
import shutil
import requests
from dotenv import load_dotenv
import pandas as pd
import yaml
import tempfile
from tqdm import tqdm

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

        # Create virtual environment - try Python 3.10 first if available
        try:
            subprocess.run(["python3.10", "-m", "venv", "venv"], check=True)
            print("Created virtual environment with Python 3.10")
        except (subprocess.CalledProcessError, FileNotFoundError):
            subprocess.run(["python3", "-m", "venv", "venv"], check=True)
            print("Created virtual environment with default Python")

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