import logging
import subprocess
from pathlib import Path

EXE_PATH = r"C:\Program Files\Gruppo Sismica\HiStrA Bridges 2025.1.6\SolverHistra.exe"
PSEXEC_PATH = r"C:\Users\mbonatte\Documents\Coding\histra-automation\PSTools\PsExec.exe"

logger = logging.getLogger(__name__)

class SolverRunError(Exception):
    """Raised when the solver fails to execute properly."""
    def __init__(self, file_path: str, message: str):
        super().__init__(message)
        self.file_path = file_path


def run_program(model_path, mode="psexec", timeout_seconds=600, print_output: bool = False):
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

        logger.info("Solver finished successfully. Return code: %s", result.returncode)
        if print_output:
            logger.info("--- STDOUT ---\n%s", decode_output(result.stdout))
            logger.info("--- STDERR ---\n%s", decode_output(result.stderr))

        return result.stdout.strip()

    except subprocess.TimeoutExpired as e:
        stdout_text = decode_output(e.stdout)
        stderr_text = decode_output(e.stderr)

        logger.error("Timeout: %s exceeded %s seconds. Killing...", model_path, timeout_seconds)
        if print_output:
            logger.error("--- PARTIAL STDOUT ---\n%s", stdout_text)
            logger.error("--- PARTIAL STDERR ---\n%s", stderr_text)

        logger.error("Killing SolverHistra.exe...")

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

        logger.error("Solver returned an error. Return code: %s", e.returncode)
        logger.error("Model path:\n%s", model_path)
        if print_output:
            logger.error("--- STDOUT ---\n%s", stdout_text)
            logger.error("--- STDERR ---\n%s", stderr_text)

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
