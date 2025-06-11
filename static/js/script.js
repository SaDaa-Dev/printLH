// DOM 요소들
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const uploadButton = document.getElementById('uploadButton');
const selectedFilesSection = document.getElementById('selectedFilesSection');
const selectedFilesList = document.getElementById('selectedFilesList');
const processButton = document.getElementById('processButton');
const clearButton = document.getElementById('clearButton');
const previewSection = document.getElementById('previewSection');
const previewImage = document.getElementById('previewImage');
const previewInfo = document.getElementById('previewInfo');
const downloadButton = document.getElementById('downloadButton');
const printButton = document.getElementById('printButton');
const resetButton = document.getElementById('resetButton');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');

// 현재 파일 정보
let selectedFiles = [];
let currentFileId = null;
let currentPhotoType = 'construction';
let currentPaperOrientation = 'portrait';

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    updatePhotoTypeSelection();
    updatePaperOrientationSelection();
});

function initializeEventListeners() {
    // 업로드 버튼 클릭
    uploadButton.addEventListener('click', () => {
        fileInput.click();
    });

    // 업로드 영역 클릭
    uploadArea.addEventListener('click', (e) => {
        if (e.target !== uploadButton) {
            fileInput.click();
        }
    });

    // 파일 선택
    fileInput.addEventListener('change', handleFileSelect);

    // 드래그 앤 드롭
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // 사진 종류 선택
    const radioButtons = document.querySelectorAll('input[name="photo_type"]');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', updatePhotoTypeSelection);
    });

    // 용지 방향 선택
    const orientationButtons = document.querySelectorAll('input[name="paper_orientation"]');
    orientationButtons.forEach(radio => {
        radio.addEventListener('change', updatePaperOrientationSelection);
    });

    // 처리 버튼
    processButton.addEventListener('click', handleProcess);

    // 지우기 버튼
    clearButton.addEventListener('click', handleClear);

    // 다운로드 버튼
    downloadButton.addEventListener('click', handleDownload);

    // 인쇄 버튼
    printButton.addEventListener('click', handlePrint);

    // 리셋 버튼
    resetButton.addEventListener('click', handleReset);
}

function updatePhotoTypeSelection() {
    const selectedRadio = document.querySelector('input[name="photo_type"]:checked');
    currentPhotoType = selectedRadio.value;
    console.log('사진 종류 선택됨:', currentPhotoType);
}

function updatePaperOrientationSelection() {
    const selectedRadio = document.querySelector('input[name="paper_orientation"]:checked');
    currentPaperOrientation = selectedRadio.value;
    console.log('용지 방향 선택됨:', currentPaperOrientation);
}

function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    if (files.length > 0) {
        addFilesToSelection(files);
    }
}

function handleDragOver(event) {
    event.preventDefault();
    uploadArea.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.preventDefault();
    uploadArea.classList.remove('drag-over');
}

function handleDrop(event) {
    event.preventDefault();
    uploadArea.classList.remove('drag-over');
    
    const files = Array.from(event.dataTransfer.files);
    if (files.length > 0) {
        addFilesToSelection(files);
    }
}

function validateFile(file) {
    // 파일 크기 체크 (16MB)
    if (file.size > 16 * 1024 * 1024) {
        showError(`${file.name}: 파일 크기가 너무 큽니다. 16MB 이하의 파일을 선택해주세요.`);
        return false;
    }

    // 파일 형식 체크
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/bmp', 'image/tiff'];
    if (!allowedTypes.includes(file.type)) {
        showError(`${file.name}: 지원하지 않는 파일 형식입니다. JPG, PNG, GIF, BMP, TIFF 파일을 선택해주세요.`);
        return false;
    }

    return true;
}

function addFilesToSelection(files) {
    const validFiles = files.filter(validateFile);
    
    // 중복 파일 체크
    validFiles.forEach(file => {
        const isDuplicate = selectedFiles.some(selectedFile => 
            selectedFile.name === file.name && selectedFile.size === file.size
        );
        
        if (!isDuplicate) {
            selectedFiles.push(file);
        } else {
            showToast(`${file.name}은 이미 선택된 파일입니다.`, 'info');
        }
    });
    
    if (selectedFiles.length > 0) {
        updateSelectedFilesDisplay();
        selectedFilesSection.style.display = 'block';
    }
}

function updateSelectedFilesDisplay() {
    selectedFilesList.innerHTML = '';
    
    selectedFiles.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'selected-file-item';
        
        // 파일 미리보기 이미지 생성
        const img = document.createElement('img');
        img.alt = file.name;
        
        const reader = new FileReader();
        reader.onload = function(e) {
            img.src = e.target.result;
        };
        reader.readAsDataURL(file);
        
        // 파일명
        const fileName = document.createElement('div');
        fileName.className = 'file-name';
        fileName.textContent = file.name;
        
        // 삭제 버튼
        const removeBtn = document.createElement('button');
        removeBtn.className = 'remove-btn';
        removeBtn.innerHTML = '×';
        removeBtn.addEventListener('click', () => {
            selectedFiles.splice(index, 1);
            updateSelectedFilesDisplay();
            
            if (selectedFiles.length === 0) {
                selectedFilesSection.style.display = 'none';
            }
        });
        
        fileItem.appendChild(removeBtn);
        fileItem.appendChild(img);
        fileItem.appendChild(fileName);
        
        selectedFilesList.appendChild(fileItem);
    });
}

function handleProcess() {
    if (selectedFiles.length === 0) {
        showError('처리할 파일을 먼저 선택해주세요.');
        return;
    }
    
    // 진행 상황 표시
    showProgress();
    progressText.textContent = `${selectedFiles.length}장의 사진을 A4에 배치하고 있습니다...`;
    
    // FormData 생성
    const formData = new FormData();
    selectedFiles.forEach((file, index) => {
        formData.append(`files`, file);
    });
    formData.append('photo_type', currentPhotoType);
    formData.append('paper_orientation', currentPaperOrientation);

    // 업로드 요청
    fetch('/upload_multiple', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            handleUploadSuccess(data);
        } else {
            showError(data.error || '처리 중 오류가 발생했습니다.');
        }
    })
    .catch(error => {
        console.error('처리 오류:', error);
        showError('네트워크 오류가 발생했습니다. 다시 시도해주세요.');
    })
    .finally(() => {
        hideProgress();
    });
}

function handleClear() {
    selectedFiles = [];
    selectedFilesList.innerHTML = '';
    selectedFilesSection.style.display = 'none';
    previewSection.style.display = 'none';
    currentFileId = null;
    fileInput.value = '';
    
    showToast('모든 파일이 제거되었습니다.', 'info');
}

function handleUploadSuccess(data) {
    currentFileId = data.file_id;
    
    // 미리보기 이미지 설정
    previewImage.src = data.thumbnail_url;
    
    // 정보 텍스트 설정
    const photoTypeText = data.photo_type === 'construction' ? '시공사진' : '대문사진';
    const fileCountText = data.file_count ? `${data.file_count}장` : '1장';
    const orientationText = data.paper_orientation === 'landscape' ? '가로 (29.7cm × 21cm)' : '세로 (21cm × 29.7cm)';
    
    previewInfo.innerHTML = `
        <p><strong>처리된 파일:</strong> ${fileCountText}</p>
        <p><strong>사진 종류:</strong> ${photoTypeText}</p>
        <p><strong>용지 방향:</strong> ${orientationText}</p>
        <p><strong>A4 용지 배치:</strong> 최적 배치 완료</p>
        <p><strong>인쇄 품질:</strong> 300 DPI</p>
    `;
    
    // 미리보기 섹션 표시
    previewSection.style.display = 'block';
    
    // 성공 메시지
    if (data.file_count && data.file_count > 1) {
        showSuccess(`${data.file_count}장의 사진이 성공적으로 A4 용지에 배치되었습니다!`);
    } else {
        showSuccess('이미지가 성공적으로 처리되었습니다!');
    }
    
    // 스크롤
    previewSection.scrollIntoView({ behavior: 'smooth' });
}

function handleDownload() {
    if (!currentFileId) {
        showError('다운로드할 파일이 없습니다.');
        return;
    }

    // 다운로드 링크 생성
    const downloadUrl = `/download/${currentFileId}`;
    
    // 다운로드 시작
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `resized_photo_${currentFileId}.jpg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showSuccess('파일 다운로드가 시작되었습니다!');
}

function handlePrint() {
    if (!currentFileId) {
        showError('인쇄할 파일이 없습니다.');
        return;
    }

    // 인쇄 확인
    if (confirm('이미지를 인쇄하시겠습니까?\n\n인쇄 설정:\n- 용지 크기: A4\n- 여백: 없음\n- 크기 조정: 실제 크기')) {
        // 브라우저 인쇄 대화상자 열기
        window.print();
        showSuccess('인쇄 대화상자가 열렸습니다!');
    }
}

function handleReset() {
    // 상태 초기화
    currentFileId = null;
    selectedFiles = [];
    fileInput.value = '';
    
    // UI 초기화
    selectedFilesSection.style.display = 'none';
    selectedFilesList.innerHTML = '';
    previewSection.style.display = 'none';
    previewImage.src = '';
    previewInfo.textContent = '';
    
    // 업로드 영역 초기화
    uploadArea.classList.remove('drag-over');
    
    showSuccess('초기화되었습니다. 새로운 파일을 선택해주세요.');
}

function showProgress() {
    progressSection.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = '이미지를 처리하고 있습니다...';
    
    // 진행 바 애니메이션
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress >= 90) {
            progress = 90;
            clearInterval(interval);
        }
        progressFill.style.width = progress + '%';
    }, 200);
    
    // 전역 변수로 저장하여 나중에 정리할 수 있도록
    window.progressInterval = interval;
}

function hideProgress() {
    // 진행 바 완료
    progressFill.style.width = '100%';
    progressText.textContent = '처리 완료!';
    
    // 인터벌 정리
    if (window.progressInterval) {
        clearInterval(window.progressInterval);
        window.progressInterval = null;
    }
    
    // 잠시 후 숨기기
    setTimeout(() => {
        progressSection.style.display = 'none';
    }, 1000);
}

function showError(message) {
    // 간단한 알림 대신 더 나은 UI로 대체 가능
    alert('❌ ' + message);
    console.error('오류:', message);
}

function showSuccess(message) {
    // 간단한 알림 대신 더 나은 UI로 대체 가능
    console.log('성공:', message);
    
    // 토스트 메시지 생성
    showToast(message, 'success');
}

function showToast(message, type = 'info') {
    // 토스트 메시지 요소 생성
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // 스타일 적용
    Object.assign(toast.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '15px 20px',
        borderRadius: '8px',
        color: 'white',
        fontWeight: '500',
        zIndex: '9999',
        opacity: '0',
        transform: 'translateY(-20px)',
        transition: 'all 0.3s ease',
        maxWidth: '300px',
        wordWrap: 'break-word'
    });
    
    // 타입별 배경색
    if (type === 'success') {
        toast.style.background = '#28a745';
    } else if (type === 'error') {
        toast.style.background = '#dc3545';
    } else {
        toast.style.background = '#17a2b8';
    }
    
    // DOM에 추가
    document.body.appendChild(toast);
    
    // 애니메이션 시작
    setTimeout(() => {
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    }, 100);
    
    // 자동 제거
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// 페이지 언로드 시 정리
window.addEventListener('beforeunload', function() {
    if (window.progressInterval) {
        clearInterval(window.progressInterval);
    }
});

// 에러 핸들링
window.addEventListener('error', function(e) {
    console.error('JavaScript 오류:', e.error);
    showError('예상치 못한 오류가 발생했습니다.');
});

// 이미지 로드 에러 핸들링
document.addEventListener('error', function(e) {
    if (e.target.tagName === 'IMG') {
        console.error('이미지 로드 실패:', e.target.src);
        showError('이미지를 불러올 수 없습니다.');
    }
}, true); 