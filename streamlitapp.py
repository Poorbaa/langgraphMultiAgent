import streamlit as st
import os
import json
import subprocess
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables (if needed)
load_dotenv()
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")

# Define file paths
LOG_FILE = "security_scan_results.log"
JSON_FILE = "security_scan_results.json"

def log_message(message):
    """Log messages to a file with a timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, "a") as log:
        log.write(log_entry)
    return log_entry

def breakdown_query(query: str):
    """Parse user query and map it to security tasks."""
    tasks = []
    url = query.split(" ")[-1] if " " in query else "unknown"

    if "open ports" in query:
        tasks.append({"id": 1, "task": "Nmap Scan", "tool": "nmap", "url": url})
    if "discover directories" in query:
        tasks.append({"id": 2, "task": "Gobuster Scan", "tool": "gobuster", "url": url})
    if "fuzz directories" in query:
        tasks.append({"id": 3, "task": "FFUF Fuzzing", "tool": "ffuf", "url": url})
    if "sql injection" in query:
        tasks.append({"id": 4, "task": "SQLMap Scan", "tool": "sqlmap", "url": url})

    return tasks if tasks else []

def execute_task(task):
    """Execute a security scan using the specified tool."""
    url = task["url"]
    command = []
    output = ""

    if task["tool"] == "nmap":
        command = ["nmap", "-Pn", url]
    elif task["tool"] == "gobuster":
        # Adjust the wordlist path as needed.
        command = ["gobuster", "dir", "-u", url, "-w", "C:/Users/Poorva/Desktop/scancode/common.txt"]
    elif task["tool"] == "ffuf":
        command = ["ffuf", "-u", f"{url}/FUZZ", "-w", "C:/Users/Poorva/Desktop/scancode/common.txt"]
    elif task["tool"] == "sqlmap":
        command = ["sqlmap", "-u", url, "--batch", "--dbs"]
    else:
        log_message(f"Unknown tool: {task['tool']}")
        return None

    log_message(f"Executing: {' '.join(command)}")
    
    # Run the command with a retry mechanism
    for attempt in range(3):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=300)
            output = result.stdout.strip() + "\n" + result.stderr.strip()

            if result.returncode == 0:
                log_message(f"{task['task']} completed successfully.")
                break
            else:
                log_message(f"Attempt {attempt + 1}: {task['task']} failed. Retrying...")
                time.sleep(2)
        except Exception as e:
            log_message(f"Error executing {task['task']}: {e}")

    # Store a limited version of the output for readability
    task["output"] = output[:500]
    return task

def save_to_json(data, filename=JSON_FILE):
    """Save scan results to a JSON file."""
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    log_message(f"Scan results saved to {filename}")

def execute_security_tasks(query):
    """Execute tasks dynamically based on the input query."""
    log_message(f"Starting security scan for query: '{query}'")
    
    tasks = breakdown_query(query)
    if not tasks:
        log_message("No valid tasks found in query.")
        return None

    executed_tasks = []
    for task in tasks:
        result = execute_task(task)
        if result:
            executed_tasks.append(result)

    results = {"query": query, "tasks": executed_tasks}
    save_to_json(results)
    log_message("All scans completed.")
    return results

def read_log():
    """Read and return the current log file contents."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            return f.read()
    return ""

def read_json():
    """Read and return the scan results from the JSON file."""
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    return {}

# ------------------ Streamlit App UI ------------------

st.title("Security Scan App")

st.markdown("""
This app accepts a security query, executes corresponding scanning tasks, and displays both the log output and a brief summary of the results.
""")

# Input for security query
query_input = st.text_input(
    "Enter your security query", 
    placeholder="e.g., scan open ports on http://example.com"
)

if st.button("Run Scan"):
    if query_input:
        # Optionally clear old log file if you want fresh logs
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        st.info("Executing scan. This may take a few moments...")
        result = execute_security_tasks(query_input)
        if result:
            st.success("Scan executed successfully!")
        else:
            st.error("No valid tasks were found for your query.")
    else:
        st.warning("Please enter a security query.")

st.subheader("Scan Logs")
log_content = read_log()
st.text_area("Logs", log_content, height=300)

st.subheader("Scan Results Summary")
json_data = read_json()
if json_data:
    st.write("**Query:**", json_data.get("query", ""))
    tasks = json_data.get("tasks", [])
    for task in tasks:
        st.markdown(f"**Task:** {task.get('task', '')}")
        st.markdown(f"**Tool:** {task.get('tool', '')}")
        brief_output = task.get("output", "")
        if len(brief_output) > 200:
            brief_output = brief_output[:200] + "..."
        st.markdown(f"**Output (brief):** {brief_output}")
        st.markdown("---")
    if st.button("View Full JSON Results"):
        st.json(json_data)
else:
    st.info("No scan results available yet.")
