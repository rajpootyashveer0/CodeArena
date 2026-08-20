import subprocess
import sys
import tempfile
import os


def run_python_code(code: str, input_data: str, timeout: int = 3):
    temp_file = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as f:
            f.write(code)
            temp_file = f.name

        result = subprocess.run(
            [sys.executable, temp_file],
            input=input_data,
            text=True,
            capture_output=True,
            timeout=timeout
        )

        if result.returncode != 0:
            return {
                "success": False,
                "output": result.stderr.strip()
            }

        return {
            "success": True,
            "output": result.stdout.strip()
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "Time Limit Exceeded"
        }

    finally:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)