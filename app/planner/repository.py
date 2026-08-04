"""SQLite Plan Repository for durable persistence of task graphs and execution logs."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.logger import JarvisLogger
from app.planner.interfaces import PlanRepository
from app.planner.models import (
    ExecutionStep,
    Goal,
    NodeStatus,
    NodeType,
    Plan,
    PlanNode,
    PlanStatus,
)

logger = JarvisLogger.get_logger("plan_repository")


class SQLitePlanRepository(PlanRepository):
    """Persists plans, DAG nodes, and execution steps to SQLite database."""

    def __init__(self, database_path: str = "data/jarvis.db") -> None:
        self.db_path = database_path
        self._mem_conn: Optional[sqlite3.Connection] = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:")
            self._mem_conn.row_factory = sqlite3.Row
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        if self._mem_conn is not None:
            return self._mem_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_schema(self) -> None:
        """Initializes database schema for plan persistence."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS planner_plans (
                    plan_id TEXT PRIMARY KEY,
                    goal_objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS planner_nodes (
                    node_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    dependencies_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL,
                    max_retries INTEGER NOT NULL,
                    verification_action TEXT,
                    rollback_action TEXT,
                    metadata_json TEXT NOT NULL,
                    FOREIGN KEY (plan_id) REFERENCES planner_plans (plan_id) ON DELETE CASCADE
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS planner_execution_logs (
                    step_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    arguments_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    output_text TEXT,
                    error_text TEXT
                )
            """)
            conn.commit()

    def save_plan(self, plan: Plan) -> None:
        """Saves or updates plan and all associated DAG nodes in SQLite."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO planner_plans (plan_id, goal_objective, status, created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(plan_id) DO UPDATE SET
                    status=excluded.status,
                    updated_at=excluded.updated_at,
                    metadata_json=excluded.metadata_json
                """,
                (
                    plan.plan_id,
                    plan.goal.objective,
                    plan.status.value,
                    plan.created_at.isoformat(),
                    plan.updated_at.isoformat(),
                    json.dumps(dict(plan.metadata))
                )
            )

            for node in plan.nodes.values():
                conn.execute(
                    """
                    INSERT INTO planner_nodes (
                        node_id, plan_id, description, node_type, action, arguments_json,
                        dependencies_json, status, retry_count, max_retries,
                        verification_action, rollback_action, metadata_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(node_id) DO UPDATE SET
                        status=excluded.status,
                        retry_count=excluded.retry_count,
                        metadata_json=excluded.metadata_json
                    """,
                    (
                        node.node_id,
                        plan.plan_id,
                        node.description,
                        node.node_type.value,
                        node.action,
                        json.dumps(dict(node.arguments)),
                        json.dumps(list(node.dependencies)),
                        node.status.value,
                        node.retry_count,
                        node.max_retries,
                        node.verification_action,
                        node.rollback_action,
                        json.dumps(dict(node.metadata))
                    )
                )
            conn.commit()

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Retrieves a plan and its DAG nodes from SQLite."""
        with self._get_connection() as conn:
            plan_row = conn.execute("SELECT * FROM planner_plans WHERE plan_id = ?", (plan_id,)).fetchone()
            if not plan_row:
                return None

            node_rows = conn.execute("SELECT * FROM planner_nodes WHERE plan_id = ?", (plan_id,)).fetchall()
            nodes: Dict[str, PlanNode] = {}
            for r in node_rows:
                node = PlanNode(
                    node_id=r["node_id"],
                    description=r["description"],
                    node_type=NodeType(r["node_type"]),
                    action=r["action"],
                    arguments=json.loads(r["arguments_json"]),
                    dependencies=json.loads(r["dependencies_json"]),
                    status=NodeStatus(r["status"]),
                    retry_count=r["retry_count"],
                    max_retries=r["max_retries"],
                    verification_action=r["verification_action"],
                    rollback_action=r["rollback_action"],
                    metadata=json.loads(r["metadata_json"])
                )
                nodes[node.node_id] = node

            goal = Goal(objective=plan_row["goal_objective"])
            created_at = datetime.fromisoformat(plan_row["created_at"])
            updated_at = datetime.fromisoformat(plan_row["updated_at"])

            return Plan(
                plan_id=plan_row["plan_id"],
                goal=goal,
                nodes=nodes,
                status=PlanStatus(plan_row["status"]),
                created_at=created_at,
                updated_at=updated_at,
                metadata=json.loads(plan_row["metadata_json"])
            )

    def list_plans(self) -> List[Plan]:
        """Lists all stored plans."""
        with self._get_connection() as conn:
            plan_rows = conn.execute("SELECT plan_id FROM planner_plans ORDER BY created_at DESC").fetchall()
            plans: List[Plan] = []
            for r in plan_rows:
                p = self.get_plan(r["plan_id"])
                if p:
                    plans.append(p)
            return plans

    def log_execution(self, step: ExecutionStep) -> None:
        """Logs an execution step to SQLite."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO planner_execution_logs (
                    step_id, plan_id, node_id, action, arguments_json, status,
                    start_time, end_time, output_text, error_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step.step_id,
                    step.plan_id,
                    step.node_id,
                    step.action,
                    json.dumps(step.arguments),
                    step.status.value,
                    step.start_time.isoformat(),
                    step.end_time.isoformat() if step.end_time else None,
                    str(step.output) if step.output is not None else None,
                    step.error_text
                )
            )
            conn.commit()
