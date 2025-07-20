from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import relationship, sessionmaker, Session, declarative_base
from typing import List, Optional
from pydantic import BaseModel

DATABASE_URL = "sqlite:///./test.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()

# ---------------------------- Models ----------------------------

class Workflow(Base):
    __tablename__ = 'workflows'
    id = Column(Integer, primary_key=True, index=True)
    workflow_str_id = Column(String, unique=True, index=True)
    name = Column(String)
    steps = relationship("Step", back_populates="workflow")

class Step(Base):
    __tablename__ = 'steps'
    id = Column(Integer, primary_key=True, index=True)
    step_str_id = Column(String, unique=True, index=True)
    description = Column(String)
    workflow_id = Column(Integer, ForeignKey("workflows.id"))
    workflow = relationship("Workflow", back_populates="steps")
    dependencies = relationship("Dependency", back_populates="step", foreign_keys="Dependency.step_id")

class Dependency(Base):
    __tablename__ = 'dependencies'
    id = Column(Integer, primary_key=True, index=True)
    step_id = Column(Integer, ForeignKey("steps.id"))
    prerequisite_id = Column(Integer, ForeignKey("steps.id"))
    step = relationship("Step", foreign_keys=[step_id], back_populates="dependencies")
    prerequisite = relationship("Step", foreign_keys=[prerequisite_id])

Base.metadata.create_all(bind=engine)

# ---------------------------- Schemas ----------------------------

class WorkflowCreate(BaseModel):
    workflow_str_id: str
    name: str

class StepCreate(BaseModel):
    step_str_id: str
    description: str

class DependencyCreate(BaseModel):
    step_str_id: str
    prerequisite_step_str_id: str

class StepDetail(BaseModel):
    step_str_id: str
    description: str
    prerequisites: List[str] = []

class WorkflowDetails(BaseModel):
    workflow_str_id: str
    name: str
    steps: List[StepDetail]

# ---------------------------- Dependency ----------------------------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------- Routes ----------------------------

@app.post("/workflows")
def create_workflow(workflow: WorkflowCreate, db: Session = Depends(get_db)):
    db_wf = Workflow(workflow_str_id=workflow.workflow_str_id, name=workflow.name)
    db.add(db_wf)
    db.commit()
    db.refresh(db_wf)
    return {"internal_db_id": db_wf.id, "workflow_str_id": db_wf.workflow_str_id, "status": "created"}

@app.post("/workflows/{workflow_str_id}/steps")
def add_step(workflow_str_id: str, step: StepCreate, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter_by(workflow_str_id=workflow_str_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    new_step = Step(step_str_id=step.step_str_id, description=step.description, workflow=wf)
    db.add(new_step)
    db.commit()
    db.refresh(new_step)
    return {"internal_db_id": new_step.id, "step_str_id": new_step.step_str_id, "status": "step_added"}

@app.post("/workflows/{workflow_str_id}/dependencies")
def add_dependency(workflow_str_id: str, dep: DependencyCreate, db: Session = Depends(get_db)):
    if dep.step_str_id == dep.prerequisite_step_str_id:
        raise HTTPException(status_code=400, detail="A step cannot depend on itself")

    wf = db.query(Workflow).filter_by(workflow_str_id=workflow_str_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    step = db.query(Step).filter_by(step_str_id=dep.step_str_id, workflow_id=wf.id).first()
    prereq = db.query(Step).filter_by(step_str_id=dep.prerequisite_step_str_id, workflow_id=wf.id).first()

    if not step or not prereq:
        raise HTTPException(status_code=404, detail="Step(s) not found")

    db_dep = Dependency(step=step, prerequisite=prereq)
    db.add(db_dep)
    db.commit()
    return {"status": "dependency_added"}

@app.get("/workflows/{workflow_str_id}/details", response_model=WorkflowDetails)
def get_workflow_details(workflow_str_id: str, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter_by(workflow_str_id=workflow_str_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps_output = []
    for step in wf.steps:
        prereqs = db.query(Dependency).filter_by(step_id=step.id).all()
        prereq_ids = [db.query(Step).get(p.prerequisite_id).step_str_id for p in prereqs]
        steps_output.append(StepDetail(
            step_str_id=step.step_str_id,
            description=step.description,
            prerequisites=prereq_ids
        ))

    return WorkflowDetails(
        workflow_str_id=wf.workflow_str_id,
        name=wf.name,
        steps=steps_output
    )

@app.get("/workflows/{workflow_str_id}/execution-order")
def get_execution_order(workflow_str_id: str, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter_by(workflow_str_id=workflow_str_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps = wf.steps
    graph = {step.step_str_id: [] for step in steps}
    indegree = {step.step_str_id: 0 for step in steps}

    for step in steps:
        deps = db.query(Dependency).filter_by(step_id=step.id).all()
        for d in deps:
            prereq_step = db.query(Step).get(d.prerequisite_id)
            graph[prereq_step.step_str_id].append(step.step_str_id)
            indegree[step.step_str_id] += 1

    # Kahn's algorithm
    queue = [node for node in indegree if indegree[node] == 0]
    result = []
    while queue:
        current = queue.pop(0)
        result.append(current)
        for neighbor in graph[current]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(steps):
        raise HTTPException(status_code=400, detail="cycle_detected")

    return {"order": result"}
