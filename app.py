from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import os
import tempfile
import uuid
import shutil
import io
import time
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['PROCESSED_FOLDER'] = 'temp_processed'

# 임시 폴더 생성
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)

# A4 용지 크기 (300 DPI 기준)
A4_WIDTH = 2480  # 픽셀
A4_HEIGHT = 3508  # 픽셀
A4_PORTRAIT_SIZE = (A4_WIDTH, A4_HEIGHT)  # 세로
A4_LANDSCAPE_SIZE = (A4_HEIGHT, A4_WIDTH)  # 가로

# 허용된 파일 확장자
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

# 업로드된 파일들을 저장할 전역 변수
uploaded_files = {}
UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']

def allowed_file(filename):
    """허용된 파일 형식인지 확인"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    """24시간 이전 파일들 정리"""
    cutoff_time = datetime.now() - timedelta(hours=24)
    
    for folder in [app.config['UPLOAD_FOLDER'], app.config['PROCESSED_FOLDER']]:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                if os.path.isfile(file_path):
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_time < cutoff_time:
                        os.remove(file_path)

def calculate_optimal_layout(photo_width, photo_height, a4_width, a4_height, margin=50):
    """최적 배치 계산 (회전 포함)"""
    layouts = []
    
    # 1. 원본 방향 (세로)
    cols_normal = (a4_width - 2 * margin) // photo_width
    rows_normal = (a4_height - 2 * margin) // photo_height
    count_normal = cols_normal * rows_normal
    
    if cols_normal > 0 and rows_normal > 0:
        layouts.append({
            'count': count_normal,
            'cols': cols_normal,
            'rows': rows_normal,
            'photo_width': photo_width,
            'photo_height': photo_height,
            'rotated': False
        })
    
    # 2. 90도 회전 (가로)
    cols_rotated = (a4_width - 2 * margin) // photo_height
    rows_rotated = (a4_height - 2 * margin) // photo_width
    count_rotated = cols_rotated * rows_rotated
    
    if cols_rotated > 0 and rows_rotated > 0:
        layouts.append({
            'count': count_rotated,
            'cols': cols_rotated,
            'rows': rows_rotated,
            'photo_width': photo_height,
            'photo_height': photo_width,
            'rotated': True
        })
    
    # 가장 많이 들어가는 배치 선택
    if layouts:
        optimal_layout = max(layouts, key=lambda x: x['count'])
        return optimal_layout
    else:
        # 최소 1개는 들어가도록
        return {
            'count': 1,
            'cols': 1,
            'rows': 1,
            'photo_width': min(photo_width, a4_width - 2 * margin),
            'photo_height': min(photo_height, a4_height - 2 * margin),
            'rotated': False
        }

def resize_for_construction_photo(image):
    """시공사진 리사이징 (9cm × 11cm, 최적 배치)"""
    # 시공사진 크기 (9cm × 11cm, 300 DPI 기준)
    photo_width = int(90 * 300 / 25.4)   # 약 1063픽셀
    photo_height = int(110 * 300 / 25.4)  # 약 1299픽셀
    
    # 최적 배치 계산
    layout = calculate_optimal_layout(photo_width, photo_height, A4_WIDTH, A4_HEIGHT)
    
    # 원본 이미지를 사진 비율에 맞게 크롭
    original_width, original_height = image.size
    target_ratio = layout['photo_width'] / layout['photo_height']
    original_ratio = original_width / original_height
    
    if original_ratio > target_ratio:
        # 원본이 더 가로가 긴 경우 - 세로를 기준으로 크롭
        new_height = original_height
        new_width = int(original_height * target_ratio)
        left = (original_width - new_width) // 2
        top = 0
        right = left + new_width
        bottom = original_height
    else:
        # 원본이 더 세로가 긴 경우 - 가로를 기준으로 크롭
        new_width = original_width
        new_height = int(original_width / target_ratio)
        left = 0
        top = (original_height - new_height) // 2
        right = original_width
        bottom = top + new_height
    
    # 크롭 및 리사이징
    cropped_image = image.crop((left, top, right, bottom))
    resized_photo = cropped_image.resize((layout['photo_width'], layout['photo_height']), Image.Resampling.LANCZOS)
    
    # 회전 처리
    if layout['rotated']:
        resized_photo = resized_photo.rotate(90, expand=True)
    
    # A4 용지에 배치
    a4_image = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
    
    # 배치 계산
    margin = 50
    x_spacing = (A4_WIDTH - 2 * margin - layout['cols'] * layout['photo_width']) // max(1, layout['cols'] - 1) if layout['cols'] > 1 else 0
    y_spacing = (A4_HEIGHT - 2 * margin - layout['rows'] * layout['photo_height']) // max(1, layout['rows'] - 1) if layout['rows'] > 1 else 0
    
    for row in range(layout['rows']):
        for col in range(layout['cols']):
            x = margin + col * (layout['photo_width'] + x_spacing)
            y = margin + row * (layout['photo_height'] + y_spacing)
            a4_image.paste(resized_photo, (x, y))
    
    return a4_image

def resize_for_document_photo(image):
    """대문사진 리사이징 (11.4cm × 15.2cm, 최적 배치)"""
    # 대문사진 크기 (11.4cm × 15.2cm, 300 DPI 기준)
    photo_width = int(114 * 300 / 25.4)   # 약 1346픽셀
    photo_height = int(152 * 300 / 25.4)  # 약 1795픽셀
    
    # 최적 배치 계산
    layout = calculate_optimal_layout(photo_width, photo_height, A4_WIDTH, A4_HEIGHT)
    
    # 원본 이미지를 사진 비율에 맞게 크롭
    original_width, original_height = image.size
    target_ratio = layout['photo_width'] / layout['photo_height']
    original_ratio = original_width / original_height
    
    if original_ratio > target_ratio:
        # 원본이 더 가로가 긴 경우 - 세로를 기준으로 크롭
        new_height = original_height
        new_width = int(original_height * target_ratio)
        left = (original_width - new_width) // 2
        top = 0
        right = left + new_width
        bottom = original_height
    else:
        # 원본이 더 세로가 긴 경우 - 가로를 기준으로 크롭
        new_width = original_width
        new_height = int(original_width / target_ratio)
        left = 0
        top = (original_height - new_height) // 2
        right = original_width
        bottom = top + new_height
    
    # 크롭 및 리사이징
    cropped_image = image.crop((left, top, right, bottom))
    resized_photo = cropped_image.resize((layout['photo_width'], layout['photo_height']), Image.Resampling.LANCZOS)
    
    # 회전 처리
    if layout['rotated']:
        resized_photo = resized_photo.rotate(90, expand=True)
    
    # A4 용지에 배치
    a4_image = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
    
    # 배치 계산
    margin = 50
    x_spacing = (A4_WIDTH - 2 * margin - layout['cols'] * layout['photo_width']) // max(1, layout['cols'] - 1) if layout['cols'] > 1 else 0
    y_spacing = (A4_HEIGHT - 2 * margin - layout['rows'] * layout['photo_height']) // max(1, layout['rows'] - 1) if layout['rows'] > 1 else 0
    
    for row in range(layout['rows']):
        for col in range(layout['cols']):
            x = margin + col * (layout['photo_width'] + x_spacing)
            y = margin + row * (layout['photo_height'] + y_spacing)
            a4_image.paste(resized_photo, (x, y))
    
    return a4_image

@app.route('/')
def index():
    """메인 페이지"""
    cleanup_old_files()
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    """파일 업로드 처리"""
    if 'file' not in request.files:
        return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
    
    file = request.files['file']
    photo_type = request.form.get('photo_type', 'general')
    
    if file.filename == '':
        return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # 고유한 파일명 생성
            unique_id = str(uuid.uuid4())
            filename = secure_filename(file.filename)
            file_extension = filename.rsplit('.', 1)[1].lower()
            
            # 업로드 파일 저장
            upload_filename = f"{unique_id}_original.{file_extension}"
            upload_path = os.path.join(app.config['UPLOAD_FOLDER'], upload_filename)
            file.save(upload_path)
            
            # 이미지 처리
            image = Image.open(upload_path)
            
            # 사진 종류에 따른 리사이징
            if photo_type == 'construction':
                processed_image = resize_for_construction_photo(image)
            else:  # document
                processed_image = resize_for_document_photo(image)
            
            # 처리된 이미지 저장
            processed_filename = f"{unique_id}_processed.jpg"
            processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
            processed_image.save(processed_path, 'JPEG', quality=95)
            
            # 미리보기용 썸네일 생성
            thumbnail = processed_image.copy()
            thumbnail.thumbnail((400, 400), Image.Resampling.LANCZOS)
            thumbnail_filename = f"{unique_id}_thumb.jpg"
            thumbnail_path = os.path.join(app.config['PROCESSED_FOLDER'], thumbnail_filename)
            thumbnail.save(thumbnail_path, 'JPEG', quality=85)
            
            return jsonify({
                'success': True,
                'file_id': unique_id,
                'original_filename': filename,
                'photo_type': photo_type,
                'thumbnail_url': f'/thumbnail/{unique_id}'
            })
            
        except Exception as e:
            return jsonify({'error': f'이미지 처리 중 오류가 발생했습니다: {str(e)}'}), 500
    
    return jsonify({'error': '지원하지 않는 파일 형식입니다'}), 400

@app.route('/upload_multiple', methods=['POST'])
def upload_multiple_files():
    """여러 파일 업로드 및 A4 배치 처리"""
    if 'files' not in request.files:
        return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
    
    files = request.files.getlist('files')
    photo_type = request.form.get('photo_type', 'construction')
    paper_orientation = request.form.get('paper_orientation', 'portrait')
    
    if not files or len(files) == 0:
        return jsonify({'error': '파일이 선택되지 않았습니다'}), 400
    
    try:
        # 고유한 배치 ID 생성
        batch_id = str(uuid.uuid4())
        
        # 업로드된 파일들을 처리
        processed_images = []
        for i, file in enumerate(files):
            if file.filename == '':
                continue
                
            if file and allowed_file(file.filename):
                # 파일 저장
                filename = secure_filename(file.filename)
                file_extension = filename.rsplit('.', 1)[1].lower()
                upload_filename = f"{batch_id}_{i}_original.{file_extension}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], upload_filename)
                file.save(upload_path)
                
                # 이미지 열기 및 처리 준비
                image = Image.open(upload_path)
                processed_images.append({
                    'image': image,
                    'filename': filename
                })
        
        if not processed_images:
            return jsonify({'error': '처리할 수 있는 이미지가 없습니다'}), 400
        
        # A4 용지에 여러 이미지 배치
        if photo_type == 'construction':
            final_image = arrange_multiple_construction_photos(processed_images, paper_orientation)
        else:  # document
            final_image = arrange_multiple_document_photos(processed_images, paper_orientation)
        
        # 최종 이미지 저장
        orientation_suffix = 'landscape' if paper_orientation == 'landscape' else 'portrait'
        type_suffix = 'construction' if photo_type == 'construction' else 'document'
        processed_filename = f"{batch_id}_{type_suffix}_{orientation_suffix}_layout.jpg"
        processed_path = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)
        final_image.save(processed_path, 'JPEG', quality=95)
        
        # 미리보기용 썸네일 생성
        thumbnail = final_image.copy()
        thumbnail.thumbnail((400, 400), Image.Resampling.LANCZOS)
        thumbnail_filename = f"{batch_id}_thumb.jpg"
        thumbnail_path = os.path.join(app.config['PROCESSED_FOLDER'], thumbnail_filename)
        thumbnail.save(thumbnail_path, 'JPEG', quality=85)
        
        return jsonify({
            'success': True,
            'file_id': batch_id,
            'file_count': len(processed_images),
            'photo_type': photo_type,
            'paper_orientation': paper_orientation,
            'thumbnail_url': f'/thumbnail/{batch_id}'
        })
        
    except Exception as e:
        return jsonify({'error': f'이미지 처리 중 오류가 발생했습니다: {str(e)}'}), 500

@app.route('/thumbnail/<file_id>')
def get_thumbnail(file_id):
    """썸네일 이미지 반환"""
    thumbnail_path = os.path.join(app.config['PROCESSED_FOLDER'], f"{file_id}_thumb.jpg")
    if os.path.exists(thumbnail_path):
        return send_file(thumbnail_path, mimetype='image/jpeg')
    return '', 404

@app.route('/download/<file_id>')
def download_file(file_id):
    """처리된 이미지 다운로드"""
    # 새로운 형식의 파일명을 먼저 찾아보기
    processed_folder = app.config['PROCESSED_FOLDER']
    
    # 새로운 형식: {id}_{type}_{orientation}_layout.jpg
    for filename in os.listdir(processed_folder):
        if filename.startswith(file_id) and filename.endswith('_layout.jpg'):
            processed_path = os.path.join(processed_folder, filename)
            # 파일명에서 정보 추출하여 다운로드명 생성
            parts = filename.replace('.jpg', '').split('_')
            if len(parts) >= 3:
                type_name = '시공사진' if parts[1] == 'construction' else '대문사진'
                orientation_name = '가로' if parts[2] == 'landscape' else '세로'
                download_name = f"A4_{type_name}_{orientation_name}_{file_id}.jpg"
            else:
                download_name = f"resized_photo_{file_id}.jpg"
            
            return send_file(
                processed_path,
                as_attachment=True,
                download_name=download_name,
                mimetype='image/jpeg'
            )
    
    # 기존 형식 fallback
    processed_path = os.path.join(processed_folder, f"{file_id}_processed.jpg")
    if os.path.exists(processed_path):
        return send_file(
            processed_path,
            as_attachment=True,
            download_name=f"resized_photo_{file_id}.jpg",
            mimetype='image/jpeg'
        )
    
    return '', 404

@app.route('/health')
def health_check():
    """헬스 체크"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

def resize_maintain_aspect_ratio(image, max_width, max_height):
    """비율을 유지하면서 최대 크기에 맞게 리사이징"""
    original_width, original_height = image.size
    
    # 비율 계산
    width_ratio = max_width / original_width
    height_ratio = max_height / original_height
    
    # 더 작은 비율을 사용하여 이미지가 최대 크기를 넘지 않게 함
    ratio = min(width_ratio, height_ratio)
    
    new_width = int(original_width * ratio)
    new_height = int(original_height * ratio)
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

# 최적화 배치를 위한 상수들
MARGIN_PX = 20  # 여백 (픽셀)
CONSTRUCTION_CM = (9.0, 11.0)  # 시공사진 크기 (cm)
DOCUMENT_CM = (11.4, 15.2)     # 대문사진 크기 (cm)

def cm_to_px(cm, dpi=300):
    """센티미터를 픽셀로 변환 (300 DPI 기준)"""
    return int(cm * dpi / 2.54)

def calculate_max_photos_single_type(photo_width_px, photo_height_px, a4_width_px, a4_height_px):
    """단일 종류 사진의 최대 배치 개수 계산 (회전 고려)"""
    # 정방향 배치
    cols_normal = (a4_width_px - MARGIN_PX) // (photo_width_px + MARGIN_PX)
    rows_normal = (a4_height_px - MARGIN_PX) // (photo_height_px + MARGIN_PX)
    total_normal = cols_normal * rows_normal
    
    # 90도 회전 배치
    cols_rotated = (a4_width_px - MARGIN_PX) // (photo_height_px + MARGIN_PX)
    rows_rotated = (a4_height_px - MARGIN_PX) // (photo_width_px + MARGIN_PX)
    total_rotated = cols_rotated * rows_rotated
    
    if total_rotated > total_normal:
        return total_rotated, True, (cols_rotated, rows_rotated), (photo_height_px, photo_width_px)
    else:
        return total_normal, False, (cols_normal, rows_normal), (photo_width_px, photo_height_px)

# 복잡한 최적화 함수들은 메모리 절약을 위해 모두 제거
# 메모리 효율적인 간단한 혼합 배치만 사용

def arrange_construction_photos_landscape(image_data_list, a4_width, a4_height):
    """가로 A4에서 시공사진 배치: 세로 3장 + 눕힌 2장 = 총 5장 per page"""
    margin = 50
    gap = 20
    
    # 페이지당 5장씩 처리
    photos_per_page = 5
    pages = []
    
    for page_start in range(0, len(image_data_list), photos_per_page):
        page_images = image_data_list[page_start:page_start + photos_per_page]
        
        # A4 용지 생성
        a4_image = Image.new('RGB', (a4_width, a4_height), 'white')
        
        # 배치 영역 계산
        available_width = a4_width - 2 * margin
        available_height = a4_height - 2 * margin
        
        # 세로 영역 (왼쪽): 3장을 세로로 배치
        vertical_area_width = available_width * 0.6  # 전체 너비의 60%
        vertical_photo_height = (available_height - 2 * gap) // 3
        vertical_photo_width = vertical_area_width
        
        # 가로 영역 (오른쪽): 2장을 눕혀서 배치
        horizontal_area_width = available_width * 0.4  # 전체 너비의 40%
        horizontal_photo_width = horizontal_area_width
        horizontal_photo_height = (available_height - gap) // 2
        
        photo_index = 0
        
        # 세로 배치 (왼쪽 3장)
        for i in range(3):
            if photo_index < len(page_images):
                image_data = page_images[photo_index]
                image = image_data['image']
                
                # 비율 유지하면서 리사이징
                resized_image = resize_maintain_aspect_ratio(image, vertical_photo_width, vertical_photo_height)
                
                # 중앙 정렬로 배치
                img_width, img_height = resized_image.size
                x = margin + (vertical_photo_width - img_width) // 2
                y = margin + i * (vertical_photo_height + gap) + (vertical_photo_height - img_height) // 2
                
                a4_image.paste(resized_image, (int(x), int(y)))
                photo_index += 1
        
        # 가로 배치 (오른쪽 2장, 90도 회전)
        for i in range(2):
            if photo_index < len(page_images):
                image_data = page_images[photo_index]
                image = image_data['image']
                
                # 90도 회전 후 비율 유지하면서 리사이징
                rotated_image = image.rotate(90, expand=True)
                resized_image = resize_maintain_aspect_ratio(rotated_image, horizontal_photo_width, horizontal_photo_height)
                
                # 중앙 정렬로 배치
                img_width, img_height = resized_image.size
                x = margin + vertical_area_width + gap + (horizontal_photo_width - img_width) // 2
                y = margin + i * (horizontal_photo_height + gap) + (horizontal_photo_height - img_height) // 2
                
                a4_image.paste(resized_image, (int(x), int(y)))
                photo_index += 1
        
        pages.append(a4_image)
    
    # 개별 페이지 리스트 반환 (다중 페이지 지원)
    return pages

def arrange_construction_photos_portrait(image_data_list, a4_width, a4_height):
    """세로 A4에서 시공사진 배치: 2x2 = 4장 per page"""
    margin = 50
    gap = 20
    
    # 페이지당 4장씩 처리
    photos_per_page = 4
    pages = []
    
    for page_start in range(0, len(image_data_list), photos_per_page):
        page_images = image_data_list[page_start:page_start + photos_per_page]
        
        # A4 용지 생성
        a4_image = Image.new('RGB', (a4_width, a4_height), 'white')
        
        # 배치 영역 계산
        available_width = a4_width - 2 * margin
        available_height = a4_height - 2 * margin
        
        photo_width = (available_width - gap) // 2
        photo_height = (available_height - gap) // 2
        
        # 2x2 배치
        photo_index = 0
        for row in range(2):
            for col in range(2):
                if photo_index < len(page_images):
                    image_data = page_images[photo_index]
                    image = image_data['image']
                    
                    # 비율 유지하면서 리사이징
                    resized_image = resize_maintain_aspect_ratio(image, photo_width, photo_height)
                    
                    # 중앙 정렬로 배치
                    img_width, img_height = resized_image.size
                    x = margin + col * (photo_width + gap) + (photo_width - img_width) // 2
                    y = margin + row * (photo_height + gap) + (photo_height - img_height) // 2
                    
                    a4_image.paste(resized_image, (int(x), int(y)))
                    photo_index += 1
        
        pages.append(a4_image)
    
    # 개별 페이지 리스트 반환 (다중 페이지 지원)
    return pages

def arrange_multiple_construction_photos(image_data_list, paper_orientation='portrait'):
    """여러 시공사진을 A4 용지에 최적 배치"""
    # 용지 방향에 따른 A4 크기 설정
    if paper_orientation == 'landscape':
        a4_width, a4_height = A4_HEIGHT, A4_WIDTH  # 가로: 3508 x 2480
        # 가로 A4에서 시공사진 배치: 세로 3장 + 눕힌 2장
        return arrange_construction_photos_landscape(image_data_list, a4_width, a4_height)
    else:
        a4_width, a4_height = A4_WIDTH, A4_HEIGHT  # 세로: 2480 x 3508
        # 세로 A4에서는 기존 로직 사용
        return arrange_construction_photos_portrait(image_data_list, a4_width, a4_height)


def arrange_multiple_document_photos(image_data_list, paper_orientation='portrait'):
    """여러 대문사진을 A4 용지에 최적 배치"""
    # 용지 방향에 따른 A4 크기 설정
    if paper_orientation == 'landscape':
        a4_width, a4_height = A4_HEIGHT, A4_WIDTH  # 가로: 3508 x 2480
        photos_per_page = 2  # 가로에서는 2장
    else:
        a4_width, a4_height = A4_WIDTH, A4_HEIGHT  # 세로: 2480 x 3508
        photos_per_page = 2  # 세로에서도 2장 (큰 사진이므로)
    
    margin = 50
    gap = 20
    pages = []
    
    for page_start in range(0, len(image_data_list), photos_per_page):
        page_images = image_data_list[page_start:page_start + photos_per_page]
        
        # A4 용지 생성
        a4_image = Image.new('RGB', (a4_width, a4_height), 'white')
        
        # 배치 영역 계산
        available_width = a4_width - 2 * margin
        available_height = a4_height - 2 * margin
        
        if paper_orientation == 'landscape':
            # 가로 모드: 나란히 배치
            photo_width = (available_width - gap) // 2
            photo_height = available_height
            
            for i, image_data in enumerate(page_images):
                if i < 2:  # 최대 2장
                    image = image_data['image']
                    
                    # 비율 유지하면서 리사이징
                    resized_image = resize_maintain_aspect_ratio(image, photo_width, photo_height)
                    
                    # 중앙 정렬로 배치
                    img_width, img_height = resized_image.size
                    x = margin + i * (photo_width + gap) + (photo_width - img_width) // 2
                    y = margin + (photo_height - img_height) // 2
                    
                    a4_image.paste(resized_image, (int(x), int(y)))
        else:
            # 세로 모드: 위아래 배치
            photo_width = available_width
            photo_height = (available_height - gap) // 2
            
            for i, image_data in enumerate(page_images):
                if i < 2:  # 최대 2장
                    image = image_data['image']
                    
                    # 비율 유지하면서 리사이징
                    resized_image = resize_maintain_aspect_ratio(image, photo_width, photo_height)
                    
                    # 중앙 정렬로 배치
                    img_width, img_height = resized_image.size
                    x = margin + (photo_width - img_width) // 2
                    y = margin + i * (photo_height + gap) + (photo_height - img_height) // 2
                    
                    a4_image.paste(resized_image, (int(x), int(y)))
        
        pages.append(a4_image)
    
    # 개별 페이지 리스트 반환 (다중 페이지 지원)
    return pages

def create_optimized_mixed_layout(construction_images, document_images, paper_orientation='portrait'):
    """모든 사진을 다중 페이지로 배치하는 함수"""
    if paper_orientation == 'landscape':
        a4_width, a4_height = A4_LANDSCAPE_SIZE
    else:
        a4_width, a4_height = A4_PORTRAIT_SIZE
    
    construction_count = len(construction_images)
    document_count = len(document_images)
    
    if construction_count == 0 and document_count == 0:
        return None, "배치할 사진이 없습니다.", 0, 0, []
    
    try:
        all_pages = []
        total_construction_placed = 0
        total_document_placed = 0
        
        # 이미지 데이터를 파일 객체로 변환
        construction_image_objects = []
        for img_data in construction_images:
            image = Image.open(io.BytesIO(img_data))
            construction_image_objects.append({'image': image})
        
        document_image_objects = []
        for img_data in document_images:
            image = Image.open(io.BytesIO(img_data))
            document_image_objects.append({'image': image})
        
        # 대문사진 페이지들 생성 (페이지당 2장)
        if document_count > 0:
            document_pages = arrange_multiple_document_photos(document_image_objects, paper_orientation)
            all_pages.extend(document_pages)
            total_document_placed = document_count
            print(f"대문사진 페이지 생성 완료: {len(document_pages)}페이지, {total_document_placed}장 배치")
        
        # 시공사진 페이지들 생성 (세로: 4장/페이지, 가로: 5장/페이지)
        if construction_count > 0:
            construction_pages = arrange_multiple_construction_photos(construction_image_objects, paper_orientation)
            all_pages.extend(construction_pages)
            total_construction_placed = construction_count
            print(f"시공사진 페이지 생성 완료: {len(construction_pages)}페이지, {total_construction_placed}장 배치")
        
        # 메모리 정리
        for img_obj in construction_image_objects:
            img_obj['image'].close()
        for img_obj in document_image_objects:
            img_obj['image'].close()
        
        total_placed = total_construction_placed + total_document_placed
        total_pages = len(all_pages)
        
        message = f"다중 페이지 배치 완료! 총 {total_pages}페이지에 {total_placed}장 배치 (시공사진: {total_construction_placed}장, 대문사진: {total_document_placed}장)"
        
        print(f"최종 배치 결과: 총 {total_pages}페이지, {total_placed}장 (시공사진: {total_construction_placed}장, 대문사진: {total_document_placed}장)")
        
        return all_pages, message, total_construction_placed, total_document_placed, total_pages
        
    except Exception as e:
        print(f"다중 페이지 배치 오류: {str(e)}")
        return None, f"배치 중 오류가 발생했습니다: {str(e)}", 0, 0, 0

# 복잡한 배치 함수들도 메모리 절약을 위해 제거됨

# 새로운 최적화 혼합 배치 엔드포인트
@app.route('/upload_optimized', methods=['POST'])
def upload_optimized_files():
    """두 종류 사진을 최적화해서 다중 페이지 배치하는 엔드포인트"""
    try:
        construction_files = request.files.getlist('construction_files')
        document_files = request.files.getlist('document_files')
        paper_orientation = request.form.get('paper_orientation', 'portrait')
        
        print(f"다중 페이지 배치 요청: 시공사진 {len(construction_files)}장, 대문사진 {len(document_files)}장")
        
        # 파일 유효성 검사 및 메모리 효율적 처리
        construction_images = []
        document_images = []
        
        # 시공사진 처리 (제한 없이 모두 처리)
        for i, file in enumerate(construction_files):
            if file and file.filename != '' and allowed_file(file.filename):
                try:
                    file_data = file.read()
                    # 파일 크기 체크 (메모리 보호)
                    if len(file_data) > 10 * 1024 * 1024:  # 10MB 제한
                        print(f"파일 크기 초과: {file.filename}")
                        continue
                    construction_images.append(file_data)
                except Exception as e:
                    print(f"시공사진 읽기 오류: {str(e)}")
                    continue
        
        # 대문사진 처리 (제한 없이 모두 처리)
        for i, file in enumerate(document_files):
            if file and file.filename != '' and allowed_file(file.filename):
                try:
                    file_data = file.read()
                    # 파일 크기 체크 (메모리 보호)
                    if len(file_data) > 10 * 1024 * 1024:  # 10MB 제한
                        print(f"파일 크기 초과: {file.filename}")
                        continue
                    document_images.append(file_data)
                except Exception as e:
                    print(f"대문사진 읽기 오류: {str(e)}")
                    continue
        
        if not construction_images and not document_images:
            return jsonify({'error': '유효한 업로드 사진이 없습니다.'}), 400
        
        print(f"처리할 이미지: 시공사진 {len(construction_images)}장, 대문사진 {len(document_images)}장")
        
        # 다중 페이지 배치 생성
        result = create_optimized_mixed_layout(construction_images, document_images, paper_orientation)
        
        if result[0] is None:  # 오류 케이스
            return jsonify({'error': result[1]}), 400
        
        result_pages, message, actual_construction_count, actual_document_count, total_pages = result
        
        # 고유한 배치 ID 생성
        layout_id = str(uuid.uuid4())
        
        # outputs 폴더 생성
        outputs_folder = 'static/outputs'
        os.makedirs(outputs_folder, exist_ok=True)
        
        # 각 페이지를 개별 파일로 저장
        page_filenames = []
        for i, page_img in enumerate(result_pages):
            # 이미지를 메모리에 저장
            img_buffer = io.BytesIO()
            page_img.save(img_buffer, format='PNG', dpi=(300, 300))
            img_buffer.seek(0)
            
            # 페이지별 파일명 생성
            filename = f"mixed_layout_{paper_orientation}_{layout_id}_page_{i+1}.png"
            page_filenames.append(filename)
            
            # 파일 저장
            file_path = os.path.join(outputs_folder, filename)
            with open(file_path, 'wb') as f:
                f.write(img_buffer.getvalue())
            
            # 메모리 정리
            img_buffer.close()
            page_img.close()
        
        # 메모리 정리
        del construction_images
        del document_images
        
        # 배치 정보 저장
        layout_info = {
            'layout_id': layout_id,
            'page_filenames': page_filenames,
            'total_pages': total_pages,
            'construction_count': actual_construction_count,
            'document_count': actual_document_count,
            'paper_orientation': paper_orientation,
            'upload_time': time.time(),
            'message': message
        }
        uploaded_files[layout_id] = layout_info
        
        print(f"다중 페이지 배치 성공: {total_pages}페이지 생성")
        
        return jsonify({
            'success': True,
            'message': message,
            'layout_id': layout_id,
            'page_filenames': page_filenames,
            'total_pages': total_pages,
            'construction_count': actual_construction_count,
            'document_count': actual_document_count,
            'uploaded_construction': len(construction_files),
            'uploaded_document': len(document_files),
            'paper_orientation': paper_orientation
        })
        
    except MemoryError:
        print("메모리 부족 오류 발생")
        return jsonify({'error': '메모리가 부족합니다. 더 적은 수의 사진으로 시도해주세요.'}), 500
    except Exception as e:
        print(f"다중 페이지 배치 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'레이아웃 생성 중 오류가 발생했습니다: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 