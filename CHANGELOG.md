# CHANGELOG

## 2026-01-26
- **[ui]** 字幕樣式即時預覽：唱前/唱後分區顯示，預覽字體放大
- **[style]** 三層描邊（白/黑/白）預覽樣式
- **[style]** 新增粗體/斜體設定並套用到 ASS 輸出
- **[font]** 日文字型優先顯示（含ゴシック常用字型），保留常用字型
- **[ui]** 字型下拉支援上下鍵快速切換
- **[config]** SubtitleConfig 新增 bold/italic 設定

## 2026-01-22
- **[subtitle]** 行級字幕渲染：上下兩句交替顯示，行首提早顯示 0.7s
- **[style]** 顏色群組管理頁：預設 A=紅/灰、B=藍/灰，可啟用群組
- **[ui]** 編輯表格新增群組下拉選單，行級套用群組樣式
- **[config]** SubtitleConfig 與群組設定可保存於專案

## 2026-01-21
- **[audio]** 音訊分離輸出選項：預設 `original.wav` + `music.wav`，可選 vocal/bass/drums/other
- **[lyrics]** 句子編輯與 Ruby 顯示調整：漢字顯示 Ruby、假名不顯示
- **[ui]** 句內游標高亮與鍵盤 Ruby 編輯（F2 / Ctrl+R）
- **[lyrics]** 句子編輯側欄、插入/刪除行
- **[validate]** LRC/ASS 輸出前驗證（可強制輸出，空行略過）
- **[subtitle]** LRC → ASS 轉換與輸出
- **[render]** FFmpeg 匯出 MP4 流程接通
- **[preview]** 預覽播放器頁面與上方預覽按鈕

## 2026-01-19
- **[phase]** 已完成 Phase 1.2（基礎 LRC 編輯器 UI）
