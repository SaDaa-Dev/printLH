from flask import Flask, render_template, request, send_file, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import os
import tempfile
import uuid
import shutil
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

# 허용된 파일 확장자
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}

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

def arrange_multiple_construction_photos(image_data_list, paper_orientation='portrait'):
    """여러 시공사진을 A4 용지에 최적 배치"""
    # 시공사진 크기 (9cm × 11cm, 300 DPI 기준)
    photo_width = int(90 * 300 / 25.4)   # 약 1063픽셀
    photo_height = int(110 * 300 / 25.4)  # 약 1299픽셀
    
    # 용지 방향에 따른 A4 크기 설정
    if paper_orientation == 'landscape':
        a4_width, a4_height = A4_HEIGHT, A4_WIDTH  # 가로: 3508 x 2480
    else:
        a4_width, a4_height = A4_WIDTH, A4_HEIGHT  # 세로: 2480 x 3508
    
    # 최적 배치 계산
    layout = calculate_optimal_layout(photo_width, photo_height, a4_width, a4_height)
    
    # A4 용지에 배치할 수 있는 최대 개수
    max_photos = layout['cols'] * layout['rows']
    
    # 실제 배치할 이미지 개수 (최대 개수와 실제 이미지 개수 중 작은 값)
    photos_to_place = min(len(image_data_list), max_photos)
    
    # 각 이미지를 목표 크기로 리사이징
    resized_photos = []
    for i in range(photos_to_place):
        image_data = image_data_list[i]
        image = image_data['image']
        
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
        
        resized_photos.append(resized_photo)
    
    # A4 용지에 배치
    a4_image = Image.new('RGB', (a4_width, a4_height), 'white')
    
    # 배치 계산
    margin = 50
    x_spacing = (a4_width - 2 * margin - layout['cols'] * layout['photo_width']) // max(1, layout['cols'] - 1) if layout['cols'] > 1 else 0
    y_spacing = (a4_height - 2 * margin - layout['rows'] * layout['photo_height']) // max(1, layout['rows'] - 1) if layout['rows'] > 1 else 0
    
    photo_index = 0
    for row in range(layout['rows']):
        for col in range(layout['cols']):
            if photo_index < len(resized_photos):
                x = margin + col * (layout['photo_width'] + x_spacing)
                y = margin + row * (layout['photo_height'] + y_spacing)
                a4_image.paste(resized_photos[photo_index], (x, y))
                photo_index += 1
    
    return a4_image

def arrange_multiple_document_photos(image_data_list, paper_orientation='portrait'):
    """여러 대문사진을 A4 용지에 최적 배치"""
    # 대문사진 크기 (11.4cm × 15.2cm, 300 DPI 기준)
    photo_width = int(114 * 300 / 25.4)   # 약 1346픽셀
    photo_height = int(152 * 300 / 25.4)  # 약 1795픽셀
    
    # 용지 방향에 따른 A4 크기 설정
    if paper_orientation == 'landscape':
        a4_width, a4_height = A4_HEIGHT, A4_WIDTH  # 가로: 3508 x 2480
    else:
        a4_width, a4_height = A4_WIDTH, A4_HEIGHT  # 세로: 2480 x 3508
    
    # 최적 배치 계산
    layout = calculate_optimal_layout(photo_width, photo_height, a4_width, a4_height)
    
    # A4 용지에 배치할 수 있는 최대 개수
    max_photos = layout['cols'] * layout['rows']
    
    # 실제 배치할 이미지 개수 (최대 개수와 실제 이미지 개수 중 작은 값)
    photos_to_place = min(len(image_data_list), max_photos)
    
    # 각 이미지를 목표 크기로 리사이징
    resized_photos = []
    for i in range(photos_to_place):
        image_data = image_data_list[i]
        image = image_data['image']
        
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
        
        resized_photos.append(resized_photo)
    
    # A4 용지에 배치
    a4_image = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
    
    # 배치 계산
    margin = 50
    x_spacing = (A4_WIDTH - 2 * margin - layout['cols'] * layout['photo_width']) // max(1, layout['cols'] - 1) if layout['cols'] > 1 else 0
    y_spacing = (A4_HEIGHT - 2 * margin - layout['rows'] * layout['photo_height']) // max(1, layout['rows'] - 1) if layout['rows'] > 1 else 0
    
    photo_index = 0
    for row in range(layout['rows']):
        for col in range(layout['cols']):
            if photo_index < len(resized_photos):
                x = margin + col * (layout['photo_width'] + x_spacing)
                y = margin + row * (layout['photo_height'] + y_spacing)
                a4_image.paste(resized_photos[photo_index], (x, y))
                photo_index += 1
    
    return a4_image

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True) 