#!/usr/bin/env python3
"""
AURA GitHub Publisher
Run this after Git is installed to publish to GitHub.
Usage: python publish_to_github.py <your-github-username>
"""
import subprocess
import sys
import os

# ─── Config ─────────────────────────────────────────────
GITHUB_USERNAME = sys.argv[1] if len(sys.argv) > 1 else "YOUR_GITHUB_USERNAME"
REPO_NAME       = "AURA-AI-Assistant"
BRANCH          = "main"
GIT_PATH        = r"C:\Program Files\Git\cmd\git.exe"
PROJECT_DIR     = r"d:\Kalai\Assistant"
# ────────────────────────────────────────────────────────

def run(cmd, check=True):
    print(f"\n>>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip())
    if check and result.returncode != 0:
        print(f"[ERROR] Command failed with code {result.returncode}")
        sys.exit(1)
    return result

def main():
    if GITHUB_USERNAME == "YOUR_GITHUB_USERNAME":
        print("Usage: python publish_to_github.py <your-github-username>")
        sys.exit(1)

    git = [GIT_PATH]

    print("=" * 60)
    print(f"  Publishing AURA to GitHub as @{GITHUB_USERNAME}")
    print("=" * 60)

    # 1. Init
    run(git + ["init", "-b", BRANCH])

    # 2. Config
    run(git + ["config", "user.name", GITHUB_USERNAME])
    run(git + ["config", "user.email", f"{GITHUB_USERNAME}@users.noreply.github.com"])

    # 3. Stage all (respects .gitignore)
    run(git + ["add", "."])

    # 4. First commit
    run(git + ["commit", "-m", "Initial commit: AURA AI Assistant v1.0"])

    # 5. Add remote
    remote_url = f"https://github.com/{GITHUB_USERNAME}/{REPO_NAME}.git"
    run(git + ["remote", "add", "origin", remote_url], check=False)

    # 6. Push
    print(f"\n[INFO] Pushing to {remote_url}")
    print("[INFO] Browser will open for GitHub login if needed (credential manager).")
    push = run(git + ["push", "-u", "origin", BRANCH], check=False)
    if push.returncode != 0:
        print("\n[TIP] If push failed with auth error:")
        print("  1. Go to https://github.com/new")
        print(f"  2. Create repo named: {REPO_NAME}  (public, NO README)")
        print("  3. Run: git push -u origin main")
    else:
        print(f"\n✅ AURA published! -> https://github.com/{GITHUB_USERNAME}/{REPO_NAME}")

if __name__ == "__main__":
    main()
