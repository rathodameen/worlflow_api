# Workflow Definition API

This is a FastAPI-based project to manage workflows, steps, and dependencies, and compute valid execution order.

## 📦 Features

- Create workflows
- Add steps to workflows
- Define dependencies between steps
- Retrieve workflow details with steps and dependencies
- Calculate valid execution order using topological sort
- Detect cycles in step dependencies

## 🚀 How to Run

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/workflow-api.git
cd workflow-api
```

### 2. Create virtual environment (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the server

```bash
uvicorn main:app --reload
```

Visit http://127.0.0.1:8000/docs for the interactive Swagger UI.

---

## 🧪 Sample Endpoints

### Create Workflow

```http
POST /workflows
Content-Type: application/json

{
  "workflow_str_id": "wf001",
  "name": "ETL Process"
}
```

### Add Step

```http
POST /workflows/wf001/steps
Content-Type: application/json

{
  "step_str_id": "stepA",
  "description": "Extract"
}
```

### Add Dependency

```http
POST /workflows/wf001/dependencies
Content-Type: application/json

{
  "step_str_id": "stepB",
  "prerequisite_step_str_id": "stepA"
}
```

### Get Workflow Details

```http
GET /workflows/wf001/details
```

### Get Execution Order

```http
GET /workflows/wf001/execution-order
```

---

## 📁 Tech Stack

- FastAPI
- SQLite
- SQLAlchemy
- Pydantic

---

## 🧠 Notes

- Prevents self-dependency
- Detects cycles in dependencies and raises error

---

## ✅ Author

Made with ❤️ by Rathod Ameen
