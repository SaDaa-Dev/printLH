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
    if (!previewImage.src) {
        showError('인쇄할 이미지가 없습니다.');
        return;
    }

    // 인쇄 확인 대화상자
    const constructionCount = constructionFiles.length;
    const documentCount = documentFiles.length;
    const totalPhotos = constructionCount + documentCount;
    const orientation = currentPaperOrientation === 'portrait' ? '세로' : '가로';
    
    const confirmMessage = `
🖨️ 인쇄 설정 확인

📄 용지: A4 ${orientation}
📷 사진: 총 ${totalPhotos}장 (시공사진: ${constructionCount}장, 대문사진: ${documentCount}장)
🎯 품질: 300 DPI 고품질

인쇄하시겠습니까?

📌 인쇄 팁:
• 용지 크기를 A4로 설정하세요
• 여백을 "없음" 또는 "최소"로 설정하세요
• 크기 조정을 "실제 크기" 또는 "100%"로 설정하세요
    `;

    if (!confirm(confirmMessage)) {
        return;
    }

    showProgress();
    
    // 새 창에서 인쇄용 페이지 생성
    const printWindow = window.open('', '_blank', 'width=800,height=600');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
                <title>사진 인쇄 - A4 ${orientation}</title>
                <style>
                    @page {
                        size: A4 ${currentPaperOrientation};
                        margin: 0;
                    }
                    
                    * {
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }
                    
                    body {
                        margin: 0;
                        padding: 0;
                        background: white;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        min-height: 100vh;
                        font-family: Arial, sans-serif;
                    }
                    
                    .print-container {
                        width: 100%;
                        height: 100vh;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        padding: 10px;
                    }
                    
                    .print-image {
                        max-width: 100%;
                        max-height: 95vh;
                        object-fit: contain;
                        box-shadow: none;
                        border: none;
                    }
                    
                    .print-info {
                        position: absolute;
                        bottom: 5px;
                        right: 10px;
                        font-size: 8px;
                        color: #999;
                        font-family: Arial, sans-serif;
                    }
                    
                    @media print {
                        .print-info {
                            display: none;
                        }
                        
                        .print-container {
                            width: 100%;
                            height: 100vh;
                            padding: 0;
                        }
                        
                        .print-image {
                            max-width: 100%;
                            max-height: 100vh;
                            object-fit: contain;
                        }
                    }
                    
                    @media screen {
                        body {
                            background: #f0f0f0;
                        }
                        
                        .print-container {
                            background: white;
                            max-width: 210mm;
                            max-height: 297mm;
                            margin: 20px auto;
                            box-shadow: 0 0 20px rgba(0,0,0,0.1);
                        }
                    }
                </style>
            </head>
            <body>
                <div class="print-container">
                    <img src="${previewImage.src}" class="print-image" alt="A4 사진 배치">
                    <div class="print-info">생성일: ${new Date().toLocaleDateString('ko-KR')} | ${totalPhotos}장 배치</div>
                </div>
                
                <script>
                    window.onload = function() {
                        // 이미지 로드 후 3초 대기 후 인쇄 대화상자 열기
                        setTimeout(function() {
                            window.print();
                        }, 1000);
                    };
                    
                    // 인쇄 완료 후 창 닫기
                    window.onafterprint = function() {
                        setTimeout(function() {
                            window.close();
                        }, 1000);
                    };
                </script>
            </body>
        </html>
    `);
    
    printWindow.document.close();
    
    // 인쇄 창이 열린 후 진행바 숨기기
    setTimeout(() => {
        hideProgress();
        showSuccess('인쇄 창이 열렸습니다. 프린터 설정을 확인하고 인쇄하세요.');
    }, 1000);
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
    const constructionCount = data.construction_count || constructionFiles.length;
    const documentCount = data.document_count || documentFiles.length;
    const totalPhotos = constructionCount + documentCount;
    const orientation = currentPaperOrientation === 'portrait' ? '세로' : '가로';
    const paperSize = currentPaperOrientation === 'portrait' ? '21cm × 29.7cm' : '29.7cm × 21cm';
    
    // 효율성 계산
    const maxPossible = currentPaperOrientation === 'portrait' ? 8 : 10; // 대략적인 최대 가능 수
    const efficiency = Math.round((totalPhotos / maxPossible) * 100);
    
    previewInfo.innerHTML = `
        <div class="layout-summary">
            <h3>📄 A4 ${orientation} 배치 완료!</h3>
            
            <div class="layout-stats">
                <div class="stat-item">
                    <span class="stat-icon">📷</span>
                    <div class="stat-content">
                        <div class="stat-number">${totalPhotos}</div>
                        <div class="stat-label">총 사진</div>
                    </div>
                </div>
                
                <div class="stat-item">
                    <span class="stat-icon">🏗️</span>
                    <div class="stat-content">
                        <div class="stat-number">${constructionCount}</div>
                        <div class="stat-label">시공사진</div>
                    </div>
                </div>
                
                <div class="stat-item">
                    <span class="stat-icon">📄</span>
                    <div class="stat-content">
                        <div class="stat-number">${documentCount}</div>
                        <div class="stat-label">대문사진</div>
                    </div>
                </div>
                
                <div class="stat-item">
                    <span class="stat-icon">⚡</span>
                    <div class="stat-content">
                        <div class="stat-number">${efficiency}%</div>
                        <div class="stat-label">공간 효율성</div>
                    </div>
                </div>
            </div>
            
            <div class="layout-details">
                <div class="detail-row">
                    <span class="detail-label">📏 용지 크기:</span>
                    <span class="detail-value">${paperSize}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">🖨️ 인쇄 품질:</span>
                    <span class="detail-value">300 DPI (고품질)</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">📐 방향:</span>
                    <span class="detail-value">${orientation} (${currentPaperOrientation})</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">📁 파일명:</span>
                    <span class="detail-value">${data.filename}</span>
                </div>
            </div>
        </div>
    `;
    
    showSuccess(`🎉 ${totalPhotos}장의 사진이 성공적으로 A4 용지에 배치되었습니다!`);
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