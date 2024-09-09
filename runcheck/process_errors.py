import pandas as pd
from github import Github
import requests
import time
from dotenv import load_dotenv
import os
from pydantic import BaseModel
import openai

# Load environment variables from .env file
load_dotenv()

# Get GitHub personal access token and OpenAI API key from environment variables
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize GitHub API client
g = Github(GITHUB_TOKEN)

# Initialize OpenAI client
openai.api_key = OPENAI_API_KEY

# Function to check if the requirement file has version numbers or not
def has_versions(requirements_content):
    for line in requirements_content.splitlines():
        # Ignore comments and empty lines
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Check if there is a version specification (>=, <=, ==, etc.)
        if any(operator in stripped for operator in ["==", ">=", "<=", ">"]):
            return True  # Return True if any version specifier is found
    return False  # Return False if no version specifier is found (i.e., no versions specified)

# Function to get the version of the package active at the commit date
def get_version_at_date(package_name, commit_date):
    pypi_url = f'https://pypi.org/pypi/{package_name}/json'

    try:
        response = requests.get(pypi_url)
        if response.status_code == 200:
            data = response.json()
            releases = data.get('releases', {})

            # Find the release versions available before the commit date
            for version, release_data in sorted(releases.items(), reverse=True):
                for release in release_data:
                    release_date = release.get('upload_time')
                    if release_date and release_date <= commit_date:
                        return version
    except Exception as e:
        print(f"Error getting version for {package_name}: {str(e)}")

    return None  # No valid version found

# Function to process the requirements.txt and add versions
def process_requirements(requirements_content, commit_date):
    updated_requirements = []

    for line in requirements_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue  # Skip empty or comment lines

        # If no version is specified, find the correct version based on the commit date
        if "==" not in stripped:
            package_name = stripped.split()[0]  # Take the package name only
            version = get_version_at_date(package_name, commit_date)
            if version:
                updated_requirements.append(f"{package_name}=={version}")
            else:
                updated_requirements.append(package_name)  # Couldn't find a version, leave it as-is
        else:
            updated_requirements.append(stripped)  # Already has a version, leave it as-is

    return updated_requirements

# Function to search for requirements.txt or similar files in the repository
def find_requirements_file(repo):
    # Search for requirements.txt or similar files
    try:
        contents = repo.get_contents("")
        for content_file in contents:
            if "requirement" in content_file.name.lower() and ".txt" in content_file.name:
                return content_file.path
    except Exception as e:
        print(f"Error finding requirements.txt: {str(e)}")
    return None

# Function to process the given repository link
def process_repository(repo_url):
    # Extract the owner and repo name from the URL
    repo_name = repo_url.split('github.com/')[-1].strip('/')

    try:
        # Get the repository
        repo = g.get_repo(repo_name)

        # Search for requirements.txt or similar file
        file_path = find_requirements_file(repo)
        if not file_path:
            print(f"No requirements.txt or similar file found in {repo_name}")
            return

        print(f"Found requirements file at {file_path}")

        # Get the commit history of the file to determine the commit date
        commits = repo.get_commits(path=file_path)
        commit_date = commits[0].commit.author.date.isoformat()  # Get the latest commit date for the file

        # Get the content of the requirements.txt file
        contents = repo.get_contents(file_path)
        requirements_text = contents.decoded_content.decode()

        # Process requirements and find the versions at commit time
        updated_requirements = process_requirements(requirements_text, commit_date)

        # Write the updated requirements to a file
        with open("updated_requirements.txt", "w") as file_output:
            for requirement in updated_requirements:
                file_output.write(requirement + "\n")

        print(f"Updated requirements for {repo_name} written to updated_requirements.txt")

        # Use OpenAI to check and update the requirements file
        check_and_update_requirements("updated_requirements.txt")

    except Exception as e:
        print(f"Error processing {repo_name}: {str(e)}")

# Function to check and update the requirements file using OpenAI
def check_and_update_requirements(file_path):
    def read_all_files_content(file_path):
        try:
            with open(file_path, 'r') as file:
                return file.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {str(e)}")
            return ""

    all_files_content = read_all_files_content(file_path)

    prompt = f"This is the requirement.txt : " + all_files_content + ", see if the packages work together and return the updated requirement.txt with fixed versions"

    # Define the Pydantic model to hold structured responses
    class UpdateSuggestion(BaseModel):
        file_name: str
        suggestion: str

    # Create the prompt to send to GPT
    system_prompt = """
    You are a senior software engineer reviewing the following repository files.
    Please analyze the following requirement.txt and make sure all the packages work together - Try to use the versions already used and only change if you think it won't work together else just clean the requirement.txt file. Return the list of packages along with their version in this format "
    package_1==version_no_for_package_1_that_works_with_the_other
    package_2==version_no_for_package_2_that_works_with_the_other
    package_3==version_no_for_package_3_that_works_with_the_other
    "
    """

    # Combine the prompt with the content
    full_prompt = system_prompt + "\n\n" + prompt  # Limit the content sent to GPT to 1000 characters for now

    # Call the GPT-4 model with OpenAI to analyze the files and return structured output
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": full_prompt}]
    )

    # Print the suggestions
    gpt_output = response.choices[0].message['content']
    print(gpt_output)

    with open("updated_requirement_from_gpt.txt", "w") as file:
        file.write(gpt_output)

    print("The output has been saved to updated_requirement_from_gpt.txt")

# Read the build_check_results.csv file
df = pd.read_csv("build_check_results.csv")

# Filter the repositories that do not have "success" status
error_repos = df[~df['status'].str.contains("success", case=False)]['file_or_repo'].tolist()

# Process each repository with errors
for repo_url in error_repos:
    process_repository(repo_url)