// DOM 요소들
const previewSection = document.getElementById('previewSection');
const previewImage = document.getElementById('previewImage');
const printButton = document.getElementById('printButton');
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

// 전역 변수들
let selectedFiles = [];
let constructionFiles = [];
let documentFiles = [];
let currentPaperOrientation = 'portrait';
let currentFileId = null;
let currentLayoutData = null; // 다중 페이지 데이터
let currentPageIndex = 0; // 현재 페이지 번호 (0부터 시작)

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

    // 혼합 배치용 이벤트 리스너
    initializeMixedLayoutEventListeners();
}

function initializeMixedLayoutEventListeners() {
    // 요소 존재 확인
    if (!constructionUploadButton || !constructionFileInput) {
        console.error('시공사진 업로드 요소를 찾을 수 없습니다.');
        return;
    }
    
    if (!documentUploadButton || !documentFileInput) {
        console.error('대문사진 업로드 요소를 찾을 수 없습니다.');
        return;
    }

    // 시공사진 업로드
    constructionUploadButton.addEventListener('click', () => {
        console.log('시공사진 버튼 클릭됨');
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
    // 파일 크기 체크 (50MB - 압축 전 원본 기준)
    if (file.size > 50 * 1024 * 1024) {
        showError(`파일 "${file.name}"이 너무 큽니다. 최대 50MB까지 지원됩니다.`);
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

// 이미지 압축 함수
function compressImage(file, maxWidth = 2000, maxHeight = 2000, quality = 0.8) {
    return new Promise((resolve, reject) => {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        img.onload = function() {
            // 원본 크기
            let { width, height } = img;
            
            // 비율 유지하면서 최대 크기 제한
            if (width > maxWidth || height > maxHeight) {
                const ratio = Math.min(maxWidth / width, maxHeight / height);
                width *= ratio;
                height *= ratio;
            }
            
            // 캔버스 크기 설정
            canvas.width = width;
            canvas.height = height;
            
            // 이미지 그리기
            ctx.drawImage(img, 0, 0, width, height);
            
            // JPEG로 압축하여 Blob 생성
            canvas.toBlob((blob) => {
                if (blob) {
                    // 원본 파일명 유지하면서 새 파일 객체 생성
                    const compressedFile = new File([blob], file.name, {
                        type: 'image/jpeg',
                        lastModified: Date.now()
                    });
                    
                    const compressionRatio = ((file.size - compressedFile.size) / file.size * 100).toFixed(1);
                    console.log(`이미지 압축 완료: ${file.name}`);
                    console.log(`원본: ${(file.size / 1024 / 1024).toFixed(2)}MB → 압축: ${(compressedFile.size / 1024 / 1024).toFixed(2)}MB (${compressionRatio}% 절약)`);
                    
                    resolve(compressedFile);
                } else {
                    reject(new Error('이미지 압축 실패'));
                }
            }, 'image/jpeg', quality);
        };
        
        img.onerror = () => reject(new Error('이미지 로드 실패'));
        img.src = URL.createObjectURL(file);
    });
}



function handlePrint() {
    if (!currentLayoutData || !currentLayoutData.page_filenames) {
        showError('인쇄할 레이아웃이 없습니다.');
        return;
    }

    // 인쇄 확인 대화상자
    const totalPages = currentLayoutData.total_pages;
    const constructionCount = currentLayoutData.construction_count;
    const documentCount = currentLayoutData.document_count;
    const totalPhotos = constructionCount + documentCount;
    const orientation = currentPaperOrientation === 'portrait' ? '세로' : '가로';
    
    const confirmMessage = `
🖨️ 다중 페이지 인쇄 확인

📄 용지: A4 ${orientation}
📋 페이지: 총 ${totalPages}페이지
📷 사진: 총 ${totalPhotos}장 (시공사진: ${constructionCount}장, 대문사진: ${documentCount}장)
🎯 품질: 300 DPI 고품질

${totalPages}페이지를 모두 인쇄하시겠습니까?

📌 인쇄 팁:
• 용지 크기를 A4로 설정하세요
• 여백을 "없음" 또는 "최소"로 설정하세요
• 크기 조정을 "실제 크기" 또는 "100%"로 설정하세요
• 양면 인쇄를 원하시면 프린터 설정에서 조정하세요
    `;

    if (!confirm(confirmMessage)) {
        return;
    }

    showProgress();
    
    // 모든 페이지를 포함한 HTML 생성
    let pagesHtml = '';
    currentLayoutData.page_filenames.forEach((filename, index) => {
        const pageBreak = index > 0 ? 'page-break-before: always;' : '';
        pagesHtml += `
            <div class="print-page" style="${pageBreak}">
                <img src="/static/outputs/${filename}" class="print-image" alt="페이지 ${index + 1}" onload="checkImageLoad()">
                <div class="print-info">페이지 ${index + 1}/${totalPages} | 생성일: ${new Date().toLocaleDateString('ko-KR')}</div>
            </div>
        `;
    });
    
    // 새 창에서 인쇄용 페이지 생성
    const printWindow = window.open('', '_blank', 'width=800,height=600');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="UTF-8">
                <title>사진 인쇄 - ${totalPages}페이지 A4 ${orientation}</title>
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
                        font-family: Arial, sans-serif;
                    }
                    
                    .print-page {
                        width: 100%;
                        height: 100vh;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                        padding: 10px;
                        position: relative;
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
                        
                        .print-page {
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
                            padding: 20px;
                        }
                        
                        .print-page {
                            background: white;
                            max-width: 210mm;
                            max-height: 297mm;
                            margin: 0 auto 20px auto;
                            box-shadow: 0 0 20px rgba(0,0,0,0.1);
                        }
                    }
                </style>
            </head>
            <body>
                ${pagesHtml}
                
                <script>
                    let loadedImages = 0;
                    const totalImages = ${totalPages};
                    
                    function checkImageLoad() {
                        loadedImages++;
                        if (loadedImages >= totalImages) {
                            // 모든 이미지 로드 완료 후 인쇄
                            setTimeout(function() {
                                window.print();
                            }, 1000);
                        }
                    }
                    
                    // 대비책: 5초 후 강제 인쇄
                    setTimeout(function() {
                        if (loadedImages < totalImages) {
                            window.print();
                        }
                    }, 5000);
                    
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
        showSuccess(`${totalPages}페이지 인쇄 창이 열렸습니다. 프린터 설정을 확인하고 인쇄하세요.`);
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

async function addMixedFilesToSelection(files, type) {
    const validFiles = files.filter(validateFile);
    
    if (validFiles.length === 0) return;

    // 압축 진행 표시
    showProgress();
    const progressText = document.getElementById('progressText');
    
    try {
        const compressedFiles = [];
        
        for (let i = 0; i < validFiles.length; i++) {
            const file = validFiles[i];
            progressText.textContent = `이미지 압축 중... (${i + 1}/${validFiles.length})`;
            
            try {
                // 이미지 압축 적용
                const compressedFile = await compressImage(file, 2000, 2000, 0.8);
                compressedFiles.push(compressedFile);
            } catch (error) {
                console.warn(`${file.name} 압축 실패, 원본 사용:`, error);
                // 압축 실패시 원본 파일 사용
                compressedFiles.push(file);
            }
        }
        
        // 압축된 파일들을 배열에 추가
        if (type === 'construction') {
            constructionFiles = [...constructionFiles, ...compressedFiles];
        } else {
            documentFiles = [...documentFiles, ...compressedFiles];
        }

        updateMixedFilesDisplay();
        
        // 압축 결과 메시지
        const originalSize = validFiles.reduce((sum, file) => sum + file.size, 0);
        const compressedSize = compressedFiles.reduce((sum, file) => sum + file.size, 0);
        const savedPercent = ((originalSize - compressedSize) / originalSize * 100).toFixed(1);
        
        showSuccess(
            `${validFiles.length}개의 ${type === 'construction' ? '시공사진' : '대문사진'}이 추가되었습니다.\n` +
            `압축률: ${savedPercent}% 절약 (${(originalSize / 1024 / 1024).toFixed(1)}MB → ${(compressedSize / 1024 / 1024).toFixed(1)}MB)`
        );
        
    } catch (error) {
        console.error('파일 처리 중 오류:', error);
        showError('파일 처리 중 오류가 발생했습니다.');
    } finally {
        hideProgress();
    }
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
    currentLayoutData = data;
    currentPageIndex = 0; // 첫 번째 페이지부터 시작
    
    // 첫 번째 페이지 이미지 설정
    updatePageDisplay();
    
    // 배치 정보 표시
    const constructionCount = data.construction_count || 0;  // 실제 배치된 개수
    const documentCount = data.document_count || 0;  // 실제 배치된 개수
    const uploadedConstruction = data.uploaded_construction || constructionFiles.length;  // 업로드한 개수
    const uploadedDocument = data.uploaded_document || documentFiles.length;  // 업로드한 개수
    
    const totalPhotos = constructionCount + documentCount;  // 실제 배치된 총 개수
    const totalUploaded = uploadedConstruction + uploadedDocument;  // 업로드한 총 개수
    const totalPages = data.total_pages || 1; // 총 페이지 수
    
    const orientation = currentPaperOrientation === 'portrait' ? '세로' : '가로';
    const paperSize = currentPaperOrientation === 'portrait' ? '21cm × 29.7cm' : '29.7cm × 21cm';
    
    // 효율성 계산 (페이지당 평균)
    const avgPhotosPerPage = totalPhotos / totalPages;
    const maxPerPage = currentPaperOrientation === 'portrait' ? 6 : 7; // 대략적인 페이지당 최대 가능 수
    const efficiency = Math.round((avgPhotosPerPage / maxPerPage) * 100);
    
    // 배치 성공률 계산
    const placementRate = totalUploaded > 0 ? Math.round((totalPhotos / totalUploaded) * 100) : 100;
    
    // 통계 카드 업데이트
    document.getElementById('totalPhotosValue').textContent = totalPhotos;
    document.getElementById('constructionCountValue').textContent = constructionCount;
    document.getElementById('documentCountValue').textContent = documentCount;
    document.getElementById('efficiencyValue').textContent = `${efficiency}%`;
    
    // 상세 정보 테이블 업데이트
    document.getElementById('paperSizeValue').textContent = paperSize;
    document.getElementById('orientationValue').textContent = orientation;
    document.getElementById('pagesValue').textContent = `${totalPages}페이지`;
    document.getElementById('qualityValue').textContent = '300 DPI (고품질)';
    document.getElementById('layoutFilename').textContent = data.layout_id || 'mixed_layout';
    
    // 경고 메시지 표시 (모든 사진이 배치되지 않은 경우)
    const warningElement = document.getElementById('placementWarning');
    if (totalPhotos < totalUploaded) {
        const notPlaced = totalUploaded - totalPhotos;
        warningElement.innerHTML = `
            <strong>⚠️ 주의:</strong> 업로드한 ${totalUploaded}장 중 ${totalPhotos}장만 배치되었습니다. 
            ${notPlaced}장은 페이지 공간 부족으로 배치되지 않았습니다.
            <br>더 많은 사진을 배치하려면 추가 페이지가 자동으로 생성됩니다.
        `;
        warningElement.style.display = 'block';
    } else {
        warningElement.innerHTML = `
            <strong>✅ 완료:</strong> 업로드한 모든 ${totalUploaded}장의 사진이 ${totalPages}페이지에 성공적으로 배치되었습니다.
        `;
        warningElement.style.display = 'block';
        warningElement.className = 'warning-message success';
    }
    
    // 프린트 버튼 텍스트 업데이트
    const printButton = document.getElementById('printButton');
    if (totalPages > 1) {
        printButton.textContent = `🖨️ ${totalPages}페이지 모두 인쇄`;
    } else {
        printButton.textContent = `🖨️ 인쇄하기`;
    }
    
    // 미리보기 섹션 표시
    previewSection.style.display = 'block';
    previewSection.scrollIntoView({ behavior: 'smooth' });
}

// 페이지 표시 업데이트 함수
function updatePageDisplay() {
    if (!currentLayoutData || !currentLayoutData.page_filenames) return;
    
    const totalPages = currentLayoutData.total_pages;
    const currentFilename = currentLayoutData.page_filenames[currentPageIndex];
    
    // 이미지 업데이트
    previewImage.src = `/static/outputs/${currentFilename}`;
    
    // 페이지 정보 업데이트
    document.getElementById('currentPageNumber').textContent = currentPageIndex + 1;
    document.getElementById('totalPagesNumber').textContent = totalPages;
    
    // 네비게이션 버튼 상태 업데이트
    document.getElementById('prevPageBtn').disabled = currentPageIndex === 0;
    document.getElementById('nextPageBtn').disabled = currentPageIndex === totalPages - 1;
    
    // 페이지 네비게이션 표시
    const pageNavigation = document.getElementById('pageNavigation');
    if (totalPages > 1) {
        pageNavigation.style.display = 'flex';
    } else {
        pageNavigation.style.display = 'none';
    }
}

// 이전 페이지로 이동
function goToPreviousPage() {
    if (currentPageIndex > 0) {
        currentPageIndex--;
        updatePageDisplay();
    }
}

// 다음 페이지로 이동
function goToNextPage() {
    if (currentLayoutData && currentPageIndex < currentLayoutData.total_pages - 1) {
        currentPageIndex++;
        updatePageDisplay();
    }
}

// 특정 페이지로 이동
function goToPage(pageNumber) {
    if (currentLayoutData && pageNumber >= 1 && pageNumber <= currentLayoutData.total_pages) {
        currentPageIndex = pageNumber - 1;
        updatePageDisplay();
    }
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