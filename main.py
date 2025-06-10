import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import os
import subprocess
import tempfile
import shutil

class PhotoResizerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("사진 리사이징 및 프린트 프로그램")
        self.root.geometry("600x500")
        self.root.configure(bg='#f0f0f0')
        
        # A4 용지 크기 (300 DPI 기준)
        self.A4_WIDTH = 2480  # 픽셀
        self.A4_HEIGHT = 3508  # 픽셀
        
        # 선택된 이미지 경로
        self.selected_image_path = None
        self.resized_image_path = None
        
        self.create_widgets()
        
    def create_widgets(self):
        # 제목
        title_label = tk.Label(self.root, text="사진 리사이징 및 프린트 프로그램", 
                              font=('Arial', 16, 'bold'), bg='#f0f0f0', fg='#333')
        title_label.pack(pady=10)
        
        # 메인 프레임
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(padx=20, pady=10, fill=tk.BOTH, expand=True)
        
        # 사진 종류 선택 프레임
        photo_type_frame = tk.LabelFrame(main_frame, text="사진 종류 선택", 
                                        font=('Arial', 12, 'bold'), bg='#f0f0f0')
        photo_type_frame.pack(fill=tk.X, pady=5)
        
        self.photo_type_var = tk.StringVar(value="일반사진")
        
        tk.Radiobutton(photo_type_frame, text="일반사진 (풍경, 인물 등)", 
                      variable=self.photo_type_var, value="일반사진",
                      font=('Arial', 10), bg='#f0f0f0').pack(anchor=tk.W, padx=10, pady=5)
        
        tk.Radiobutton(photo_type_frame, text="증명사진 (여권, 신분증 등)", 
                      variable=self.photo_type_var, value="증명사진",
                      font=('Arial', 10), bg='#f0f0f0').pack(anchor=tk.W, padx=10, pady=5)
        
        # 파일 선택 프레임
        file_frame = tk.LabelFrame(main_frame, text="파일 선택", 
                                  font=('Arial', 12, 'bold'), bg='#f0f0f0')
        file_frame.pack(fill=tk.X, pady=5)
        
        self.file_path_var = tk.StringVar(value="파일이 선택되지 않았습니다")
        file_path_label = tk.Label(file_frame, textvariable=self.file_path_var, 
                                  font=('Arial', 10), bg='#f0f0f0', fg='#666')
        file_path_label.pack(anchor=tk.W, padx=10, pady=5)
        
        select_button = tk.Button(file_frame, text="사진 파일 선택", 
                                 command=self.select_file, 
                                 font=('Arial', 10), bg='#4CAF50', fg='white',
                                 activebackground='#45a049', cursor='hand2')
        select_button.pack(pady=5)
        
        # 미리보기 프레임
        preview_frame = tk.LabelFrame(main_frame, text="미리보기", 
                                     font=('Arial', 12, 'bold'), bg='#f0f0f0')
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_label = tk.Label(preview_frame, text="미리보기 이미지가 여기에 표시됩니다", 
                                     bg='white', relief=tk.SUNKEN, bd=1)
        self.preview_label.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 버튼 프레임
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=10)
        
        resize_button = tk.Button(button_frame, text="사진 리사이징", 
                                 command=self.resize_image, 
                                 font=('Arial', 11, 'bold'), bg='#2196F3', fg='white',
                                 activebackground='#1976D2', cursor='hand2')
        resize_button.pack(side=tk.LEFT, padx=5)
        
        print_button = tk.Button(button_frame, text="프린트", 
                                command=self.print_image, 
                                font=('Arial', 11, 'bold'), bg='#FF9800', fg='white',
                                activebackground='#F57C00', cursor='hand2')
        print_button.pack(side=tk.LEFT, padx=5)
        
        # 상태 표시줄
        self.status_var = tk.StringVar(value="준비")
        status_label = tk.Label(self.root, textvariable=self.status_var, 
                               font=('Arial', 10), bg='#e0e0e0', fg='#333', relief=tk.SUNKEN)
        status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
    def select_file(self):
        """파일 선택 다이얼로그"""
        file_path = filedialog.askopenfilename(
            title="사진 파일 선택",
            filetypes=[
                ("이미지 파일", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
                ("모든 파일", "*.*")
            ]
        )
        
        if file_path:
            self.selected_image_path = file_path
            self.file_path_var.set(os.path.basename(file_path))
            self.update_status("파일이 선택되었습니다")
            self.show_preview()
        
    def show_preview(self):
        """선택된 이미지의 미리보기 표시"""
        if self.selected_image_path:
            try:
                # 이미지 열기
                image = Image.open(self.selected_image_path)
                
                # 미리보기 크기 계산 (최대 300x300)
                image.thumbnail((300, 300), Image.Resampling.LANCZOS)
                
                # Tkinter용 이미지 변환
                photo = ImageTk.PhotoImage(image)
                
                # 미리보기 업데이트
                self.preview_label.configure(image=photo, text="")
                self.preview_label.image = photo  # 참조 유지
                
            except Exception as e:
                messagebox.showerror("오류", f"이미지를 불러올 수 없습니다: {str(e)}")
                
    def resize_image(self):
        """선택된 사진 종류에 따라 이미지 리사이징"""
        if not self.selected_image_path:
            messagebox.showwarning("경고", "먼저 사진 파일을 선택해주세요")
            return
            
        try:
            self.update_status("이미지 리사이징 중...")
            
            # 이미지 열기
            image = Image.open(self.selected_image_path)
            
            # 사진 종류에 따른 리사이징
            photo_type = self.photo_type_var.get()
            
            if photo_type == "일반사진":
                # 일반사진: A4 용지에 맞게 비율 유지하면서 최대 크기로 리사이징
                resized_image = self.resize_for_general_photo(image)
                
            elif photo_type == "증명사진":
                # 증명사진: 여러 장을 배치할 수 있도록 작은 크기로 리사이징
                resized_image = self.resize_for_id_photo(image)
                
            # 리사이징된 이미지 저장
            temp_dir = tempfile.gettempdir()
            filename = f"resized_{os.path.basename(self.selected_image_path)}"
            self.resized_image_path = os.path.join(temp_dir, filename)
            
            resized_image.save(self.resized_image_path, quality=95)
            
            self.update_status("이미지 리사이징 완료")
            messagebox.showinfo("완료", "이미지 리사이징이 완료되었습니다!")
            
        except Exception as e:
            messagebox.showerror("오류", f"이미지 리사이징 중 오류가 발생했습니다: {str(e)}")
            self.update_status("리사이징 실패")
            
    def resize_for_general_photo(self, image):
        """일반사진 리사이징 (A4 용지 전체 활용)"""
        # 원본 이미지 크기
        original_width, original_height = image.size
        
        # A4 비율에 맞게 조정
        a4_ratio = self.A4_WIDTH / self.A4_HEIGHT
        image_ratio = original_width / original_height
        
        if image_ratio > a4_ratio:
            # 이미지가 A4보다 가로가 긴 경우
            new_width = self.A4_WIDTH
            new_height = int(self.A4_WIDTH / image_ratio)
        else:
            # 이미지가 A4보다 세로가 긴 경우
            new_height = self.A4_HEIGHT
            new_width = int(self.A4_HEIGHT * image_ratio)
        
        # 리사이징
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # A4 크기의 흰색 배경에 중앙 배치
        a4_image = Image.new('RGB', (self.A4_WIDTH, self.A4_HEIGHT), 'white')
        x_offset = (self.A4_WIDTH - new_width) // 2
        y_offset = (self.A4_HEIGHT - new_height) // 2
        a4_image.paste(resized_image, (x_offset, y_offset))
        
        return a4_image
        
    def resize_for_id_photo(self, image):
        """증명사진 리사이징 (여러 장 배치)"""
        # 증명사진 크기 (35mm x 45mm, 300 DPI 기준)
        id_width = int(35 * 300 / 25.4)  # 약 413픽셀
        id_height = int(45 * 300 / 25.4)  # 약 531픽셀
        
        # 원본 이미지를 증명사진 비율에 맞게 크롭
        original_width, original_height = image.size
        id_ratio = id_width / id_height
        original_ratio = original_width / original_height
        
        if original_ratio > id_ratio:
            # 원본이 더 가로가 긴 경우 - 세로를 기준으로 크롭
            new_height = original_height
            new_width = int(original_height * id_ratio)
            left = (original_width - new_width) // 2
            top = 0
            right = left + new_width
            bottom = original_height
        else:
            # 원본이 더 세로가 긴 경우 - 가로를 기준으로 크롭
            new_width = original_width
            new_height = int(original_width / id_ratio)
            left = 0
            top = (original_height - new_height) // 2
            right = original_width
            bottom = top + new_height
        
        # 크롭 및 리사이징
        cropped_image = image.crop((left, top, right, bottom))
        id_photo = cropped_image.resize((id_width, id_height), Image.Resampling.LANCZOS)
        
        # A4 용지에 여러 장 배치 (2x3 = 6장)
        a4_image = Image.new('RGB', (self.A4_WIDTH, self.A4_HEIGHT), 'white')
        
        # 배치 계산
        cols = 2
        rows = 3
        margin = 50
        
        x_spacing = (self.A4_WIDTH - 2 * margin - cols * id_width) // (cols - 1)
        y_spacing = (self.A4_HEIGHT - 2 * margin - rows * id_height) // (rows - 1)
        
        for row in range(rows):
            for col in range(cols):
                x = margin + col * (id_width + x_spacing)
                y = margin + row * (id_height + y_spacing)
                a4_image.paste(id_photo, (x, y))
        
        return a4_image
        
    def print_image(self):
        """리사이징된 이미지 프린트"""
        if not self.resized_image_path or not os.path.exists(self.resized_image_path):
            messagebox.showwarning("경고", "먼저 이미지를 리사이징해주세요")
            return
            
        try:
            self.update_status("프린트 중...")
            
            # 윈도우에서 기본 이미지 뷰어로 프린트
            if os.name == 'nt':  # Windows
                os.startfile(self.resized_image_path, "print")
            else:
                # 다른 OS의 경우 기본 이미지 뷰어로 열기
                if os.name == 'posix':  # macOS, Linux
                    subprocess.run(['open', self.resized_image_path])
                    
            self.update_status("프린트 대화상자가 열렸습니다")
            messagebox.showinfo("프린트", "프린트 대화상자가 열렸습니다. 프린터 설정을 확인하고 인쇄해주세요.")
            
        except Exception as e:
            messagebox.showerror("오류", f"프린트 중 오류가 발생했습니다: {str(e)}")
            self.update_status("프린트 실패")
            
    def update_status(self, message):
        """상태 표시줄 업데이트"""
        self.status_var.set(message)
        self.root.update_idletasks()

def main():
    root = tk.Tk()
    app = PhotoResizerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 