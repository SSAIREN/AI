# 🚀 SSIREN AI Agent 배포 잔여 작업 체크리스트 (우회 방식 - PAT 사용)

조직의 권한 잠금을 우회하기 위해 **Personal Access Token(PAT)**을 사용하여 배포하는 절차입니다. 완료한 항목은 `[x]`로 체크해 주세요.

---

## 💻 1. 로컬 개발 PC 작업 목록 (Local Tasks)

- [x] **GitHub 개인 액세스 토큰 (PAT) 발급**
  - [x] GitHub Profile 클릭 ➔ **Settings** ➔ **Developer settings** ➔ **Personal access tokens** ➔ **Tokens (classic)** 이동
  - [x] **Generate new token (classic)** 클릭
  - [x] **`write:packages`** 권한 체크 (체크 시 `read:packages` 자동 활성화)
  - [x] 생성된 토큰 값(`ghp_...`)을 안전하게 복사해 두기


- [ ] **GitHub Secrets 등록 (4개 필수)**
  - [ ] GitHub 저장소 ➔ **Settings** ➔ **Secrets and variables** ➔ **Actions** ➔ **New repository secret** 클릭
  - [ ] `GHCR_PAT`: 방금 생성하고 복사한 개인 액세스 토큰 값 입력 (필수)
  - [ ] `EC2_HOST`: EC2 퍼블릭 IP 또는 도메인 주소 (예: `h14k009.p.ssafy.io`)
  - [ ] `EC2_USER`: `ubuntu`
  - [ ] `EC2_SSH_KEY`: EC2 접속에 사용하는 `.pem` 개인키 전체 텍스트 내용 입력

- [ ] **코드 Commit 및 push**
  - [ ] 작성된 툴 수정 및 배포 설정 코드를 `main` 브랜치에 push하여 배포 가동
  ```bash
  git add .
  git commit -m "feat: Dockerize FastAPI & GitHub Actions CI/CD with GHCR_PAT bypass"
  git push origin main
  ```

---

## ☁️ 2. AWS EC2 서버 작업 목록 (EC2 Tasks)

- [ ] **Docker 및 Compose v2 초기 설치 스크립트 실행**
  - [ ] EC2 SSH 접속 후 아래 명령어 실행
  ```bash
  curl -fsSL https://raw.githubusercontent.com/<깃허브_OWNER>/<깃허브_REPO>/main/setup.sh -o setup.sh
  chmod +x setup.sh
  ./setup.sh
  ```

- [ ] **EC2 SSH 재접속 (로그아웃 후 로그인)**
  - [ ] `exit` 명령어로 로그아웃 후 다시 접속하여 docker 권한 적용 확인

- [ ] **운영 환경변수 파일(`.env`) 생성 및 배치**
  - [ ] 배포 전용 격리 디렉토리(`/home/ubuntu/ai-agent`)로 이동
  - [ ] `.env` 파일을 새로 생성하고 실제 운영용 Key 값 기입 후 저장
  ```bash
  cd /home/ubuntu/ai-agent
  nano .env
  ```

- [ ] **최초 1회 GHCR 로그인**
  - [ ] 아래 명령어로 도커 로그인을 수동 1회 수행
  ```bash
  docker login ghcr.io -u <GitHub_아이디>
  # 비밀번호 입력 창에 발급받은 GHCR_PAT 입력
  ```
