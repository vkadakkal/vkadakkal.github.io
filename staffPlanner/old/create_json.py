import json
import random

# Constants
domains = ["HW", "Analysis", "MPG", "Functional"]
managers = ["Bob", "Alice", "Charlie"]

# Build employees
employees = [
    {"id": "1", "name": "Employee1", "domain": "HW", "manager": "Bob"},
    {"id": "2", "name": "Employee2", "domain": "Analysis", "manager": "Alice"},
    {"id": "3", "name": "Employee3", "domain": "Analysis", "manager": "Charlie"}
]
for i in range(4, 151):
    employees.append({
        "id": str(i),
        "name": f"Employee{i}",
        "domain": random.choice(domains),
        "manager": random.choice(managers)
    })

# Build availability (note: Python 3.9+ for dict union; see below for alternatives)
availability = {
    "1": {"2025-06": 1.0, "2025-07": 0.8},
    "2": {**{f"2025-{m:02d}": 0.0 for m in range(6, 13)}, **{f"2026-{m:02d}": 0.0 for m in range(1,6)}},
    "3": {}
}

# Build projects
projects = {}
for p in range(1, 21):
    projects[f"Project {p}"] = {
        "scaling_factor": round(random.uniform(0.7, 1.3), 2),
        "monthly_demand": {
            f"2025-{m:02d}": round(random.uniform(0.2, 3.0), 2)
            for m in range(6, 12)
        }
    }

# Build allocation
allocation = [
    {
        "employee_id": "2",
        "project": "Project 2",
        "monthly_allocation": {"2025-06": 2.0, "2025-07": 2.0}
    },
    {
        "employee_id": "2",
        "project": "Project A",
        "monthly_allocation": {}
    }
]

# Thresholds
thresholds = {
    "output1_red": 1.0,
    "output1_blue": 0.0,
    "output2_red": 1.2,
    "output2_blue": 0.8
}

# Assemble data
data = {
    "employees": employees,
    "availability": availability,
    "demand": projects,
    "allocation": allocation,
    "thresholds": thresholds
}

# Write to file
with open("staffing_data.json", "w") as f:
    json.dump(data, f, indent=2)

print('Data written to staffing_data.json')
