# Claw

**Claw** is a minimal, blazing-fast workspace management tool optimized for Windows. 

It allows you to manage multiple Git repositories as a single cohesive project, driven entirely by a lightweight XML manifest file.

## Features
- Initialize huge multi-repository workspaces instantly
- Clone, fetch, and synchronize projects in bulk based on tracked branches/revisions
- Execute `git` operations smoothly over all repositories
- Powered by Python, meaning virtually perfect cross-platform compatibility (Native Windows, PowerShell, Git Bash).

## Installation

Claw is distributed as a standard Python package. You do not need to download standalone binaries—you can install it directly from the source using `pip`!

**Prerequisites:** Python 3.7 or higher installed on your machine.

Open your terminal (PowerShell, Command Prompt, or Git Bash) and run:
```bash
pip install git+https://github.com/keshavjha018/claw.git
```

This downloads compiling execution directly from GitHub and registers the `claw` executable directly in your system PATH.

### Developer Setup
If you are modifying the source code of Claw locally, you can install it in "editable" mode:
1. Clone the repository and navigate into the folder:
   ```bash
   git clone https://github.com/keshavjha018/claw.git
   cd claw
   ```
2. Run the editable install command:
   ```bash
   pip install -e .
   ```

## Usage Guide

Claw uses an XML manifest (usually `default.xml`) to understand your project structure.

### 1. Initialize a Workspace
To create a new workspace, navigate to an empty directory and use `claw init`. You can point this to a local XML file or a remote git repository that contains your manifest.
```bash
claw init -u /path/to/my/manifest.xml
```

### 2. Sync Projects
Once initialized, pull down all the repositories specified in your manifest:
```bash
claw sync
```

### 3. Check Branch Status
Quickly list out what branches are currently active across all of your cloned repositories:
```bash
claw branch
```

### 4. List Repositories
View the local directory paths and their corresponding remote URLs:
```bash
claw list
```

### 5. Check Logs
You can run a Git log specifically tailored to any project path, safely passing down any native git flags:
```bash
claw log path/to/my/module -n 5 --oneline
```
