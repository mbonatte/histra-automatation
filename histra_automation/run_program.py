import subprocess
from pathlib import Path

EXE_PATH = r"C:\Program Files\Gruppo Sismica\HiStrA Bridges 2025.1.6\SolverHistra.exe"
PSEXEC_PATH = r"C:\Users\mbonatte\Documents\Coding\histra-automation\PSTools\PsExec.exe"

class SolverRunError(Exception):
    """Raised when the solver fails to execute properly."""
    def __init__(self, file_path: str, message: str):
        super().__init__(message)
        self.file_path = file_path


def run_program(model_path, mode="psexec", timeout_seconds=600):
    model_path = Path(model_path).resolve()

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    if mode == "psexec":
        cmd = [
            PSEXEC_PATH,
            "-accepteula",
            "-nobanner",
            "-i", "1",
            "-h",
            EXE_PATH,
            "run",
            str(model_path),
            "-CloseWithoutAsk", "true",
        ]
    elif mode == "local":
        cmd = [
            EXE_PATH,
            "run",
            str(model_path),
            "-CloseWithoutAsk", "true",
        ]
    else:
        raise ValueError(f"Invalid mode '{mode}'. Must be 'psexec' or 'local'.")



    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=True
        )

        print("\nSolver finished successfully.")
        print(f"Return code: {result.returncode}")

        print("\n--- STDOUT ---")
        print(decode_output(result.stdout))

        print("\n--- STDERR ---")
        print(decode_output(result.stderr))

        return result.stdout.strip()

    except subprocess.TimeoutExpired as e:
        stdout_text = decode_output(e.stdout)
        stderr_text = decode_output(e.stderr)

        print(f"Timeout: {model_path} exceeded {timeout_seconds} seconds. Killing...")

        print("\n--- PARTIAL STDOUT ---")
        print(stdout_text)

        print("\n--- PARTIAL STDERR ---")
        print(stderr_text)

        print("\nKilling SolverHistra.exe...")

        subprocess.run(
            ["taskkill", "/IM", "SolverHistra.exe", "/F"],
            capture_output=True,
            text=True,
        )

        if "StackOverflowException" in stderr_text:
            raise SolverRunError(
                str(model_path),
                f"Solver crashed with StackOverflowException while processing: {model_path}"
            ) from e

        raise

    except subprocess.CalledProcessError as e:
        stdout_text = decode_output(e.stdout)
        stderr_text = decode_output(e.stderr)

        print("\nSolver returned an error.")
        print(f"Return code: {e.returncode}")
        print(f"Model path:\n", model_path)

        print("\n--- STDOUT ---")
        print(stdout_text)

        print("\n--- STDERR ---")
        print(stderr_text)

        if "with error code 1" in stderr_text:
            raise SolverRunError(
                model_path,
                stderr_text,
            )
        if "StackOverflowException" in stderr_text:
            raise SolverRunError(
                model_path,
                stderr_text,
            )
        raise

def decode_output(value):
    if value is None:
        return "[empty]"

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace") or "[empty]"

    return value or "[empty]"
