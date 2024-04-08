#!/usr/bin/env python3
# pylint: disable=redefined-outer-name
# pylint: disable=too-few-public-methods
# pylint: disable=line-too-long

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Repos
# @raycast.mode fullOutput

# Optional parameters:
# @raycast.icon 🤖
# @raycast.argument1 { "type": "dropdown", "placeholder": "", "data" : [{"title": "Clone", "value": "-c"}, {"title": "Delete", "value": "-d"}, {"title": "Missing", "value": "-m"}], "optional": true}

# Documentation:
# @raycast.description Manage Github repos
# @raycast.author darrengoulden
# @raycast.authorURL https://github.com/darrengoulden

"""
Script to manage Github repositories from Raycast.
"""

import argparse
import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from github import Github
from git import Repo

repo_folder = f"{Path.home()}/github/personal/"
ignored_folders = [
    ".git",
    ".DS_Store",
    ".obsidian",
]
USE_GIT_URL = False

load_dotenv()
u = os.getenv("GITHUB_USERNAME")
t = os.getenv("GITHUB_TOKEN")

g = Github(t)


class Repos:
    """Get all repos from git user and check if they are cloned on locally."""

    def __init__(self, interactive=False):
        self.interactive = interactive
        self.repos = g.get_user().get_repos()
        self.active_repos = {}
        self.missing_repos = self.missing() if self.active_repos else None
        self.orphaned_repos = []
        self.orphaned_repos_deleted = 0

    def get(self):
        """Get repos."""
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
                    "visibility": repo.visibility,
                }
        return self.active_repos

    def clone(self):
        """Clone repos."""
        for repo in self.missing_repos:  # pylint: disable=not-an-iterable
            if self.active_repos[repo]["archived"]:
                continue
            print()
            print(f"Cloning {repo}...")
            if USE_GIT_URL:
                Repo.clone_from(
                    f'{self.active_repos[repo]["git_url"]}', f"{repo_folder}{repo}"
                )
            else:
                Repo.clone_from(
                    f'{self.active_repos[repo]["ssh_url"].replace("github.com", "github-dg")}',
                    f"{repo_folder}{repo}",
                )  # Use github-dg for ssh_url

    def missing(self):
        """Get missing repos."""
        missing_repos = []
        for repo in self.active_repos:
            if self.active_repos[repo]["archived"]:
                continue
            if not os.path.exists(f"{repo_folder}{repo}"):
                missing_repos.append(repo)
        return missing_repos

    def delete(self):
        """Delete repos."""
        for repo in os.listdir(repo_folder):
            if repo not in ignored_folders:
                if repo not in self.active_repos:
                    self.orphaned_repos.append(repo)
        for repo in self.active_repos:
            if self.active_repos[repo]["archived"]:
                if os.path.exists(f"{repo_folder}{repo}"):
                    self.orphaned_repos.append(repo)
        if self.orphaned_repos:
            for repo in self.orphaned_repos:  # pylint: disable=not-an-iterable
                print()
                if self.interactive:
                    choice = input(f"Press 'y' to delete {repo}...")
                    if choice.lower() == "y":
                        os.system(f"rm -rf {repo_folder}{repo}")
                        self.orphaned_repos_deleted += 1
                else:
                    # Raycast does not support input, so we will delete the orphaned repos without confirmation
                    os.system(f"rm -rf {repo_folder}{repo}")
                    self.orphaned_repos_deleted += 1
            print(f"Deleted {self.orphaned_repos_deleted} orphaned repos.")
        else:
            print()
            print("No orphaned repos found.")

    def print(self, repos):
        """Print repos."""
        for repo in repos:
            if os.path.exists(f"{repo_folder}{repo}"):
                current_repo = Repo(f"{repo_folder}{repo}")
                if current_repo.untracked_files:
                    print(f"\033[0;33m●\033[0m {repo} (untracked files)")
                elif current_repo.is_dirty():
                    print(f"\033[0;33m●\033[0m {repo} (dirty)")
                else:
                    print(f"\033[0;32m●\033[0m {repo}")


def parse_args(args=None, unknown=None):
    """Arg parser."""
    parser = argparse.ArgumentParser(description="Check repos")
    parser.add_argument(
        "-c", "--clone", help="Clone all missing repos", action="store_true"
    )
    parser.add_argument(
        "-d", "--delete", help="Delete orphaned repos", action="store_true"
    )
    parser.add_argument(
        "-m", "--missing", help="List missing repos", action="store_true"
    )
    args, unknown = parser.parse_known_args()

    if sys.stdin and sys.stdin.isatty():
        if unknown:
            parser.print_help()
            sys.exit(1)
    return args


def main():  # pylint: disable=too-many-branches
    """Main function."""
    args = parse_args()

    interactive = False
    public = []
    private = []

    if sys.stdin and sys.stdin.isatty():
        interactive = True

    repositories = Repos(interactive)
    all_repos = repositories.get()
    missing_repos = repositories.missing()

    if all_repos:
        for repo in all_repos:
            if repo in ignored_folders:
                continue
            if all_repos[repo]["visibility"] == "public":
                if not all_repos[repo]["archived"]:
                    public.append(repo)
            else:
                if not all_repos[repo]["archived"]:
                    private.append(repo)
        if public:
            print(f"Public repos ({len(public)}):")
            repositories.print(public)
        if private:
            print()
            print(f"Private repos ({len(private)}):")
            repositories.print(private)
        if args.missing:
            if missing_repos:
                print()
                print("Missing repos:")
                for repo in missing_repos:
                    print(f"\033[0;31m●\033[0m {repo}")
            else:
                print()
                print("No missing repos.")
        if args.clone:
            if missing_repos:
                for repo in missing_repos:
                    repositories.clone()
            else:
                print()
                print("No missing repos to clone.")
        if args.delete:
            repositories.delete()
    else:
        print("No repos found.")


if __name__ == "__main__":
    assert u, "Please set GITHUB_USERNAME in .env"
    assert t, "Please set GITHUB_TOKEN in .env"
    main()
