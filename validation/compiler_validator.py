
import os
import shlex
import subprocess
import tempfile
from pathlib import Path


def validate_with_compiler(sysml_text: str) -> dict:
    """
    Submit a SysML candidate to an externally configured validator.

    The configured command must accept a SysML file path
    as its final argument and return exit code 0 on success.
    """

    if not isinstance(sysml_text, str) or not sysml_text.strip():
        return {
            "success": False,
            "error": "EMPTY_CANDIDATE"
        }

    command = os.getenv("SYSML_VALIDATOR_CMD")

    if not command:
        return {
            "success": False,
            "error": "COMPILER_NOT_CONFIGURED",
            "message": "No external SysML validator is configured."
        }

    try:
        with tempfile.TemporaryDirectory() as temp_dir:

            candidate_path = Path(temp_dir) / "candidate.sysml"

            candidate_path.write_text(
                sysml_text,
                encoding="utf-8"
            )

            args = shlex.split(command) + [str(candidate_path)]

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "error": "COMPILER_REJECTED",
                    "compiler_output": result.stderr[:2000]
                }

            return {
                "success": True,
                "compiler_validated": True,
                "compiler_output": result.stdout[:2000]
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "COMPILER_TIMEOUT"
        }

    except Exception:
        return {
            "success": False,
            "error": "COMPILER_EXECUTION_FAILED"
        }
