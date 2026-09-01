"""Tests for the calculator skill.

These cover both the happy path (correct math) and the security property
the AST whitelist is supposed to provide: code injection attempts must
bounce. If any of these tests start failing, the safety guarantee has
been broken — a real injection, not a UI regression."""

import unittest
import sys
from pathlib import Path

# Make the project root importable when running tests directly.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from skills.calculator.code import calculator


class TestCalculatorMath(unittest.TestCase):
    """The happy path. The model uses this for real arithmetic; if it
    breaks, every multi-step problem is wrong."""

    def test_simple(self):
        self.assertEqual(calculator("2 + 2"), "Result: 4")

    def test_multiplication(self):
        self.assertEqual(calculator("23 * 7"), "Result: 161")

    def test_precedence(self):
        self.assertEqual(calculator("2 + 3 * 4"), "Result: 14")

    def test_parentheses(self):
        self.assertEqual(calculator("(2 + 3) * 4"), "Result: 20")

    def test_floats(self):
        result = calculator("0.1 + 0.2")
        # Don't use exact equality — IEEE 754. Just check it's a Result: line.
        self.assertTrue(result.startswith("Result: "))
        self.assertAlmostEqual(float(result.split(": ")[1]), 0.3, places=6)

    def test_unary_minus(self):
        self.assertEqual(calculator("-5 + 10"), "Result: 5")

    def test_power(self):
        self.assertEqual(calculator("2 ** 10"), "Result: 1024")

    def test_division_by_zero(self):
        result = calculator("1/0")
        self.assertIn("Error", result)
        self.assertIn("division by zero", result)

    def test_modulo(self):
        self.assertEqual(calculator("10 % 3"), "Result: 1")


class TestCalculatorSecurity(unittest.TestCase):
    """The property the AST whitelist exists to enforce: only numbers and
    arithmetic operators reach the evaluator. Anything else is rejected
    at parse time, before execution."""

    def test_function_call_rejected(self):
        # The classic eval-injection: a function call. Our AST allows no
        # function-call node, so this must fail with a 'not allowed' error.
        result = calculator("__import__('os').getcwd()")
        self.assertIn("Error", result)
        self.assertIn("not allowed", result)

    def test_attribute_access_rejected(self):
        result = calculator("(1).__class__")
        self.assertIn("Error", result)

    def test_string_rejected(self):
        result = calculator("'hello'")
        self.assertIn("Error", result)

    def test_list_comprehension_rejected(self):
        result = calculator("[x for x in range(10)]")
        self.assertIn("Error", result)

    def test_lambda_rejected(self):
        result = calculator("lambda x: x + 1")
        self.assertIn("Error", result)

    def test_empty_input(self):
        result = calculator("")
        self.assertIn("Error", result)


if __name__ == "__main__":
    unittest.main()
