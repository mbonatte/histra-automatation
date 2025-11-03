import subprocess

EXE_PATH = r"C:\Program Files\Gruppo Sismica\HiStrA Bridges 2024.1.1\SolverHistra.exe"

class SolverRunError(Exception):
    """Raised when the solver fails to execute properly."""
    def __init__(self, file_path: str, message: str):
        super().__init__(message)
        self.file_path = file_path


from pathlib import Path
PSEXEC_PATH = r"C:\Users\mbonatte\Documents\Coding\histra-automation\PSTools\PsExec.exe"
def run_program(model_path, mode="psexec", timeout_seconds=600):
    model_path = Path(model_path)
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
        return result.stdout.strip()

    except subprocess.TimeoutExpired:
        print(f"⏰ Timeout: {model_path} exceeded {timeout_seconds} seconds. Killing...")
        subprocess.run(["taskkill", "/IM", "SolverHistra.exe", "/F"], capture_output=True)
        raise

    except subprocess.CalledProcessError as e:
        print("❌ Solver returned an error.")
        print(f"Model path:\n", model_path)
        print("STDOUT:\n", e.stdout)
        print("STDERR:\n", e.stderr)
        if "with error code 1" in e.stderr:
            raise SolverRunError(
                model_path,
                e.stderr,
            )
        if "StackOverflowException" in e.stderr:
            raise SolverRunError(
                model_path,
                e.stderr,
            )
        raise