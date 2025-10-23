import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent


class ImageDropArea(QLabel):
    """
    画像をドラッグアンドドロップで受け付けるためのカスタムQLabelクラス
    """
    # ファイルがドロップされたときにファイルパスを通知するシグナル
    fileDropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 1. ドロップ操作の受け入れを許可する
        self.setAcceptDrops(True)
        
        # 初期テキストとスタイルを設定
        self.setText("ここに画像をドラッグ＆ドロップ")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # スクリーンショットの紫色の四角のスタイルを再現
        # 点線(dashed)、太さ3px、紫(#800080)
        self.setStyleSheet("""
            ImageDropArea {
                border: 3px dashed #800080;
                border-radius: 10px;
                background-color: #f0f0f0;
                color: #aaa;
                font-size: 18px;
            }
        """)
        
        # ウィジェットが拡大できるようにポリシーを設定
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 200) # 最小サイズ

    def dragEnterEvent(self, event: QDragEnterEvent):
        """
        2. ドラッグされたアイテムが領域に入った時のイベント
        """
        # (a) ドラッグされたデータにURL (ファイルパス) が含まれているか確認
        if event.mimeData().hasUrls():
            # (b) 含まれていれば、ドロップ操作を受け入れる (カーソルが変わる)
            event.acceptProposedAction()
        else:
            # (c) URLでなければ拒否する
            event.ignore()

    def dragMoveEvent(self, event: QDragEnterEvent):
        """
        (オプション) ドラッグ中に領域内で移動した時のイベント
        基本的には dragEnterEvent と同じロジックで受け入れ/拒否を判定
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        """
        3. アイテムがドロップされた時のイベント
        """
        # (a) URLデータが含まれているか確認 (念のため)
        if event.mimeData().hasUrls():
            # (b) 最初のURLを取得
            url = event.mimeData().urls()[0]
            
            # (c) URLをローカルファイルのパスに変換
            filepath = url.toLocalFile()
            
            # (d) ファイルパスが実際に存在するか、画像ファイルかなどをここでチェック
            # (ここでは簡易的に拡張子でチェック)
            if filepath.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                print(f"画像ファイルがドロップされました: {filepath}")
                
                # (e) ファイルパスをメインウィンドウに通知する
                self.fileDropped.emit(filepath)
                
                # (f) ドロップ操作が完了したことを通知
                event.acceptProposedAction()
            else:
                print(f"画像ファイルではありません: {filepath}")
                event.ignore()
        else:
            event.ignore()

    def update_preview(self, filepath: str):
        """
        ドロップされた画像でプレビューを更新する
        """
        pixmap = QPixmap(filepath)
        # ラベルのサイズに合わせて画像をスケーリングして表示
        scaled_pixmap = pixmap.scaled(
            self.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled_pixmap)
        # テキストをクリア
        self.setText("")
        # スタイルをリセット (枠線は残す)
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
        
        # メインとなるウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # レイアウト
        layout = QVBoxLayout(central_widget)
        
        # (1) 紫色の領域に相当するドラッグアンドドロップエリア
        self.drop_area = ImageDropArea()
        # シグナルとスロットを接続
        self.drop_area.fileDropped.connect(self.handle_file_drop)
        
        # (2) レイアウトに追加
        layout.addWidget(self.drop_area)

        # (3) 他のUI要素 (ここではダミーのラベル)
        self.info_label = QLabel("ドロップされたファイルパス: ")
        self.info_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.info_label)

        # ウィンドウの初期サイズ
        self.setGeometry(300, 300, 600, 450)

    def handle_file_drop(self, filepath: str):
        """
        ファイルがドロップされた時の処理
        """
        # (a) ドロップエリアの表示を更新
        self.drop_area.update_preview(filepath)
        
        # (b) 情報ラベルを更新
        self.info_label.setText(f"処理対象ファイル: {filepath}")
        
        # (c) ここで画像の変換処理を呼び出す
        # self.convert_image(filepath)

    def convert_image(self, filepath: str):
        print(f"--- {filepath} の変換処理を開始 ---")
        # 例: Pillow (PIL) を使った処理
        # from PIL import Image
        # try:
        #     img = Image.open(filepath)
        #     # 何らかの変換処理 (例: グレースケール)
        #     gray_img = img.convert('L')
        #     save_path = filepath + "_converted.png"
        #     gray_img.save(save_path)
        #     print(f"変換完了: {save_path}")
        #     self.info_label.setText(f"変換完了: {save_path}")
        # except Exception as e:
        #     print(f"変換エラー: {e}")
        #     self.info_label.setText(f"変換エラー: {e}")
        pass


if __name__ == "__main__":
    # PyQt6 アプリケーションの実行
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
