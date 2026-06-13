#!/bin/bash
# ==============================================================================
# SSIREN AI Agent EC2 Hot-Reload & Redeploy Script
# ==============================================================================

# 프로젝트 디렉토리 경로 (EC2 상의 경로에 맞게 자동 감지하거나 지정)
PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)

echo "=== 1. Moving to Project Directory: $PROJECT_DIR ==="
cd "$PROJECT_DIR" || exit 1

echo "=== 2. Pulling Latest Changes from GitHub ==="
git pull origin main

echo "=== 3. Checking Virtual Environment & Installing Dependencies ==="
if [ ! -d "venv" ]; then
    echo "Virtual environment (venv) not found. Creating one..."
    python3 -m venv venv
fi
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt

echo "=== 4. Stopping Running AI Server Processes ==="
# 1) 8000번 포트를 점유하고 있는 프로세스 종료 (lsof 사용)
if command -v lsof >/dev/null 2>&1; then
    PORT_PID=$(lsof -t -i:8000)
    if [ -n "$PORT_PID" ]; then
        echo "Killing processes on port 8000 (PIDs: $PORT_PID)..."
        echo "$PORT_PID" | xargs kill -9 2>/dev/null
        sleep 1
    fi
fi

# 2) 8000번 포트 강제 클리어 (fuser 사용)
if command -v fuser >/dev/null 2>&1; then
    fuser -k 8000/tcp >/dev/null 2>&1
fi

# 3) run.py 또는 uvicorn으로 띄워진 파이썬 프로세스들 찾아 종료
PIDS=$(ps -ef | grep -E 'run.py|uvicorn' | grep -v 'grep' | grep -v 'restart.sh' | awk '{print $2}')
if [ -n "$PIDS" ]; then
    echo "Stopping AI Server processes (PIDs: $PIDS)..."
    echo "$PIDS" | xargs kill -9 2>/dev/null
    sleep 1
else
    echo "No running AI Server processes found."
fi

echo "=== 5. Starting AI Server in Background ==="
# 가상환경의 python 바이너리를 직접 지정하여 실행합니다. (source activate 생략 가능)
nohup venv/bin/python run.py > app.log 2>&1 &
sleep 2

echo "=== 6. Verification ==="
PID_NEW=$(ps -ef | grep 'run.py' | grep -v 'grep' | grep -v 'restart.sh' | awk '{print $2}')
if [ -n "$PID_NEW" ]; then
    echo "AI Server successfully started (PID: $PID_NEW)!"
    echo "Checking last 10 lines of app.log:"
    tail -n 10 app.log
else
    echo "ERROR: Failed to start AI Server. Please check app.log"
    tail -n 20 app.log
fi
