
# File Integrity Monitoring (FIM) Tool – Python

## Overview
This project is a **File Integrity Monitoring (FIM)** tool built using **Python**.  
It monitors selected files or directories and detects changes such as:

- File creation  
- File modification  
- File deletion  
- File renaming  

The tool creates a **baseline** using cryptographic hashes and then continuously watches for changes, logging all events with timestamps.

This project is intended for **learning cybersecurity concepts** and as a **portfolio project** demonstrating blue-team fundamentals.

---

## Why File Integrity Monitoring Matters
File Integrity Monitoring is an important security control used to:
- Detect malware or unauthorized changes
- Monitor system and configuration files
- Support incident response and forensics
- Meet compliance requirements (PCI-DSS, CIS, HIPAA)

---

## Features
- SHA-256 hashing for file integrity verification
- Baseline creation of trusted file states
- Real-time monitoring using filesystem events
- Detects:
  - File creation
  - File modification
  - File deletion
  - File rename/move
- Logs events with UTC timestamps
- Uses a Python virtual environment

---

## Technologies Used
- Python 3
- watchdog
- hashlib
- argparse
- json

---

## Project Structure
```

file-integrity-monitoring/
├── src/
│   └── fim.py
├── .venv/
├── fim_db.json
├── fim.log
├── README.md
└── test_folder/

````

---

## Setup Instructions

### 1. Create and activate virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
````

### 2. Install dependencies

```bash
python -m pip install watchdog
```

---

## How to Use

### Step 1: Create a test folder

```bash
mkdir test_folder
echo "hello" > test_folder/test.txt
```

### Step 2: Build the baseline

```bash
python src/fim.py test_folder --baseline
```

### Step 3: Start monitoring

```bash
python src/fim.py test_folder
```

### Step 4: Trigger file changes

```bash
echo "world" >> test_folder/test.txt
touch test_folder/new_file.txt
rm test_folder/test.txt
```

The tool will log all detected changes.

---

## Logs and Baseline

* Baseline file: `fim_db.json`
* Log file: `fim.log`

Each log entry includes:

* Timestamp (UTC)
* Action type
* File path
* Hash values (when applicable)

---

## Security Notes

* Files are never executed
* Only metadata and hashes are collected
* Safe for local and learning environments

---

## Future Improvements

* Severity levels for events
* Alerting (email or notifications)
* Periodic full integrity scans
* SQLite database backend
* Configuration file support

---

## Author

Rhea Sharma

Built as a hands-on cybersecurity learning and portfolio project.

```

---

If you want next, I can:
- Add **severity levels to the code**
- Help you write **resume bullet points**
- Help you **publish this on GitHub properly**

Just tell me what you want to do next.
```
