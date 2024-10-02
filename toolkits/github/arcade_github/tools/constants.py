# Base URL for GitHub API
GITHUB_API_BASE_URL = "https://api.github.com"

# Endpoint patterns
ENDPOINTS = {
    "repo": "/repos/{owner}/{repo}",
    "org_repos": "/orgs/{org}/repos",
    "repo_activity": "/repos/{owner}/{repo}/activity",
    "repo_pulls_comments": "/repos/{owner}/{repo}/pulls/comments",
    "repo_issues": "/repos/{owner}/{repo}/issues",
    "repo_issue_comments": "/repos/{owner}/{repo}/issues/{issue_number}/comments",
    "repo_pulls": "/repos/{owner}/{repo}/pulls",
    "repo_pull": "/repos/{owner}/{repo}/pulls/{pull_number}",
    "repo_pull_commits": "/repos/{owner}/{repo}/pulls/{pull_number}/commits",
    "repo_pull_comments": "/repos/{owner}/{repo}/pulls/{pull_number}/comments",
    "repo_pull_comment_replies": "/repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies",
    "user_starred": "/user/starred/{owner}/{repo}",
    "repo_stargazers": "/repos/{owner}/{repo}/stargazers",
}
