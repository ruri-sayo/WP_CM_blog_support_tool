import sys
import os # 拡張子を変更するためにインポート
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSizePolicy, QPushButton, QLineEdit, QFileDialog, QStyle
)
from PyQt6.QtCore import Qt, pyqtSignal, QStandardPaths
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QIcon
# Pillow (PIL) をインポート (実際の変換処理に必要)
# pip install Pillow pillow-avif-plugin
try:
    from PIL import Image
    import pillow_avif # AVIFサポートプラグインを有効化
except ImportError:
    print("警告: PIL (Pillow) または pillow-avif-plugin がインストールされていません。")
    print("インストールしてください: pip install Pillow pillow-avif-plugin")
    Image = None

class ImageDropArea(QLabel):
    """
    画像をドラッグアンドドロップで受け付けるためのカスタムQLabelクラス
    (変更なし)
    """
    # ファイルがドロップされたときにファイルパスを通知するシグナル
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
                print(f"画像ファイルがドロップされました: {filepath}")
                self.fileDropped.emit(filepath)
                event.acceptProposedAction()
            else:
                print(f"画像ファイルではありません: {filepath}")
                event.ignore()
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

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("画像変換アプリ")
        
        self.source_filepath = None
        self.output_filepath = None # ユーザーが *選択した* パス (拡張子変更前)

        # メインとなるウィジェットとレイアウト
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget) # 全体の垂直レイアウト

        # --- 1. ドラッグアンドドロップエリア ---
        self.drop_area = ImageDropArea()
        self.drop_area.fileDropped.connect(self.handle_file_drop)
        main_layout.addWidget(self.drop_area)

        # --- ドロップされたファイル情報ラベル ---
        self.info_label = QLabel("ドロップされたファイルパス: ")
        self.info_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        main_layout.addWidget(self.info_label)

        # --- 2. 変換ボタンエリア (レイアウト変更) ---
        button_area_layout = QHBoxLayout() # 水平レイアウト
        
        # (A) WebP変換エリア (垂直レイアウト)
        webp_layout = QVBoxLayout()
        self.convert_button_webp = QPushButton("webPに変換")
        self.convert_button_webp.setMinimumHeight(60) # 縦の大きさを倍 (約60px) に設定
        self.convert_button_webp.clicked.connect(self.run_conversion_webp)
        
        self.webp_settings_button = QPushButton("webP変換設定")
        self.webp_settings_button.setFlat(True) # テキストリンク風にする
        self.webp_settings_button.setStyleSheet("color: #0078d4;") # 色付け
        self.webp_settings_button.clicked.connect(self.open_webp_settings)
        
        webp_layout.addWidget(self.convert_button_webp)
        webp_layout.addWidget(self.webp_settings_button, 0, Qt.AlignmentFlag.AlignCenter) # 中央揃え

        # (B) AVIF変換エリア (垂直レイアウト)
        avif_layout = QVBoxLayout()
        self.convert_button_avif = QPushButton("AVIFに変換")
        self.convert_button_avif.setMinimumHeight(60) # 縦の大きさを倍 (約60px) に設定
        self.convert_button_avif.clicked.connect(self.run_conversion_avif)
        
        self.avif_settings_button = QPushButton("AVIF変換設定")
        self.avif_settings_button.setFlat(True) # テキストリンク風にする
        self.avif_settings_button.setStyleSheet("color: #0078d4;") # 色付け
        self.avif_settings_button.clicked.connect(self.open_avif_settings)
        
        avif_layout.addWidget(self.convert_button_avif)
        avif_layout.addWidget(self.avif_settings_button, 0, Qt.AlignmentFlag.AlignCenter) # 中央揃え

        # (C) 2つのエリアをボタンエリアレイアウトに追加
        button_area_layout.addLayout(webp_layout)
        button_area_layout.addLayout(avif_layout)
        
        main_layout.addLayout(button_area_layout) # ボタンエリアレイアウトをメインに追加

        # --- スペーサー (これより下のウィジェットを一番下に押しやる) ---
        main_layout.addStretch(1)

        # --- 3. 吐き出し先ファイルパス設定 ---
        output_layout = QHBoxLayout()
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("吐き出し先のファイルパス（拡張子は自動で変更されます）")
        self.output_path_edit.setReadOnly(True)
        
        self.select_output_button = QPushButton()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        self.select_output_button.setIcon(icon)
        self.select_output_button.setToolTip("吐き出し先のファイルパスを選択")
        self.select_output_button.clicked.connect(self.select_output_path)
        
        output_layout.addWidget(self.output_path_edit)
        output_layout.addWidget(self.select_output_button)
        
        main_layout.addLayout(output_layout)

        self.setGeometry(300, 300, 600, 550) # 高さを少し増やす

    def handle_file_drop(self, filepath: str):
        self.source_filepath = filepath
        self.drop_area.update_preview(filepath)
        self.info_label.setText(f"処理対象ファイル: {filepath}")

    def select_output_path(self):
        """
        吐き出し先の *ベース* となるパスを選択
        """
        default_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
        
        # フィルタに WebP と AVIF を追加
        filter = "WebP画像 (*.webp);;AVIF画像 (*.avif);;PNG画像 (*.png);;JPEG画像 (*.jpg *.jpeg);;すべてのファイル (*)"
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "吐き出し先のファイルを選択",
            default_dir,
            filter
        )
        
        if filepath:
            self.output_filepath = filepath
            # 拡張子は変換時に変更される旨を伝える
            base_path, _ = os.path.splitext(filepath)
            self.output_path_edit.setText(f"{base_path}.[webp/avif]")
            print(f"吐き出し先ベースパスに設定: {filepath}")

    def _check_prerequisites(self) -> bool:
        """ 変換実行前の共通チェック """
        if not self.source_filepath:
            self.info_label.setText("エラー: 変換するファイルを先にドロップしてください。")
            return False
        if not self.output_filepath:
            self.info_label.setText("エラー: 吐き出し先ファイルパスを設定してください。")
            return False
        if Image is None:
            self.info_label.setText("エラー: Pillow (PIL) が見つかりません。")
            return False
        return True

    def run_conversion_webp(self):
        """ 「webPに変換」ボタンが押された時の処理 """
        if not self._check_prerequisites():
            return
            
        # 出力パスの拡張子を .webp に変更
        base_path, _ = os.path.splitext(self.output_filepath)
        final_output_path = base_path + ".webp"

        print(f"--- WebP変換 を実行 ---")
        print(f"  入力: {self.source_filepath}")
        print(f"  出力: {final_output_path}")
        
        try:
            # Pillow を使った WebP 変換処理
            img = Image.open(self.source_filepath)
            # WebP の変換設定 (例: 可逆圧縮 quality=100, 非可逆圧縮 quality=80)
            # setting = self.get_webp_settings() # 設定画面から値を取得 (将来)
            img.save(final_output_path, format="WEBP", quality=90, method=6)
            
            self.info_label.setText(f"WebP変換 完了: {final_output_path}")
        except Exception as e:
            print(f"WebP変換 エラー: {e}")
            self.info_label.setText(f"WebP変換 エラー: {e}")

    def run_conversion_avif(self):
        """ 「AVIFに変換」ボタンが押された時の処理 """
        if not self._check_prerequisites():
            return

        # 出力パスの拡張子を .avif に変更
        base_path, _ = os.path.splitext(self.output_filepath)
        final_output_path = base_path + ".avif"

        print(f"--- AVIF変換 を実行 ---")
        print(f"  入力: {self.source_filepath}")
        print(f"  出力: {final_output_path}")
        
        try:
            # Pillow と pillow-avif-plugin を使った AVIF 変換処理
            img = Image.open(self.source_filepath)
            # AVIF の変換設定 (例: 可逆圧縮 quality=100, 非可逆圧縮 quality=60, speed=4)
            # setting = self.get_avif_settings() # 設定画面から値を取得 (将来)
            img.save(final_output_path, format="AVIF", quality=70, speed=5)
            
            self.info_label.setText(f"AVIF変換 完了: {final_output_path}")
        except Exception as e:
            print(f"AVIF変換 エラー: {e}")
            self.info_label.setText(f"AVIF変換 エラー: {e}")

    def open_webp_settings(self):
        """ (ダミー) WebP変換設定画面を開く """
        print("WebP変換設定ダイアログを開きます (未実装)")
        # ここで QDialog を継承した設定ウィンドウなどを開く
        self.info_label.setText("WebP変換設定 (未実装)")

    def open_avif_settings(self):
        """ (ダミー) AVIF変換設定画面を開く """
        print("AVIF変換設定ダイアログを開きます (未実装)")
        # ここで QDialog を継承した設定ウィンドウなどを開く
        self.info_label.setText("AVIF変換設定 (未実装)")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
