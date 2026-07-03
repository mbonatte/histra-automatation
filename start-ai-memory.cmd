@echo off
setlocal EnableExtensions

title ai-memory server

REM ============================================================
REM  ai-memory portable project launcher
REM
REM  Put this file in the root of your project.
REM
REM  It will use:
REM    <this folder>\ai-memory
REM
REM  It loads secrets/config from:
REM    <this folder>\.env
REM ============================================================

REM Folder where this .cmd file lives.
set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

set "AI_MEMORY_EXE=%LOCALAPPDATA%\ai-memory\ai-memory.exe"
set "AI_MEMORY_DATA_DIR=%PROJECT_ROOT%\ai-memory"
set "AI_MEMORY_SERVER_URL=http://127.0.0.1:49374"

REM Defaults. These can be overridden in .env.
set "AI_MEMORY_LLM_PROVIDER=openai-oauth"
set "AI_MEMORY_LLM_MODEL=gpt-5-mini"
set "AI_MEMORY_BIND=127.0.0.1:49374"

REM Central OpenAI OAuth token location.
set "AI_MEMORY_CENTRAL_AUTH=%LOCALAPPDATA%\ai-memory\auth.json"
set "AI_MEMORY_PROJECT_AUTH=%AI_MEMORY_DATA_DIR%\auth.json"

REM Load .env from the same folder as this launcher.
set "ENV_FILE=%PROJECT_ROOT%\.env"

if exist "%ENV_FILE%" (
    echo Loading .env:
    echo   %ENV_FILE%
    echo.

    for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
        if not "%%A"=="" (
            set "%%A=%%B"
        )
    )
) else (
    echo WARNING: .env file not found:
    echo   %ENV_FILE%
    echo.
    echo Create one from .env.example and set AI_MEMORY_AUTH_TOKEN.
    echo.
)

echo.
echo ============================================================
echo  ai-memory server
echo ============================================================
echo.
echo Project root:
echo   %PROJECT_ROOT%
echo.
echo Executable:
echo   %AI_MEMORY_EXE%
echo.
echo Data dir:
echo   %AI_MEMORY_DATA_DIR%
echo.
echo Server:
echo   %AI_MEMORY_SERVER_URL%
echo.
echo LLM provider:
echo   %AI_MEMORY_LLM_PROVIDER%
echo.
echo LLM model:
echo   %AI_MEMORY_LLM_MODEL%
echo.

if not exist "%AI_MEMORY_EXE%" (
    echo ERROR: ai-memory.exe was not found at:
    echo   %AI_MEMORY_EXE%
    echo.
    echo Check your installation path.
    echo.
    pause
    exit /b 1
)

if not exist "%AI_MEMORY_DATA_DIR%" (
    echo Creating data directory...
    mkdir "%AI_MEMORY_DATA_DIR%"
)

if not exist "%AI_MEMORY_DATA_DIR%\config.toml" (
    echo.
    echo No config.toml found in this project's ai-memory data directory.
    echo Running first-time init...
    echo.
    "%AI_MEMORY_EXE%" --data-dir "%AI_MEMORY_DATA_DIR%" init

	echo Removing [auth] block from config.toml for local no-token mode...
	powershell -NoProfile -ExecutionPolicy Bypass -Command ^
	  "$p = '%AI_MEMORY_DATA_DIR%\config.toml';" ^
	  "$text = Get-Content $p -Raw;" ^
	  "$text = [regex]::Replace($text, '(?ms)^\[auth\]\r?\n(?:^(?!\[).*\r?\n?)*', '');" ^
	  "Set-Content -Path $p -Value $text -Encoding UTF8"

    echo.
    echo IMPORTANT:
    echo   A new config.toml was created here:
    echo   %AI_MEMORY_DATA_DIR%\config.toml
    echo.
	echo Local no-token mode configured.
	echo The [auth] block was removed from config.toml automatically.
	echo.
    echo If you use auth, either:
    echo   1. set AI_MEMORY_AUTH_TOKEN in .env, and
    echo   2. ensure [auth].bearer_token in config.toml matches it
    echo.
    echo Then close this window and run this launcher again.
    echo.
    pause
    exit /b 0
)

REM Make the project data-dir see the central OpenAI OAuth auth.json.
if not exist "%AI_MEMORY_CENTRAL_AUTH%" (
    echo.
    echo WARNING: central OAuth auth.json was not found:
    echo   %AI_MEMORY_CENTRAL_AUTH%
    echo.
    echo To create it, run:
    echo   ai-memory --data-dir "%LOCALAPPDATA%\ai-memory" auth login openai-oauth
    echo.
    echo The server will still start, but LLM provider may not work.
    echo.
) else (
    if not exist "%AI_MEMORY_PROJECT_AUTH%" (
        echo Creating hard link for OAuth auth.json...
        powershell -NoProfile -ExecutionPolicy Bypass -Command ^
            "New-Item -ItemType HardLink -Path '%AI_MEMORY_PROJECT_AUTH%' -Target '%AI_MEMORY_CENTRAL_AUTH%' | Out-Null"
    )
)

cd /d "%PROJECT_ROOT%"

REM Do not rerun install-instructions if AGENTS.md already exists,
REM because ai-memory creates AGENTS.md.bak-* backup files.
if not exist "%PROJECT_ROOT%\AGENTS.md" (
    echo.
    echo AGENTS.md not found.
    echo Installing ai-memory instructions for Codex...
    echo.
    "%AI_MEMORY_EXE%" --data-dir "%AI_MEMORY_DATA_DIR%" install-instructions --target AGENTS.md
) else (
    echo.
    echo AGENTS.md already exists.
    echo Skipping install-instructions to avoid creating AGENTS.md.bak-* files.
    echo.
)

REM ============================================================
REM  Install Codex integration
REM ============================================================

echo Installing ai-memory MCP config for Codex...
"%AI_MEMORY_EXE%" --data-dir "%AI_MEMORY_DATA_DIR%" install-mcp --client codex --apply

echo.
echo Installing ai-memory hooks for Codex...
"%AI_MEMORY_EXE%" --data-dir "%AI_MEMORY_DATA_DIR%" install-hooks --agent codex --apply --project-strategy repo-root

REM ============================================================
REM  Install Antigravity integration
REM ============================================================

echo.
echo Installing ai-memory MCP config for Antigravity...
"%AI_MEMORY_EXE%" --data-dir "%AI_MEMORY_DATA_DIR%" install-mcp --client antigravity --apply

echo.
echo Installing ai-memory hooks for Antigravity...
"%AI_MEMORY_EXE%" --data-dir "%AI_MEMORY_DATA_DIR%" install-hooks --agent antigravity --apply --project-strategy repo-root

echo.
echo Current ai-memory status:
echo.
"%AI_MEMORY_EXE%" --data-dir "%AI_MEMORY_DATA_DIR%" status

echo.
echo ============================================================
echo  Starting ai-memory server
echo ============================================================
echo.
echo Keep this window open while using Codex.
echo Press Ctrl+C to stop the server.
echo.
echo ============================================================
echo.

"%AI_MEMORY_EXE%" --data-dir "%AI_MEMORY_DATA_DIR%" serve --transport http --bind "%AI_MEMORY_BIND%" --enable-web

echo.
echo ai-memory server stopped.
echo.
pause
