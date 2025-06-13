// DOM 요소들
const previewSection = document.getElementById('previewSection');
const previewImage = document.getElementById('previewImage');
const previewInfo = document.getElementById('previewInfo');
const downloadButton = document.getElementById('downloadButton');
const printButton = document.getElementById('printButton');
const resetButton = document.getElementById('resetButton');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');

// 혼합 배치용 DOM 요소들
const mixedUploadSection = document.getElementById('mixedUploadSection');
const constructionUploadArea = document.getElementById('constructionUploadArea');
const constructionFileInput = document.getElementById('constructionFileInput');
const constructionUploadButton = document.getElementById('constructionUploadButton');
const constructionFilesList = document.getElementById('constructionFilesList');
const documentUploadArea = document.getElementById('documentUploadArea');
const documentFileInput = document.getElementById('documentFileInput');
const documentUploadButton = document.getElementById('documentUploadButton');
const documentFilesList = document.getElementById('documentFilesList');
const processMixedButton = document.getElementById('processMixedButton');
const clearMixedButton = document.getElementById('clearMixedButton');

// 현재 파일 정보
let currentFileId = null;
let currentPaperOrientation = 'portrait';

// 혼합 배치용 파일 정보
let constructionFiles = [];
let documentFiles = [];

// 초기화
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    updatePaperOrientationSelection();
});

function initializeEventListeners() {
    // 용지 방향 선택
    const orientationButtons = document.querySelectorAll('input[name="paper_orientation"]');
    orientationButtons.forEach(radio => {
        radio.addEventListener('change', updatePaperOrientationSelection);
    });

    // 다운로드 버튼
    downloadButton.addEventListener('click', handleDownload);

    // 인쇄 버튼
    printButton.addEventListener('click', handlePrint);

    // 리셋 버튼
    resetButton.addEventListener('click', handleReset);

    // 혼합 배치용 이벤트 리스너
    initializeMixedLayoutEventListeners();
}

function initializeMixedLayoutEventListeners() {
    // 시공사진 업로드
    constructionUploadButton.addEventListener('click', () => {
        constructionFileInput.click();
    });

    constructionUploadArea.addEventListener('click', (e) => {
        if (e.target !== constructionUploadButton) {
            constructionFileInput.click();
        }
    });

    constructionFileInput.addEventListener('change', (e) => {
        handleMixedFileSelect(e, 'construction');
    });

    // 대문사진 업로드
    documentUploadButton.addEventListener('click', () => {
        documentFileInput.click();
    });

    documentUploadArea.addEventListener('click', (e) => {
        if (e.target !== documentUploadButton) {
            documentFileInput.click();
        }
    });

    documentFileInput.addEventListener('change', (e) => {
        handleMixedFileSelect(e, 'document');
    });

    // 드래그 앤 드롭 - 시공사진
    constructionUploadArea.addEventListener('dragover', (e) => handleMixedDragOver(e, 'construction'));
    constructionUploadArea.addEventListener('dragleave', (e) => handleMixedDragLeave(e, 'construction'));
    constructionUploadArea.addEventListener('drop', (e) => handleMixedDrop(e, 'construction'));

    // 드래그 앤 드롭 - 대문사진
    documentUploadArea.addEventListener('dragover', (e) => handleMixedDragOver(e, 'document'));
    documentUploadArea.addEventListener('dragleave', (e) => handleMixedDragLeave(e, 'document'));
    documentUploadArea.addEventListener('drop', (e) => handleMixedDrop(e, 'document'));

    // 혼합 배치 처리 버튼
    processMixedButton.addEventListener('click', handleMixedProcess);

    // 혼합 배치 지우기 버튼
    clearMixedButton.addEventListener('click', handleMixedClear);
}

function updatePaperOrientationSelection() {
    const selectedRadio = document.querySelector('input[name="paper_orientation"]:checked');
    currentPaperOrientation = selectedRadio.value;
    console.log('용지 방향 선택됨:', currentPaperOrientation);
}

function validateFile(file) {
    // 파일 크기 체크 (16MB)
    if (file.size > 16 * 1024 * 1024) {
        showError(`파일 "${file.name}"이 너무 큽니다. 최대 16MB까지 지원됩니다.`);
        return false;
    }

    // 파일 형식 체크
    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 'image/gif', 'image/tiff'];
    if (!allowedTypes.includes(file.type)) {
        showError(`파일 "${file.name}"은 지원되지 않는 형식입니다. JPG, PNG, BMP, GIF, TIFF 파일만 지원됩니다.`);
        return false;
    }

    return true;
}

function handleDownload() {
    if (currentFileId) {
        const link = document.createElement('a');
        link.href = `/download/${currentFileId}`;
        link.download = `${currentFileId}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showSuccess('다운로드가 시작되었습니다.');
    }
}

function handlePrint() {
    if (previewImage.src) {
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>사진 인쇄</title>
                    <style>
                        @page { margin: 0; }
                        body { margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
                        img { max-width: 100%; max-height: 100vh; object-fit: contain; }
                    </style>
                </head>
                <body>
                    <img src="${previewImage.src}" onload="window.print(); window.close();">
                </body>
            </html>
        `);
        printWindow.document.close();
    }
}

function handleReset() {
    // 혼합 배치 초기화
    constructionFiles = [];
    documentFiles = [];
    updateMixedFilesDisplay();
    
    // UI 초기화
    previewSection.style.display = 'none';
    currentFileId = null;
    
    showSuccess('모든 내용이 초기화되었습니다.');
}

function showProgress() {
    progressSection.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = '이미지를 처리하고 있습니다...';
    
    // 진행 상황 애니메이션
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        progressFill.style.width = progress + '%';
        
        if (progress >= 90) {
            clearInterval(interval);
        }
    }, 200);
}

function hideProgress() {
    setTimeout(() => {
        progressFill.style.width = '100%';
        setTimeout(() => {
            progressSection.style.display = 'none';
        }, 500);
    }, 100);
}

function showError(message) {
    showToast(message, 'error');
}

function showSuccess(message) {
    showToast(message, 'success');
}

function showToast(message, type = 'info') {
    // 기존 토스트 제거
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon">
                ${type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️'}
            </span>
            <span class="toast-message">${message}</span>
        </div>
    `;

    // 스타일 적용
    Object.assign(toast.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '15px 20px',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        zIndex: '10000',
        maxWidth: '400px',
        color: 'white',
        fontWeight: '500',
        transform: 'translateX(100%)',
        transition: 'transform 0.3s ease-in-out',
        backgroundColor: type === 'error' ? '#e74c3c' : type === 'success' ? '#27ae60' : '#3498db'
    });

    document.body.appendChild(toast);

    // 슬라이드 인 애니메이션
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 100);

    // 자동 제거
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 5000);
}

function handleMixedFileSelect(event, type) {
    const files = Array.from(event.target.files);
    if (files.length > 0) {
        addMixedFilesToSelection(files, type);
    }
}

function handleMixedDragOver(event, type) {
    event.preventDefault();
    const uploadArea = type === 'construction' ? constructionUploadArea : documentUploadArea;
    uploadArea.classList.add('drag-over');
}

function handleMixedDragLeave(event, type) {
    event.preventDefault();
    const uploadArea = type === 'construction' ? constructionUploadArea : documentUploadArea;
    uploadArea.classList.remove('drag-over');
}

function handleMixedDrop(event, type) {
    event.preventDefault();
    const uploadArea = type === 'construction' ? constructionUploadArea : documentUploadArea;
    uploadArea.classList.remove('drag-over');
    
    const files = Array.from(event.dataTransfer.files);
    if (files.length > 0) {
        addMixedFilesToSelection(files, type);
    }
}

function addMixedFilesToSelection(files, type) {
    const validFiles = files.filter(validateFile);
    
    if (validFiles.length === 0) return;

    if (type === 'construction') {
        constructionFiles = [...constructionFiles, ...validFiles];
    } else {
        documentFiles = [...documentFiles, ...validFiles];
    }

    updateMixedFilesDisplay();
    showSuccess(`${validFiles.length}개의 ${type === 'construction' ? '시공사진' : '대문사진'}이 추가되었습니다.`);
}

function updateMixedFilesDisplay() {
    updateFilesList(constructionFiles, constructionFilesList, 'construction');
    updateFilesList(documentFiles, documentFilesList, 'document');
    
    // 처리 버튼 표시 여부 결정
    const hasFiles = constructionFiles.length > 0 || documentFiles.length > 0;
    processMixedButton.style.display = hasFiles ? 'inline-block' : 'none';
}

function updateFilesList(files, container, type) {
    container.innerHTML = '';
    
    files.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-preview">
                <img src="${URL.createObjectURL(file)}" alt="${file.name}" class="file-thumbnail">
            </div>
            <div class="file-info">
                <div class="file-name">${file.name}</div>
                <div class="file-size">${(file.size / (1024 * 1024)).toFixed(2)} MB</div>
            </div>
            <button class="file-remove" onclick="removeMixedFile(${index}, '${type}')">×</button>
        `;
        container.appendChild(fileItem);
    });
}

function removeMixedFile(index, type) {
    if (type === 'construction') {
        constructionFiles.splice(index, 1);
    } else {
        documentFiles.splice(index, 1);
    }
    updateMixedFilesDisplay();
}

function handleMixedProcess() {
    if (constructionFiles.length === 0 && documentFiles.length === 0) {
        showError('최소 하나의 사진을 선택해주세요.');
        return;
    }

    showProgress();

    const formData = new FormData();
    
    // 시공사진 추가
    constructionFiles.forEach((file, index) => {
        formData.append('construction_files', file);
    });
    
    // 대문사진 추가
    documentFiles.forEach((file, index) => {
        formData.append('document_files', file);
    });
    
    // 용지 방향 추가
    formData.append('paper_orientation', currentPaperOrientation);

    fetch('/upload_optimized', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        hideProgress();
        if (data.success) {
            handleMixedUploadSuccess(data);
        } else {
            showError(data.message || '파일 업로드 중 오류가 발생했습니다.');
        }
    })
    .catch(error => {
        hideProgress();
        console.error('Error:', error);
        showError('서버와의 통신 중 오류가 발생했습니다.');
    });
}

function handleMixedUploadSuccess(data) {
    currentFileId = data.file_id;
    
    // 미리보기 이미지 설정
    previewImage.src = `/static/outputs/${data.filename}`;
    previewImage.onload = function() {
        previewSection.style.display = 'block';
        previewSection.scrollIntoView({ behavior: 'smooth' });
    };
    
    // 배치 정보 표시
    const constructionCount = constructionFiles.length;
    const documentCount = documentFiles.length;
    const orientation = currentPaperOrientation === 'portrait' ? '세로' : '가로';
    
    previewInfo.innerHTML = `
        <strong>📄 A4 ${orientation} 배치 완료!</strong><br>
        시공사진: ${constructionCount}장, 대문사진: ${documentCount}장<br>
        <small>용지 크기: ${currentPaperOrientation === 'portrait' ? '21cm × 29.7cm' : '29.7cm × 21cm'}</small>
    `;
    
    showSuccess('A4 배치가 완료되었습니다!');
}

function handleMixedClear() {
    constructionFiles = [];
    documentFiles = [];
    updateMixedFilesDisplay();
    
    // 파일 input 초기화
    constructionFileInput.value = '';
    documentFileInput.value = '';
    
    previewSection.style.display = 'none';
    currentFileId = null;
    
    showSuccess('모든 파일이 제거되었습니다.');
} 