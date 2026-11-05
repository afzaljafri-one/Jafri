#!/usr/bin/env python3
"""
IndexNow bulk URL submission script for https://jafri.one.
Detects added, modified, and deleted published canonical pages,
and submits them to the IndexNow API.
"""

import os
import sys
import glob
import json
import time
import subprocess
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

HOST = "jafri.one"
BASE_URL = f"https://{HOST}"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"

def get_key_and_location():
    """Finds the IndexNow key verification file in repository root."""
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

def file_to_canonical(filename):
    """
    Maps repository files to public canonical URLs.
    Only published canonical pages at the root of https://jafri.one are eligible.
    Excludes 404.html, assets, backups, and hidden workflow files.
    """
    clean = filename.replace("\\", "/").strip().lstrip("./")
    # Only root html files
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
    """Extracts all public canonical URLs from sitemap.xml."""
    if not os.path.exists("sitemap.xml"):
        return []
    tree = ET.parse("sitemap.xml")
    root = tree.getroot()
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [elem.text.strip() for elem in root.findall("ns:url/ns:loc", ns) if elem.text]

def get_changed_urls(before_sha=None):
    """
    Determines which URLs were added, modified, or deleted in the push.
    """
    submit_all = os.getenv("SUBMIT_ALL", "").lower() in ("true", "1", "yes")
    event_name = os.getenv("EVENT_NAME", "").lower()
    
    if submit_all or event_name == "workflow_dispatch":
        print("Workflow triggered with full submission request. Reading sitemap.xml...")
        return get_all_canonical_urls_from_sitemap()
    
    # Run git diff to find changed files
    diff_cmd = []
    if before_sha and before_sha != "0000000000000000000000000000000000000000":
        # Check if before_sha exists in history
        check = subprocess.run(["git", "cat-file", "-t", before_sha], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if check.returncode == 0:
            diff_cmd = ["git", "diff", "--name-status", f"{before_sha}..HEAD"]
    
    if not diff_cmd:
        # Fallback to inspecting changes in latest commit HEAD
        diff_cmd = ["git", "diff-tree", "-r", "--no-commit-id", "--name-status", "HEAD"]
    
    print(f"Executing: {' '.join(diff_cmd)}")
    res = subprocess.run(diff_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        print(f"Git diff failed: {res.stderr.strip()}. Falling back to sitemap.xml...")
        return get_all_canonical_urls_from_sitemap()
    
    lines = res.stdout.strip().splitlines()
    print(f"Git diff reported {len(lines)} changed items:")
    for line in lines:
        print(f"  {line}")
    
    changed_urls = []
    sitemap_changed = False
    
    for line in lines:
        parts = line.strip().split("\t")
        if len(parts) < 2:
            continue
        status = parts[0]
        filename = parts[1]
        
        if filename == "sitemap.xml":
            sitemap_changed = True
        
        url = file_to_canonical(filename)
        if url:
            action_desc = "Added" if status.startswith("A") else ("Deleted" if status.startswith("D") else "Modified")
            print(f"  -> {action_desc} canonical page: {url}")
            changed_urls.append(url)
            
    if sitemap_changed:
        print("sitemap.xml was modified; incorporating all canonical URLs from sitemap...")
        changed_urls.extend(get_all_canonical_urls_from_sitemap())
    
    # Deduplicate while preserving order
    return list(dict.fromkeys(changed_urls))

def verify_live_key(key_location, expected_key, retries=5, delay=10):
    """Verifies that the IndexNow key is reachable and matching on the live website."""
    print(f"Verifying live key accessibility at: {key_location}")
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                key_location,
                headers={"User-Agent": "IndexNow-Verification-Bot/1.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status == 200:
                    body = resp.read().decode("utf-8").strip()
                    if body == expected_key:
                        print(f"Live key verified successfully on attempt {attempt} (HTTP 200).")
                        return True
                    else:
                        print(f"Attempt {attempt}: Key content mismatch. Expected {len(expected_key)} chars, got {len(body)} chars.")
        except Exception as e:
            print(f"Attempt {attempt}: Error fetching key file: {e}")
        
        if attempt < retries:
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)
            
    print("Warning: Live key verification did not return HTTP 200 with matching content yet.")
    return False

def submit_to_indexnow(key, key_location, urls):
    """Submits the canonical URL list to the IndexNow bulk submission endpoint."""
    if not urls:
        print("No published canonical URLs to submit.")
        return True
    
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": key_location,
        "urlList": urls
    }
    
    json_data = json.dumps(payload, indent=2)
    print(f"\nSubmitting {len(urls)} URL(s) to IndexNow endpoint ({INDEXNOW_ENDPOINT}):")
    for u in urls:
        print(f"  - {u}")
    
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
            print(f"\nIndexNow Response: HTTP {status} {reason}")
            if body:
                print(f"Response Body: {body}")
            if status in (200, 202):
                print(f"SUCCESS: Successfully submitted {len(urls)} URL(s) to IndexNow.")
                return True
            else:
                print(f"Notice: Unexpected response status HTTP {status}")
                return False
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"IndexNow HTTP Error: {e.code} {e.reason}")
        print(f"Error Details: {err_body}")
        return False
    except Exception as e:
        print(f"IndexNow Submission Error: {e}")
        return False

def main():
    try:
        key, key_file, key_location = get_key_and_location()
        # In GitHub Actions, mask the key so it is never exposed in logs
        print(f"::add-mask::{key}")
        print(f"Discovered IndexNow key file: {key_file}")
        
        before_sha = os.getenv("BEFORE_SHA")
        urls = get_changed_urls(before_sha)
        
        if not urls:
            print("No published website page changes detected. Skipping submission.")
            return 0
        
        # Verify key file on live host
        verify_live_key(key_location, key)
        
        # Submit URLs
        success = submit_to_indexnow(key, key_location, urls)
        return 0 if success else 1
    except Exception as e:
        print(f"Fatal error during IndexNow processing: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
