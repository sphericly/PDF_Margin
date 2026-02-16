import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageEnhance, ImageDraw  # Görsel efektler için eklendi
import os
import sys
import tempfile

# Kütüphane Kontrolleri
try:
    import fitz  # PyMuPDF
except ImportError:
    import tkinter.messagebox
    root = tk.Tk()
    root.withdraw()
    tkinter.messagebox.showerror("Missing Library", "Preview requires PyMuPDF.\nPlease run: pip install pymupdf")
    sys.exit()

try:
    from pypdf import PdfReader, PdfWriter, Transformation, PageObject
except ImportError:
    sys.exit()

class PDFToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Master Tool (Reorder, Merge, Margin & Booklet)")
        self.root.geometry("1000x800")
        
        # --- VERİ YAPISI ---
        # Sayfaları hafızada tutmak için liste. 
        # Her eleman şöyledir: { 'file_path': str, 'page_num': int, 'thumb': PhotoImage, 'is_deleted': bool, 'id': str }
        self.pdf_pages = [] 
        self.batch_counter = 0
        self.file_colors = ["black", "#0038A8", "#D60270", "#9B4F96"]
        
        # Değişkenler
        self.output_folder = tk.StringVar()
        self.margin_value = tk.IntVar(value=0)
        self.operation_mode = tk.StringVar(value="margin")
        
        # Sürükle-Bırak için geçici değişkenler
        self.drag_data = {"item": None, "x": 0, "y": 0, "index": None, "target_index_visual": None}
        self.drag_window = None  # Sürükleme animasyonu için pencere
        self.drop_indicator = None # Sürükleme sırasında araya giren çizgi
        self.last_clicked_index = None

        self.style = ttk.Style()
        self.style.configure('TButton', font=('Segoe UI', 9))
        self.style.configure('TLabel', font=('Segoe UI', 10))
        self.style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'))

        self.create_layout()

    def create_layout(self):
        # --- Üst Panel (Dosya İşlemleri) ---
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        # Butonlar
        ttk.Button(top_frame, text="Open Main PDF", command=lambda: self.add_pdf(clear=True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="➕ Merge PDF (Append)", command=lambda: self.add_pdf(clear=False)).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(top_frame, text="Output Folder:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(top_frame, textvariable=self.output_folder, width=40, state="readonly").pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Select Folder", command=self.select_output_folder).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(top_frame, text="Clear All", command=self.clear_all).pack(side=tk.RIGHT, padx=5)

        # --- Orta Panel (Önizleme / Reorder Alanı) ---
        preview_frame = ttk.LabelFrame(self.root, text="Preview (Drag to Reorder | Click to Delete)", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(preview_frame, bg="#e0e0e0")
        scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.canvas.yview)
        
        # Sayfaların duracağı iç çerçeve
        self.scrollable_frame = tk.Frame(self.canvas, bg="#e0e0e0")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # --- Alt Panel (Ayarlar ve İşlem) ---
        bottom_frame = ttk.Frame(self.root, padding="15")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Modlar
        ttk.Label(bottom_frame, text="Mode:", style='Header.TLabel').grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(bottom_frame, text="Add Margin", variable=self.operation_mode, value="margin", command=self.toggle_inputs).grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(bottom_frame, text="Booklet (2-up)", variable=self.operation_mode, value="booklet", command=self.toggle_inputs).grid(row=1, column=1, sticky="w")
        
        # Margin
        self.lbl_margin = ttk.Label(bottom_frame, text="Margin (pts):")
        self.lbl_margin.grid(row=2, column=0, sticky="w")
        self.spin_margin = ttk.Spinbox(bottom_frame, from_=0, to=200, textvariable=self.margin_value, width=5)
        self.spin_margin.grid(row=2, column=1, sticky="w")

        # Process Button
        self.btn_process = ttk.Button(bottom_frame, text="PROCESS PDF", command=self.start_processing, width=25)
        self.btn_process.grid(row=0, column=3, rowspan=3, padx=50)

        # Status
        self.lbl_status = ttk.Label(bottom_frame, text="Ready. Load a PDF to start.", foreground="gray")
        self.lbl_status.grid(row=3, column=0, columnspan=4, sticky="w", pady=10)

        # Watermark
        tk.Label(self.root, text="sphericly © 2026", fg="#cccccc", font=("Arial", 8)).place(relx=0.98, rely=0.99, anchor="se")
        
        self.load_logo()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def toggle_inputs(self):
        if self.operation_mode.get() == "margin":
            self.spin_margin.state(["!disabled"])
        else:
            self.spin_margin.state(["disabled"])

    def load_logo(self):
        try:
            # Dosya yolunu kontrol et
            logo_path = "itu_cyber_bee.svg"
            if not os.path.exists(logo_path):
                # Script'in olduğu klasöre de bak
                logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "itu_cyber_bee.svg")
                if not os.path.exists(logo_path):
                    return

            doc = fitz.open(logo_path)
            page = doc[0]
            
            # Boyutlandırma (Yükseklik ~40px)
            zoom = 40 / page.rect.height
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=True)
            
            # PIL Image dönüşümü ve Renklendirme (#cccccc)
            img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
            _, _, _, a = img.split()
            colored_img = Image.new("RGBA", img.size, "#cccccc")
            colored_img.putalpha(a)
            
            self.logo_photo = ImageTk.PhotoImage(colored_img)
            
            # Arayüze ekle (Yazının üstüne)
            lbl_logo = tk.Label(self.root, image=self.logo_photo, bg=self.root.cget("bg"))
            lbl_logo.place(relx=0.98, rely=0.95, anchor="se")
            
        except Exception as e:
            print(f"Logo yükleme hatası: {e}")

    def select_output_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.output_folder.set(path)

    def clear_all(self):
        self.pdf_pages = []
        self.last_clicked_index = None
        self.refresh_grid()
        self.lbl_status.config(text="Cleared all pages.")

    # --- PDF YÜKLEME VE GÖRSEL İŞLEME ---

    def add_pdf(self, clear=False):
        files = filedialog.askopenfilenames(filetypes=[("PDF Files", "*.pdf")])
        if not files:
            return

        if clear:
            self.pdf_pages = []
            self.batch_counter = 0
            self.last_clicked_index = None
            # İlk dosyanın klasörünü çıktı klasörü olarak öner
            if not self.output_folder.get():
                self.output_folder.set(os.path.dirname(files[0]))

        self.lbl_status.config(text="Loading pages...", foreground="blue")
        self.root.update()

        for file_path in files:
            current_color = self.file_colors[self.batch_counter % len(self.file_colors)]
            try:
                doc = fitz.open(file_path)
                for i, page in enumerate(doc):
                    # Görseli oluştur (Thumbnail)
                    pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
                    img_pil = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    self.pdf_pages.append({
                        "file_path": file_path,
                        "page_num": i,
                        "original_pil": img_pil,  # Orijinal temiz resim
                        "is_deleted": False,
                        "tk_image": ImageTk.PhotoImage(img_pil), # Ekranda görünen
                        "text_color": current_color
                    })
                doc.close()
                self.batch_counter += 1
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load {file_path}:\n{e}")

        self.refresh_grid()
        self.lbl_status.config(text=f"Total pages: {len(self.pdf_pages)}", foreground="green")

    def get_display_image(self, page_data):
        """Silinme durumuna göre görseli (Normal veya Karanlık+X) döndürür."""
        pil_img = page_data["original_pil"].copy()

        if page_data["is_deleted"]:
            # 1. Karart (Darken)
            enhancer = ImageEnhance.Brightness(pil_img)
            pil_img = enhancer.enhance(0.4) # %40 parlaklık
            
            # 2. Kırmızı X Çiz
            draw = ImageDraw.Draw(pil_img)
            w, h = pil_img.size
            line_width = 5
            draw.line((0, 0, w, h), fill="red", width=line_width)
            draw.line((0, h, w, 0), fill="red", width=line_width)

        return ImageTk.PhotoImage(pil_img)

    def update_page_visual(self, index):
        """Sayfanın görsel durumunu günceller (Silindi/Normal)."""
        page = self.pdf_pages[index]
        new_tk_img = self.get_display_image(page)
        page["tk_image"] = new_tk_img
        
        widgets = self.scrollable_frame.winfo_children()
        if index < len(widgets):
            target_frame = widgets[index]
            btn = target_frame.winfo_children()[0]
            btn.configure(image=new_tk_img)
            
            status_text = "DELETED" if page["is_deleted"] else f"Pg {page['page_num']+1}"
            lbl = target_frame.winfo_children()[1]
            txt_color = "red" if page["is_deleted"] else page.get("text_color", "black")
            lbl.configure(text=status_text, fg=txt_color)

    def toggle_delete(self, index):
        """Bir sayfayı silindi/silinmedi olarak işaretler."""
        self.pdf_pages[index]["is_deleted"] = not self.pdf_pages[index]["is_deleted"]
        self.update_page_visual(index)

    # --- SÜRÜKLE BIRAK (DRAG & DROP) VE ARAYÜZ ---

    def refresh_grid(self):
        """Tüm grid'i self.pdf_pages listesine göre yeniden çizer."""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        cols = 5
        for i, page in enumerate(self.pdf_pages):
            # Container Frame
            frame = tk.Frame(self.scrollable_frame, bg="#e0e0e0", bd=2)
            frame.grid(row=i//cols, column=i%cols, padx=5, pady=5)
            
            # Resim (Buton olarak, tıklayınca silme toggler)
            # Not: Sürükleme için bind olaylarını butona ekleyeceğiz
            img = page["tk_image"]
            btn = tk.Label(frame, image=img, cursor="hand2")
            btn.pack()
            
            # Olayları Bağla
            btn.bind("<Button-1>", lambda e, idx=i: self.on_click(e, idx))
            btn.bind("<B1-Motion>", lambda e, idx=i: self.on_drag(e, idx))
            btn.bind("<ButtonRelease-1>", lambda e, idx=i: self.on_drop(e, idx))
            
            # Etiket
            txt = "DELETED" if page["is_deleted"] else f"Pg {page['page_num']+1}"
            color = "red" if page["is_deleted"] else page.get("text_color", "black")
            lbl = tk.Label(frame, text=txt, bg="#e0e0e0", fg=color, font=("Arial", 8))
            lbl.pack()

    # --- DRAG & DROP LOGIC ---
    def on_click(self, event, index):
        self.drag_data["index"] = index
        self.drag_data["start_x"] = event.x
        self.drag_data["start_y"] = event.y
        self.drag_data["is_dragging"] = False

    def on_drag(self, event, index):
        # Küçük titremelerde sürükleme başlamasın
        if abs(event.x - self.drag_data["start_x"]) > 5 or abs(event.y - self.drag_data["start_y"]) > 5:
            self.drag_data["is_dragging"] = True
            self.root.config(cursor="fleur") # İmleci değiştir
            
            # --- SÜRÜKLEME ANİMASYONU (GHOST IMAGE) ---
            if self.drag_window is None:
                # Sürüklenen görseli içeren çerçevesiz, yarı saydam pencere oluştur
                self.drag_window = tk.Toplevel(self.root)
                self.drag_window.overrideredirect(True) # Pencere kenarlıklarını kaldır
                self.drag_window.attributes('-topmost', True) # En üstte tut
                self.drag_window.attributes('-alpha', 0.7) # Şeffaflık (%70 görünür)
                
                # Görseli pencereye ekle
                page = self.pdf_pages[index]
                img = page["tk_image"]
                lbl = tk.Label(self.drag_window, image=img, bg="#cccccc", bd=2, relief="solid")
                lbl.pack()
            
            # Pencereyi fareyi takip edecek şekilde konumlandır
            # x_root ve y_root ekran koordinatlarını verir
            img = self.pdf_pages[index]["tk_image"]
            x = event.x_root - (img.width() // 2)
            y = event.y_root - (img.height() // 2)
            self.drag_window.geometry(f"+{x}+{y}")
            
            # --- DROP INDICATOR (Araya girme çizgisi) ---
            if not hasattr(self, 'drop_indicator') or self.drop_indicator is None or not self.drop_indicator.winfo_exists():
                self.drop_indicator = tk.Frame(self.scrollable_frame, bg="#0038A8", width=4)
            
            # Hedef konumu bul
            x_root, y_root = event.x_root, event.y_root
            found_target = False
            
            # Gösterge hariç diğer widgetları al
            widgets = [w for w in self.scrollable_frame.winfo_children() if w != self.drop_indicator]
            
            for i, widget in enumerate(widgets):
                wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
                ww, wh = widget.winfo_width(), widget.winfo_height()
                
                # Fare bu hücrenin sınırları içinde mi?
                if wx <= x_root <= wx + ww and wy <= y_root <= wy + wh:
                    # Sol yarı mı sağ yarı mı?
                    if x_root < wx + (ww // 2):
                        self.drag_data["target_index_visual"] = i
                        ix = widget.winfo_x() - 2 # Sol kenar
                    else:
                        self.drag_data["target_index_visual"] = i + 1
                        ix = widget.winfo_x() + ww + 2 # Sağ kenar
                    
                    iy = widget.winfo_y()
                    ih = wh
                    
                    self.drop_indicator.place(x=ix, y=iy, height=ih)
                    self.drop_indicator.lift()
                    found_target = True
                    break
            
            if not found_target:
                self.drop_indicator.place_forget()
                self.drag_data["target_index_visual"] = None

    def on_drop(self, event, index):
        self.root.config(cursor="") # İmleci düzelt
        
        # Animasyon penceresini temizle
        if self.drag_window:
            self.drag_window.destroy()
            self.drag_window = None
            
        # Göstergeyi gizle
        if self.drop_indicator:
            self.drop_indicator.place_forget()
        
        if not self.drag_data["is_dragging"]:
            # Sürükleme değilse, sadece tıklamadır -> SİLME İŞLEMİ
            # Shift tuşu kontrolü (Bit 0)
            if (event.state & 0x0001) and self.last_clicked_index is not None:
                start = min(self.last_clicked_index, index)
                end = max(self.last_clicked_index, index)
                # Hedef durumu, son tıklanan (anchor) sayfanın durumuna göre belirle
                target_state = self.pdf_pages[self.last_clicked_index]["is_deleted"]
                
                for i in range(start, end + 1):
                    if self.pdf_pages[i]["is_deleted"] != target_state:
                        self.pdf_pages[i]["is_deleted"] = target_state
                        self.update_page_visual(i)
            else:
                self.toggle_delete(index)
                self.last_clicked_index = index
            return

        # Sürükleme bittiyse -> YER DEĞİŞTİRME
        target_index = self.drag_data.get("target_index_visual")
        
        if target_index is not None and target_index != index:
            # Listede yer değiştir
            item = self.pdf_pages.pop(index)
            if target_index > index:
                target_index -= 1
            self.pdf_pages.insert(target_index, item)
            self.refresh_grid()
            self.last_clicked_index = None # Sıralama değişince seçimi sıfırla

        self.drag_data["is_dragging"] = False
        self.drag_data["target_index_visual"] = None

    # --- PROCESS ---

    def start_processing(self):
        if not self.pdf_pages:
            messagebox.showwarning("Warning", "No pages loaded.")
            return
        
        if not self.output_folder.get():
             messagebox.showwarning("Warning", "Please select an output folder.")
             return

        self.btn_process.config(state="disabled")
        self.lbl_status.config(text="Processing...", foreground="blue")
        self.root.update()

        try:
            # 1. Önce "Merge" edilmiş ve "Sort" edilmiş temiz bir geçici PDF oluştur
            temp_writer = PdfWriter()
            
            # Performans için dosyaları bir kere açıp tutalım
            open_files = {} 
            
            count = 0
            for page_data in self.pdf_pages:
                if page_data["is_deleted"]:
                    continue
                
                f_path = page_data["file_path"]
                p_num = page_data["page_num"]
                
                if f_path not in open_files:
                    open_files[f_path] = PdfReader(f_path)
                
                reader = open_files[f_path]
                temp_writer.add_page(reader.pages[p_num])
                count += 1
            
            if count == 0:
                raise Exception("All pages are deleted!")

            # Geçici dosyaya kaydet
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                temp_writer.write(tmp)
                temp_pdf_path = tmp.name

            # 2. Şimdi bu temiz dosyaya Margin veya Booklet uygula
            # --- DOSYA ADI OLUŞTURMA ---
            active_pages = [p for p in self.pdf_pages if not p["is_deleted"]]
            unique_files = []
            seen = set()
            for p in active_pages:
                if p["file_path"] not in seen:
                    unique_files.append(p["file_path"])
                    seen.add(p["file_path"])
            
            base_names = [os.path.splitext(os.path.basename(f))[0] for f in unique_files]
            joined_name = "_".join(base_names)
            
            # Durum Analizi
            has_deleted = any(p["is_deleted"] for p in self.pdf_pages)
            is_merged = len(unique_files) > 1
            
            # Reorder Kontrolü
            is_reordered = False
            current_file = None
            last_pg = -1
            file_set = set()
            for p in active_pages:
                if p["file_path"] != current_file:
                    if p["file_path"] in file_set: is_reordered = True
                    file_set.add(p["file_path"])
                    current_file = p["file_path"]
                    last_pg = -1
                if p["page_num"] < last_pg: is_reordered = True
                last_pg = p["page_num"]
            
            is_organised = has_deleted or is_reordered
            
            parts = []
            if is_organised: parts.append("organised")
            if is_merged: parts.append("merged")
            if self.operation_mode.get() == "margin" and self.margin_value.get() > 0: parts.append("margined")
            elif self.operation_mode.get() == "booklet": parts.append("booklet")
            
            suffix = "_".join(parts) if parts else "processed"
            final_filename = f"{joined_name}_{suffix}.pdf"
            final_path = self.get_unique_filename(self.output_folder.get(), final_filename)
            
            if self.operation_mode.get() == "margin":
                self.process_margin(temp_pdf_path, final_path, self.margin_value.get())
            else:
                self.process_booklet(temp_pdf_path, final_path)

            os.remove(temp_pdf_path) # Temizle
            
            self.lbl_status.config(text="Done!", foreground="green")
            if messagebox.askyesno("Success", f"File Saved:\n{final_path}\n\nOpen output folder?"):
                os.startfile(self.output_folder.get())

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.lbl_status.config(text="Error occurred", foreground="red")
        finally:
            self.btn_process.config(state="normal")

    def get_unique_filename(self, folder, filename):
        counter = 1
        name, ext = os.path.splitext(filename)
        full_path = os.path.join(folder, filename)
        while os.path.exists(full_path):
            filename = f"{name}_{counter}{ext}"
            full_path = os.path.join(folder, filename)
            counter += 1
        return full_path

    def process_margin(self, input_path, output_path, margin):
        reader = PdfReader(input_path)
        writer = PdfWriter()

        for i, page in enumerate(reader.pages):
            width = float(page.mediabox.width)
            height = float(page.mediabox.height)
            page_num = i + 1

            if page_num % 2 == 1:
                tx = margin
            else:
                tx = 0

            op = Transformation().translate(tx=tx, ty=0)
            new_page = writer.add_blank_page(width=width + margin, height=height)
            new_page.merge_transformed_page(page, op)

        with open(output_path, "wb") as f:
            writer.write(f)

    def get_fit_transform(self, page, target_w, target_h, x_offset, y_offset):
        """Sayfayı hedef alana orantılı sığdırır (Kırpma yapmaz, ortalar)."""
        mb = page.mediabox
        src_w = float(mb.width)
        src_h = float(mb.height)
        
        if src_w == 0 or src_h == 0:
            return Transformation().translate(x_offset, y_offset)

        scale = min(target_w / src_w, target_h / src_h)
        new_w = src_w * scale
        new_h = src_h * scale
        
        dx = x_offset + (target_w - new_w) / 2
        dy = y_offset + (target_h - new_h) / 2
        
        return Transformation().scale(scale, scale).translate(dx, dy)

    def process_booklet(self, input_path, output_path):
        reader = PdfReader(input_path)
        writer = PdfWriter()
        
        pages = list(reader.pages)
        total_pages = len(pages)
        
        remainder = total_pages % 4
        if remainder != 0:
            pages_needed = 4 - remainder
            ref_width = pages[0].mediabox.width
            ref_height = pages[0].mediabox.height
            for _ in range(pages_needed):
                pages.append(PageObject.create_blank_page(width=ref_width, height=ref_height))
        
        total_pages = len(pages)
        num_sheets = total_pages // 4
        
        A4_WIDTH_PT = 595.276
        A4_HEIGHT_PT = 841.89
        out_width = A4_HEIGHT_PT
        out_height = A4_WIDTH_PT
        
        for i in range(num_sheets):
            idx_front_left = total_pages - 1 - (2 * i)
            idx_front_right = 2 * i
            
            sheet_front = PageObject.create_blank_page(width=out_width, height=out_height)
            
            page_fl = pages[idx_front_left]
            tf_fl = self.get_fit_transform(page_fl, out_width/2, out_height, 0, 0)
            sheet_front.merge_transformed_page(page_fl, tf_fl)
            
            page_fr = pages[idx_front_right]
            tf_fr = self.get_fit_transform(page_fr, out_width/2, out_height, out_width/2, 0)
            sheet_front.merge_transformed_page(page_fr, tf_fr)
            
            writer.add_page(sheet_front)
            
            idx_back_left = 2 * i + 1
            idx_back_right = total_pages - 1 - (2 * i + 1)
            
            sheet_back = PageObject.create_blank_page(width=out_width, height=out_height)
            
            page_bl = pages[idx_back_left]
            tf_bl = self.get_fit_transform(page_bl, out_width/2, out_height, 0, 0)
            sheet_back.merge_transformed_page(page_bl, tf_bl)
            
            page_br = pages[idx_back_right]
            tf_br = self.get_fit_transform(page_br, out_width/2, out_height, out_width/2, 0)
            sheet_back.merge_transformed_page(page_br, tf_br)
            
            writer.add_page(sheet_back)

        with open(output_path, "wb") as f:
            writer.write(f)

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFToolApp(root)
    root.mainloop()