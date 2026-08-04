"""Calculator Example Plugin for Jarvis Plugin SDK."""

import ast
import operator
from typing import Any, Dict
from app.plugins.interfaces import Plugin
from app.plugins.sdk import JarvisPluginSDK
from app.tools.base import BaseTool
from app.tools.models import ToolPermission, ToolResult


class CalculateExpressionTool(BaseTool):
    """Safely evaluates basic arithmetic math expressions."""

    name = "calculate_expression"
    description = "Evaluates basic math expressions safely."
    permission_level = ToolPermission.SAFE

    parameters = {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Math expression string (e.g. '12 * (4 + 8)')."}
        },
        "required": ["expression"]
    }

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "permission_level": self.permission_level.value,
            "parameters": self.parameters
        }

    def execute(self, **kwargs: Any) -> ToolResult:
        expr = kwargs.get("expression", "")
        try:
            val = self._eval_expr(expr)
            return ToolResult(tool_name=self.name, success=True, output={"expression": expr, "result": val})
        except Exception as e:
            return ToolResult(tool_name=self.name, success=False, output={}, error=f"Calculation error: {e}")

    def _eval_expr(self, expr: str) -> float:
        operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.USub: operator.neg,
        }

        def _eval(node: Any) -> float:
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return float(node.value)
            if isinstance(node, ast.BinOp):
                return operators[type(node.op)](_eval(node.left), _eval(node.right))
            if isinstance(node, ast.UnaryOp):
                return operators[type(node.op)](_eval(node.operand))
            raise ValueError(f"Unsupported syntax in math expression.")

        parsed = ast.parse(expr, mode="eval")
        return _eval(parsed.body)


class CalculatorPlugin(Plugin):
    """Plugin implementation for Calculator example."""

    def initialize(self, sdk: JarvisPluginSDK) -> None:
        self.sdk = sdk

    def shutdown(self) -> None:
        pass

    def register_tools(self, sdk: JarvisPluginSDK) -> None:
        sdk.tools.register(CalculateExpressionTool())
