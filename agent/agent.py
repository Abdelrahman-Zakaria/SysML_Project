
from agent.tool_registry import TOOL_REGISTRY
from validation.argument_validator import validate_tool_call


class Agent:

    def __init__(self, planner, max_tool_calls=5):

        self.planner = planner
        self.max_tool_calls = max_tool_calls

    def run(self, user_request: str):

        if not isinstance(user_request, str) or not user_request.strip():
            return {
                "success": False,
                "error": "INVALID_REQUEST"
            }

        # Ask the planner to select tools
        try:
            plan = self.planner.plan(user_request)
        except Exception:
            return {
                "success": False,
                "error": "PLANNING_FAILED"
            }

        if not isinstance(plan, dict):
            return {
                "success": False,
                "error": "INVALID_PLAN"
            }

        calls = plan.get("calls")

        if not isinstance(calls, list):
            return {
                "success": False,
                "error": "INVALID_PLAN"
            }

        if not calls:
            return {
                "success": False,
                "error": "NO_EVIDENCE",
                "message": "No suitable tool call was produced."
            }

        # Enforce the call limit
        if len(calls) > self.max_tool_calls:
            return {
                "success": False,
                "error": "TOOL_CALL_LIMIT_EXCEEDED"
            }

        results = []

        for call in calls:

            if not isinstance(call, dict):
                return {
                    "success": False,
                    "error": "INVALID_PLAN"
                }

            tool_name = call.get("tool_name")
            arguments = call.get("arguments")

            # Validate before execution
            validation = validate_tool_call(
                tool_name,
                arguments
            )

            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "results": results
                }

            # Retrieve the approved function
            tool_function = TOOL_REGISTRY[tool_name]["function"]

            # Execute the tool
            try:
                result = tool_function(**arguments)

            except Exception:
                return {
                    "success": False,
                    "error": "TOOL_EXECUTION_FAILED",
                    "results": results
                }

            # Never treat a failed tool as success
            if not isinstance(result, dict):
                return {
                    "success": False,
                    "error": "INVALID_TOOL_RESPONSE",
                    "results": results
                }

            if result.get("success") is not True:
                return {
                    "success": False,
                    "error": result.get(
                        "error",
                        "TOOL_EXECUTION_FAILED"
                    ),
                    "results": results
                }

            # Evidence must exist
            evidence = result.get("evidence")

            if not isinstance(evidence, str) or not evidence.strip():
                return {
                    "success": False,
                    "error": "NO_EVIDENCE",
                    "results": results
                }

            results.append({
                "tool_name": tool_name,
                "data": result
            })

        return {
            "success": True,
            "results": results
        }
