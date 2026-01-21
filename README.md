# train-bookara-maker-v2

手動伴唱影片製作工具，輸入 MP4 影片（含畫面與音軌），輸出帶有日文歌詞字幕的 MP4 影片。
支援音訊分離與字級時間軸標記，讓手工字幕製作流程更順暢。

## 專案定位

- 目標：製作便利性高、模組化程度高的手動伴唱影片製作工具
- 輸入：`.mp4` 影片（畫面 + 音軌）
- 輸出：`.mp4` 影片（畫面 + 字幕軌）

## 目前功能

- 音訊分離：匯入影片後可選擇輸出 `original.wav`、`music.wav`，並可選擇額外分離 vocal/bass/drums/other
- 歌詞載入：支援 `.txt` / `.lrc`，一行一句的句子編輯
- 句內編輯：Ruby 僅顯示在漢字上方；可用鍵盤移動字級游標並以 F2 / Ctrl+R 編輯 Ruby
- 時間標記：播放中按空白鍵逐字標記時間軸並即時高亮當前字
- 驗證輸出：輸出 LRC / ASS 前會先驗證，必要時可強制輸出
- 轉換與渲染：LRC → ASS、FFmpeg 匯出 MP4
- 預覽播放器：可預覽影片/音訊並同步顯示歌詞

## 專案結構

```text
train-bookara-maker-v2/
├── gui/                # GUI 元件
│   ├── widgets/        # 自訂元件
│   └── main_window.py  # 主視窗
├── core/               # 核心邏輯
│   ├── audio/          # 音訊處理
│   ├── lrc/            # LRC 格式處理
│   ├── subtitle/       # 字幕轉換
│   └── video/          # 影片渲染
├── pipeline/           # 流程編排
├── tests/              # 測試
├── resources/          # 資源
├── main.py             # 入口
└── config.py           # 設定
```

## 安裝與執行

1. 建立虛擬環境：
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # 或
   venv\Scripts\activate     # Windows
   ```
2. 安裝相依套件：
   ```bash
   pip install -r requirements.txt
   ```
3. 執行程式：
   ```bash
   python main.py
   ```

## 開發階段

- [x] Phase 1.1：影片上傳與音源分離
- [x] Phase 1.2：基礎 LRC 編輯器 UI
- [x] Phase 1.3：LRC 驗證與 I/O
- [x] Phase 1.4：LRC → ASS 轉換
- [x] Phase 1.5：FFmpeg 渲染
- [x] Phase 1.6：簡單預覽播放器

目前進度：Phase 1.6（簡單預覽播放器）完成。

詳細規劃請見 `docs/細粒度開發階段規劃2-0.md`。
專案規範與決策請見 `docs/專案憲法2-2.md`。
變更紀錄請見 `CHANGELOG.md`。
