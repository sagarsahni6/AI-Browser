from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
from backend.app.database.engine import get_db
from backend.app.database.repository import Repository
from backend.app.dependencies import verify_local_token

router = APIRouter(prefix="/agent/tasks", tags=["tasks"], dependencies=[Depends(verify_local_token)])

class CreateTaskRequest(BaseModel):
    title: str
    prompt: str

class TaskStepResponse(BaseModel):
    id: str
    step_number: int
    description: str
    tool_name: Optional[str] = None
    status: str
    result_json: Optional[str] = None
    error: Optional[str] = None

class TaskResponse(BaseModel):
    id: str
    title: str
    prompt: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: float
    completed_at: Optional[float] = None

class TaskDetailResponse(TaskResponse):
    steps: List[TaskStepResponse]

@router.get("", response_model=List[TaskResponse])
async def list_tasks(limit: int = 50, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    tasks = await repo.get_tasks(limit=limit)
    return [
        TaskResponse(
            id=t.id,
            title=t.title,
            prompt=t.prompt,
            status=t.status,
            result=t.result,
            error=t.error,
            created_at=t.created_at,
            completed_at=t.completed_at
        )
        for t in tasks
    ]

@router.post("", response_model=TaskResponse)
async def create_task(req: CreateTaskRequest, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    task = await repo.create_task(title=req.title, prompt=req.prompt)
    return TaskResponse(
        id=task.id,
        title=task.title,
        prompt=task.prompt,
        status=task.status,
        created_at=task.created_at
    )

@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    steps = await repo.get_task_steps(task_id)
    return TaskDetailResponse(
        id=task.id,
        title=task.title,
        prompt=task.prompt,
        status=task.status,
        result=task.result,
        error=task.error,
        created_at=task.created_at,
        completed_at=task.completed_at,
        steps=[
            TaskStepResponse(
                id=s.id,
                step_number=s.step_number,
                description=s.description,
                tool_name=s.tool_name,
                status=s.status,
                result_json=s.result_json,
                error=s.error
            )
            for s in steps
        ]
    )

@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, db: AsyncSession = Depends(get_db)):
    repo = Repository(db)
    task = await repo.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await repo.update_task_status(task_id, status="cancelled", error="Cancelled by user")
    return {"status": "cancelled", "id": task_id}
