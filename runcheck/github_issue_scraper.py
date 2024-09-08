import requests
import pandas as pd

# Search term for the repository
REPO_NAME = "huggingface/transformers"  # replace with your repository search term
SEARCH_URL = f"https://api.github.com/search/repositories?q={REPO_NAME}"

# Optional: Use your GitHub token for higher rate limits
# HEADERS = {
#     "Authorization": "token YOUR_PERSONAL_ACCESS_TOKEN"  # replace with your token
# }

# Search for repositories
issue_list = []
search_response = requests.get(SEARCH_URL)

if search_response.status_code == 200:
    search_results = search_response.json()

    if search_results["total_count"] > 0:
        repo_info = search_results["items"][0]  # Assuming the first result is the one you want
        owner = repo_info["owner"]["login"]
        repo_name = repo_info["name"]

        print(f"Found repository: {repo_name} owned by {owner}")

        # Now, scrape issues for this repository
        ISSUES_URL = f"https://api.github.com/repos/{owner}/{repo_name}/issues"
        page = 1
        while True:
            issues_response = requests.get(ISSUES_URL, params={"page": page, "per_page": 100})
            if issues_response.status_code == 200:
                issues = issues_response.json()
                if not issues:
                    break
                for issue in issues:
                    temp = {}
                    temp["title"] = issue["title"]
                    temp["body"] = issue["body"]
                    temp["labels"] = issue["labels"]
                    temp["comments"] = issue["comments"]
                    temp["state"] = issue["state"]  # Check if the issue is closed
                    issue_list.append(temp)
                page += 1
            else:
                print(f"Failed to retrieve issues: {issues_response.status_code}")
                break

        df = pd.DataFrame(issue_list)
        df.to_csv("issues.csv", index=False)
    else:
        print("No repositories found.")
else:
    print(f"Failed to search repositories: {search_response.status_code}")

