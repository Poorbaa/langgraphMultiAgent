import json
import subprocess
from typing import List, Dict, Union
from langgraph.graph import StateGraph, END

# Assuming you have these tools installed: nmap, gobuster, ffuf, sqlmap


def breakdown_query(
        query: str) -> Union[List[Dict[str, Union[int, str]]], str]:
    """Map security query to tasks."""
    tasks = []
    url = query.split(" ")[-1] if " " in query else "unknown"

    if "open ports" in query:
        tasks.append({
            "id": 1,
            "task": "Run Nmap scan",
            "tool": "nmap",
            "url": url
        })
    if "discover directories" in query or "fuzz directories" in query:
        tasks.append({
            "id": 2,
            "task": "Run Gobuster",
            "tool": "gobuster",
            "url": url
        })
    if "fuzz directories" in query:
        tasks.append({
            "id": 3,
            "task": "FFUF Fuzzing",
            "tool": "ffuf",
            "url": url
        })
    if "sql injection" in query:
        tasks.append({
            "id": 4,
            "task": "SQLMap Scan",
            "tool": "sqlmap",
            "url": url
        })

    return tasks if tasks else "No valid security tasks found."


def execute_task(task: Dict[str, Union[int, str]]) -> Dict[str, str]:
    """Execute a security scan using the specified tool."""
    url = task["url"]
    command = []

    if task["tool"] == "nmap":
        command = ["nmap", "-Pn", url]
    elif task["tool"] == "gobuster":
        command = [
            "gobuster", "dir", "-u", url, "-w", "common.txt"
        ]  #ensure common.txt is in the same directory or provide full path
    elif task["tool"] == "ffuf":
        command = [
            "ffuf", "-u", f"{url}/FUZZ", "-w", "common.txt"
        ]  #ensure common.txt is in the same directory or provide full path
    elif task["tool"] == "sqlmap":
        command = ["sqlmap", "-u", url, "--batch", "--dbs"]
    else:
        return {"result": f"Unknown tool: {task['tool']}"}

    print(f"Executing: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    return {"result": f"stdout: {result.stdout}, stderr: {result.stderr}"}


def save_to_json(data: Dict,
                 filename: str = "security_query_steps.json") -> None:
    """Save the extracted tasks to a JSON file."""
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)
    print(f"Results saved to {filename}")


def planning(state: Dict) -> str:
    """Plan the tasks based on the query."""
    query = state["query"]
    tasks = breakdown_query(query)
    if isinstance(tasks, str):
        return "end"  # No tasks found
    return "execute"


def execution(state: Dict) -> Dict:
    """Execute the tasks."""
    query = state["query"]
    tasks = breakdown_query(query)
    if isinstance(tasks, str):
        return {"results": "No tasks to execute"}

    results = []
    for task in tasks:
        result = execute_task(task)
        results.append({
            "task_id": task["id"],
            "task": task["task"],
            "result": result["result"]
        })
    return {"results": results}


def final_results(state: Dict) -> Dict:
    """Format and return the final results."""
    return {"final_results": state["results"]}


if __name__ == "__main__":
    query = input("Enter your security-related NLP query: ")

    workflow = StateGraph(dict)

    workflow.add_node("planning", planning)
    workflow.add_node("execute", execution)
    workflow.add_node("final_results", final_results)

    workflow.set_entry_point("planning")

    def should_execute(state):
        return state.get("tasks") != "No tasks found"

    workflow.add_edge("planning", "execute")
    workflow.add_edge("planning", END)
    workflow.add_edge("execute", "final_results")
    workflow.add_edge("final_results", END)

    app = workflow.compile()

    inputs = {"query": query}
    results = app.invoke(inputs)

    save_to_json({"query": query, "results": results.get("final_results", {})})
    print(json.dumps(results, indent=4))
