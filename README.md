# SSIREN AI Agent Server 배포 및 CI/CD 가이드

이 프로젝트는 **FastAPI** 기반의 보이스피싱 탐지 AI 에이전트 서버입니다.  
**GitHub Actions**와 **Docker / Docker Compose**를 활용하여 AWS EC2 등에 자동으로 빌드 및 배포되는 파이프라인이 구축되어 있습니다.

---

## 🏗️ 1. CI/CD 배포 흐름 요약

```mermaid
flowchart LR
    A[Local Commit] -->|git push main| B(GitHub Action)
    B -->|1. Build & Tag| C(Docker Image)
    C -->|2. Push| D[GHCR (Github Registry)]
    B -->|3. SSH command| E[AWS EC2 Server]
    E -->|4. Docker compose pull| D
    E -->|5. Container run| F[FastAPI App (Port: 8000)]
```

1. **빌드 & 패키징 (GitHub)**: `main` 브랜치에 코드가 `push`되면, Docker 이미지가 빌드되고 **GHCR (GitHub Container Registry)**에 `latest` 및 `vYYYYMMDD-commitHash` 태그로 업로드됩니다.
2. **EC2 배포 명령 (SSH)**: GitHub Actions가 EC2 인스턴스에 SSH로 접속하여 `/home/ubuntu/ai-agent` 경로에 최신 `docker-compose.yml`을 배치하고 컨테이너를 재실행합니다.

---

## 🔑 2. GitHub Secrets 설정 가이드

GitHub Repository의 **Settings ➔ Secrets and variables ➔ Actions ➔ Repository secrets**에 아래 비밀값들을 반드시 등록해야 자동 배포가 이루어집니다.

| Secret Name | 설명 | 예시 / 입력값 |
| :--- | :--- | :--- |
| `EC2_HOST` | EC2 인스턴스의 퍼블릭 IP 또는 도메인 주소 | `h14k009.p.ssafy.io` 또는 `3.34.12.3` |
| `EC2_USER` | EC2 SSH 로그인 사용자명 | `ubuntu` |
| `EC2_SSH_KEY` | EC2 접속 시 사용하는 `.pem` 키의 **전체 텍스트** | `-----BEGIN RSA PRIVATE KEY----- ...` |
| `GHCR_PAT` | (선택) GitHub Private 저장소일 경우 GHCR 이미지 pull용 개인 토큰 | `ghp_...` 또는 `github_pat_...` *(Public 저장소로 전환하면 설정하지 않아도 무방)* |

---

## 🖥️ 3. EC2 서버 최초 셋업 (1회 필수)

서버 최초 배포 시, SSH로 EC2에 접속하여 아래 작업을 먼저 수행해야 합니다.

### ① Docker 및 Docker Compose v2 자동 설치
프로젝트에 포함된 `setup.sh` 스크립트를 사용하여 손쉽게 설치할 수 있습니다.
```bash
# setup.sh를 EC2에 복사하여 실행하거나 직접 명령어로 설치
curl -fsSL https://raw.githubusercontent.com/<OWNER>/<REPO>/main/setup.sh -o setup.sh
chmod +x setup.sh
./setup.sh
```
*설치 후 **SSH 세션을 나갔다가 다시 로그인**해야 sudo 없이 docker 명령어를 사용할 수 있는 그룹 권한이 적용됩니다.*

### ② 배포 디렉토리 확인 및 `.env` 파일 배치
파이썬 AI 서버 작동을 위해 배포 폴더 내에 환경 변수 파일(`.env`)을 **수동으로 직접 생성**해주어야 합니다. (보안상의 이유로 Git에 포함되지 않습니다.)
```bash
cd /home/ubuntu/ai-agent
nano .env
```

**`.env` 설정 내용 예시:**
```env
# FastAPI 앱 설정
PORT=8000
HOST="0.0.0.0"

# GMS API/OpenAI 설정
OPENAI_API_KEY="your-gms-api-key"
OPENAI_API_BASE="https://gms.ssafy.io/gmsapi/api.openai.com/v1"
OPENAI_MODEL="gpt-5-nano"

# Spring 백엔드 통신 설정
SPRING_API_URL="http://localhost:8080"
SPRING_INTERNAL_API_KEY="dummy"

# LangSmith 설정 (데모 발표 추적용)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY="your-langsmith-pat-key"
LANGCHAIN_PROJECT="SSAIREN"
```

---

## 🛠️ 4. 트러블슈팅 (Troubleshooting)

### Q1. GitHub Actions 빌드 시 `denied: Permission to write to package` 에러 발생
- **원인**: GitHub Actions 워크플로우에 GHCR 패키지 쓰기 권한이 부여되지 않았습니다.
- **해결**: Repository ➔ Settings ➔ Actions ➔ General ➔ **Workflow permissions**로 이동하여 **"Read and write permissions"**에 체크하고 저장해 주세요.

### Q2. EC2 배포 시 `image pull access denied` 에러 발생
- **원인**: GitHub 저장소가 **Private(비공개)** 상태일 때, EC2에 배포할 때 GHCR에 로그인되어 있지 않아 발생합니다.
- **해결**: 
  1. GitHub Profile Settings에서 `write:packages`/`read:packages` 권한을 가진 **Personal Access Token (PAT)**를 발급받습니다.
  2. GitHub Secrets에 `GHCR_PAT` 이름으로 등록합니다.
  3. 또는 GitHub 저장소를 **Public(공개)** 상태로 전환하면 별도 로그인 없이도 이미지 pull이 가능해집니다.

### Q3. 기존 Spring Boot 컨테이너와 포트가 충돌하나요?
- **답변**: **충돌하지 않습니다.** 
- 스프링은 호스트의 `8080` 포트를 점유하고 있고, 본 AI 서비스는 호스트의 `8000` 포트를 매핑하여 별도의 격리된 디렉토리(`/home/ubuntu/ai-agent`)에서 작동하므로 리소스나 네트워크 간섭 없이 안전하게 공존할 수 있습니다.
