import argparse
import os
import sys
import subprocess
import xml.etree.ElementTree as ET
import shutil
import urllib.request

def run_git(args, cwd=None, capture_output=False, check=True):
    """Run a git command using subprocess."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=capture_output,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error executing git {' '.join(args)} in {cwd or '.'}")
        if capture_output:
            print(e.stderr)
        raise
    except FileNotFoundError:
        print("Git is not installed or not found in PATH.")
        sys.exit(1)

def parse_manifest(manifest_path):
    """
    Parse the XML manifest and return a list of projects.
    Returns: list of dicts: [{'name': '...', 'path': '...', 'revision': '...', 'remote': '...', 'remote_url': '...'}]
    """
    if not os.path.exists(manifest_path):
        print(f"Manifest file not found at {manifest_path}")
        sys.exit(1)

    tree = ET.parse(manifest_path)
    root = tree.getroot()

    # Parse remotes
    remotes = {}
    for remote in root.findall('remote'):
        r_name = remote.get('name')
        r_fetch = remote.get('fetch')
        if r_name and r_fetch:
            remotes[r_name] = r_fetch

    # Parse default
    default = root.find('default')
    default_remote = default.get('remote') if default is not None else None
    default_revision = default.get('revision') if default is not None else 'main'

    # Parse projects
    projects = []
    for project in root.findall('project'):
        p_name = project.get('name')
        p_path = project.get('path', p_name) # Default path to name if path not specified
        p_remote = project.get('remote', default_remote)
        p_revision = project.get('revision', default_revision)
        
        # Calculate full remote URL
        if not p_remote or p_remote not in remotes:
            print(f"Warning: Remote '{p_remote}' not found for project '{p_name}'")
            continue
            
        base_url = remotes[p_remote].rstrip('/')
        remote_url = f"{base_url}/{p_name}.git"

        projects.append({
            'name': p_name,
            'path': p_path,
            'revision': p_revision,
            'remote': p_remote,
            'remote_url': remote_url
        })

    return projects

def main():
    parser = argparse.ArgumentParser(description="Claw: A minimal repo-like tool optimized for Windows.")
    parser.add_argument("-v", "--version", action="version", version="0.1.0")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize a claw workspace in the current directory")
    init_parser.add_argument("-u", "--url", required=True, help="URL or local path to the manifest repository or file")
    init_parser.add_argument("-m", "--manifest-name", default="default.xml", help="Name of the manifest file in the repository")
    init_parser.add_argument("-b", "--branch", help="Manifest branch or revision")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync the repositories as per the manifest")

    # branch command
    branch_parser = subparsers.add_parser("branch", help="List active branches across all cloned projects")

    # list command
    list_parser = subparsers.add_parser("list", help="List down the cloned repositories")

    # log command
    log_parser = subparsers.add_parser("log", help="Shows logs for a specific project")
    log_parser.add_argument("path", help="Relative path to the repository")
    log_parser.add_argument("git_args", nargs=argparse.REMAINDER, help="Additional arguments to pass to git log")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        print(f"Initializing Claw with manifest: {args.url}")
        claw_dir = os.path.join(os.getcwd(), ".claw")
        os.makedirs(claw_dir, exist_ok=True)
        
        manifest_dest = os.path.join(claw_dir, "manifest.xml")
        manifest_repo_dir = os.path.join(claw_dir, "manifest")

        # Determine if it's an HTTP file link (like a raw xml file or a github blob link)
        is_http_file = args.url.startswith("http") and (
            args.url.endswith(".xml") or "/blob/" in args.url or "/raw/" in args.url
        )

        # If it's a local file, copy it directly
        if os.path.isfile(args.url):
            try:
                shutil.copy2(args.url, manifest_dest)
                print(f"Copied local manifest to {manifest_dest}")
            except Exception as e:
                print(f"Failed to copy manifest: {e}")
                sys.exit(1)
        elif is_http_file:
            print(f"Downloading manifest file from {args.url}...")
            # Automatically convert GitHub blob URLs to raw file URLs
            download_url = args.url
            if "github.com" in download_url and "/blob/" in download_url:
                download_url = download_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
            
            try:
                urllib.request.urlretrieve(download_url, manifest_dest)
                print(f"Downloaded remote manifest to {manifest_dest}")
            except Exception as e:
                print(f"Failed to download remote manifest: {e}")
                sys.exit(1)
        else:
            # It's a git repository URL
            if os.path.exists(manifest_repo_dir):
                print("Updating existing manifest repository...")
                run_git(["pull"], cwd=manifest_repo_dir)
                if args.branch:
                    run_git(["checkout", args.branch], cwd=manifest_repo_dir)
            else:
                print(f"Cloning manifest repository from {args.url}...")
                clone_cmd = ["clone"]
                if args.branch:
                    clone_cmd.extend(["--branch", args.branch])
                clone_cmd.extend([args.url, manifest_repo_dir])
                run_git(clone_cmd)
            print(f"Manifest repository synced in {manifest_repo_dir}")
            
        # Save the manifest name preference for sync
        with open(os.path.join(claw_dir, "manifest_name"), "w") as f:
            f.write(args.manifest_name)
            
        print("\nClaw workspace initialized. Run `claw sync` to fetch projects.")

    elif args.command == "sync":
        print("Syncing repositories...")
        claw_dir = os.path.join(os.getcwd(), ".claw")
        if not os.path.exists(claw_dir):
            print("Error: Not a claw workspace. Run `claw init -u <manifest>` first.")
            sys.exit(1)
            
        # Determine where the manifest is
        local_xml = os.path.join(claw_dir, "manifest.xml")
        
        # Check for saved manifest name preference
        manifest_name = "default.xml"
        manifest_name_file = os.path.join(claw_dir, "manifest_name")
        if os.path.exists(manifest_name_file):
            with open(manifest_name_file, "r") as f:
                manifest_name = f.read().strip()
                
        repo_xml = os.path.join(claw_dir, "manifest", manifest_name)
        
        manifest_path = None
        if os.path.exists(local_xml):
            manifest_path = local_xml
        elif os.path.exists(repo_xml):
            manifest_path = repo_xml
        else:
            print(f"Error: Could not find manifest.xml or manifest/{manifest_name} in .claw/")
            sys.exit(1)
            
        projects = parse_manifest(manifest_path)
        print(f"Found {len(projects)} projects in manifest.")
        
        for p in projects:
            path = p['path']
            url = p['remote_url']
            rev = p['revision']
            
            # Use absolute path for safety
            full_path = os.path.join(os.getcwd(), path)
            
            print(f"\n---> Syncing project {p['name']} at '{path}'")
            if os.path.exists(os.path.join(full_path, ".git")):
                # Existing project -> fetch and update
                print(f"Fetching from {url}...")
                run_git(["fetch", "origin"], cwd=full_path)
                print(f"Checking out {rev}...")
                # Note: If it's a remote branch, we might need a detached HEAD or to track it.
                # A simple git checkout will usually work if it exists.
                try:
                    run_git(["checkout", rev], cwd=full_path)
                    # Try to pull if it's a tracking branch, ignore if detached
                    run_git(["pull", "--rebase"], cwd=full_path, check=False)
                except Exception as e:
                    print(f"Warning: Issue checking out/pulling {rev} for {p['name']}.")
            else:
                # New project -> clone
                print(f"Cloning from {url} to {path} (branch: {rev})...")
                os.makedirs(os.path.dirname(full_path) or ".", exist_ok=True)
                try:
                    # shallow clone or branch clone
                    run_git(["clone", "--branch", rev, url, path])
                except Exception as e:
                    print(f"Failed to clone {p['name']}. Continuing...")
    elif args.command == "branch":
        claw_dir = os.path.join(os.getcwd(), ".claw")
        if not os.path.exists(claw_dir):
            print("Error: Not a claw workspace.")
            sys.exit(1)
            
        local_xml = os.path.join(claw_dir, "manifest.xml")
        repo_xml = os.path.join(claw_dir, "manifest", "default.xml")
        manifest_path = local_xml if os.path.exists(local_xml) else repo_xml
        
        projects = parse_manifest(manifest_path)
        
        print(f"{'BRANCH':<25} | {'PROJECT'}")
        print("-" * 50)
        for p in projects:
            path = p['path']
            full_path = os.path.join(os.getcwd(), path)
            if os.path.exists(os.path.join(full_path, ".git")):
                res = run_git(["branch", "--show-current"], cwd=full_path, capture_output=True, check=False)
                branch = res.stdout.strip()
                if not branch:
                    branch = "(detached)"
                print(f"*  {branch:<22} | in {path}")
            else:
                print(f"*  {'(not cloned)':<22} | in {path}")

    elif args.command == "list":
        claw_dir = os.path.join(os.getcwd(), ".claw")
        if not os.path.exists(claw_dir):
            print("Error: Not a claw workspace.")
            sys.exit(1)
            
        local_xml = os.path.join(claw_dir, "manifest.xml")
        repo_xml = os.path.join(claw_dir, "manifest", "default.xml")
        manifest_path = local_xml if os.path.exists(local_xml) else repo_xml
        
        projects = parse_manifest(manifest_path)
        
        for p in projects:
            print(f"{p['path']:<30} | {p['remote_url']}")

    elif args.command == "log":
        full_path = os.path.join(os.getcwd(), args.path)
        if not os.path.exists(os.path.join(full_path, ".git")):
            print(f"Error: No git repository found at '{args.path}'")
            print(f"(Did you run `claw sync`? Did that module fail to clone?)")
            sys.exit(1)
            
        # Do not capture output, so it uses the user's terminal/pager directly
        git_cmd = ["git", "log"] + args.git_args
        subprocess.run(git_cmd, cwd=full_path)

if __name__ == "__main__":
    main()
