# import os
# import requests
# from bs4 import BeautifulSoup
# from concurrent.futures import ThreadPoolExecutor, as_completed

# def get_issues(repo_url):
#     issues = []
#     page = 1
#     while True:
#         response = requests.get(f"{repo_url}/issues?page={page}")
#         if response.status_code != 200:
#             break
#         soup = BeautifulSoup(response.content, 'html.parser')
#         issue_links = soup.select('a[data-hovercard-type="issue"]')
#         if not issue_links:
#             break
#         for link in issue_links:
#             issue_url = 'https://github.com' + link['href']
#             issue_title = link.get_text(strip=True)
#             issues.append({'title': issue_title, 'url': issue_url})
#         page += 1
#     return issues

# def get_issue_body(issue):
#     issue_url = issue['url']
#     response = requests.get(issue_url)
#     if response.status_code == 200:
#         soup = BeautifulSoup(response.content, 'html.parser')
        
#         # Get issue body
#         body_element = soup.select_one('.js-comment-body')
#         if body_element:
#             issue['body'] = body_element.get_text(strip=True)
#         else:
#             issue['body'] = "Failed to retrieve issue body."
        
#         # Store the HTML content for all issues
#         issue['html_content'] = str(soup)
        
#         # Get comments
#         comments = []
#         comment_elements = soup.select('.js-comment-container')
#         for comment in comment_elements[1:]:  # Skip the first one as it's the issue body
#             author = comment.select_one('.author')
#             comment_body = comment.select_one('.js-comment-body')
#             if author and comment_body:
#                 comments.append({
#                     'author': author.get_text(strip=True),
#                     'body': comment_body.get_text(strip=True)
#                 })
#         issue['comments'] = comments
        
#         # Get labels
#         labels = []
#         label_elements = soup.select('.IssueLabel')
#         for label in label_elements:
#             labels.append(label.get_text(strip=True))
#         issue['labels'] = labels
        
#     else:
#         issue['body'] = "Failed to retrieve issue body."
#         issue['comments'] = []
#         issue['labels'] = []
#         issue['html_content'] = None
#     return issue

# def main():
#     repo_url = input("Enter the GitHub repository URL: ")
#     issues = get_issues(repo_url)
    
#     if issues:
#         with ThreadPoolExecutor(max_workers=10) as executor:
#             future_to_issue = {executor.submit(get_issue_body, issue): issue for issue in issues}
#             for future in as_completed(future_to_issue):
#                 issue = future_to_issue[future]
#                 try:
#                     future.result()
#                 except Exception as exc:
#                     print(f"Issue {issue['url']} generated an exception: {exc}")

#         repo_name = repo_url.rstrip('/').split('/')[-1]
#         os.makedirs(repo_name, exist_ok=True)
#         os.makedirs(os.path.join(repo_name, 'no_body_html'), exist_ok=True)

#         for i, issue in enumerate(issues, start=1):
#             issue_filename = os.path.join(repo_name, f"issue_{i}.txt")
#             with open(issue_filename, 'w', encoding='utf-8') as f:
#                 f.write(f"Title: {issue['title']}\n")
#                 f.write(f"URL: {issue['url']}\n")
#                 f.write(f"Labels: {', '.join(issue['labels'])}\n")
#                 f.write(f"Body:\n{issue['body']}\n\n")
#                 f.write("Comments:\n")
#                 for comment in issue['comments']:
#                     f.write(f"Author: {comment['author']}\n")
#                     f.write(f"Comment: {comment['body']}\n\n")
            
#             # Save HTML content for issues with "Failed to retrieve issue body"
#             if issue['body'] == "Failed to retrieve issue body." and issue.get('html_content'):
#                 html_filename = os.path.join(repo_name, 'no_body_html', f"issue_{i}.html")
#                 with open(html_filename, 'w', encoding='utf-8') as f:
#                     f.write(issue['html_content'])

#         print(f"Issues saved in folder '{repo_name}'")
#         print(f"HTML files for issues with no body saved in '{repo_name}/no_body_html'")
#     else:
#         print("No issues found or failed to retrieve issues.")

# if __name__ == "__main__":
#     main()