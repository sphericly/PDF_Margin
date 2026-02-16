import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
from pypdf import PdfReader, PdfWriter, Transformation

class PDFMarginApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Delgeç Payı Ekleyici")
        self.root.geometry("500x250")
        self.root.resizable(False, False)

        # Değişkenler
        self.input_path = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.margin_value = tk.IntVar(value=30)

        self.create_widgets()

    def create_widgets(self):
        # Ana çerçeve (Padding için)
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Girdi Dosyası Seçimi
        ttk.Label(main_frame, text="Girdi PDF Dosyası:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.input_path, width=40, state="readonly").grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Seç", command=self.select_input_file).grid(row=0, column=2, padx=5, pady=5)

        # 2. Çıktı Klasörü Seçimi
        ttk.Label(main_frame, text="Çıktı Klasörü:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.output_folder, width=40, state="readonly").grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(main_frame, text="Seç", command=self.select_output_folder).grid(row=1, column=2, padx=5, pady=5)

        # 3. Margin Değeri
        ttk.Label(main_frame, text="Margin Değeri (Puan):").grid(row=2, column=0, sticky="w", pady=5)
        spinbox = ttk.Spinbox(main_frame, from_=0, to=200, textvariable=self.margin_value, width=10)
        spinbox.grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # 4. Başlat Butonu
        self.start_button = ttk.Button(main_frame, text="İşlemi Başlat", command=self.start_process)
        self.start_button.grid(row=3, column=0, columnspan=3, pady=20, sticky="ew")

        # Durum Çubuğu
        self.status_label = ttk.Label(main_frame, text="Hazır", foreground="gray")
        self.status_label.grid(row=4, column=0, columnspan=3, sticky="w")

    def select_input_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("PDF Dosyaları", "*.pdf")])
        if file_path:
            self.input_path.set(file_path)
            # Çıktı klasörü seçilmediyse, varsayılan olarak girdi dosyasının olduğu yeri seç
            if not self.output_folder.get():
                self.output_folder.set(os.path.dirname(file_path))

    def select_output_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.output_folder.set(folder_path)

    def add_binding_margin(self, input_pdf_path, output_pdf_path, binding_margin_points):
        """
        Orijinal mantık korunmuştur:
        Tek sayfalar (1, 3...): İçeriği SAĞA kaydırır.
        Çift sayfalar (2, 4...): İçeriği SOLA yaslar (kaydırma 0).
        """
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()

        for i, page in enumerate(reader.pages):
            # Sayfa boyutlarını al
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            page_num = i + 1

            # Tek sayfalarda sağa kaydır (Boşluk solda kalır)
            if page_num % 2 == 1:
                tx = binding_margin_points
            # Çift sayfalarda kaydırma yok (Boşluk sağda kalır, sayfa genişlediği için)
            else:
                tx = 0

            # Dönüşüm oluştur
            op = Transformation().translate(tx=tx, ty=0)

            # Genişletilmiş yeni boş sayfa oluştur
            new_page = writer.add_blank_page(width=width + binding_margin_points, height=height)

            # Orijinal içeriği yeni sayfaya yerleştir
            new_page.merge_transformed_page(page, op)

        with open(output_pdf_path, "wb") as f:
            writer.write(f)

    def start_process(self):
        input_file = self.input_path.get()
        output_dir = self.output_folder.get()
        
        try:
            margin = self.margin_value.get()
        except:
            messagebox.showerror("Hata", "Lütfen geçerli bir sayısal margin değeri girin.")
            return

        if not input_file or not os.path.exists(input_file):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir PDF dosyası seçin.")
            return
        
        if not output_dir or not os.path.exists(output_dir):
            messagebox.showwarning("Uyarı", "Lütfen geçerli bir çıktı klasörü seçin.")
            return

        self.start_button.config(state="disabled")
        self.status_label.config(text="İşleniyor...", foreground="blue")
        self.root.update()

        try:
            filename = os.path.basename(input_file)
            name, ext = os.path.splitext(filename)
            output_filename = f"{name}_delgec{ext}"
            output_path = os.path.join(output_dir, output_filename)

            self.add_binding_margin(input_file, output_path, margin)

            self.status_label.config(text="Tamamlandı", foreground="green")
            messagebox.showinfo("Başarılı", f"İşlem Tamamlandı!\nDosya konumu:\n{output_path}")
            
        except Exception as e:
            messagebox.showerror("Hata", f"Bir hata oluştu:\n{str(e)}")
            self.status_label.config(text="Hata oluştu", foreground="red")
        finally:
            self.start_button.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFMarginApp(root)
    root.mainloop()