#!/usr/bin/env python3
"""
IndexNow URL Submission Script for https://jafri.one

Capabilities:
1. Mandatory verification of the live IndexNow API key file (aborts on failure).
2. Verification of GitHub Pages deployment completion via GitHub check-runs API.
3. Multi-commit push change detection (diffing before_sha..head_sha across all commits without silent fallback).
4. Strict validation of every canonical URL extracted from sitemap.xml.
5. Verification of live HTTP 404/410 status for deleted URLs before notifying IndexNow.
6. Detailed logging of submitted URLs, endpoints, and exact HTTP response codes.
"""

import os
import sys
import glob
import json
import time
import subprocess
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET

HOST = "jafri.one"
BASE_URL = f"https://{HOST}"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

def get_key_and_location():
    """
    Finds the IndexNow key verification file in repository root.
    Preserves exact filename and validates content match.
    """
    key_files = glob.glob("[0-9a-f]*.txt")
    valid_key_files = [f for f in key_files if re_match_key(os.path.basename(f))]
    if not valid_key_files:
        raise FileNotFoundError("Could not find IndexNow key file matching pattern [0-9a-f]{8,128}.txt")
    
    key_file = os.path.basename(valid_key_files[0])
    with open(key_file, "r", encoding="utf-8") as f:
        key = f.read().strip()
    
    key_from_filename = key_file.replace(".txt", "").strip()
    if key != key_from_filename:
        raise ValueError(f"Key content ({key}) does not match filename ({key_file})")
    
    key_location = f"{BASE_URL}/{key_file}"
    return key, key_file, key_location

def re_match_key(filename):
    import re
    return bool(re.match(r"^[0-9a-f]{8,128}\.txt$", filename))

def validate_url(raw_url):
    """
    Strictly validates a canonical URL for jafri.one:
    - Only allows HTTPS scheme.
    - Host must be strictly 'jafri.one'.
    - Excludes query parameters (?) and URL fragments (#).
    - Preserves canonical homepage URL as 'https://jafri.one/'.
    - Rejects path traversal (..) or invalid formatting.
    """
    if not raw_url or not isinstance(raw_url, str):
        return None
    url = raw_url.strip()
    if not url.startswith("https://"):
        return None
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return None
        
    if parsed.scheme != "https":
        return None
    if parsed.netloc.lower() != HOST:
        return None
    if parsed.query or parsed.fragment:
        return None
        
    path = parsed.path
    if not path or path == "/":
        return f"{BASE_URL}/"
        
    if ".." in path or "\\" in path:
        return None
        
    return f"{BASE_URL}{path}"

def file_to_canonical(filename):
    """
    Maps repository files to public canonical URLs.
    Only published canonical pages at the root of https://jafri.one are eligible.
    Excludes 404.html, assets, backups, and hidden workflow files.
    """
    clean = filename.replace("\\", "/").strip().lstrip("./")
    # Only root html files belong to published canonical pages
    if "/" in clean:
        return None
    if not clean.endswith(".html"):
        return None
    if clean == "404.html":
        return None
    if clean == "index.html":
        return f"{BASE_URL}/"
    return f"{BASE_URL}/{clean}"

def get_all_canonical_urls_from_sitemap():
    """
    Extracts and strictly validates every canonical URL from sitemap.xml:
    - Only allows HTTPS URLs belonging to jafri.one.
    - Excludes duplicates and invalid URLs.
    - Preserves the correct canonical homepage URL (https://jafri.one/).
    """
    if not os.path.exists("sitemap.xml"):
        raise FileNotFoundError("sitemap.xml not found in repository root")
    
    tree = ET.parse("sitemap.xml")
    root = tree.getroot()
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    
    raw_locs = [elem.text.strip() for elem in root.findall("ns:url/ns:loc", ns) if elem.text]
    valid_urls = []
    
    for raw in raw_locs:
        v = validate_url(raw)
        if not v:
            print(f"  [Sitemap] Discarded invalid/non-conforming URL: '{raw}'")
            continue
        if v not in valid_urls:
            valid_urls.append(v)
        else:
            print(f"  [Sitemap] Excluded duplicate URL: '{v}'")
            
    print(f"Extracted and strictly validated {len(valid_urls)} canonical URL(s) from sitemap.xml.")
    return valid_urls

def verify_deleted_url_status(url):
    """
    Requirement 5: Ensures deleted URLs are notified only when their live response
    correctly represents deletion (HTTP 404 or HTTP 410).
    """
    print(f"Checking live HTTP status for deleted candidate: {url}")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "IndexNow-Deletion-Verifier/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"  -> Returned HTTP {resp.status} (active/not deleted). Will NOT notify IndexNow as deleted.")
            return False
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            print(f"  -> Confirmed HTTP {e.code} ({e.reason}). Verified for IndexNow de-indexing notification.")
            return True
        else:
            print(f"  -> Returned unexpected HTTP {e.code}. Will NOT notify IndexNow.")
            return False
    except Exception as e:
        print(f"  -> Error checking deleted URL {url}: {e}. Skipping.")
        return False

def get_changed_urls(before_sha, head_sha, event_name, submit_all):
    """
    Requirement 3: Computes changed URLs across multiple commits pushed together (before_sha..head_sha).
    Does not silently fall back to examining only HEAD.
    """
    if submit_all or event_name == "workflow_dispatch":
        print(f"Submission mode: Manual/Full sitemap submission (event: {event_name}).")
        return get_all_canonical_urls_from_sitemap()
    
    # Push event: must compare across the entire commit range
    if not before_sha or before_sha == "0000000000000000000000000000000000000000":
        print("Initial branch push detected (no before_sha). Submitting all canonical URLs from sitemap...")
        return get_all_canonical_urls_from_sitemap()
    
    print(f"Comparing push commit range: {before_sha}..{head_sha}")
    
    # Ensure both commits are present locally; if not, fetch them explicitly
    for sha, name in [(before_sha, "before"), (head_sha, "head")]:
        check = subprocess.run(
            ["git", "rev-parse", "--verify", f"{sha}^{{commit}}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if check.returncode != 0:
            print(f"Commit {name} ({sha}) not in shallow clone. Fetching commit from origin...")
            fetch_res = subprocess.run(
                ["git", "fetch", "origin", sha],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if fetch_res.returncode != 0:
                raise RuntimeError(
                    f"Fatal error: Unable to resolve {name} commit {sha} in git history. "
                    f"Cannot compute multi-commit diff: {fetch_res.stderr.strip()}"
                )
    
    diff_cmd = ["git", "diff", "--name-status", f"{before_sha}..{head_sha}"]
    print(f"Executing: {' '.join(diff_cmd)}")
    res = subprocess.run(diff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"Fatal error: 'git diff --name-status {before_sha}..{head_sha}' failed with code {res.returncode}: "
            f"{res.stderr.strip()}"
        )
    
    lines = res.stdout.strip().splitlines()
    print(f"Git diff reported {len(lines)} changed items across all pushed commits:")
    for line in lines:
        print(f"  {line}")
    
    changed_urls = []
    sitemap_changed = False
    
    for line in lines:
        parts = line.strip().split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        # Handle rename lines (e.g. R100 old_file new_file)
        filename = parts[-1]
        
        if filename == "sitemap.xml" or filename.startswith(".github/"):
            sitemap_changed = True
        
        canonical = file_to_canonical(filename)
        if not canonical:
            continue
        
        valid_url = validate_url(canonical)
        if not valid_url:
            print(f"  [Diff] Discarded non-conforming URL: {canonical}")
            continue
            
        if status.startswith("D"):
            # Requirement 5: Ensure deleted URLs are notified only when their live response correctly represents deletion (404 or 410)
            if verify_deleted_url_status(valid_url):
                print(f"  -> Added verified deleted URL for notification: {valid_url}")
                changed_urls.append(valid_url)
            else:
                print(f"  -> Excluded deleted URL {valid_url} (live response not 404/410)")
        else:
            action_desc = "Added" if status.startswith("A") else "Modified"
            print(f"  -> {action_desc} canonical page: {valid_url}")
            changed_urls.append(valid_url)
            
    if sitemap_changed:
        print("sitemap.xml was modified; incorporating all canonical URLs from sitemap...")
        changed_urls.extend(get_all_canonical_urls_from_sitemap())
    
    # Deduplicate while preserving order
    return list(dict.fromkeys(changed_urls))

def verify_live_key(key_location, expected_key, retries=5, delay=10):
    """
    Requirement 1: Mandatory verification of live key accessibility.
    If verification fails, stops execution and does not submit URLs.
    """
    print(f"\n[Mandatory] Verifying live key accessibility at: {key_location}")
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                key_location,
                headers={"User-Agent": "IndexNow-Key-Verifier/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    body = resp.read().decode("utf-8").strip()
                    if body == expected_key:
                        print(f"PASS: Live key verified successfully on attempt {attempt} (HTTP 200, matching body).")
                        return True
                    else:
                        print(f"FAIL (Attempt {attempt}): Key content mismatch. Expected length {len(expected_key)}, got {len(body)}.")
                else:
                    print(f"FAIL (Attempt {attempt}): Unexpected HTTP status {resp.status}.")
        except Exception as e:
            print(f"Attempt {attempt}: Error fetching key file: {e}")
        
        if attempt < retries:
            print(f"Waiting {delay}s before retry...")
            time.sleep(delay)
            
    print("FATAL: Live key verification failed after all retries.")
    return False

def wait_for_github_pages_deployment(repo, sha, token=None, event_name="push", timeout=300, interval=10):
    """
    Requirement 2: Replaces static sleep with live polling of GitHub Pages deployment completion.
    Verifies that the GitHub Actions deploy check-run for the commit has completed successfully.
    Strictly verifies complete 40-character hexadecimal commit SHAs.
    """
    if sha and sha.upper() == "HEAD":
        try:
            sha = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.PIPE
            ).strip()
        except Exception:
            pass

    sha = (sha or "").strip().lower()
    if len(sha) != 40 or not all(c in "0123456789abcdef" for c in sha):
        print(f"FATAL: Invalid commit SHA '{sha}'. Deployment verification requires a complete 40-character hexadecimal SHA.")
        return False

    print(f"\n[Deployment Verification] Checking GitHub Pages deployment for {repo} at commit {sha[:7]}...")
    
    headers = {
        "User-Agent": "IndexNow-Deploy-Checker/1.0",
        "Accept": "application/vnd.github+json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    url = f"https://api.github.com/repos/{repo}/commits/{sha}/check-runs?check_name=deploy"
    start = time.time()
    
    while time.time() - start < timeout:
        elapsed = int(time.time() - start)
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                runs = data.get("check_runs", [])

            matching_runs = [
                r for r in runs
                if r.get("name") == "deploy" and r.get("head_sha", "").strip().lower() == sha
            ]

            if matching_runs:
                run = matching_runs[0]
                status = run.get("status")
                conclusion = run.get("conclusion")
                print(f"Deploy check-run: status='{status}', conclusion='{conclusion}' (elapsed: {elapsed}s)")
                if status == "completed":
                    if conclusion == "success":
                        print(f"PASS: GitHub Pages deployment for commit {sha[:7]} completed successfully!")
                        return True
                    else:
                        print(f"FATAL: GitHub Pages deployment ended with conclusion '{conclusion}'. Aborting.")
                        return False
            else:
                print(f"Deploy check-run not created yet for {sha[:7]} (elapsed: {elapsed}s)...")
        except Exception as e:
            print(f"Check-runs API query notice: {e}")
            
        time.sleep(interval)
        
    print(f"FATAL: Timed out ({timeout}s) waiting for GitHub Pages deployment to complete.")
    return False

def submit_to_indexnow(key, key_location, urls):
    """
    Requirement 8: Captures the actual IndexNow HTTP response and the submitted URL list.
    """
    if not urls:
        print("No published canonical URLs to submit.")
        return True
    
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": key_location,
        "urlList": urls
    }
    
    print("\n" + "=" * 65)
    print(f"SUBMITTING {len(urls)} CANONICAL URL(S) TO INDEXNOW")
    print(f"Endpoint: {INDEXNOW_ENDPOINT}")
    print(f"Host:     {HOST}")
    print(f"Key Loc:  {key_location}")
    print("-" * 65)
    for i, u in enumerate(urls, 1):
        print(f"  {i}. {u}")
    print("=" * 65 + "\n")
    
    req = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            reason = resp.reason
            body = resp.read().decode("utf-8")
            headers = dict(resp.headers)
            
            print(f"IndexNow HTTP Response Status: {status} {reason}")
            if body:
                print(f"IndexNow Response Body: {body}")
            else:
                print("IndexNow Response Body: <empty> (Standard confirmation for HTTP 200/202)")
            print(f"IndexNow Response Headers:\n{json.dumps(headers, indent=2)}")
            
            if status in (200, 202):
                print(f"\nSUCCESS: IndexNow successfully accepted all {len(urls)} URL(s).")
                return True
            else:
                print(f"\nWARNING: Unexpected response status HTTP {status} from IndexNow.")
                return False
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"IndexNow HTTP Error: {e.code} {e.reason}")
        print(f"Error Details: {err_body}")
        return False
    except Exception as e:
        print(f"IndexNow Request Failed: {e}")
        return False

def main():
    # Handle --wait-for-deployment argument for the deployment gate step
    if len(sys.argv) > 1 and sys.argv[1] == "--wait-for-deployment":
        repo = os.getenv("REPOSITORY", "afzaljafri-one/Jafri")
        sha = os.getenv("COMMIT_SHA", "HEAD")
        token = os.getenv("GITHUB_TOKEN")
        event = os.getenv("EVENT_NAME", "push")
        success = wait_for_github_pages_deployment(repo, sha, token=token, event_name=event)
        return 0 if success else 1
    
    try:
        # Step 1: Discover key file
        key, key_file, key_location = get_key_and_location()
        # In GitHub Actions, mask the key so it is never exposed in logs
        print(f"::add-mask::{key}")
        print(f"Discovered IndexNow key file: {key_file}")
        
        # Step 2: Requirement 1 — Mandatory verification of live key
        if not verify_live_key(key_location, key):
            print("FATAL: Live key verification failed. Aborting IndexNow submission immediately.")
            return 1
        
        # Step 3: Requirement 3 — Multi-commit change detection
        before_sha = os.getenv("BEFORE_SHA", "").strip()
        head_sha = os.getenv("COMMIT_SHA", "HEAD").strip()
        event_name = os.getenv("EVENT_NAME", "").strip().lower()
        submit_all = os.getenv("SUBMIT_ALL", "").strip().lower() in ("true", "1", "yes")
        
        urls = get_changed_urls(before_sha, head_sha, event_name, submit_all)
        
        if not urls:
            print("No published website canonical page changes detected. Skipping IndexNow submission.")
            return 0
        
        # Step 4: Requirement 8 — Submit to IndexNow and log full details
        success = submit_to_indexnow(key, key_location, urls)
        return 0 if success else 1
    except Exception as e:
        print(f"Fatal error during IndexNow processing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
