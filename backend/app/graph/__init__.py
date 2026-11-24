"""
LangGraph multi-agent orchestration runtime for the AI Browser.

This module provides a stateful graph-based execution engine that runs
alongside (and can eventually replace) the legacy SupervisorAgent.

Entry points:
    - GraphRunner.run_task(task_id)         → start a new graph-driven task
    - GraphRunner.resume_approved_task(...) → resume after user approval
    - GraphRunner.cancel_task(task_id)      → mark task cancelled

The graph is selected via engine="langgraph" in the tasks.create RPC call.
"""
