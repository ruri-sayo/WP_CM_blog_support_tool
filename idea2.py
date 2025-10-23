import sys
import os 
import json # ★ 設定の保存/読み込みのためにインポート
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy, QPushButton, QLineEdit, QFileDialog, QStyle,
    QDialog, QGroupBox, QRadioButton, QSpinBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QStandardPaths
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QIcon, QCloseEvent

# Pillow (PIL) をインポート (実際の変換処理に必要)
# pip install Pillow pillow-avif-plugin
try:
    from PIL import Image
    import pillow_avif # AVIFサポートプラグインを有効化
except ImportError:
    print("警告: PIL (Pillow) または pillow-avif-plugin がインストールされていません。")
    print("インストールしてください: pip install Pillow pillow-avif-plugin")
    Image = None


# ★ 新規ヘルパー関数: PyInstaller対応
def get_base_path():
    """ 
    PyInstaller で .exe 化された場合 (frozen) と、
    スクリプト実行の場合で、基準となるパス（.exe または .py ファイル）を取得する 
    """
    if getattr(sys, 'frozen', False):
        # .exe として実行されている場合 (PyInstaller)
        # sys.executable は .exe ファイルのフルパス
        return os.path.dirname(sys.executable)
    else:
        # スクリプトとして実行されている場合 (.py)
        try:
            # __file__ は現在のスクリプトファイルのパス
            return os.path.dirname(os.path.abspath(__file__))
        except NameError:
            # 対話モードなどで __file__ が定義されていない場合
            return os.path.abspath(".")


class ImageDropArea(QLabel):
    """
    画像をドラッグアンドロップで受け付けるためのカスタムQLabelクラス
    (変更なし)
    """
    fileDropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setText("ここに画像をドラッグ＆ドロップ")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            ImageDropArea {
                border: 3px dashed #800080;
                border-radius: 10px;
                background-color: #f0f0f0;
                color: #aaa;
                font-size: 18px;
            }
        """)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 200)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            filepath = url.toLocalFile()
            if filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.fileDropped.emit(filepath)
                event.acceptProposedAction()
            else:
                event.ignore()

    def update_preview(self, filepath: str):
        pixmap = QPixmap(filepath)
        scaled_pixmap = pixmap.scaled(
            self.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)
        self.setText("")
        self.setStyleSheet("""
            ImageDropArea {
                border: 3px dashed #800080;
                border-radius: 10px;
                background-color: #ffffff;
            }
        """)


class ConversionSettingsDialog(QDialog):
    """
    WebP/AVIF の変換設定を行うサブウィンドウ
    (変更なし)
    """
    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("変換設定")
        self.setModal(True) 

        # --- UI要素の作成 ---

        # 1. 圧縮形式グループ
        compression_group = QGroupBox("圧縮形式")
        self.radio_lossless = QRadioButton("可逆 (Lossless)")
        self.radio_lossy = QRadioButton("非可逆 (Lossy)")
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setRange(0, 100)
        self.quality_spinbox.setValue(current_settings["quality"])
        
        comp_layout = QVBoxLayout()
        comp_layout.addWidget(self.radio_lossless)
        comp_layout.addWidget(self.radio_lossy)
        
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("品質 (非可逆時):"))
        quality_layout.addWidget(self.quality_spinbox)
        comp_layout.addLayout(quality_layout)
        compression_group.setLayout(comp_layout)
        
        if current_settings["lossless"]:
            self.radio_lossless.setChecked(True)
            self.quality_spinbox.setEnabled(False)
        else:
            self.radio_lossy.setChecked(True)
            self.quality_spinbox.setEnabled(True)

        # 2. リサイズグループ
        resize_group = QGroupBox("リサイズ")
        self.radio_original = QRadioButton("オリジナルサイズ")
        self.radio_specify = QRadioButton("指定サイズ")
        
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(1, 10000)
        self.width_spinbox.setValue(current_settings["width"])
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(1, 10000)
        self.height_spinbox.setValue(current_settings["height"])

        resize_layout = QVBoxLayout()
        resize_layout.addWidget(self.radio_original)
        resize_layout.addWidget(self.radio_specify)
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("幅:"))
        size_layout.addWidget(self.width_spinbox)
        size_layout.addWidget(QLabel("x 高さ:"))
        size_layout.addWidget(self.height_spinbox)
        resize_layout.addLayout(size_layout)
        resize_group.setLayout(resize_layout)
        
        if current_settings["resize_mode"] == "original":
            self.radio_original.setChecked(True)
            self.width_spinbox.setEnabled(False)
            self.height_spinbox.setEnabled(False)
        else:
            self.radio_specify.setChecked(True)
            self.width_spinbox.setEnabled(True)
            self.height_spinbox.setEnabled(True)

        # 3. 保存ボタン
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)

        # --- レイアウト設定 ---
        main_layout = QVBoxLayout()
        main_layout.addWidget(compression_group)
        main_layout.addWidget(resize_group)
        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

        # --- シグナル接続 ---
        self.radio_lossless.toggled.connect(lambda: self.quality_spinbox.setEnabled(False))
        self.radio_lossy.toggled.connect(lambda: self.quality_spinbox.setEnabled(True))
        
        self.radio_original.toggled.connect(lambda: self.set_resize_spinbox_enabled(False))
        self.radio_specify.toggled.connect(lambda: self.set_resize_spinbox_enabled(True))
        
        button_box.accepted.connect(self.accept) 
        button_box.rejected.connect(self.reject) 

    def set_resize_spinbox_enabled(self, enabled):
        self.width_spinbox.setEnabled(enabled)
        self.height_spinbox.setEnabled(enabled)

    def get_settings(self):
        return {
            "lossless": self.radio_lossless.isChecked(),
            "quality": self.quality_spinbox.value(),
            "resize_mode": "specify" if self.radio_specify.isChecked() else "original",
            "width": self.width_spinbox.value(),
            "height": self.height_spinbox.value()
        }


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("画像変換アプリ")
        
        self.source_filepath = None
        self.output_folder_path = None 
        
        # ★ 変更点: 設定ファイルパスを定義
        self.settings_filepath = os.path.join(get_base_path(), "image_converter_settings.json")
        print(f"設定ファイルパス: {self.settings_filepath}")

        # --- デフォルト変換設定 ---
        default_settings = {
            "lossless": False,
            "quality": 90, 
            "resize_mode": "original",
            "width": 1280,
            "height": 720
        }
        self.webp_settings = default_settings.copy()
        self.avif_settings = default_settings.copy()
        self.avif_settings["quality"] = 70 
        
        # ★ 変更点: 起動時に設定を読み込む
        self.load_settings()

        # --- メインウィンドウUI ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 1. ドロップエリア
        self.drop_area = ImageDropArea()
        self.drop_area.fileDropped.connect(self.handle_file_drop)
        main_layout.addWidget(self.drop_area)

        # 2. 情報ラベル
        self.info_label = QLabel("ドロップされたファイルパス: ")
        self.info_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.info_label)

        # 3. 変換ボタンエリア
        button_area_layout = QHBoxLayout()
        
        # WebP
        webp_layout = QVBoxLayout()
        self.convert_button_webp = QPushButton("webPに変換")
        self.convert_button_webp.setMinimumHeight(60)
        self.convert_button_webp.setStyleSheet("""
            QPushButton {
                background-color: #6495cf;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #77a8e0;
            }
        """)
        self.convert_button_webp.clicked.connect(self.run_conversion_webp)
        
        self.webp_settings_button = QPushButton("webP変換設定")
        self.webp_settings_button.setMinimumHeight(60)
        self.webp_settings_button.clicked.connect(self.open_webp_settings)
        
        webp_layout.addWidget(self.convert_button_webp)
        webp_layout.addWidget(self.webp_settings_button) 

        # AVIF
        avif_layout = QVBoxLayout()
        self.convert_button_avif = QPushButton("AVIFに変換")
        self.convert_button_avif.setMinimumHeight(60)
        self.convert_button_avif.setStyleSheet("""
            QPushButton {
                background-color: #274079;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3a5aa0;
            }
        """)
        self.convert_button_avif.clicked.connect(self.run_conversion_avif)
        
        self.avif_settings_button = QPushButton("AVIF変換設定")
        self.avif_settings_button.setMinimumHeight(60)
        self.avif_settings_button.clicked.connect(self.open_avif_settings)
        
        avif_layout.addWidget(self.convert_button_avif)
        avif_layout.addWidget(self.avif_settings_button) 

        button_area_layout.addLayout(webp_layout)
        button_area_layout.addLayout(avif_layout)
        
        main_layout.addLayout(button_area_layout)

        # 4. 吐き出し先フォルダ設定
        output_layout = QHBoxLayout()
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("吐き出し先のフォルダ")
        self.output_path_edit.setReadOnly(True)
        
        # ★ 変更点: load_settings の後で、読み込んだパスをUIに反映
        if self.output_folder_path:
            self.output_path_edit.setText(self.output_folder_path)
            
        self.select_output_button = QPushButton()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        self.select_output_button.setIcon(icon)
        self.select_output_button.setToolTip("吐き出し先のフォルダを選択")
        self.select_output_button.clicked.connect(self.select_output_folder)
        
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.select_output_button)
        
        main_layout.addLayout(output_layout)

        self.setGeometry(300, 300, 600, 500) 

    def handle_file_drop(self, filepath: str):
        self.source_filepath = filepath
        self.drop_area.update_preview(filepath)
        self.info_label.setText(f"処理対象ファイル: {filepath}")
        
        if not self.output_folder_path:
            folder = os.path.dirname(filepath)
            self.output_folder_path = folder
            self.output_path_edit.setText(folder)
            # ★ 変更点: 自動設定した場合も保存
            self.save_settings() 

    def select_output_folder(self):
        default_dir = self.output_folder_path or \
                      QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        
        folderpath = QFileDialog.getExistingDirectory(
            self,
            "吐き出し先のフォルダを選択",
            default_dir
        )
        
        if folderpath:
            self.output_folder_path = folderpath
            self.output_path_edit.setText(folderpath)
            print(f"吐き出し先フォルダに設定: {folderpath}")
            # ★ 変更点: フォルダ設定変更時にも保存
            self.save_settings()

    def _check_prerequisites(self) -> bool:
        if not self.source_filepath:
            self.info_label.setText("エラー: 変換するファイルを先にドロップしてください。")
            return False
        if not self.output_folder_path:
            self.info_label.setText("エラー: 吐き出し先フォルダを設定してください。")
            return False
        if Image is None:
            self.info_label.setText("エラー: Pillow (PIL) が見つかりません。")
            return False
        return True

    def _get_final_output_path(self, new_extension: str) -> str:
        base_filename = os.path.basename(self.source_filepath)
        filename_without_ext, _ = os.path.splitext(base_filename)
        new_filename = filename_without_ext + new_extension
        return os.path.join(self.output_folder_path, new_filename)

    def _process_image(self, img: Image.Image, settings: dict) -> Image.Image:
        if settings["resize_mode"] == "specify":
            try:
                new_size = (settings["width"], settings["height"])
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            except Exception as e:
                print(f"リサイズエラー: {e}")
        return img

    def run_conversion_webp(self):
        if not self._check_prerequisites():
            return
            
        final_output_path = self._get_final_output_path(".webp")
        settings = self.webp_settings

        print(f"--- WebP変換 を実行 (設定: {settings}) ---")
        self.info_label.setText("WebPに変換中...") 
        
        try:
            img = Image.open(self.source_filepath)
            img = self._process_image(img, settings)

            save_options = {
                "format": "WEBP",
                "lossless": settings["lossless"],
                "method": 6 
            }
            if not settings["lossless"]:
                save_options["quality"] = settings["quality"]

            img.save(final_output_path, **save_options)
            
            self.info_label.setText(f"WebP変換 完了: {final_output_path}")
        except Exception as e:
            print(f"WebP変換 エラー: {e}")
            self.info_label.setText(f"WebP変換 エラー: {e}")
        
        QApplication.processEvents()

    def run_conversion_avif(self):
        if not self._check_prerequisites():
            return

        final_output_path = self._get_final_output_path(".avif")
        settings = self.avif_settings

        print(f"--- AVIF変換 を実行 (設定: {settings}) ---")
        self.info_label.setText("AVIFに変換中...") 
        
        try:
            img = Image.open(self.source_filepath)
            img = self._process_image(img, settings)

            save_options = {
                "format": "AVIF",
                "speed": 5 
            }
            if settings["lossless"]:
                save_options["quality"] = 100
            else:
                save_options["quality"] = settings["quality"]

            img.save(final_output_path, **save_options)
            
            self.info_label.setText(f"AVIF変換 完了: {final_output_path}")
        except Exception as e:
            print(f"AVIF変換 エラー: {e}")
            self.info_label.setText(f"AVIF変換 エラー: {e}")
            
        QApplication.processEvents()

    def open_webp_settings(self):
        dialog = ConversionSettingsDialog(self.webp_settings, self)
        
        if dialog.exec():
            self.webp_settings = dialog.get_settings()
            print("WebP設定が更新されました:", self.webp_settings)
            self.info_label.setText("WebP設定を更新しました")
            # ★ 変更点: 設定ダイアログ保存時にも保存
            self.save_settings()

    def open_avif_settings(self):
        dialog = ConversionSettingsDialog(self.avif_settings, self)
        
        if dialog.exec():
            self.avif_settings = dialog.get_settings()
            print("AVIF設定が更新されました:", self.avif_settings)
            self.info_label.setText("AVIF設定を更新しました")
            # ★ 変更点: 設定ダイアログ保存時にも保存
            self.save_settings()

    # ★ 新規メソッド: 設定の読み込み
    def load_settings(self):
        """ 起動時に設定ファイル (JSON) を読み込む """
        if not os.path.exists(self.settings_filepath):
             print("設定ファイルが見つかりません。デフォルト設定で起動します。")
             return
             
        try:
            with open(self.settings_filepath, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            
            # .get() を使い、キーが存在しない場合は現在の値 (デフォルト) を維持
            # 辞書全体がキーになっているか確認し、なければデフォルトを割り当て
            self.webp_settings.update(settings_data.get("webp_settings", {}))
            self.avif_settings.update(settings_data.get("avif_settings", {}))
            
            # パスはNoneかもしれないので、Noneをデフォルトに
            self.output_folder_path = settings_data.get("output_folder_path", None)
            
            print("設定を読み込みました。")
            
        except (json.JSONDecodeError, TypeError) as e:
            print(f"設定ファイルが破損している可能性があります: {e}")
            print("デフォルト設定で起動します。")
        except Exception as e:
            print(f"設定の読み込み中に予期せぬエラーが発生しました: {e}")

    # ★ 新規メソッド: 設定の保存
    def save_settings(self):
        """ 設定ファイル (JSON) に保存する """
        settings_data = {
            "webp_settings": self.webp_settings,
            "avif_settings": self.avif_settings,
            "output_folder_path": self.output_folder_path
        }
        
        try:
            with open(self.settings_filepath, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4, ensure_ascii=False)
            print(f"設定を保存しました: {self.settings_filepath}")
        except IOError as e:
            print(f"設定ファイルの保存に失敗しました: {e}")
        except Exception as e:
            print(f"設定の保存中に予期せぬエラーが発生しました: {e}")

    # ★ 新規メソッド: ウィンドウが閉じられるときのイベント
    def closeEvent(self, event: QCloseEvent):
        """ ウィンドウが閉じられるときに設定を保存する (フェイルセーフ) """
        self.save_settings() 
        event.accept() # ウィンドウを閉じる処理を続行

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
