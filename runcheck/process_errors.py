import pandas as pd
from github import Github
import requests
import time
from dotenv import load_dotenv
import os
import instructor
from pydantic import BaseModel
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# Get GitHub personal access token and OpenAI API key from environment variables
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize GitHub API client
g = Github(GITHUB_TOKEN)

# Initialize OpenAI client
client = instructor.from_openai(OpenAI(api_key=OPENAI_API_KEY))

# Define the Pydantic model to hold structured responses
class UpdateSuggestion(BaseModel):
    file_name: str
    suggestion: str

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

# Function to check and update the requirements file using OpenAI
def check_and_update_requirements(requirements_text):
    prompt = f"This is the requirement.txt : " + requirements_text + ", see if the packages work together and return the updated requirement.txt with fixed versions"

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

    # Call the GPT-4 model with Instructor to analyze the files and return structured output
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": full_prompt}],
        response_model=UpdateSuggestion  # Use the Pydantic model to ensure structured output
    )

    # Get the suggestions
    gpt_output = response.suggestion
    return gpt_output

# Function to commit and push the updated requirements file to the repository
def commit_and_push(repo, file_path, updated_requirements_str):
    try:
        # Get the file content and sha
        contents = repo.get_contents(file_path)
        sha = contents.sha

        # Commit and push the updated requirements file
        repo.update_file(
            path=file_path,
            message="Update requirements.txt with fixed versions",
            content=updated_requirements_str,
            sha=sha
        )
        print(f"Updated requirements.txt pushed to {repo.full_name}")
    except Exception as e:
        print(f"Error pushing updated requirements.txt to {repo.full_name}: {str(e)}")

# Function to process the given repository link and return updated requirements
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
            return None  # Return None if no requirements file found

        print(f"Found requirements file at {file_path}")

        # Get the commit history of the file to determine the commit date
        commits = repo.get_commits(path=file_path)
        commit_date = commits[0].commit.author.date.isoformat()  # Get the latest commit date for the file

        # Get the content of the requirements.txt file
        contents = repo.get_contents(file_path)
        requirements_text = contents.decoded_content.decode()

        # Process requirements and find the versions at commit time
        updated_requirements = process_requirements(requirements_text, commit_date)

        # Convert updated_requirements to a string format
        updated_requirements_str = "\n".join(updated_requirements)

        print(f"Updated requirements for {repo_name}:\n{updated_requirements_str}")

        # Use OpenAI to check and update the requirements file
        gpt_output = check_and_update_requirements(updated_requirements_str)

        # Commit and push the updated requirements file to the repository
        commit_and_push(repo, file_path, gpt_output)

        return gpt_output

    except Exception as e:
        print(f"Error processing {repo_name}: {str(e)}")
        return None

# Read the build_check_results.csv file
df = pd.read_csv("build_check_results.csv")

# Filter the repositories that do not have "success" status
error_repos = df[~df['status'].str.contains("success", case=False)]['file_or_repo'].tolist()

# List to store the results
results = []

# Process each repository with errors and save the result to the list
for repo_url in error_repos:
    gpt_output = process_repository(repo_url)
    if gpt_output:
        results.append({'github_link': repo_url, 'updated_requirements': gpt_output})

# Convert the results to a DataFrame and save as CSV
results_df = pd.DataFrame(results)
results_df.to_csv("updated_requirements_results.csv", index=False)

print("The updated requirements have been saved to updated_requirements_results.csv")