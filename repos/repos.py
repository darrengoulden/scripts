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

    def __init__(self, include_archived=False, interactive=False):
        self.repos = g.get_user().get_repos()
        self.interactive = interactive
        self.include_archived = include_archived
        self.active_repos = {}
        self.missing_repos = self.missing()
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
                    "orphaned": False,
                    "size": repo.size,
                    "ssh_url": repo.ssh_url,
                    "watchers_count": repo.watchers_count,
                    "visibility": repo.visibility,
                }
        return self.active_repos

    def clone(self, missing_repos):
        """Clone repos."""
        for repo in missing_repos:  # pylint: disable=not-an-iterable
            if not self.include_archived:
                if self.active_repos[repo]["archived"]:
                    continue
            print()
            print(f"Cloning {repo}...")
            if USE_GIT_URL:
                if not os.path.exists(f"{repo_folder}{repo}"):
                    Repo.clone_from(
                        f'{self.active_repos[repo]["git_url"]}', f"{repo_folder}{repo}"
                    )
            else:
                if not os.path.exists(f"{repo_folder}{repo}"):
                    Repo.clone_from(
                        f'{self.active_repos[repo]["ssh_url"].replace("github.com", "github-dg")}',
                        f"{repo_folder}{repo}",
                    )  # Use github-dg for ssh_url

    def missing(self):
        """Get missing repos."""
        missing_repos = []
        for repo in self.active_repos:  # pylint: disable=consider-using-dict-items
            if not self.include_archived:
                if self.active_repos[repo]["archived"]:
                    continue
            if not os.path.exists(f"{repo_folder}{repo}"):
                missing_repos.append(repo)
            if self.active_repos[repo]["orphaned"]:
                if os.path.exists(f"{repo_folder}{repo}"):
                    missing_repos.append(repo)
        return missing_repos

    def delete(self, ignore_prompt=False):  # pylint: disable=too-many-branches
        """Delete repos."""
        for repo in os.listdir(repo_folder):
            if repo not in ignored_folders:
                if repo not in self.active_repos:
                    self.orphaned_repos.append(repo)
        for repo in self.active_repos:  # pylint: disable=consider-using-dict-items
            if not self.include_archived:
                if self.active_repos[repo]["archived"]:
                    if os.path.exists(f"{repo_folder}{repo}"):
                        self.orphaned_repos.append(repo)
        if self.orphaned_repos:
            for repo in self.orphaned_repos:  # pylint: disable=not-an-iterable
                if ignore_prompt or not self.interactive:
                    # Raycast does not support input, so we will delete the orphaned repos without confirmation
                    os.system(f"rm -rf {repo_folder}{repo}")
                    self.orphaned_repos_deleted += 1
                else:
                    choice = input(f"Press 'y' to delete {repo}...")
                    if choice.lower() == "y":
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
                try:
                    current_repo = Repo(f"{repo_folder}{repo}")
                except:  # pylint: disable=bare-except
                    self.active_repos[repo]["orphaned"] = True
                if current_repo.untracked_files:
                    print(f"\033[0;33m●\033[0m {repo} (untracked files)")
                elif current_repo.is_dirty():
                    print(f"\033[0;33m●\033[0m {repo} (dirty)")
                elif self.active_repos[repo]["orphaned"]:
                    print(f"\033[0;33m●\033[0m {repo} (orphaned)")
                elif self.active_repos[repo]["archived"]:
                    print(f"\033[0;30;40m●\033[0m {repo} (archived)")
                else:
                    print(f"\033[0;32m●\033[0m {repo}")
            else:
                print(f"\033[0;30;40m●\033[0m {repo} (archived not cloned)")


def parse_args(args=None, unknown=None):
    """Arg parser."""
    parser = argparse.ArgumentParser(description="Check repos")
    parser.add_argument(
        "-a", "--archived", help="Include archived repos", action="store_true"
    )
    parser.add_argument(
        "-c", "--clone", help="Clone all missing repos", action="store_true"
    )
    parser.add_argument(
        "-d", "--delete", help="Delete orphaned repos", action="store_true"
    )
    parser.add_argument(
        "-m", "--missing", help="List missing repos", action="store_true"
    )
    parser.add_argument(
        "-y",
        "--yes",
        help="Skip input prompt when deleting orphaned repos",
        action="store_true",
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
    include_archived = args.archived
    public = []
    private = []

    if sys.stdin and sys.stdin.isatty():
        interactive = True

    repositories = Repos(include_archived, interactive)
    all_repos = repositories.get()
    missing_repos = repositories.missing()

    if all_repos:
        for repo in all_repos:  # pylint: disable=consider-using-dict-items
            if repo in ignored_folders:
                continue
            if all_repos[repo]["visibility"] == "public":
                if not include_archived:
                    if not all_repos[repo]["archived"]:
                        public.append(repo)
                else:
                    public.append(repo)
            else:
                if not include_archived:
                    if not all_repos[repo]["archived"]:
                        private.append(repo)
                else:
                    private.append(repo)
        if public:
            print(f"Public repos ({len(public)}):")
            repositories.print(public)
        if private:
            print()
            print(f"Private repos ({len(private)}):")
            repositories.print(private)
        if args.clone:
            if missing_repos:
                for repo in missing_repos:
                    repositories.clone(missing_repos)
            else:
                print()
                print("No missing repos to clone.")
        if args.missing:
            if missing_repos:
                print()
                print("Missing repos:")
                for repo in missing_repos:
                    print(f"\033[0;31m●\033[0m {repo}")
            else:
                print()
                print("No missing repos.")
        if args.delete:
            repositories.delete(args.yes)
    else:
        print("No repos found.")


if __name__ == "__main__":
    assert u, "Please set GITHUB_USERNAME in .env"
    assert t, "Please set GITHUB_TOKEN in .env"
    main()
