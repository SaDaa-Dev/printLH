# 📸 사진 리사이징 및 프린트 웹 애플리케이션

Mac과 Windows에서 모두 사용할 수 있는 웹 기반 사진 리사이징 프로그램입니다. Docker를 사용하여 쉽게 배포하고 관리할 수 있습니다.

## 🎯 주요 기능

### 📷 2가지 사진 종류 지원
- **시공사진**: 가로 9cm × 세로 11cm (A4 용지에 최대 4장 배치)
- **대문사진**: 가로 11.4cm × 세로 15.2cm (A4 용지에 최대 2장 배치)

### 🌟 핵심 특징
- **크로스 플랫폼**: Mac, Windows, Linux 모두 지원
- **웹 기반**: 브라우저만 있으면 어디서든 사용 가능
- **Docker 지원**: 컨테이너로 쉽게 배포 및 관리
- **반응형 디자인**: 모바일, 태블릿, 데스크톱 모두 지원
- **드래그 앤 드롭**: 직관적인 파일 업로드
- **실시간 미리보기**: 처리 결과를 즉시 확인

## 🚀 빠른 시작 (Docker 사용)

### 1. 저장소 클론
```bash
git clone <repository-url>
cd printLH
```

### 2. Docker로 실행
```bash
# 간단한 실행
docker-compose -f docker-compose.simple.yml up -d

# 또는 전체 기능 포함
docker-compose up -d
```

### 3. 웹 브라우저에서 접속
```
http://localhost:5001
```

## 🛠️ 로컬 개발 환경 설정

### 1. Python 환경 설정
```bash
# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 애플리케이션 실행
```bash
python app.py
```

### 3. 브라우저에서 접속
```
http://localhost:5001
```

## 📋 사용 방법

### 1. 사진 종류 선택
- **시공사진**: 가로 9cm × 세로 11cm 크기
- **대문사진**: 가로 11.4cm × 세로 15.2cm 크기

### 2. 파일 업로드
- 드래그 앤 드롭으로 파일 업로드
- 또는 "파일 선택" 버튼 클릭
- 지원 형식: JPG, PNG, BMP, GIF, TIFF (최대 16MB)

### 3. 자동 처리
- 선택한 종류에 따라 자동으로 A4 크기에 맞게 리사이징
- 실시간 미리보기 제공

### 4. 다운로드
- 처리된 이미지를 다운로드
- 일반 프린터로 A4 용지에 프린트

## 🎨 사진 처리 규칙

### 🏗️ 시공사진 모드
- 크기: 가로 9cm × 세로 11cm
- 자동 크롭 및 리사이징으로 비율 맞춤
- **스마트 배치**: 가로/세로 회전하여 최대한 많이 배치
- A4 용지에 최대 4장 배치 (2열 2행)
- 300 DPI 고해상도 출력

### 📄 대문사진 모드
- 크기: 가로 11.4cm × 세로 15.2cm
- 자동 크롭 및 리사이징으로 비율 맞춤
- **스마트 배치**: 가로/세로 회전하여 최대한 많이 배치
- A4 용지에 최대 2장 배치 (회전 시 가로 배치)
- 300 DPI 고해상도 출력

### 🔄 스마트 최적화 기능
- **자동 회전**: 더 많이 들어갈 수 있는 방향으로 자동 회전
- **최적 배치**: A4 용지 공간을 최대한 활용
- **용지 절약**: 여백을 최소화하여 인쇄 비용 절약

## 🐳 Docker 사용법

### 기본 실행
```bash
# 이미지 빌드 및 실행
docker-compose -f docker-compose.simple.yml up -d

# 로그 확인
docker-compose logs -f photo-resizer

# 정지
docker-compose down
```

### 고급 설정
```bash
# 전체 설정으로 실행 (Nginx 포함)
docker-compose up -d

# 이미지 강제 리빌드
docker-compose build --no-cache

# 볼륨 포함 완전 삭제
docker-compose down -v
```

### 개발 모드로 실행
```bash
# 개발 환경 변수 설정
export FLASK_ENV=development
export FLASK_DEBUG=1

# 개발 서버 실행
python app.py
```

## 📁 프로젝트 구조

```
printLH/
├── app.py                      # Flask 메인 애플리케이션
├── requirements.txt            # Python 의존성
├── Dockerfile                  # Docker 이미지 설정
├── docker-compose.yml          # Docker Compose 설정
├── docker-compose.simple.yml   # 간단한 Docker 설정
├── .dockerignore              # Docker 빌드 제외 파일
├── templates/
│   └── index.html             # 웹 페이지 템플릿
├── static/
│   ├── css/
│   │   └── style.css          # 스타일시트
│   └── js/
│       └── script.js          # JavaScript
├── temp_uploads/              # 업로드된 파일 임시 저장
├── temp_processed/            # 처리된 파일 임시 저장
└── README.md                  # 이 파일
```

## 🔧 시스템 요구사항

### 로컬 실행
- Python 3.8 이상
- 메모리: 최소 512MB
- 디스크 공간: 100MB 이상

### Docker 실행
- Docker 20.10 이상
- Docker Compose 1.29 이상
- 메모리: 최소 512MB
- 디스크 공간: 1GB 이상

## 🎨 지원 이미지 형식

- **JPEG** (.jpg, .jpeg)
- **PNG** (.png)
- **BMP** (.bmp)
- **GIF** (.gif)
- **TIFF** (.tiff)

## 🌍 크로스 플랫폼 지원

### Windows
- Docker Desktop 설치 후 실행
- 웹 브라우저에서 `http://localhost:5001` 접속

### Mac
- Docker Desktop 설치 후 실행
- 웹 브라우저에서 `http://localhost:5001` 접속

### Linux
- Docker 및 Docker Compose 설치 후 실행
- 웹 브라우저에서 `http://localhost:5001` 접속

## 💡 사용 팁

1. **고품질 출력**: 가능한 한 고해상도 이미지 사용
2. **증명사진**: 정면을 바라보는 사진이 최적
3. **프린트 설정**: 용지 설정을 A4로 확인
4. **색상 품질**: 컬러 프린터 사용 시 '고품질' 설정 권장

## 🚨 문제 해결

### 일반적인 문제들

**Q: 웹 페이지가 로드되지 않아요**
```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인
docker-compose logs photo-resizer

# 포트 확인
netstat -an | grep 5001
```

**Q: 이미지 업로드가 안 돼요**
- 파일 크기가 16MB 이하인지 확인
- 지원되는 이미지 형식인지 확인
- 브라우저 콘솔에서 오류 메시지 확인

**Q: Docker 빌드가 실패해요**
```bash
# 캐시 없이 다시 빌드
docker-compose build --no-cache

# 이미지 삭제 후 재빌드
docker system prune -a
```

## 🔄 업데이트 및 배포

### 애플리케이션 업데이트
```bash
# 코드 변경 후
docker-compose build
docker-compose up -d
```

### 운영 환경 배포
```bash
# 환경 변수 설정
export FLASK_ENV=production

# 운영 모드로 실행
docker-compose -f docker-compose.yml up -d
```

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📞 지원 및 문의

- **이슈 신고**: GitHub Issues
- **기능 요청**: GitHub Issues
- **기술 지원**: 문서 참조 또는 이슈 등록

## 📋 추가 개선 사항

필요한 기능이 있으시면 다음과 같은 개선이 가능합니다:

- 🔧 다양한 증명사진 크기 지원
- 🔄 배치 처리 기능 (여러 파일 동시 처리)
- 🎨 이미지 회전 및 조정 기능
- 🏷️ 워터마크 추가 기능
- 📏 다양한 용지 크기 지원 (A3, A5 등)
- 🔒 사용자 인증 및 권한 관리
- 📊 사용 통계 및 분석
- 🌐 다국어 지원

## 📜 라이선스

이 프로젝트는 MIT 라이선스 하에 있습니다.

---

🎉 **이제 어떤 기기에서든 쉽게 사진을 리사이징하고 프린트할 수 있습니다!** 