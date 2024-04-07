#!/usr/bin/env python3

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title repos
# @raycast.mode fullOutput

# Optional parameters:
# @raycast.icon 🤖
# @raycast.argument1 { "type": "dropdown", "placeholder": "", "data" : [{"title": "Clone", "value": "-c"}, {"title": "Delete", "value": "-d"}, {"title": "Missing", "value": "-m"}], "optional": true}

# Documentation:
# @raycast.description Check repos
# @raycast.author darrengoulden
# @raycast.authorURL https://github.com/darrengoulden

import argparse
import os

from dotenv import load_dotenv
from github import Github
from git import Repo
from pathlib import Path

repo_folder = f'{Path.home()}/github/personal/'
ignored_folders = [
    '.git',
    '.DS_Store',
    '.obsidian',
]
use_git_url = False
use_ssh_url = True

load_dotenv()
u = os.getenv("GITHUB_USERNAME")
t = os.getenv("GITHUB_TOKEN")

g = Github(t)


class GetRepos:
    """Get all repos from git user and check if they are cloned on locally."""
    def __init__(self):
        self.repos = g.get_user().get_repos()
        self.active_repos = {}

    def get_repos(self):
        if self.repos:
            for repo in self.repos:
                if repo.owner.login == u:
                    self.active_repos[repo.name] = {
                        "archived": repo.archived,
                        "created_at": repo.created_at,
                        "default_branch": repo.default_branch,
                        "git_url": repo.git_url,
                        "last_modified": repo.last_modified,
                        "size": repo.size,
                        "ssh_url": repo.ssh_url,
                        "watchers_count": repo.watchers_count,
                        "visibility": repo.visibility
                    }
            return self.active_repos
        else:
            return None


class CloneRepos:
    """Clone all missing repos."""
    def __init__(self, repos, missing_repos):
        self.repos = repos
        self.missing_repos = missing_repos

    def clone_repos(self):
        for repo in self.missing_repos:
            if self.repos[repo]['archived']:
                continue
            print()
            print(f"Cloning {repo}...")
            if use_git_url:
                Repo.clone_from(f'{self.repos[repo]["git_url"]}', f'{repo_folder}{repo}')
            Repo.clone_from(f'{self.repos[repo]["ssh_url"].replace("github.com", "github-dg")}', f'{repo_folder}{repo}')  # Use github-dg for ssh_url


class MissingRepos:
    """Check if any repos are missing."""
    def __init__(self, repos):
        self.repos = repos

    def missing_repos(self):
        missing_repos = []
        for repo in self.repos:
            if not os.path.exists(f'{repo_folder}{repo}'):
                missing_repos.append(repo)
        return missing_repos


class DeleteRepos:
    """Delete orphaned repos."""
    def __init__(self, repos):
        self.repos = repos
        self.orphaned_repos = []
        self.orphaned_repos_deleted = 0

    def delete_repos(self):
        for repo in os.listdir(repo_folder):
            if repo not in ignored_folders:
                if repo not in [r for r in self.repos]:
                    self.orphaned_repos.append(repo)
        if self.orphaned_repos:
            for repo in self.orphaned_repos:
                print()
                choice = input(f"Press 'y' to delete {repo}...")
                if choice.lower() == "y":
                    os.system(f'rm -rf {repo_folder}{repo}')
                    self.orphaned_repos_deleted += 1
            print(f"Deleted {self.orphaned_repos_deleted} orphaned repos.")
        else:
            print()
            print("No orphaned repos found.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check repos")
    parser.add_argument("-c", "--clone", help="Clone all missing repos", action="store_true")
    parser.add_argument("-d", "--delete", help="Delete orphaned repos", action="store_true")
    parser.add_argument("-m", "--missing", help="List missing repos", action="store_true")
    args, unknown = parser.parse_known_args()

    assert u, "Please set GITHUB_USERNAME in .env"
    assert t, "Please set GITHUB_TOKEN in .env"

    all_repos = GetRepos().get_repos()
    missing_repos = MissingRepos(all_repos).missing_repos()

    if all_repos:
        public = []
        private = []
        for repo in all_repos:
            if repo in ignored_folders:
                continue
            if all_repos[repo]['visibility'] == "public":
                public.append(repo)
            else:
                private.append(repo)
        if public:
            print(f"Public repos ({len(public)}):")
            for repo in public:
                if os.path.exists(f'{repo_folder}{repo}'):
                    current_repo = Repo(f'{repo_folder}{repo}')
                    if current_repo.untracked_files:
                        print(f"\033[0;33m●\033[0m {repo} (untracked files)")
                    elif current_repo.is_dirty():
                        print(f"\033[0;33m●\033[0m {repo} (dirty)")
                    else:
                        print(f"\033[0;32m●\033[0m {repo}")
        if private:
            print()
            print(f"Private repos ({len(private)}):")
            for repo in private:
                if os.path.exists(f'{repo_folder}{repo}'):
                    current_repo = Repo(f'{repo_folder}{repo}')
                    
                    if current_repo.untracked_files:
                        print(f"\033[0;33m●\033[0m {repo} (untracked files)")
                    elif current_repo.is_dirty():
                        print(f"\033[0;33m●\033[0m {repo} (dirty)")
                    else:
                        print(f"\033[0;32m●\033[0m {repo}")
        if args.missing:
            if missing_repos:
                print()
                print("Missing repos:")
                for repo in missing_repos:
                    if all_repos[repo]['archived']:
                        continue
                    print(f"\033[0;31m●\033[0m {repo}")
            else:
                print()
                print("No missing repos.")
        if args.clone:
            if missing_repos:
                for repo in missing_repos:
                    CloneRepos(all_repos, missing_repos).clone_repos()
            else:
                print()
                print("No missing repos to clone.")
        if args.delete:
            DeleteRepos(all_repos).delete_repos()
    else:
        print("No repos found.")
