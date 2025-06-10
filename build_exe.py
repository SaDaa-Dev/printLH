import os
import subprocess
import shutil

def build_executable():
    """실행 파일 빌드"""
    print("사진 리사이징 프로그램 실행 파일 빌드 시작...")
    
    # PyInstaller 명령어 설정
    pyinstaller_cmd = [
        'pyinstaller',
        '--onefile',  # 단일 실행 파일로 생성
        '--windowed',  # 콘솔 창 숨김
        '--name=PhotoResizer',  # 실행 파일 이름
        '--icon=icon.ico',  # 아이콘 파일 (있는 경우)
        '--clean',  # 이전 빌드 파일 정리
        'main.py'
    ]
    
    # 아이콘 파일이 없는 경우 아이콘 옵션 제거
    if not os.path.exists('icon.ico'):
        pyinstaller_cmd.remove('--icon=icon.ico')
    
    try:
        # PyInstaller 실행
        result = subprocess.run(pyinstaller_cmd, check=True, capture_output=True, text=True)
        
        print("✅ 실행 파일 빌드 완료!")
        print(f"실행 파일 위치: {os.path.abspath('dist/PhotoResizer.exe')}")
        
        # 빌드 정보 출력
        print("\n📋 빌드 정보:")
        print(f"- 실행 파일: PhotoResizer.exe")
        print(f"- 크기: {get_file_size('dist/PhotoResizer.exe')}")
        print(f"- 위치: dist/ 폴더")
        
        # 정리 옵션
        clean_build_files()
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 빌드 실패: {e}")
        print(f"오류 메시지: {e.stderr}")
        return False
    
    except FileNotFoundError:
        print("❌ PyInstaller가 설치되어 있지 않습니다.")
        print("다음 명령어로 설치하세요: pip install pyinstaller")
        return False
    
    return True

def get_file_size(file_path):
    """파일 크기를 사람이 읽기 쉬운 형태로 반환"""
    if not os.path.exists(file_path):
        return "알 수 없음"
    
    size = os.path.getsize(file_path)
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

def clean_build_files():
    """빌드 과정에서 생성된 임시 파일들 정리"""
    dirs_to_remove = ['build', '__pycache__']
    files_to_remove = ['PhotoResizer.spec']
    
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"🗑️  {dir_name} 폴더 정리 완료")
    
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"🗑️  {file_name} 파일 정리 완료")

if __name__ == "__main__":
    success = build_executable()
    
    if success:
        print("\n🎉 빌드가 성공적으로 완료되었습니다!")
        print("dist/PhotoResizer.exe 파일을 실행하여 프로그램을 사용하세요.")
    else:
        print("\n💡 빌드 전 확인사항:")
        print("1. pip install -r requirements.txt")
        print("2. Python 3.7 이상 버전 사용")
        print("3. 모든 의존성 라이브러리 설치 완료") 