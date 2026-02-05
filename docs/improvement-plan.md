# Train Bookara Maker v2 改善計畫

## 專案概述

本文件針對 [train-bookara-maker-v2](https://github.com/newhandarky/train-bookara-maker-v2) 專案進行問題分析與改善規劃，目標是達到或超越 ニコカラメーカー 的字幕品質，特別是在 Ruby(振假名)對齊方面的完美呈現。

---

## 當前狀態評估

### 已實現功能

根據專案程式碼分析，目前已完成以下核心功能:

- ✅ **音訊處理**：影片上傳、音源分離(原始音軌、伴奏、人聲等)
- ✅ **歌詞編輯**：支援 LRC/TXT 格式、Ruby 註音編輯、字級時間軸標記
- ✅ **字幕渲染**：LRC → ASS 轉換、行級交替顯示(上下兩句)
- ✅ **顏色群組**：A/B 群組管理，可套用不同樣式
- ✅ **樣式設定**：字型、字級、描邊、陰影、粗體/斜體、字距
- ✅ **影片輸出**：FFmpeg 渲染 MP4、預覽播放器

### 與 ニコカラ 的差距

| 功能項目 | 現況 | 目標 | 優先度 |
|---------|------|------|--------|
| **字幕填色流暢度** | 使用 `\k` 標籤 | 使用 `\kf` 或 `\ko` 標籤 | 🔥 高 |
| **Ruby 對齊精準度** | 簡單實作，對齊效果不理想 | 完美對齊漢字位置，自動計算寬度 | 🔥🔥🔥 **最高** |
| **即時預覽** | 需輸出 MP4 才能預覽 | 即時編輯預覽 | ⚡ 中高 |
| **時間軸編輯效率** | 基本功能 | 波形顯示、更好的快捷鍵 | ⚡ 中 |

---

## 改善重點規劃

### 重點一：字幕填色流暢度提升 🔥

#### 問題分析

目前實作使用 ASS 的 `\k` 標籤進行逐字填色，這是最基本的卡拉 OK 效果。`\k` 標籤的特性是:
- 逐字「瞬間」變色
- 沒有漸進填充的視覺效果
- 看起來較為生硬

#### ニコカラ 的做法

ニコカラ 使用更流暢的填色標籤:
- `\kf` (karaoke fill): 填充式效果，從左到右平滑填充
- `\ko` (karaoke outline): 邊框式效果，邊框顏色變化

#### 改善方案

**方案 A: 預設使用 `\kf` 標籤(建議)**

修改 `core/subtitle/converter.py` 的 `_build_karaoke_text` 方法:

```python
def _build_karaoke_text(self, line, line_start: float) -> str:
    """組合行級別卡拉OK標籤字串(使用 \kf 提升流暢度)"""
    parts = []
    prev_end = line_start

    for word in line.words:
        gap = max(0.0, word.start_time - prev_end)
        gap_cs = int(round(gap * 100))
        if gap_cs > 0:
            parts.append(f"{{\\kf{gap_cs}}}")  # 使用 \kf 取代 \k

        duration_cs = int(round(max(0.0, word.end_time - word.start_time) * 100))
        parts.append(f"{{\\kf{duration_cs}}}{word.text}")  # 使用 \kf
        prev_end = word.end_time

    return ''.join(parts)
```

**方案 B: 提供使用者選項**

在 `SubtitleConfig` 中增加配置選項:

```python
@dataclass
class SubtitleConfig:
    # ... 現有設定 ...
    
    # 卡拉OK填色模式
    karaoke_effect_type: str = "kf"  # "k" | "kf" | "ko"
```

然後在轉換時根據設定選擇:

```python
effect_tag = self.config.karaoke_effect_type  # "k", "kf", 或 "ko"
parts.append(f"{{\\{effect_tag}{duration_cs}}}{word.text}")
```

#### 預期效果

- 字幕填色從「瞬間跳變」改為「平滑填充」
- 視覺效果更自然、更專業
- 更接近 ニコカラ 和 Aegisub 的標準效果

---

### 重點二: Ruby(振假名)完美對齊 🔥🔥🔥

#### 問題分析

這是您最在意的功能。目前實作的問題:

1. **Ruby 寬度計算不精確**
   - 目前使用空格字元 (`chr(0x3000)`) 填充非漢字位置
   - 無法精確計算 Ruby 與漢字的寬度關係
   - 導致 Ruby 無法完美居中對齊

2. **缺乏字符寬度計算**
   - 漢字、平假名、片假名的寬度不同
   - Ruby 字型大小不同，寬度也會變化
   - 需要實際計算字符像素寬度

3. **沒有 Ruby 間距微調機制**
   - 當 Ruby 比漢字寬時，需要分散對齊
   - 當 Ruby 比漢字窄時，需要居中對齊
   - 目前缺乏這種智能調整

#### ニコカラ 和 Aegisub 的做法

專業字幕工具的 Ruby 對齊技術:

1. **精確字符寬度計算**
   - 使用 QFontMetrics(Qt) 或 FontMetrics(Python)
   - 根據實際字型計算每個字符的像素寬度
   - 考慮字距(spacing)的影響

2. **智能對齊算法**
   - Ruby 寬度 < 漢字寬度: 居中對齊
   - Ruby 寬度 > 漢字寬度: Ruby 左對齊漢字，或使用 `\fsp` 分散對齊
   - 連續多個漢字共用一串 Ruby: 整體對齊計算

3. **ASS 間距標籤**
   - 使用 `\fsp<pixels>` 調整字距
   - 為 Ruby 的每個字符單獨設定間距
   - 實現完美的視覺對齊

#### 改善方案

**階段 1: 實作字符寬度計算引擎**

建立新模組 `core/subtitle/font_metrics.py`:

```python
"""
字型度量計算模組
用於精確計算字符寬度，實現 Ruby 完美對齊
"""

from typing import Dict, Optional
from PyQt5.QtGui import QFont, QFontMetrics, QFontDatabase
from PyQt5.QtWidgets import QApplication
import sys


class FontMetricsCalculator:
    """字型度量計算器"""
    
    def __init__(self):
        # 確保 QApplication 存在(QFontMetrics 需要)
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        
        self._font_cache: Dict[str, QFont] = {}
        self._metrics_cache: Dict[str, QFontMetrics] = {}
    
    def get_font(self, font_name: str, font_size: int, 
                 bold: bool = False, italic: bool = False) -> QFont:
        """獲取字型物件(帶快取)"""
        cache_key = f"{font_name}_{font_size}_{bold}_{italic}"
        
        if cache_key not in self._font_cache:
            font = QFont(font_name, font_size)
            font.setBold(bold)
            font.setItalic(italic)
            self._font_cache[cache_key] = font
        
        return self._font_cache[cache_key]
    
    def get_metrics(self, font_name: str, font_size: int,
                    bold: bool = False, italic: bool = False) -> QFontMetrics:
        """獲取字型度量物件(帶快取)"""
        cache_key = f"{font_name}_{font_size}_{bold}_{italic}"
        
        if cache_key not in self._metrics_cache:
            font = self.get_font(font_name, font_size, bold, italic)
            metrics = QFontMetrics(font)
            self._metrics_cache[cache_key] = metrics
        
        return self._metrics_cache[cache_key]
    
    def calculate_text_width(self, text: str, font_name: str, 
                            font_size: int, spacing: int = 0,
                            bold: bool = False, italic: bool = False) -> float:
        """計算文字實際寬度(像素)"""
        metrics = self.get_metrics(font_name, font_size, bold, italic)
        
        # 基礎寬度
        width = metrics.horizontalAdvance(text)
        
        # 加上字距影響(每個字符之間)
        if len(text) > 1:
            width += spacing * (len(text) - 1)
        
        return width
    
    def calculate_char_widths(self, text: str, font_name: str,
                             font_size: int, spacing: int = 0,
                             bold: bool = False, italic: bool = False) -> list:
        """計算每個字符的寬度列表"""
        metrics = self.get_metrics(font_name, font_size, bold, italic)
        
        widths = []
        for char in text:
            char_width = metrics.horizontalAdvance(char)
            widths.append(char_width)
        
        return widths
```

**階段 2: 實作 Ruby 對齊算法**

建立新模組 `core/subtitle/ruby_aligner.py`:

```python
"""
Ruby 對齊算法模組
實現 Ruby(振假名)與漢字的完美對齊
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass
from .font_metrics import FontMetricsCalculator


@dataclass
class RubyAlignment:
    """Ruby 對齊結果"""
    base_spacing: int = 0      # 基礎文字間距調整
    ruby_spacing: int = 0      # Ruby 文字間距調整
    ruby_offset_x: int = 0     # Ruby 水平偏移
    alignment_type: str = ""   # 對齊類型: center, left, distributed


class RubyAligner:
    """Ruby 對齊計算器"""
    
    def __init__(self, font_calculator: FontMetricsCalculator):
        self.font_calc = font_calculator
    
    def calculate_alignment(
        self,
        base_text: str,
        ruby_text: str,
        base_font: str,
        base_size: int,
        ruby_font: str,
        ruby_size: int,
        base_spacing: int = 0,
        base_bold: bool = False,
        base_italic: bool = False
    ) -> RubyAlignment:
        """
        計算 Ruby 對齊參數
        
        Args:
            base_text: 基礎文字(漢字)
            ruby_text: Ruby 文字(假名)
            base_font: 基礎文字字型
            base_size: 基礎文字大小
            ruby_font: Ruby 字型
            ruby_size: Ruby 大小
            base_spacing: 基礎文字原始間距
            base_bold: 基礎文字是否粗體
            base_italic: 基礎文字是否斜體
        
        Returns:
            RubyAlignment: 對齊參數
        """
        # 計算基礎文字總寬度
        base_width = self.font_calc.calculate_text_width(
            base_text, base_font, base_size, base_spacing, base_bold, base_italic
        )
        
        # 計算 Ruby 文字總寬度
        ruby_width = self.font_calc.calculate_text_width(
            ruby_text, ruby_font, ruby_size, 0, False, False
        )
        
        result = RubyAlignment()
        
        # 情況 1: Ruby 寬度 <= 基礎文字寬度(Ruby 居中)
        if ruby_width <= base_width:
            result.alignment_type = "center"
            result.base_spacing = base_spacing  # 維持原始間距
            result.ruby_spacing = 0
            # 計算居中偏移
            result.ruby_offset_x = int((base_width - ruby_width) / 2)
        
        # 情況 2: Ruby 寬度 > 基礎文字寬度(需要調整)
        else:
            width_diff = ruby_width - base_width
            
            # 子情況 2a: 差距不大(<20%)，使用分散對齊
            if width_diff / base_width < 0.2:
                result.alignment_type = "distributed"
                # 計算 Ruby 需要的間距來匹配基礎寬度
                if len(ruby_text) > 1:
                    # 分散 Ruby 字符以匹配基礎寬度
                    result.ruby_spacing = int(width_diff / (len(ruby_text) - 1))
                result.base_spacing = base_spacing
                result.ruby_offset_x = 0
            
            # 子情況 2b: 差距較大，擴展基礎文字間距
            else:
                result.alignment_type = "expand_base"
                # 擴展基礎文字間距來容納 Ruby
                if len(base_text) > 1:
                    extra_spacing = int(width_diff / (len(base_text) - 1))
                    result.base_spacing = base_spacing + extra_spacing
                result.ruby_spacing = 0
                result.ruby_offset_x = 0
        
        return result
    
    def calculate_multi_char_alignment(
        self,
        base_chars: List[str],
        ruby_chars: List[str],
        base_font: str,
        base_size: int,
        ruby_font: str,
        ruby_size: int,
        base_spacing: int = 0
    ) -> List[Tuple[str, int]]:
        """
        計算多字符 Ruby 對齊(進階版)
        為每個 Ruby 字符計算精確的間距
        
        Returns:
            List[Tuple[str, int]]: (字符, 該字符前的間距)
        """
        # 計算每個基礎字符的寬度
        base_widths = self.font_calc.calculate_char_widths(
            ''.join(base_chars), base_font, base_size, base_spacing
        )
        
        # 計算每個 Ruby 字符的寬度
        ruby_widths = self.font_calc.calculate_char_widths(
            ''.join(ruby_chars), ruby_font, ruby_size, 0
        )
        
        total_base_width = sum(base_widths) + base_spacing * (len(base_chars) - 1)
        total_ruby_width = sum(ruby_widths)
        
        # 分配間距給每個 Ruby 字符
        ruby_spacings = []
        
        if total_ruby_width <= total_base_width:
            # Ruby 較窄: 均勻分配剩餘空間
            remaining_space = total_base_width - total_ruby_width
            if len(ruby_chars) > 1:
                avg_spacing = int(remaining_space / (len(ruby_chars) - 1))
                ruby_spacings = [avg_spacing] * (len(ruby_chars) - 1)
                ruby_spacings.append(0)  # 最後一個字符不需要間距
            else:
                ruby_spacings = [0]
        else:
            # Ruby 較寬: 使用緊湊間距
            ruby_spacings = [0] * len(ruby_chars)
        
        # 組合結果
        result = []
        for i, char in enumerate(ruby_chars):
            spacing = ruby_spacings[i] if i < len(ruby_spacings) else 0
            result.append((char, spacing))
        
        return result
```

**階段 3: 整合到 ASS 轉換器**

修改 `core/subtitle/converter.py`:

```python
from .font_metrics import FontMetricsCalculator
from .ruby_aligner import RubyAligner

class LrcToAssConverter:
    """LRC -> ASS 轉換器(加強 Ruby 對齊)"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = SubtitleConfig.from_dict(config) if config else SubtitleConfig()
        
        # 初始化字型計算器
        self.font_calc = FontMetricsCalculator()
        self.ruby_aligner = RubyAligner(self.font_calc)
    
    def _build_ruby_text_v2(self, line, line_start: float) -> tuple:
        """
        組合 Ruby 行文字(版本 2: 完美對齊)
        """
        parts = []
        prev_end = line_start
        has_ruby = False
        
        base_font = self.config.fontname
        base_size = self.config.fontsize
        ruby_font = self.config.ruby_fontname or base_font
        ruby_size = self.config.ruby_fontsize or max(1, int(base_size * 0.5))
        base_spacing = int(self.config.spacing or 0)
        base_bold = getattr(self.config, 'bold', False)
        base_italic = getattr(self.config, 'italic', False)
        
        for word in line.words:
            gap = max(0.0, word.start_time - prev_end)
            gap_cs = int(round(gap * 100))
            if gap_cs > 0:
                parts.append(f"{{\\kf{gap_cs}}}")
            
            duration_cs = int(round(max(0.0, word.end_time - word.start_time) * 100))
            
            # 判斷是否有 Ruby 且為漢字
            if word.ruby_pair and word.ruby_pair.ruby and self._is_kanji(word.text):
                has_ruby = True
                
                # 計算對齊參數
                alignment = self.ruby_aligner.calculate_alignment(
                    base_text=word.text,
                    ruby_text=word.ruby_pair.ruby,
                    base_font=base_font,
                    base_size=base_size,
                    ruby_font=ruby_font,
                    ruby_size=ruby_size,
                    base_spacing=base_spacing,
                    base_bold=base_bold,
                    base_italic=base_italic
                )
                
                # 根據對齊類型生成 ASS 標籤
                ruby_text = word.ruby_pair.ruby
                
                if alignment.alignment_type == "center":
                    # Ruby 居中: 使用偏移
                    if alignment.ruby_offset_x > 0:
                        parts.append(f"{{\\kf{duration_cs}}}{{\\fsp0}}{{\\pos({alignment.ruby_offset_x},0)}}{ruby_text}")
                    else:
                        parts.append(f"{{\\kf{duration_cs}}}{ruby_text}")
                
                elif alignment.alignment_type == "distributed":
                    # 分散對齊: 調整 Ruby 間距
                    parts.append(f"{{\\kf{duration_cs}}}{{\\fsp{alignment.ruby_spacing}}}{ruby_text}")
                
                elif alignment.alignment_type == "expand_base":
                    # 擴展基礎: Ruby 正常顯示(基礎文字會自動調整)
                    parts.append(f"{{\\kf{duration_cs}}}{ruby_text}")
                
            else:
                # 非漢字或無 Ruby: 使用全形空格佔位
                space_char = chr(0x3000)
                parts.append(f"{{\\kf{duration_cs}}}{space_char}")
            
            prev_end = word.end_time
        
        return ''.join(parts), has_ruby
```

**階段 4: 配置選項擴展**

在 `SubtitleConfig` 中增加 Ruby 相關配置:

```python
@dataclass
class SubtitleConfig:
    # ... 現有設定 ...
    
    # Ruby 對齊設定
    ruby_alignment_mode: str = "auto"  # auto, center, distributed
    ruby_auto_spacing: bool = True      # 自動計算間距
    ruby_min_spacing: int = 0           # Ruby 最小間距
    ruby_max_spacing: int = 20          # Ruby 最大間距
```

#### 實作優先順序

1. **第一步(最小可行)**: 實作 `FontMetricsCalculator`
2. **第二步(核心功能)**: 實作基本的 `RubyAligner`(單字符對齊)
3. **第三步(完整功能)**: 整合到 `LrcToAssConverter`
4. **第四步(優化)**: 實作多字符精確對齊、邊界情況處理

#### 預期效果

- ✅ Ruby 完美居中對齊漢字
- ✅ 自動處理 Ruby 寬度 > 漢字寬度的情況
- ✅ 支援連續多個漢字共用一串 Ruby
- ✅ 達到 ニコカラ 和 Aegisub 的專業水準

#### 測試案例

建議建立以下測試案例驗證對齊效果:

1. **單字符測試**:
   - 漢字: `東` / Ruby: `ひがし`(Ruby 較寬)
   - 漢字: `日` / Ruby: `ひ`(Ruby 較窄)

2. **多字符測試**:
   - 漢字: `東京` / Ruby: `とうきょう`
   - 漢字: `大切` / Ruby: `たいせつ`

3. **混合測試**:
   - `東京へ行く` 其中只有 `東京` 和 `行` 有 Ruby

---

### 重點三: 即時預覽系統 ⚡

#### 問題分析

目前需要完整輸出 MP4 才能查看最終效果，調整效率低落。

#### 改善方案

**方案 A: 使用 python-mpv 實作即時預覽**

1. 安裝依賴:
```bash
pip install python-mpv
```

2. 建立預覽模組 `gui/widgets/live_preview_player.py`:

```python
"""
即時預覽播放器
使用 mpv 實現 ASS 字幕即時預覽
"""

import tempfile
import os
from typing import Optional
import mpv


class LivePreviewPlayer:
    """即時字幕預覽播放器"""
    
    def __init__(self):
        self.player = mpv.MPV(
            keep_open=True,
            osc=True,
            input_default_bindings=True,
            input_vo_keyboard=True
        )
        self.current_video: Optional[str] = None
        self.temp_ass_file: Optional[str] = None
    
    def load_video(self, video_path: str):
        """載入影片"""
        self.current_video = video_path
        self.player.play(video_path)
        self.player.pause = True  # 預設暫停
    
    def update_subtitle(self, ass_content: str):
        """
        更新字幕內容(即時)
        
        Args:
            ass_content: ASS 字幕內容
        """
        # 寫入暫存 ASS 檔案
        if self.temp_ass_file:
            os.unlink(self.temp_ass_file)
        
        fd, self.temp_ass_file = tempfile.mkstemp(suffix='.ass', text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(ass_content)
        
        # 移除舊字幕軌
        try:
            self.player.sub_remove()
        except:
            pass
        
        # 載入新字幕
        self.player.sub_add(self.temp_ass_file)
    
    def play(self):
        """播放"""
        self.player.pause = False
    
    def pause(self):
        """暫停"""
        self.player.pause = True
    
    def seek(self, time_sec: float):
        """跳轉到指定時間"""
        self.player.seek(time_sec, reference='absolute')
    
    def get_current_time(self) -> float:
        """獲取當前播放時間"""
        return self.player.time_pos or 0.0
    
    def cleanup(self):
        """清理資源"""
        if self.temp_ass_file and os.path.exists(self.temp_ass_file):
            os.unlink(self.temp_ass_file)
        self.player.terminate()
```

3. 整合到主視窗:

在字幕樣式編輯介面加入「即時預覽」按鈕，當用戶調整參數時:
- 即時生成 ASS 內容
- 呼叫 `update_subtitle()` 更新預覽
- 無需重新輸出完整影片

**方案 B: 使用 libass + PyQt5 Canvas 渲染**

優點: 更輕量、更可控
缺點: 實作較複雜

建議先實作方案 A，若效能不佳再考慮方案 B。

#### 預期效果

- 調整字型/顏色/大小後，1 秒內看到預覽效果
- 大幅提升調試效率
- 更好的使用者體驗

---

### 重點四: 時間軸編輯優化 ⚡

#### 改善方向

1. **波形顯示**
   - 在時間軸編輯器中顯示音訊波形
   - 更容易找到精確的標記點

2. **快捷鍵優化**
   - 空格: 標記當前字並播放
   - Ctrl+Space: 標記並跳到下一字
   - Shift+Space: 回退上一字
   - J/K/L: 快速倒退/暫停/前進(仿 YouTube)
   - ←/→: 微調當前字的時間(±50ms)

3. **自動預填時間軸(可選)**
   - 使用 Whisper 語音識別預填時間軸
   - 使用者只需微調即可
   - 大幅減少手動標記工作量

#### 實作建議

波形顯示可以使用 `matplotlib` 或 `pyqtgraph`:

```python
import librosa
import matplotlib.pyplot as plt

def generate_waveform(audio_path: str, output_image: str):
    """生成波形圖片"""
    y, sr = librosa.load(audio_path)
    plt.figure(figsize=(12, 2))
    plt.plot(y)
    plt.axis('off')
    plt.savefig(output_image, bbox_inches='tight', pad_inches=0)
    plt.close()
```

---

## 不實作的功能

以下功能根據您的要求暫不實作:

### ❌ 字幕動畫效果

- ❌ 淡入淡出(`\fad`)
- ❌ 滑動、縮放、旋轉等動畫
- ❌ 複雜的 `\t` 變換效果

**原因**: 專注於基礎品質，動畫效果可作為未來擴展功能。

### ❌ 內嵌圖像功能

- ❌ 字幕中插入圖片
- ❌ emoji / 絵文字支援

**原因**: 使用場景有限，實作成本高。

---

## 實作時程建議

### Phase 2.4: 字幕效果優化(1-2 週)

**目標**: 提升字幕流暢度

- [ ] 實作 `\kf` 標籤替換 `\k`
- [ ] 加入配置選項(`karaoke_effect_type`)
- [ ] 測試不同歌曲的效果
- [ ] 更新文檔

**完成標準**: 字幕填色平滑自然，無跳變感。

---

### Phase 2.5: Ruby 完美對齊(3-4 週) 🔥🔥🔥

**目標**: 實現 Ruby 與漢字的完美對齊

**子階段 2.5.1: 字型計算引擎(1 週)**
- [ ] 實作 `FontMetricsCalculator`
- [ ] 測試各種字型的寬度計算
- [ ] 建立單元測試

**子階段 2.5.2: Ruby 對齊算法(1 週)**
- [ ] 實作 `RubyAligner` 基本功能
- [ ] 處理三種對齊情況(居中、分散、擴展)
- [ ] 建立測試案例

**子階段 2.5.3: 整合與優化(1-2 週)**
- [ ] 整合到 `LrcToAssConverter`
- [ ] 實作多字符精確對齊
- [ ] 處理邊界情況(特殊字符、混合文字)
- [ ] 大量測試不同歌曲

**完成標準**:
- Ruby 完美居中漢字上方
- 支援 Ruby 比漢字寬/窄的情況
- 視覺效果達到 ニコカラ 水準

---

### Phase 2.6: 即時預覽系統(2-3 週)

**目標**: 實作參數調整即時預覽

- [ ] 整合 python-mpv
- [ ] 實作 `LivePreviewPlayer`
- [ ] 在主視窗加入預覽控制
- [ ] 實作參數變更自動更新機制

**完成標準**: 調整參數後 1 秒內看到預覽效果。

---

### Phase 2.7: 時間軸編輯優化(2-3 週)

**目標**: 提升時間軸標記效率

- [ ] 實作波形顯示
- [ ] 優化快捷鍵系統
- [ ] 加入微調功能(±50ms)
- [ ] (可選)整合 Whisper 自動預填

**完成標準**: 標記效率提升 50% 以上。

---

## 技術依賴

### 新增依賴套件

```
# 字型度量計算
PyQt5>=5.15.0

# 即時預覽
python-mpv>=1.0.1

# 波形顯示(可選)
librosa>=0.10.0
matplotlib>=3.7.0
```

### 系統需求

- Python 3.8+
- FFmpeg(已有)
- mpv 播放器(用於即時預覽)

---

## 測試策略

### 單元測試

1. **字型計算測試**
   - 測試各種字型的寬度計算準確性
   - 測試不同字號、粗體、斜體的影響

2. **Ruby 對齊測試**
   - 測試三種對齊模式
   - 測試邊界情況

### 整合測試

1. **歌曲測試集**
   - 準備 5-10 首不同風格的日文歌曲
   - 涵蓋不同的 Ruby 使用情況

2. **視覺比對測試**
   - 與 ニコカラ 的輸出結果進行視覺比對
   - 確保對齊效果達標

---

## 成功標準

### Phase 2.5(Ruby 對齊)成功標準

1. ✅ Ruby 視覺上完美居中漢字
2. ✅ 支援 Ruby 寬度大於/小於漢字的情況
3. ✅ 連續多個漢字的 Ruby 正確分配
4. ✅ 與 ニコカラ 輸出效果相當或更好

### 整體專案成功標準

1. ✅ 字幕流暢度達到 ニコカラ 水準
2. ✅ Ruby 對齊品質達到專業水準
3. ✅ 即時預覽功能正常運作
4. ✅ 時間軸編輯效率顯著提升
5. ✅ 使用者反饋滿意度 > 80%

---

## 參考資源

### 技術文檔

- [ASS 字幕格式規範](http://www.tcax.org/docs/ass-specs.htm)
- [Aegisub Furigana 實作](https://aegisub.org/docs/latest/furigana_karaoke/)
- [PyQt5 QFontMetrics 文檔](https://doc.qt.io/qt-5/qfontmetrics.html)

### 開源專案參考

- [rubysubs](https://github.com/RicBent/rubysubs) - Ruby 字幕工具
- [Aegisub](https://github.com/Aegisub/Aegisub) - 專業字幕編輯器
- [karaoke.dev](https://github.com/karaoke-dev/karaoke) - 卡拉 OK 遊戲引擎

---

## 附錄: 程式碼檢查清單

### 實作 Ruby 對齊前的準備

- [ ] 確認 PyQt5 已安裝
- [ ] 測試 QFontMetrics 在當前環境可用
- [ ] 準備測試用日文字型(至少 2-3 種)
- [ ] 建立測試案例資料集

### 程式碼品質要求

- [ ] 所有新模組都有 docstring
- [ ] 關鍵函數有類型標註
- [ ] 單元測試覆蓋率 > 80%
- [ ] 通過 pylint 檢查(評分 > 8.0)

---

## 結語

本改善計畫聚焦於您最在意的 **Ruby 完美對齊** 功能，並同步提升字幕流暢度。預計 Phase 2.5 完成後，專案將在字幕品質方面達到或超越 ニコカラメーカー 的水準。

即時預覽系統(Phase 2.6)將大幅提升開發和使用體驗，建議作為第二優先級實作。

時間軸編輯優化(Phase 2.7)可提升製作效率，可視需求彈性調整優先順序。

如有任何技術問題或需要更詳細的程式碼範例，請隨時提出討論。
