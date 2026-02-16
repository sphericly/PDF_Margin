import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import sys

# PyPDF kontrolü
try:
    from pypdf import PdfReader, PdfWriter, Transformation
except ImportError:
    import tkinter.messagebox
    root = tk.Tk()
    root.withdraw()
    tkinter.messagebox.showerror("Missing Library", "Please run this command in terminal:\npip install pypdf")
    sys.exit()

class PDFMarginApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Margin Adder")
        # Pencereyi genişlettik (600px)
        self.root.geometry("600x300")
        self.root.resizable(False, False)

        # Stil ayarları
        self.style = ttk.Style()
        self.style.configure('TButton', font=('Helvetica', 9))
        self.style.configure('TLabel', font=('Helvetica', 10))

        # Değişkenler
        self.input_path = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.margin_value = tk.IntVar(value=30)

        self.create_widgets()

    def create_widgets(self):
        # Ana çerçeve
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Grid Sütun Ayarı: Ortadaki sütun (Entry) uzasın, butonlar sağda kalsın
        main_frame.columnconfigure(1, weight=1)

        # 1. Girdi Dosyası (Input File)
        ttk.Label(main_frame, text="Input PDF File:").grid(row=0, column=0, sticky="w", pady=10)
        ttk.Entry(main_frame, textvariable=self.input_path, state="readonly").grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        ttk.Button(main_frame, text="Select", command=self.select_input_file).grid(row=0, column=2, padx=0, pady=10)

        # 2. Çıktı Klasörü (Output Folder)
        ttk.Label(main_frame, text="Output Folder:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Entry(main_frame, textvariable=self.output_folder, state="readonly").grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        ttk.Button(main_frame, text="Select", command=self.select_output_folder).grid(row=1, column=2, padx=0, pady=5)

        # 3. Margin Değeri
        ttk.Label(main_frame, text="Margin (Points):").grid(row=2, column=0, sticky="w", pady=10)
        spinbox = ttk.Spinbox(main_frame, from_=0, to=200, textvariable=self.margin_value, width=10)
        spinbox.grid(row=2, column=1, sticky="w", padx=10, pady=10)

        # 4. Başlat Butonu (Start Process)
        self.start_button = ttk.Button(main_frame, text="START PROCESS", command=self.start_process, width=20)
        self.start_button.grid(row=3, column=0, columnspan=3, pady=25)

        # Durum Çubuğu
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="gray")
        self.status_label.grid(row=4, column=0, columnspan=2, sticky="w")

        # Sağ Alt Köşe Numarası (Watermark)
        # Grid yerine 'place' kullanarak kesin konumlandırma yaptık
        lbl_id = tk.Label(self.root, text="010210608", fg="#999999", font=("Arial", 8))
        lbl_id.place(relx=0.98, rely=0.98, anchor="se")

    def select_input_file(self):
        file_path = filedialog.askopenfilename(parent=self.root, title="Select PDF", filetypes=[("PDF Files", "*.pdf")])
        if file_path:
            self.input_path.set(file_path)
            if not self.output_folder.get():
                self.output_folder.set(os.path.dirname(file_path))

    def select_output_folder(self):
        folder_path = filedialog.askdirectory(parent=self.root, title="Select Output Folder")
        if folder_path:
            self.output_folder.set(folder_path)

    def get_unique_filename(self, folder, base_name, ext):
        """Aynı isimde dosya varsa sonuna _1, _2 ekler."""
        counter = 1
        output_filename = f"{base_name}_margin{ext}"
        output_path = os.path.join(folder, output_filename)
        
        while os.path.exists(output_path):
            output_filename = f"{base_name}_margin_{counter}{ext}"
            output_path = os.path.join(folder, output_filename)
            counter += 1
        
        return output_path

    def add_binding_margin(self, input_pdf_path, output_pdf_path, binding_margin_points):
        reader = PdfReader(input_pdf_path)
        writer = PdfWriter()

        for i, page in enumerate(reader.pages):
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            page_num = i + 1

            # Odd pages (Right shift)
            if page_num % 2 == 1:
                tx = binding_margin_points
            # Even pages (No shift)
            else:
                tx = 0

            op = Transformation().translate(tx=tx, ty=0)
            new_page = writer.add_blank_page(width=width + binding_margin_points, height=height)
            new_page.merge_transformed_page(page, op)

        with open(output_pdf_path, "wb") as f:
            writer.write(f)

    def start_process(self):
        input_file = self.input_path.get()
        output_dir = self.output_folder.get()
        
        try:
            margin = self.margin_value.get()
        except:
            messagebox.showerror("Error", "Please enter a valid numeric margin value.")
            return

        if not input_file or not os.path.exists(input_file):
            messagebox.showwarning("Warning", "Please select a valid PDF file.")
            return
        
        if not output_dir or not os.path.exists(output_dir):
            messagebox.showwarning("Warning", "Please select a valid output folder.")
            return

        self.start_button.config(state="disabled")
        self.status_label.config(text="Processing...", foreground="blue")
        self.root.update()

        try:
            filename = os.path.basename(input_file)
            name, ext = os.path.splitext(filename)
            
            # Benzersiz dosya ismi oluşturma
            final_output_path = self.get_unique_filename(output_dir, name, ext)

            self.add_binding_margin(input_file, final_output_path, margin)

            self.status_label.config(text="Completed", foreground="green")
            
            cevap = messagebox.askyesno("Success", f"Process Completed!\nSaved to:\n{final_output_path}\n\nOpen folder?")
            if cevap:
                os.startfile(output_dir)
            
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred:\n{str(e)}")
            self.status_label.config(text="Error", foreground="red")
        finally:
            self.start_button.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFMarginApp(root)
    root.mainloop()