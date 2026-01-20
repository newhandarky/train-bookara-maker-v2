"""
LRC 驗證器

作用：
- 驗證時間軸順序
- 驗證文字與假名對應
"""

from dataclasses import dataclass
from typing import List, Tuple

from .model import LrcTimeline


@dataclass
class ValidationError:
    """驗證錯誤資訊"""

    line_index: int  # 行索引
    word_index: int  # 詞索引
    error_type: str  # 錯誤類型代碼
    message: str  # 錯誤訊息


class LrcValidator:
    """LRC 驗證器"""

    def validate(self, timeline: LrcTimeline) -> Tuple[bool, List[ValidationError]]:
        """驗證 LRC 時間軸內容"""
        errors: List[ValidationError] = []
        previous_start_time = None  # 前一個詞的開始時間

        for line_idx, line in enumerate(timeline.lines):
            # 檢查空行
            if not line.words:
                errors.append(
                    ValidationError(
                        line_index=line_idx,
                        word_index=-1,
                        error_type='EMPTY_LINE',
                        message='歌詞行為空',
                    )
                )
                continue

            for word_idx, word in enumerate(line.words):
                # 檢查文字是否為空
                if not word.text:
                    errors.append(
                        ValidationError(
                            line_index=line_idx,
                            word_index=word_idx,
                            error_type='EMPTY_TEXT',
                            message='文字內容為空',
                        )
                    )

                # 檢查時間有效性
                if word.start_time is None or word.end_time is None:
                    errors.append(
                        ValidationError(
                            line_index=line_idx,
                            word_index=word_idx,
                            error_type='TIME_MISSING',
                            message='時間戳缺失',
                        )
                    )
                else:
                    if word.start_time < 0 or word.end_time < 0:
                        errors.append(
                            ValidationError(
                                line_index=line_idx,
                                word_index=word_idx,
                                error_type='TIME_NEGATIVE',
                                message='時間戳不可為負數',
                            )
                        )
                    if word.end_time <= word.start_time:
                        errors.append(
                            ValidationError(
                                line_index=line_idx,
                                word_index=word_idx,
                                error_type='TIME_RANGE',
                                message='結束時間必須大於開始時間',
                            )
                        )

                # 檢查時間順序（跨行全域遞增）
                if (
                    previous_start_time is not None
                    and word.start_time is not None
                    and word.start_time < previous_start_time
                ):
                    errors.append(
                        ValidationError(
                            line_index=line_idx,
                            word_index=word_idx,
                            error_type='TIME_ORDER',
                            message='時間戳倒序或重疊',
                        )
                    )
                if word.start_time is not None:
                    previous_start_time = word.start_time

                # 檢查漢字與假名對應
                if word.ruby_pair and word.text != word.ruby_pair.kanji:
                    errors.append(
                        ValidationError(
                            line_index=line_idx,
                            word_index=word_idx,
                            error_type='KANJI_RUBY_MISMATCH',
                            message='漢字與假名對應不一致',
                        )
                    )

        return len(errors) == 0, errors
