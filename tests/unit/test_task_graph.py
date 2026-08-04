"""Unit tests for TaskGraph DAG dependency resolution and topological sort."""

import pytest
from app.planner.graph import TaskGraph, GraphCycleError
from app.planner.models import NodeStatus, NodeType, PlanNode


def test_task_graph_topological_sort():
    n1 = PlanNode(node_id="n1", description="Step 1", node_type=NodeType.TOOL, action="a1")
    n2 = PlanNode(node_id="n2", description="Step 2", node_type=NodeType.TOOL, action="a2", dependencies=["n1"])
    nodes = {"n1": n1, "n2": n2}

    graph = TaskGraph(nodes)
    topo = graph.topological_sort()
    assert [n.node_id for n in topo] == ["n1", "n2"]


def test_task_graph_cycle_detection():
    n1 = PlanNode(node_id="n1", description="Step 1", node_type=NodeType.TOOL, action="a1", dependencies=["n2"])
    n2 = PlanNode(node_id="n2", description="Step 2", node_type=NodeType.TOOL, action="a2", dependencies=["n1"])
    nodes = {"n1": n1, "n2": n2}

    with pytest.raises(GraphCycleError):
        TaskGraph(nodes)


def test_task_graph_get_ready_nodes():
    n1 = PlanNode(node_id="n1", description="Step 1", node_type=NodeType.TOOL, action="a1", status=NodeStatus.COMPLETED)
    n2 = PlanNode(node_id="n2", description="Step 2", node_type=NodeType.TOOL, action="a2", dependencies=["n1"], status=NodeStatus.PENDING)
    nodes = {"n1": n1, "n2": n2}

    graph = TaskGraph(nodes)
    ready = graph.get_ready_nodes()
    assert len(ready) == 1
    assert ready[0].node_id == "n2"
