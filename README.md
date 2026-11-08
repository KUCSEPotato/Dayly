# Dayly / Personal Todo Management

## Project Overview

Dayly는 개인의 할 일을 날짜별로 관리하고, 수행 내역과 달성률을 통해 자신의 활동을 돌아볼 수 있는 **로컬 단일 사용자용 생산성 관리 웹 서비스**입니다.

FastAPI를 학습하면서 실제로 사용할 수 있는 앱을 만드는 것이 개발 배경입니다. React 화면, FastAPI API, SQLite를 연결하고, Router·Schema·Model·Service의 역할을 분리해 요청 처리와 데이터 저장 흐름을 코드로 이해할 수 있도록 구성했습니다.

현재 구현 버전은 **v0.2.1**입니다. 실시간 할 일 관리에 더해, Task Events로 과거 상태를 복원한 고정 회고와 경험치 기록을 제공합니다. 앱 실행 시 샘플 데이터를 자동으로 넣지 않습니다.

프로젝트 버전은 `v0.2.1`, 개발 브랜치는 `dev-v0.2.1`처럼 표기합니다. 버전별 변경 내역은 [Release Notes](#release-notes)에서 확인할 수 있습니다.

## Features

### Task Management

- 날짜별 할 일 생성·조회·수정·삭제, 제목·설명·예정 날짜 관리
- 완료 체크 및 해제, 완료 시각 기록, 완료 항목의 시각적 구분
- 월간 달력 이동, 오늘·선택 날짜 강조, 날짜별 완료/전체 개수 표시
- API 저장 성공 후 목록·달력·통계 갱신, 실패 시 오류 표시와 폼 입력 보존

### Progress Tracking

- 오늘 / 최근 7일 달성률 전환, 완료 개수와 Progress Bar
- 선택 날짜의 달성률과 최근 7일의 일별 막대그래프
- 전체 할 일 수를 기준으로 계산하는 주간 달성률

### Retrospectives

- 일간·주간·월간 고정 회고, 이전/다음 기간 이동
- Task Events를 이용한 날짜별 종료 시점 상태 복원
- Snapshot에 통계·완료/미완료 Task 사본·기간 XP를 저장하고 고정
- 일별 그래프, 월간 주차별 완료 개수, 가장 많이 완료한 날짜 표시
- 활동 기록 없음·부분 기록·복원 불가·미종료 기간 구분

### Growth System

- Task 최초 추적 완료에 따른 XP, 확정 일일 달성률 보너스와 일일 상한
- 누적 XP·현재 레벨·다음 레벨 진행률·지급 내역 조회
- 반복 완료·재조회·서버 재시작에 따른 중복 지급 방지

### Workspace

- **나의 하루**, **나만의 회고**, **나만의 세계** 메뉴
- 달성률 카드에서 일간/주간 회고로 이동
- 모바일 대응과 로딩·오류·재시도 상태
- Forest / Ocean 소개와 Coming Soon 화면. 실제 성장 이미지·애니메이션은 개발 예정입니다.

## Tech Stack

| 영역 | 기술 | 역할 |
|---|---|---|
| Frontend | React 19, TypeScript | 컴포넌트와 화면 상태, API 응답 타입 |
| Frontend | Vite, Tailwind CSS 4, Lucide React | 개발 서버·빌드, 스타일, 아이콘 |
| Backend | Python 3.11+, FastAPI, Uvicorn | REST API, OpenAPI 문서, ASGI 서버 |
| Backend | Pydantic 2, pydantic-settings | 입출력 검증·직렬화, 환경 설정 |
| Database | SQLite, SQLAlchemy 2.x | 로컬 영속 저장과 ORM |
| Database | Alembic | 버전별 스키마 마이그레이션 |
| Testing | pytest, FastAPI TestClient, HTTPX | API·도메인 로직·마이그레이션 검증 |
| Testing | Playwright, TypeScript | 실제 API를 사용하는 브라우저 테스트와 타입 검사 |
| Infrastructure / DevOps | Docker, Docker Compose, Nginx | 실행 환경 구성, 정적 화면 제공, API 프록시 |
| Development Tools | uv, npm | 의존성 및 잠금 파일 관리 |

달력과 통계 차트는 React/CSS로 직접 구현했습니다. PostgreSQL은 향후 전환을 고려한 대상이며 현재 검증된 DB는 SQLite입니다.

## Getting Started

### Prerequisites

- Docker 실행: Docker Desktop 또는 Docker Engine과 Docker Compose v2. 스크립트의 `docker compose … --wait`를 지원해야 합니다.
- Docker 없이 개발: Python 3.11 이상, [uv](https://docs.astral.sh/uv/getting-started/installation/), Node.js 22.12 이상과 npm
- 아래 명령은 별도의 `cd` 표시가 없으면 프로젝트 루트에서 실행합니다.

기본값으로 실행할 때 환경 파일은 필수가 아닙니다. 설정을 바꾸려면 아래 [Environment Variables](#environment-variables)의 예시 파일을 사용하세요.

### Development Server — 8081

Docker를 실행한 뒤 기존 개발 스크립트를 사용합니다.

```bash
sh deploy/dev.sh
```

- 서비스: http://localhost:8081
- Swagger UI: http://localhost:8081/docs

첫 실행은 이미지를 빌드합니다. 백엔드는 `alembic upgrade head` 성공 후 시작하며, 스크립트는 서비스 준비 상태까지 기다립니다. 같은 명령으로 코드 변경 후 재빌드할 수 있습니다.

```bash
sh deploy/dev.sh ps    # 상태 확인
sh deploy/dev.sh logs  # 로그 확인
sh deploy/dev.sh down  # 종료, 개발 데이터 유지
```

개발 DB는 `dayly-dev_dev-data` 볼륨에 저장합니다. 종료·컨테이너 재생성·재빌드 후에도 유지됩니다. 8081 포트를 다른 서버가 사용 중이면 해당 서버를 종료한 뒤 다시 실행하세요.

직접 Compose를 사용할 때는 개발 파일 하나만 선택합니다.

```bash
docker compose -f compose.dev.yaml up -d --build --wait
docker compose -f compose.dev.yaml down
```

`compose.yaml`과 `compose.dev.yaml`은 각각 독립 설정입니다. 두 파일을 함께 병합해 실행하지 않습니다.

### Main / Production Environment — 8080

기본 개인 사용 환경은 `compose.yaml`로 실행합니다. 여기서 Production은 로컬 사용 환경을 뜻하며 공개 인터넷 배포 구성은 포함하지 않습니다.

```bash
docker compose up -d --build --wait
```

- 서비스: http://localhost:8080
- Swagger UI: http://localhost:8080/docs

```bash
docker compose up -d --wait  # 기존 이미지로 다시 실행
docker compose ps          # 상태 확인
docker compose logs -f     # 로그 확인
docker compose down        # 종료, 데이터 유지
docker compose down -v     # 종료, 기록 삭제 (데이터가 삭제되기 때문에 권장하지 않음.)
```

| 설정 | 기본 개인 사용 환경 | 개발 환경 |
|---|---|---|
| Compose 파일 | `compose.yaml` | `compose.dev.yaml` |
| 프로젝트 | `dayly` | `dayly-dev` |
| 호스트 웹 포트 | `127.0.0.1:8080` | `127.0.0.1:8081` |
| DB 볼륨 | `dayly_data` | `dayly-dev_dev-data` |
| 컨테이너 내부 포트 | Nginx 80 / FastAPI 8000 | Nginx 80 / FastAPI 8000 |

두 환경은 컨테이너·네트워크·DB 볼륨이 분리되어 있습니다. 호스트에는 로컬 웹 포트만 열고, Nginx가 정적 React 빌드와 `/api` 요청을 함께 제공합니다. Docker 실행에는 호스트 Python·Node.js 설치가 필요하지 않습니다.

Docker가 실행 중이어야 서비스를 사용할 수 있습니다. `restart: unless-stopped`로 직접 중지하지 않은 컨테이너는 Docker 엔진 재시작 시 다시 시작합니다. Mac 로그인 후 자동 실행이 필요하면 Docker Desktop의 로그인 시 시작 옵션도 설정하세요.

### Docker 없이 개발

백엔드와 프론트엔드를 각각 별도 터미널에서 실행합니다.

```bash
# 터미널 1 — Backend
cd backend
uv sync --locked
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```bash
# 터미널 2 — Frontend
cd frontend
npm ci
npm run dev
```

화면은 http://127.0.0.1:5173, API 문서는 http://127.0.0.1:8000/docs 입니다. Vite가 `/api` 요청을 백엔드로 전달합니다. 직접 실행한 DB는 실행 위치와 관계없이 `backend/data/todo.db`에 저장되며, Docker 볼륨과는 별개입니다.

### Environment Variables

예시 파일을 해당 위치의 `.env`로 복사하고 필요한 값만 수정합니다. 이미 `.env`가 있다면 기존 설정을 유지하면서 필요한 키를 추가하세요. 환경변수는 백엔드 `.env` 값보다 우선합니다.

| 예시 파일 | 적용 위치와 설정 |
|---|---|
| [루트 .env.example](.env.example) | 기본 Docker 포트 `DAYLY_PORT`, 개발 Docker의 `XP_*` 설정 |
| [backend/.env.example](backend/.env.example) | 직접 실행하는 API의 `DATABASE_URL`, JSON 배열 형식의 `CORS_ORIGINS`, `XP_*` |
| [frontend/.env.example](frontend/.env.example) | 직접 개발/빌드 시 `VITE_API_BASE_URL`. 기본은 빈 값과 Vite 프록시 사용 |

`VITE_API_BASE_URL`에는 `/api`를 붙이지 않습니다. 개발 프록시 대상만 바꿀 때는 `API_PROXY_TARGET`을 사용합니다. Docker에서는 같은 주소의 Nginx를 통해 화면과 API를 제공하므로 별도 API 주소나 CORS 설정이 필요하지 않습니다. `backend/.env`는 Docker 이미지에 포함되지 않으며 컨테이너 설정은 Compose의 `environment`를 사용합니다.

개발 포트 8081은 고정입니다. 기본 개인 사용 환경의 8080이 점유되어 있으면 루트 `.env`의 `DAYLY_PORT`를 변경하거나 다음과 같이 실행할 수 있습니다.

```bash
DAYLY_PORT=8082 docker compose up -d --wait
```

XP 수치는 **임시 정책**입니다. 아래 설정값은 새 지급 건에 적용되고 기존 지급 내역·Snapshot은 재계산하지 않습니다.

| 환경변수 | 기본값 | 의미 |
|---|---|---|
| `XP_TASK_POINTS` | 10 | 최초 추적 완료 XP |
| `XP_DAILY_CAP` | 100 | 완료 XP와 보너스를 합한 하루 상한 |
| `XP_BONUS_HALF` | 10 | 확정 일일 달성률 50% 이상 보너스 |
| `XP_BONUS_FULL` | 20 | 100% 보너스. 50% 보너스와 중복하지 않음 |
| `XP_LEVEL_STEP` | 100 | 다음 레벨 필요량의 증가 단위 |

## Project Structure

```text
backend/
├── app/
│   ├── api/          # Tasks, Calendar/Stats, Retrospectives, Growth Router와 의존성
│   ├── schemas/      # Pydantic 요청·응답 계약
│   ├── models/       # Task, Event, Snapshot, XP 원장 등 SQLAlchemy 모델
│   ├── services/     # CRUD, 과거 복원, 회고 집계, XP·레벨, 트랜잭션
│   ├── core/         # 설정, UTC/서울 시계, 회고 기간, 도메인 오류
│   ├── db.py         # Engine, Base, 요청별 Session
│   └── main.py       # 앱 조립, CORS, 예외 응답
├── alembic/          # 스키마 변경 및 기존 데이터 마이그레이션
├── tests/            # pytest와 브라우저 테스트 전용 데이터 준비
├── pyproject.toml
└── uv.lock
frontend/
├── src/
│   ├── components/   # 달력·Task·달성률 카드·회고·세계 화면
│   ├── hooks/        # Dashboard 데이터 조회와 요청 취소
│   ├── lib/          # API 호출과 날짜 처리
│   ├── App.tsx       # Workspace와 해시 기반 화면 이동
│   ├── types.ts      # API 응답 타입
│   └── styles.css
├── e2e/              # 실제 API와 연결한 Playwright 테스트
└── package-lock.json
deploy/               # Backend/Frontend Dockerfile, Nginx, 실행 스크립트
docs/releases/        # 버전별 패치노트
compose.yaml          # 기본 개인 사용 환경
compose.dev.yaml      # 분리된 개발 환경
```

### FastAPI 핵심 개념과 설계 이유

| 계층 | 책임 | 예시 |
|---|---|---|
| Router | 경로·HTTP 상태·쿼리 정의, 검증된 입력을 Service에 전달 | `api/tasks.py`, `api/retrospectives.py` |
| Pydantic Schema | 요청 검증과 응답 직렬화, 공개 필드 정의 | `TaskCreate`, `TaskUpdate`, `TaskRead` |
| SQLAlchemy Model | 테이블·컬럼·인덱스·DB 제약과 객체 매핑 | `Task`, `TaskEvent`, `RetrospectiveSnapshot` |
| Service | 완료 시각, 조회 정책, 이벤트·회고·XP 규칙과 트랜잭션 | `TaskService`, `TaskHistoryService`, `GrowthService` |
| DB / Configuration | 연결과 Session 수명, 환경 설정 | `db.py`, `core/config.py` |

`APIRouter`를 `main.py`의 `include_router()`로 연결하고, `Depends`로 요청별 Session과 날짜·시각을 주입합니다. `response_model`과 `from_attributes=True`는 ORM 객체를 정해진 응답 형식으로 변환합니다. 생성·수정·응답 Schema를 분리해 서버 관리 필드의 임의 변경을 막습니다.

완료 체크는 **입력 검증 → Router → TaskService → Task 변경과 Event 삽입 → 같은 트랜잭션으로 commit → 응답 → 화면 재조회** 순서로 처리합니다. 실패 시 rollback합니다. Service는 HTTP 객체를 사용하지 않고 도메인 오류를 발생시키며, `main.py`가 이를 HTTP 응답으로 바꿉니다.

동기 ORM에 맞춰 동기 Router를 사용하고 Session을 요청 간 공유하지 않습니다. 현재 규모에서는 별도 Repository 계층을 추가하지 않고 Service에서 SQLAlchemy를 사용합니다.

학습 참고: [FastAPI APIRouter](https://fastapi.tiangolo.com/tutorial/bigger-applications/) · [SQLAlchemy Session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html).

## API Overview

개발 Docker의 Swagger UI는 http://localhost:8081/docs 입니다. 기본 환경은 http://localhost:8080/docs, 직접 실행은 http://127.0.0.1:8000/docs 를 사용합니다. 각 서버의 `/openapi.json`에서도 API 정의를 확인할 수 있습니다.

### Task API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/tasks?date=YYYY-MM-DD` | 해당 날짜의 할 일 목록 |
| POST | `/api/tasks` | 제목·예정 날짜·선택 설명으로 생성, 201 반환 |
| PATCH | `/api/tasks/{id}` | 제목·설명·예정 날짜·완료 여부 변경 |
| DELETE | `/api/tasks/{id}` | 삭제, 본문 없는 204 반환 |
| GET | `/api/calendar?year=2026&month=11` | 월간 날짜별 완료/전체 현황 |
| GET | `/api/stats/daily?date=YYYY-MM-DD` | 특정 날짜의 실시간 달성률 |
| GET | `/api/stats/weekly` | 오늘을 포함한 최근 7일 실시간 통계 |

제목은 공백 제거 후 1~200자, 설명은 최대 5,000자입니다. PATCH에서 생략한 필드는 유지하고 `description: null`로 설명을 지웁니다. 제목·날짜·완료 상태의 명시적 null, 빈 PATCH, 정의되지 않은 입력 필드는 거절합니다.

### Retrospective API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/retrospectives` | 최근 종료된 세 종류의 누락 Snapshot 생성 후 저장된 회고 목록 |
| GET | `/api/retrospectives?kind=daily` | 종류별 목록과 최근 종료 기간 회고 |
| GET | `/api/retrospectives?kind=weekly&date=2026-11-02` | 지정 날짜가 속한 기간의 회고·상태 |
| GET | `/api/retrospectives/{id}` | 저장된 Snapshot 상세, 재계산 없음 |

`kind`는 `daily`, `weekly`, `monthly`입니다. `date` 지정 시 `kind`가 필요합니다. 목록 응답은 `items`, `total`, `requested_period`, `status`를 포함하며, 회고 목록 조회는 필요한 종료 기간 Snapshot을 저장할 수 있습니다.

### Growth API

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/growth/summary` | 누락 XP 동기화 후 누적 XP·레벨·다음 레벨 진행 상태·정책 |
| GET | `/api/growth/history` | 누락 XP 동기화 후 지급 내역 |

회고 목록과 XP 내역은 `limit`(1~100), `offset`(0 이상)을 지원합니다. 잘못된 입력은 422, 없는 항목은 404, 과거 Task 상세 제한은 403, 저장소 오류는 503입니다. 도메인 오류는 `code`와 `detail`, 입력 검증 오류는 FastAPI의 `detail` 배열을 사용합니다. 회고 종류 없이 날짜만 요청하는 경우에는 문자열 `detail`과 422를 반환합니다.

## Database & Data Management

| 데이터 | 역할과 보존 방식 |
|---|---|
| `tasks` | 현재 할 일 상태. 완료 체크 시 UTC 완료 시각을 저장하고 해제하면 null로 초기화 |
| `task_events` | 생성·수정·완료·해제·삭제·BASELINE의 전체 before/after 사본. Task 삭제 후에도 유지하는 append-only 이력 |
| `retrospective_snapshots` | 종류·기간·고정 통계·Task 사본·기간 XP. 같은 종류와 기간에는 하나만 저장하며 생성 후 변경하지 않음 |
| `experience_grants` | XP Ledger. 지급 원인·Task/이벤트·귀속 날짜·지급량·고유 키를 보관하고 중복 지급 방지 |
| `history_coverage` | 신뢰할 수 있는 이력 추적 시작 시각. 활동 없음과 복원 불가를 구분하는 기준 |

### 날짜와 달성률

예정 날짜는 `YYYY-MM-DD`, 타임스탬프는 UTC로 저장·반환합니다. 오늘과 회고 날짜 경계는 `Asia/Seoul` 기준입니다. SQLite가 잃는 시간대 메타데이터는 `UTCDateTime`이 복원합니다.

실시간 Task 상세와 일일 통계는 오늘−6일부터 미래 날짜까지 제공합니다. 오래된 Task 데이터는 삭제하지 않고 달력 요약으로 보존합니다. 같은 제한은 오래된 Task의 수정·삭제 및 해당 날짜로의 생성·이동에도 적용합니다. **고정 회고 조회에는 이 7일 제한을 적용하지 않습니다.**

달성률은 `완료 / 전체 × 100`이며, 주간·월간 비율도 완료 합계 / 전체 합계를 사용합니다. 일별 비율을 단순 평균하지 않습니다. 할 일이 없으면 비율은 null, 할 일이 있지만 완료가 없으면 0%입니다. API는 소수 둘째 자리까지, UI는 정수 반올림으로 표시합니다.

고정 회고는 일간 하루, 월요일~일요일 한 주, 달력의 한 달을 대상으로 합니다. 각 날짜 종료 시각 직전의 상태를 복원해 합산하고, 기간이 종료된 뒤 누락 Snapshot을 생성합니다. 모든 기간은 **[시작, 종료)**이며 `period_end`는 미포함 종료 날짜입니다. 대시보드의 최근 7일과 주간 고정 회고는 집계 기간이 다릅니다.

| 회고 상태 | 의미 |
|---|---|
| `ready` | 이력이 충분하고 계획이 있었음. 완료 0개는 정상 0% |
| `no_activity` | 이력이 충분하지만 계획이 없었음 |
| `partial` | 추적 이전 시간이 포함되어 일부 기록만 확인 가능 |
| `unavailable` | 전체 기간이 추적 이전이라 정확한 복원 불가 |
| `not_ended` | 아직 종료되지 않아 Snapshot을 생성하지 않음 |

XP는 Task의 최초 추적 완료에 한 번 지급하고 완료 해제·삭제 시 회수하지 않습니다. BASELINE에서 이미 완료된 항목에는 과거 완료 보상을 추정하지 않습니다. 성장 API 조회와 새 Snapshot 생성 시 누락된 지급을 동기화합니다. 기본 누적 레벨 경계는 0 / 100 / 300 / 600 XP이며, 자세한 계산·중복 방지·보너스 귀속 규칙은 [v0.2.1 설계](docs/releases/v0.2.1.md)를 참고하세요.

### 마이그레이션과 백업

Alembic `0001`은 Task, `0002`는 Task Events와 기존 Task의 BASELINE, `0003`은 Snapshot·XP 원장·추적 시작 정보를 구성합니다. 기존 ID와 데이터를 보존하며, 앱에서 `create_all()`로 마이그레이션 누락을 숨기지 않습니다. 변경 전에는 대상 DB를 백업하세요. downgrade는 이력 테이블을 제거할 수 있으므로 일반 종료에 사용하지 않습니다.

Docker DB 파일은 `/app/data/todo.db`입니다. `down`은 볼륨을 유지하지만 **`down -v`는 데이터까지 삭제**합니다. Docker 기본/개발 볼륨과 직접 실행 DB 사이의 자동 복사·동기화는 없습니다.

실행 중인 개발 DB의 일관된 백업은 SQLite backup 기능을 사용합니다. 기존 `todo-backup.db`가 있다면 다른 이름으로 복사하세요.

```bash
docker compose -f compose.dev.yaml exec -T backend python -c "import sqlite3; source = sqlite3.connect('/app/data/todo.db'); target = sqlite3.connect('/tmp/todo-backup.db'); source.backup(target); target.close(); source.close()"
docker compose -f compose.dev.yaml cp backend:/tmp/todo-backup.db ./todo-backup.db
```

기본 개인 사용 환경은 위 명령에서 `-f compose.dev.yaml`을 빼고 실행합니다. 실제 환경 파일, 개인키·계정 설정, DB·백업·로그는 `.gitignore`로 제외하며 공유용 설정 예시는 유지합니다.

## Testing

### Backend — pytest

```bash
cd backend
uv sync --locked
uv run pytest -q
```

각 테스트는 임시 SQLite 파일에 실제 마이그레이션을 적용합니다. Task CRUD, 입력 검증, 통계, 이벤트·rollback·과거 복원, 회고 불변성, XP 정책·동시 요청 등을 검증하며 개인 DB를 초기화하지 않습니다.

### Frontend / E2E — Playwright

```bash
cd frontend
npm ci
npx playwright install chromium
npm run test:e2e
```

기본 설정은 별도 임시 DB, 백엔드 8001·프론트엔드 5174 포트를 사용합니다. 테스트 전용 과거 데이터를 넣어 Dashboard·회고·성장 화면과 실제 API를 검증합니다. 이 데이터 준비는 앱의 정상 실행에 포함되지 않습니다. 지정된 포트는 비어 있어야 합니다.

`E2E_BASE_URL`을 지정하면 해당 서버를 사용합니다. 테스트가 Task를 생성·삭제하므로 개인 기록이 없는 별도 검증 서버에만 지정하세요. 스크린샷과 실패 trace는 `frontend/test-results/`에 생성되며 Git에서 제외됩니다.

### Build / Migration 검증

```bash
cd frontend
npm run build
```

엄격한 TypeScript 검사 후 Vite가 `frontend/dist/`를 생성합니다. 빌드 결과만 열어서는 API가 제공되지 않으며 위 Docker 또는 개발 서버 방식으로 함께 실행해야 합니다.

```bash
cd backend
uv run alembic upgrade head
uv run alembic check
```

`upgrade head`는 선택한 DB에 마이그레이션을 적용하고, `check`는 적용된 스키마와 모델의 차이를 확인합니다. 실행 대상은 `DATABASE_URL` 또는 기본 개발 DB이므로 대상 데이터를 백업한 뒤 사용하세요. Docker 개발 DB의 일치 검사만 수행하려면 루트에서 다음을 실행합니다.

```bash
docker compose -f compose.dev.yaml exec -T backend alembic check
```

버전별 검증 결과와 상세 시나리오는 [v0.2.1 패치노트](docs/releases/v0.2.1.md#testing)를 참고하세요.

## Release Notes

| 버전 | 핵심 변경 사항 |
|---|---|
| [v0.1.0](docs/releases/v0.1.0.md) | Task CRUD, 달력, 일일·최근 7일 통계와 Docker 실행 |
| [v0.2.0](docs/releases/v0.2.0.md) | Task Events, 과거 복원, BASELINE, 달성률 전환과 개발 환경 분리 |
| [v0.2.1](docs/releases/v0.2.1.md) | 고정 회고 Snapshot, XP·레벨 원장, 회고/세계 워크스페이스 |

## Roadmap

**v1.0 — Growth Worlds (개발 예정)**

- Forest: 완료한 할 일에 따라 성장하는 숲
- Ocean: 성장하는 고래와 해양 생태계
- 성장 단계별 시각적 변화와 애니메이션
- 세계관과 고정 회고 시스템 연동
- 연간 성장 기록과 보관함

현재는 두 테마의 소개 화면과 공통 XP·레벨 데이터까지 구현했습니다. 실제 테마별 성장 연출은 포함하지 않습니다.

이력 추적 이전의 정확한 상태 복원, 대규모 장기 이력의 증분 처리와 PostgreSQL 실서버 검증은 남아 있습니다. PostgreSQL 전환 시에는 별도 드라이버·연결 설정·데이터 이관 및 검증이 필요합니다.

이 프로젝트는 인증과 다중 사용자 권한이 없는 로컬 개인용 서비스입니다. 공개 인터넷에 배포하려면 인증·접근 제어가 필요하며 CORS는 이를 대신하지 않습니다. 반복 일정·알림과 공개 배포 구성은 현재 포함하지 않습니다.
