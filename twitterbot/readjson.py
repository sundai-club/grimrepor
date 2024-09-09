import json
import subprocess

# Read the JSON file and extract owner_name and repo_name
def read_json(file_path):
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    # Extract the first repository as an example
    repo_info = data[0]  # Adjust the index for the repo you want
    
    # Extract the owner_name and repo_name
    owner_name = repo_info['repo_url'].split('/')[-2]
    repo_name = repo_info['repo_url'].split('/')[-1]
    
    return owner_name, repo_name

if __name__ == "__main__":
    # Path to the JSON file
    json_file_path = "test_paper_repo_info.json"
    
    # Read and extract fields
    owner, repo = read_json(json_file_path)
    
    # Call the post_tweet.py script with the extracted fields
    subprocess.run(["python", "xclient.py", owner, repo])
