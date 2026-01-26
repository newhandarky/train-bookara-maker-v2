"""
GUI 元件公開介面
"""

from .lrc_editor import LrcEditorDialog, LrcTimelineEditor
from .lrc_line_editor import LrcLineEditor
from .output_options_dialog import OutputOptionsDialog
from .ruby_edit_dialog import RubyEditDialog
from .lyrics_timing_panel import LyricsTimingPanel
from .preview_player import PreviewPlayer
from .color_group_panel import ColorGroupPanel
from .color_editor_dialog import ColorEditorDialog
from .timestamp_editor import TimeStampEditor

__all__ = [
    'LrcEditorDialog',
    'LrcTimelineEditor',
    'LrcLineEditor',
    'OutputOptionsDialog',
    'RubyEditDialog',
    'LyricsTimingPanel',
    'PreviewPlayer',
    'ColorGroupPanel',
    'ColorEditorDialog',
    'TimeStampEditor',
]
