# 📄 PDF Dual Viewer & Translator (PDF 듀얼 뷰어 & 번역기)

[[English](README.md)] [[한국어](README_ko.md)]

## 📝 프로젝트 소개

이 프로젝트는 PDF 파일을 원본/번역본 듀얼 뷰로 보여주고, 페이지 네비게이션, 하이라이트 동기화, 번역 연동, 스타일/레이아웃 유지 등 다양한 기능을 제공하는 데스크탑 앱입니다. PySide6, PyMuPDF 등 최신 Python 라이브러리를 활용하여 클린 아키텍처 기반으로 설계되었습니다.

## 📂 폴더 구조

```
src/
├─adapters/           # 컨트롤러, 게이트웨이, 프레젠터 등
├─common/             # 공통 유틸리티/상수
├─core/               # 엔티티, 유즈케이스(비즈니스 로직)
│  └─use_cases/
├─infrastructure/     # PDF 파싱, 번역, DB 등 외부 연동
│  ├─dtos/
│  ├─pdf_parsing/
│  ├─persistence/
│  └─translation/
└─ui/                 # PySide6 기반 UI, 위젯, 리소스
    ├─resources/
    └─widgets/
main.py               # 앱 진입점
pyproject.toml        # 의존성 및 설정
README.md             # 영문 설명서
readme_ko.md          # 한글 설명서
```

## 🚀 실행 방법

1. [uv](https://github.com/astral-sh/uv) 설치 (빠른 파이썬 패키지 매니저)
2. 의존성 설치:
   ```cmd
   uv pip install -r requirements.txt
   ```
3. 앱 실행:
   ```cmd
   uv venv exec python main.py
   ```

## ✨ 주요 기능
- PDF 파일 열기 및 듀얼 뷰(원본/번역본) 표시
- 페이지 네비게이션, 입력 이동
- 하이라이트 동기화(양쪽 뷰 동시 강조)
- 번역 API 연동(예정)
- 스타일/레이아웃 유지, 이미지 렌더링
- 클린 아키텍처 기반 구조

## 🛠️ 기술 스택
- Python 3.10+
- PySide6 (Qt 기반 GUI)
- PyMuPDF (PDF 파싱)
- 기타: Clean Architecture, MVC, etc.

## 📌 참고/기여
- 자세한 설계 및 구조는 design.md 참고
- PR/이슈/기여 환영!