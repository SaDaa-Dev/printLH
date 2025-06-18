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
    """가로 A4에서 시공사진 배치: 정방향 3장 + 회전 2장 = 총 5장 per page"""
    # 시공사진 크기 (9cm × 11cm, 300 DPI 기준)
    photo_w_px = int(90 * 300 / 25.4)   # 약 1063픽셀 (9cm)
    photo_h_px = int(110 * 300 / 25.4)  # 약 1299픽셀 (11cm)
    
    # 마진과 갭 최소화
    margin = 30  # 줄임
    gap = 15     # 줄임
    
    # 페이지당 5장씩 처리
    photos_per_page = 5
    pages = []
    
    for page_start in range(0, len(image_data_list), photos_per_page):
        page_images = image_data_list[page_start:page_start + photos_per_page]
        
        # A4 용지 생성
        a4_image = Image.new('RGB', (a4_width, a4_height), 'white')
        
        # 배치 영역 계산
        available_width = a4_width - 2 * margin   # 약 3448px (29.1cm)
        available_height = a4_height - 2 * margin # 약 2420px (20.4cm)
        
        # 실제 배치 계산:
        # 위쪽 정방향 3장: 3 × 9cm + 2 × 0.4cm = 27.8cm (가능)
        # 아래쪽 회전 2장: 2 × 11cm + 1 × 0.4cm = 22.4cm (가능)
        # 전체 높이: 11cm + 9cm + 0.4cm = 20.4cm (가능)
        
        photo_index = 0
        
        # 1단계: 위쪽 정방향 3장 (가로 배치)
        top_photos_width = 3 * photo_w_px + 2 * gap  # 3장 + 2개 갭
        if top_photos_width <= available_width:
            start_x = margin + (available_width - top_photos_width) // 2  # 가로 중앙 정렬
            start_y = margin
            
            for i in range(3):
                if photo_index < len(page_images):
                    image_data = page_images[photo_index]
                    image = image_data['image']
                    
                    # 정방향 리사이징 (9cm × 11cm)
                    resized_image = resize_to_exact_size(image, photo_w_px, photo_h_px)
                    
                    # 배치 위치
                    x = start_x + i * (photo_w_px + gap)
                    y = start_y
                    
                    a4_image.paste(resized_image, (int(x), int(y)))
                    photo_index += 1
                    resized_image.close()
        
        # 2단계: 아래쪽 회전 2장 (가로 배치)
        bottom_photos_width = 2 * photo_h_px + gap  # 회전된 2장 + 1개 갭
        if bottom_photos_width <= available_width:
            start_x = margin + (available_width - bottom_photos_width) // 2  # 가로 중앙 정렬
            start_y = margin + photo_h_px + gap  # 위쪽 사진 높이 + 갭
            
            for i in range(2):
                if photo_index < len(page_images):
                    image_data = page_images[photo_index]
                    image = image_data['image']
                    
                    # 정방향으로 리사이징 후 90도 회전
                    resized_image = resize_to_exact_size(image, photo_w_px, photo_h_px)
                    rotated_image = resized_image.rotate(90, expand=True)
                    
                    # 배치 위치
                    x = start_x + i * (photo_h_px + gap)  # 회전된 너비 사용
                    y = start_y
                    
                    a4_image.paste(rotated_image, (int(x), int(y)))
                    photo_index += 1
                    resized_image.close()
                    rotated_image.close()
        
        pages.append(a4_image)
    
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
        # 가로 A4에서 시공사진 배치: 정방향 3장 + 회전 2장
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

def calculate_grid_layout(photo_type, a4_width_cm, a4_height_cm, margin_cm=0.2):
    """같은 타입 사진의 최적 그리드 배치 계산 (혼합 배치 포함)"""
    if photo_type == 'construction':
        photo_w_cm, photo_h_cm = 9.0, 11.0
    else:  # document
        photo_w_cm, photo_h_cm = 11.4, 15.2
    
    # 정방향 배치
    cols_normal = int((a4_width_cm + margin_cm) // (photo_w_cm + margin_cm))
    rows_normal = int((a4_height_cm + margin_cm) // (photo_h_cm + margin_cm))
    total_normal = cols_normal * rows_normal
    
    # 회전 배치
    cols_rotated = int((a4_width_cm + margin_cm) // (photo_h_cm + margin_cm))
    rows_rotated = int((a4_height_cm + margin_cm) // (photo_w_cm + margin_cm))
    total_rotated = cols_rotated * rows_rotated
    
    # 혼합 배치 (시공사진만, A4 가로 방향에서 특히 효과적)
    mixed_total = 0
    mixed_layout = None
    
    if photo_type == 'construction':
        # 전략 1: 위쪽 정방향 + 아래쪽 회전
        top_cols = int((a4_width_cm + margin_cm) // (photo_w_cm + margin_cm))  # 정방향 가로 개수
        top_space_height = photo_h_cm + margin_cm  # 위쪽 필요 세로 공간
        
        if top_space_height <= a4_height_cm:  # 위쪽 공간이 확보되면
            remaining_height = a4_height_cm - top_space_height
            bottom_rows = int((remaining_height + margin_cm) // (photo_w_cm + margin_cm))  # 회전된 사진 세로 개수
            bottom_cols = int((a4_width_cm + margin_cm) // (photo_h_cm + margin_cm))  # 회전된 사진 가로 개수
            
            if bottom_rows > 0:
                mixed_1 = top_cols + (bottom_cols * bottom_rows)
                if mixed_1 > mixed_total:
                    mixed_total = mixed_1
                    mixed_layout = ('top_normal_bottom_rotated', top_cols, bottom_cols, bottom_rows)
        
        # 전략 2: 위쪽 회전 + 아래쪽 정방향
        top_cols = int((a4_width_cm + margin_cm) // (photo_h_cm + margin_cm))  # 회전 가로 개수
        top_space_height = photo_w_cm + margin_cm  # 위쪽 필요 세로 공간
        
        if top_space_height <= a4_height_cm:
            remaining_height = a4_height_cm - top_space_height
            bottom_rows = int((remaining_height + margin_cm) // (photo_h_cm + margin_cm))  # 정방향 세로 개수
            bottom_cols = int((a4_width_cm + margin_cm) // (photo_w_cm + margin_cm))  # 정방향 가로 개수
            
            if bottom_rows > 0:
                mixed_2 = top_cols + (bottom_cols * bottom_rows)
                if mixed_2 > mixed_total:
                    mixed_total = mixed_2
                    mixed_layout = ('top_rotated_bottom_normal', top_cols, bottom_cols, bottom_rows)
    
    print(f"   {photo_type} 그리드 계산:")
    print(f"   정방향: {cols_normal}×{rows_normal} = {total_normal}개")
    print(f"   회전됨: {cols_rotated}×{rows_rotated} = {total_rotated}개")
    if mixed_total > 0:
        print(f"   혼합배치: {mixed_layout[0]} = {mixed_total}개")
    
    # 가장 효율적인 방법 선택
    if mixed_total > max(total_normal, total_rotated):
        return 'mixed', mixed_layout[1], mixed_layout[2], mixed_total, mixed_layout
    elif total_rotated > total_normal:
        return 'rotated', cols_rotated, rows_rotated, total_rotated, None
    else:
        return 'normal', cols_normal, rows_normal, total_normal, None

def create_grid_layout_page(photos, orientation, a4_width_cm, a4_height_cm, construction_images, document_images):
    """그리드 배치로 페이지 생성"""
    if orientation == 'landscape':
        a4_width_px, a4_height_px = cm_to_px(a4_width_cm), cm_to_px(a4_height_cm)
    else:
        a4_width_px, a4_height_px = cm_to_px(a4_width_cm), cm_to_px(a4_height_cm)
    
    layout_image = Image.new('RGB', (a4_width_px, a4_height_px), 'white')
    margin_px = cm_to_px(0.2)
    
    # 이미지 데이터 매핑
    image_map = {}
    for i, img_data in enumerate(construction_images):
        image_map[f"construction_{i}"] = img_data
    for i, img_data in enumerate(document_images):
        image_map[f"document_{i}"] = img_data
    
    # 첫 번째 사진 타입으로 그리드 계산
    first_photo = photos[0]
    grid_type, cols, rows, max_photos, mixed_layout = calculate_grid_layout(
        first_photo.photo_type, a4_width_cm, a4_height_cm
    )
    
    # 그리드 배치
    placed_count = 0
    for i, photo in enumerate(photos[:max_photos]):  # 최대 개수만큼만 배치
        row = i // cols
        col = i % cols
        
        # 기본 크기
        if photo.photo_type == 'construction':
            photo_w_px, photo_h_px = cm_to_px(9.0), cm_to_px(11.0)
        else:
            photo_w_px, photo_h_px = cm_to_px(11.4), cm_to_px(15.2)
        
        # 회전 처리
        if grid_type == 'rotated':
            final_w_px, final_h_px = photo_h_px, photo_w_px
            rotated = True
        else:
            final_w_px, final_h_px = photo_w_px, photo_h_px
            rotated = False
        
        # 배치 위치 계산
        x = margin_px + col * (final_w_px + margin_px)
        y = margin_px + row * (final_h_px + margin_px)
        
        # 이미지 처리
        if photo.photo_id in image_map:
            img_data = image_map[photo.photo_id]
            image = Image.open(io.BytesIO(img_data))
            
            # 정방향으로 리사이징
            resized_image = resize_to_exact_size(image, photo_w_px, photo_h_px)
            
            # 회전 처리
            if rotated:
                final_image = resized_image.rotate(90, expand=True)
                resized_image.close()
            else:
                final_image = resized_image
            
            # 배치
            if x + final_image.width <= a4_width_px and y + final_image.height <= a4_height_px:
                layout_image.paste(final_image, (int(x), int(y)))
                placed_count += 1
                print(f"   ✅ {photo.photo_id} 그리드 배치: ({int(x)}, {int(y)}) {'회전' if rotated else '정방향'}")
            
            image.close()
            final_image.close()
    
    return layout_image, placed_count

def create_optimized_mixed_layout(construction_images, document_images, paper_orientation='portrait'):
    """개선된 혼합 배치: 같은 타입이 많으면 그리드, 혼합이면 2D 빈패킹"""
    print(f"개선된 배치 시작 - 시공사진: {len(construction_images)}장, 대문사진: {len(document_images)}장, 방향: {paper_orientation}")
    
    try:
        # 방향별 A4 크기 설정
        if paper_orientation == 'portrait':
            a4_width_cm, a4_height_cm = 21.0, 29.7
        else:
            a4_width_cm, a4_height_cm = 29.7, 21.0
        
        print(f"A4 크기: {a4_width_cm}cm x {a4_height_cm}cm")
        
        # Photo 객체들 생성
        all_photos = create_photo_objects(construction_images, document_images)
        
        if len(all_photos) == 0:
            return None, "배치할 사진이 없습니다.", 0, 0, []
        
        pages = []
        remaining_photos = all_photos.copy()
        page_num = 1
        total_construction_placed = 0
        total_document_placed = 0
        
        while remaining_photos:
            print(f"\n=== 페이지 {page_num} 배치 시작 - 남은 사진: {len(remaining_photos)}장 ===")
            
            # 남은 사진 타입별 개수 확인
            construction_count = sum(1 for p in remaining_photos if p.photo_type == 'construction')
            document_count = sum(1 for p in remaining_photos if p.photo_type == 'document')
            
            print(f"남은 사진: 시공 {construction_count}장, 대문 {document_count}장")
            
            placed_count = 0
            page_image = None
            
            # 전략 1: 시공사진이 있으면 먼저 배치 (혼합 상황에서도 시공사진 우선)
            if construction_count > 0:
                print("🏗️ 시공사진 우선 배치 시도")
                # 시공사진이 있으면 먼저 배치 (대문사진 유무와 관계없이)
                construction_image_data = []
                for photo in remaining_photos:
                    if photo.photo_type == 'construction':
                        # photo_id에서 실제 인덱스 추출 (예: "construction_3" -> 3)
                        try:
                            actual_index = int(photo.photo_id.split('_')[1])
                            if actual_index < len(construction_images):
                                img_data = construction_images[actual_index]
                                image = Image.open(io.BytesIO(img_data))
                                construction_image_data.append({
                                    'image': image,
                                    'filename': f'construction_{actual_index}.jpg'
                                })
                        except (ValueError, IndexError):
                            print(f"Invalid photo_id format: {photo.photo_id}")
                            continue
                
                if construction_image_data:
                    # 가로/세로 방향에 따른 배치
                    if paper_orientation == 'landscape':
                        # 가로 A4: 5장 배치
                        a4_width, a4_height = cm_to_px(a4_width_cm), cm_to_px(a4_height_cm)
                        result_pages = arrange_construction_photos_landscape(construction_image_data, a4_width, a4_height)
                        placed_count = min(5, len(construction_image_data))
                    else:
                        # 세로 A4: 4장 배치
                        a4_width, a4_height = cm_to_px(a4_width_cm), cm_to_px(a4_height_cm)
                        result_pages = arrange_construction_photos_portrait(construction_image_data, a4_width, a4_height)
                        placed_count = min(4, len(construction_image_data))
                    
                    if result_pages:
                        page_image = result_pages[0]  # 첫 번째 페이지 사용
                        total_construction_placed += placed_count
                        # 배치된 시공사진들을 제거
                        remaining_photos = remaining_photos[placed_count:]
                        
                        # 이미지 정리
                        for img_data in construction_image_data:
                            img_data['image'].close()
            
            # 전략 2: 시공사진이 모두 처리된 후 대문사진 배치
            elif document_count >= 1:
                print("📄 대문사진 배치 시도")
                # 대문사진 데이터 준비
                document_image_data = []
                for photo in remaining_photos:
                    if photo.photo_type == 'document':
                        # photo_id에서 실제 인덱스 추출 (예: "document_2" -> 2)
                        try:
                            actual_index = int(photo.photo_id.split('_')[1])
                            if actual_index < len(document_images):
                                img_data = document_images[actual_index]
                                image = Image.open(io.BytesIO(img_data))
                                document_image_data.append({
                                    'image': image,
                                    'filename': f'document_{actual_index}.jpg'
                                })
                        except (ValueError, IndexError):
                            print(f"Invalid photo_id format: {photo.photo_id}")
                            continue
                
                if document_image_data:
                    # 가로/세로 방향에 따른 배치 (대문사진은 보통 2장씩)
                    a4_width, a4_height = cm_to_px(a4_width_cm), cm_to_px(a4_height_cm)
                    result_pages = arrange_multiple_document_photos(document_image_data, paper_orientation)
                    placed_count = min(2, len(document_image_data))  # 대문사진은 최대 2장
                    
                    if result_pages:
                        page_image = result_pages[0]  # 첫 번째 페이지 사용
                        total_document_placed += placed_count
                        # 배치된 대문사진들을 제거
                        remaining_photos = remaining_photos[placed_count:]
                        
                        # 이미지 정리
                        for img_data in document_image_data:
                            img_data['image'].close()
                
            else:
                # 전략 3: 혼합 배치는 2D 빈패킹 사용
                print("🧩 2D 빈패킹 혼합 배치 시도")
                packer = BinPacker(
                    cm_to_px(a4_width_cm), 
                    cm_to_px(a4_height_cm), 
                    margin_cm=0.2
                )
                
                placed_count, placed_photos = packer.pack_photos(remaining_photos.copy())
                
                if placed_count == 0:
                    print("더 이상 배치할 수 없습니다.")
                    break
                
                page_image = create_optimized_layout_image(
                    all_photos, placed_photos, paper_orientation,
                    construction_images, document_images
                )
                
                # 배치된 사진 개수 집계
                for photo in placed_photos:
                    if photo.photo_type == 'construction':
                        total_construction_placed += 1
                    elif photo.photo_type == 'document':
                        total_document_placed += 1
                
                # 배치된 사진들 제거
                placed_ids = {photo.photo_id for photo in placed_photos}
                remaining_photos = [p for p in remaining_photos if p.photo_id not in placed_ids]
            
            if placed_count > 0 and page_image is not None:
                pages.append(page_image)
                print(f"페이지 {page_num} 완성 - {placed_count}장 배치됨")
                page_num += 1
            else:
                print("배치 실패")
                break
            
            # 무한 루프 방지
            if page_num > 20:
                print("최대 페이지 수 도달")
                break
        
        total_placed = total_construction_placed + total_document_placed
        total_pages = len(pages)
        
        print(f"\n=== 최종 결과 ===")
        print(f"총 {total_pages}개 페이지 생성")
        print(f"배치된 사진: 시공사진 {total_construction_placed}장, 대문사진 {total_document_placed}장")
        
        if not pages:
            if paper_orientation == 'portrait':
                a4_width, a4_height = A4_PORTRAIT_SIZE
            else:
                a4_width, a4_height = A4_LANDSCAPE_SIZE
            empty_page = Image.new('RGB', (a4_width, a4_height), 'white')
            pages.append(empty_page)
            total_pages = 1
        
        message = f"개선된 배치 완료! 총 {total_pages}페이지에 {total_placed}장 배치 (시공사진: {total_construction_placed}장, 대문사진: {total_document_placed}장)"
        
        return pages, message, total_construction_placed, total_document_placed, total_pages
        
    except Exception as e:
        print(f"개선된 배치 오류: {str(e)}")
        import traceback
        traceback.print_exc()
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

# 2D 빈 패킹을 위한 클래스들
class Photo:
    def __init__(self, photo_id, width_cm, height_cm, photo_type):
        self.photo_id = photo_id
        self.width_cm = width_cm
        self.height_cm = height_cm
        self.photo_type = photo_type  # 'construction' or 'document'
        self.placed_x = None
        self.placed_y = None
        self.rotated = False
        self.placed = False

class Rectangle:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y  
        self.width = width
        self.height = height
    
    def area(self):
        return self.width * self.height
    
    def can_fit(self, photo_width, photo_height, margin=0):
        """사진이 이 공간에 들어갈 수 있는지 확인"""
        return (self.width >= photo_width + margin and 
                self.height >= photo_height + margin)

class BinPacker:
    def __init__(self, bin_width, bin_height, margin_cm=0.2):
        self.bin_width = bin_width
        self.bin_height = bin_height
        self.margin_px = cm_to_px(margin_cm)
        self.available_spaces = [Rectangle(0, 0, bin_width, bin_height)]
        self.placed_photos = []
        
        print(f"📦 BinPacker 초기화")
        print(f"   A4 크기: {bin_width}×{bin_height}px")
        print(f"   여백: {margin_cm}cm ({self.margin_px}px)")
        print(f"   시공사진 크기: 9×11cm ({cm_to_px(9.0)}×{cm_to_px(11.0)}px)")
        print(f"   대문사진 크기: 11.4×15.2cm ({cm_to_px(11.4)}×{cm_to_px(15.2)}px)")
    
    def get_best_orientation(self, photo, space):
        """사진의 최적 방향(정방향/회전) 결정"""
        # 기본 크기 (cm에서 픽셀로 변환)
        if photo.photo_type == 'construction':
            w_px, h_px = cm_to_px(9.0), cm_to_px(11.0)
        else:  # document
            w_px, h_px = cm_to_px(11.4), cm_to_px(15.2)
        
        # 정방향으로 들어가는지 확인
        fits_normal = space.can_fit(w_px, h_px, self.margin_px)
        # 회전해서 들어가는지 확인  
        fits_rotated = space.can_fit(h_px, w_px, self.margin_px)
        
        if fits_normal and fits_rotated:
            # 둘 다 가능하면 남는 공간이 더 적은 방향 선택
            waste_normal = (space.width - w_px) * (space.height - h_px)
            waste_rotated = (space.width - h_px) * (space.height - w_px) 
            if waste_rotated < waste_normal:
                return True, (h_px, w_px)  # 회전: 높이×너비
            else:
                return False, (w_px, h_px)  # 정방향: 너비×높이
        elif fits_rotated:
            return True, (h_px, w_px)  # 회전만 가능
        elif fits_normal:
            return False, (w_px, h_px)  # 정방향만 가능
        else:
            return None, None  # 들어가지 않음
    
    def find_best_space(self, photo):
        """사진에 가장 적합한 빈 공간 찾기 (Best Fit 전략)"""
        best_space_idx = -1
        best_fit_info = None
        min_waste = float('inf')
        
        for i, space in enumerate(self.available_spaces):
            rotation_info = self.get_best_orientation(photo, space)
            if rotation_info[0] is not None:  # 들어갈 수 있음
                rotated, (fit_w, fit_h) = rotation_info
                waste = space.area() - (fit_w * fit_h)
                
                if waste < min_waste:
                    min_waste = waste
                    best_space_idx = i
                    best_fit_info = (rotated, fit_w, fit_h)
        
        return best_space_idx, best_fit_info
    
    def split_space(self, space, photo_width, photo_height):
        """사진을 배치한 후 남은 공간을 겹치지 않게 분할"""
        new_spaces = []
        
        # 우측 공간 (전체 높이)
        if space.width > photo_width + self.margin_px:
            new_spaces.append(Rectangle(
                space.x + photo_width + self.margin_px,
                space.y,
                space.width - photo_width - self.margin_px,
                space.height
            ))
        
        # 하단 공간 (사진 너비만큼만)
        if space.height > photo_height + self.margin_px:
            new_spaces.append(Rectangle(
                space.x,
                space.y + photo_height + self.margin_px,
                photo_width,  # 사진 너비만큼만 (우측 공간과 겹치지 않게)
                space.height - photo_height - self.margin_px
            ))
        
        return new_spaces
    
    def place_photo(self, photo):
        """사진을 배치 시도"""
        space_idx, fit_info = self.find_best_space(photo)
        
        if space_idx == -1:
            print(f"⚠️  {photo.photo_id} ({photo.photo_type}) 배치 불가 - 남은 공간 없음")
            return False  # 배치 불가
        
        # 공간 제거
        space = self.available_spaces.pop(space_idx)
        rotated, fit_w, fit_h = fit_info
        
        # 사진 배치 정보 설정
        photo.placed_x = space.x
        photo.placed_y = space.y
        photo.rotated = rotated
        photo.placed = True
        
        # 배치 정보 출력
        rotation_text = "회전됨" if rotated else "정방향"
        print(f"✅ {photo.photo_id} ({photo.photo_type}) 배치 완료")
        print(f"   위치: ({int(space.x)}, {int(space.y)})")
        print(f"   크기: {photo.width_cm}×{photo.height_cm}cm → {fit_w}×{fit_h}px ({rotation_text})")
        
        self.placed_photos.append(photo)
        
        # 남은 공간 분할하여 추가
        new_spaces = self.split_space(space, fit_w, fit_h)
        self.available_spaces.extend(new_spaces)
        
        # 공간을 면적 기준으로 정렬 (큰 공간부터)
        self.available_spaces.sort(key=lambda s: s.area(), reverse=True)
        
        print(f"   남은 빈 공간: {len(self.available_spaces)}개")
        
        return True
    
    def pack_photos(self, photos):
        """모든 사진을 배치"""
        # 큰 사진부터 배치 (면적 기준)
        sorted_photos = sorted(photos, 
                              key=lambda p: p.width_cm * p.height_cm, 
                              reverse=True)
        
        placed_count = 0
        for photo in sorted_photos:
            if self.place_photo(photo):
                placed_count += 1
        
        return placed_count, self.placed_photos

def create_photo_objects(construction_images, document_images):
    """업로드된 이미지를 Photo 객체로 변환"""
    photos = []
    
    # 시공사진 (9cm × 11cm)
    for i, img_data in enumerate(construction_images):
        photo = Photo(f"construction_{i}", 9.0, 11.0, 'construction')
        photo.image_data = img_data
        photos.append(photo)
    
    # 대문사진 (11.4cm × 15.2cm)  
    for i, img_data in enumerate(document_images):
        photo = Photo(f"document_{i}", 11.4, 15.2, 'document')
        photo.image_data = img_data
        photos.append(photo)
    
    return photos

def optimize_a4_orientation(photos, margin_cm=0.2):
    """A4 용지 방향 최적화"""
    # A4 크기 (cm)
    A4_W, A4_H = 21.0, 29.7
    
    # 세로 A4 시도
    portrait_packer = BinPacker(cm_to_px(A4_W), cm_to_px(A4_H), margin_cm)
    portrait_count, portrait_placed = portrait_packer.pack_photos([
        Photo(p.photo_id, p.width_cm, p.height_cm, p.photo_type) 
        for p in photos
    ])
    
    # 가로 A4 시도
    landscape_packer = BinPacker(cm_to_px(A4_H), cm_to_px(A4_W), margin_cm)
    landscape_count, landscape_placed = landscape_packer.pack_photos([
        Photo(p.photo_id, p.width_cm, p.height_cm, p.photo_type) 
        for p in photos
    ])
    
    # 더 많이 배치된 방향 선택
    if landscape_count > portrait_count:
        return 'landscape', landscape_packer, landscape_placed
    else:
        return 'portrait', portrait_packer, portrait_placed

def create_optimized_layout_image(photos, placed_photos, orientation, construction_images, document_images):
    """최적화된 배치로 A4 이미지 생성"""
    if orientation == 'landscape':
        a4_width, a4_height = cm_to_px(29.7), cm_to_px(21.0)
    else:
        a4_width, a4_height = cm_to_px(21.0), cm_to_px(29.7)
    
    # A4 캔버스 생성
    layout_image = Image.new('RGB', (a4_width, a4_height), 'white')
    
    # 이미지 데이터 매핑
    image_map = {}
    for i, img_data in enumerate(construction_images):
        image_map[f"construction_{i}"] = img_data
    for i, img_data in enumerate(document_images):
        image_map[f"document_{i}"] = img_data
    
    # 배치된 사진들을 캔버스에 그리기
    for placed_photo in placed_photos:
        if placed_photo.photo_id in image_map:
            print(f"🖼️  {placed_photo.photo_id} 이미지 생성 중...")
            
            # === 1단계: 원본 이미지 로드 ===
            img_data = image_map[placed_photo.photo_id]
            image = Image.open(io.BytesIO(img_data))
            
            # === 2단계: 정방향으로 고정 크기 리사이징 ===
            if placed_photo.photo_type == 'construction':
                target_w_px, target_h_px = cm_to_px(9.0), cm_to_px(11.0)
                print(f"   시공사진 정방향 리사이징: {target_w_px}×{target_h_px}px")
            else:  # document
                target_w_px, target_h_px = cm_to_px(11.4), cm_to_px(15.2)
                print(f"   대문사진 정방향 리사이징: {target_w_px}×{target_h_px}px")
            
            # 정방향으로 리사이징 (항상 같은 크기)
            resized_image = resize_to_exact_size(image, target_w_px, target_h_px)
            print(f"   ✅ 1단계 리사이징 완료: {resized_image.size}")
            
            # === 3단계: 필요시 회전 처리 ===
            if placed_photo.rotated:
                rotated_image = resized_image.rotate(90, expand=True)
                print(f"   🔄 2단계 회전 완료: {resized_image.size} → {rotated_image.size}")
                resized_image.close()  # 메모리 정리
                final_image = rotated_image
            else:
                print(f"   ➡️  회전 없음: {resized_image.size} 유지")
                final_image = resized_image
            
            # === 4단계: 캔버스에 배치 ===
            x, y = int(placed_photo.placed_x), int(placed_photo.placed_y)
            print(f"   배치 위치: ({x}, {y})")
            print(f"   최종 이미지 크기: {final_image.size}")
            
            # 캔버스 경계 확인
            if x + final_image.width <= a4_width and y + final_image.height <= a4_height:
                layout_image.paste(final_image, (x, y))
                print(f"   ✅ 성공적으로 배치됨")
            else:
                print(f"   ⚠️ 경계를 벗어남: A4 크기 {a4_width}×{a4_height}, 필요 공간: {x + final_image.width}×{y + final_image.height}")
            
            # 메모리 정리
            image.close()
            final_image.close()
    
    return layout_image

def resize_to_exact_size(image, target_width, target_height):
    """이미지를 정확한 크기로 리사이징 (비율 유지하고 크롭)"""
    original_width, original_height = image.size
    target_ratio = target_width / target_height
    original_ratio = original_width / original_height
    
    if original_ratio > target_ratio:
        # 원본이 더 가로가 긴 경우 - 세로 기준으로 크롭
        new_height = original_height
        new_width = int(original_height * target_ratio)
        left = (original_width - new_width) // 2
        top = 0
        right = left + new_width
        bottom = original_height
    else:
        # 원본이 더 세로가 긴 경우 - 가로 기준으로 크롭
        new_width = original_width
        new_height = int(original_width / target_ratio)
        left = 0
        top = (original_height - new_height) // 2
        right = original_width
        bottom = top + new_height
    
    # 크롭 후 리사이징
    cropped = image.crop((left, top, right, bottom))
    resized = cropped.resize((target_width, target_height), Image.Resampling.LANCZOS)
    cropped.close()
    
    return resized

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 