"""calculator skill — safe arithmetic evaluator."""

import ast
import operator

_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_node(node):
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPERATORS:
        return _OPERATORS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"not allowed in the calculator: {type(node).__name__}")


def calculator(expression: str) -> str:
    """Evaluate arithmetic: numbers, + - * / // % ** and parentheses."""
    try:
        tree = ast.parse(expression, mode="eval")
        value = _eval_node(tree)
    except (SyntaxError, ValueError, ZeroDivisionError, TypeError, OverflowError) as e:
        return f"Error: could not evaluate '{expression}': {e}"
    return f"Result: {value}"


TOOLS = {"calculator": calculator}
TOOL_SCHEMAS = [{
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "Evaluates a math expression. Use this for any arithmetic.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate, e.g. '23 * 7'",
                }
            },
            "required": ["expression"],
        },
    },
}]
