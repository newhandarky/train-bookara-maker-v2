"""
音源分離（Demucs）
Phase 1.1.2: 影片上傳與音源分離

作用：
- 從影片讀取音訊
- 產出四軌 stems（vocal/drums/bass/other）
"""

import os
import logging
from typing import Dict, Tuple

import numpy as np

import config

try:
    import librosa
    import soundfile as sf
    import torch
    from demucs.pretrained import get_model
    from demucs.audio import convert_audio
    from demucs.apply import apply_model
except ImportError as e:
    raise ImportError(
        f"Required package not found: {e}. "
        f"Install with: pip install demucs librosa soundfile torch"
    )

logger = logging.getLogger(__name__)


class AudioSeparator:
    """音源分離器 - 產出音訊檔案"""

    def __init__(self, model_name: str = config.DEMUCS_MODEL):
        # 模型名稱
        self.model_name = model_name
        # Demucs 模型實例
        self.model = None
        # 運算裝置（CPU/GPU）
        self.device = None
        logger.info(f"Initializing AudioSeparator with model: {model_name}")

    def _load_model(self):
        """延遲載入 Demucs 模型"""
        if self.model is not None:
            return

        logger.info(f"Loading Demucs model: {self.model_name}")
        try:
            # 裝置選擇
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"Using device: {self.device}")

            # 載入模型
            self.model = get_model(self.model_name)
            self.model = self.model.to(self.device)
            self.model.eval()

            logger.info(f"Model loaded successfully on {self.device}")
        except Exception as exc:
            logger.error(f"Failed to load model: {exc}")
            raise

    def _load_audio(self, video_path: str) -> Tuple[np.ndarray, int]:
        """從影片讀取音訊（保持原始取樣率）"""
        # 讀取音訊（mono=False 以保留聲道資訊）
        audio, sample_rate = librosa.load(video_path, sr=None, mono=False)
        # 單聲道時轉為 (1, samples)
        if audio.ndim == 1:
            audio = np.expand_dims(audio, axis=0)
        return audio, sample_rate

    def _map_source_name(self, source: str) -> str:
        """統一 stems 名稱（vocals -> vocal）"""
        if source == 'vocals':
            return 'vocal'
        if source == 'vocal':
            return 'vocal'
        return source

    def _separate_audio(self, audio: np.ndarray, sample_rate: int) -> Tuple[Dict[str, np.ndarray], int]:
        """分離音源（使用已讀取音訊）"""
        self._load_model()

        # 轉為 torch tensor（batch=1）
        audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)  # 音訊張量

        # Demucs 目標參數
        target_sr = getattr(self.model, 'samplerate', 44100)  # 目標取樣率
        target_channels = getattr(self.model, 'audio_channels', 2)  # 目標聲道數

        # 轉為 Demucs 標準格式
        audio_tensor = convert_audio(audio_tensor, sample_rate, target_sr, target_channels)
        audio_tensor = audio_tensor.to(self.device)

        # 執行分離
        logger.info("Starting separation...")
        with torch.no_grad():
            stems_tensor = apply_model(self.model, audio_tensor)  # 分離結果張量

        # 轉為 numpy
        stems: Dict[str, np.ndarray] = {}  # stems 音源字典
        sources = list(getattr(self.model, 'sources', []))  # stems 名稱列表
        for index, source in enumerate(sources):
            # 單一 stem：形狀 (channels, samples)
            stem_audio = stems_tensor[0, index].cpu().numpy()  # 單一 stem 音訊
            stem_key = self._map_source_name(source)  # stems key
            stems[stem_key] = stem_audio

        logger.info("Separation complete: stems=%s", list(stems.keys()))
        return stems, target_sr

    def separate(self, video_path: str) -> Tuple[Dict[str, np.ndarray], int]:
        """
        分離音源並回傳 stems

        Args:
            video_path: 影片檔案路徑

        Returns:
            (stems, sample_rate)
        """
        # 檢查檔案存在
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # 讀取音訊
        audio, sample_rate = self._load_audio(video_path)  # 音訊資料與取樣率
        logger.info(
            "Audio loaded: shape=%s, sr=%s, duration=%.2fs",
            audio.shape,
            sample_rate,
            audio.shape[-1] / sample_rate,
        )
        return self._separate_audio(audio, sample_rate)

    def _save_audio(self, audio: np.ndarray, sample_rate: int, output_path: str):
        """保存音訊檔案"""
        # 轉換為 (samples, channels)
        audio_to_save = audio
        if audio_to_save.ndim == 2:
            audio_to_save = audio_to_save.T
        sf.write(output_path, audio_to_save, sample_rate)

    def save_stems(self, stems: Dict[str, np.ndarray], sample_rate: int, output_dir: str) -> Dict[str, str]:
        """
        保存 stems 為 WAV 檔

        Args:
            stems: 音源字典
            sample_rate: 取樣率
            output_dir: 輸出資料夾

        Returns:
            stems_paths: 儲存路徑字典
        """
        # 建立輸出目錄
        os.makedirs(output_dir, exist_ok=True)

        stems_paths: Dict[str, str] = {}  # stems 路徑字典
        for stem_name, stem_audio in stems.items():  # stems 逐項處理
            # 儲存路徑
            output_path = os.path.join(output_dir, f"{stem_name}.wav")  # 輸出路徑

            # 寫入檔案
            self._save_audio(stem_audio, sample_rate, output_path)
            stems_paths[stem_name] = output_path

            logger.info("Stem saved: %s", output_path)

        return stems_paths

    def process_video(self, video_path: str, output_dir: str, output_options: dict) -> Dict[str, str]:
        """
        完整流程：分離並保存

        Args:
            video_path: 影片路徑
            output_dir: 輸出資料夾

        Returns:
            stems_paths: 儲存路徑字典
        """
        # 建立輸出資料夾
        os.makedirs(output_dir, exist_ok=True)

        # 預設輸出選項
        if not output_options:
            output_options = {'original': True, 'music': True}  # 預設輸出

        # 讀取原始音訊
        original_audio, original_sr = self._load_audio(video_path)  # 原始音訊

        # 先處理 original.wav
        output_paths: Dict[str, str] = {}  # 輸出路徑
        if output_options.get('original'):
            original_path = os.path.join(output_dir, 'original.wav')
            self._save_audio(original_audio, original_sr, original_path)
            output_paths['original'] = original_path

        # 判斷是否需要分離
        need_separation = any(
            output_options.get(key)
            for key in ['music', 'vocal', 'drums', 'bass', 'other']
        )
        if not need_separation:
            return output_paths

        # 分離 stems
        stems, sample_rate = self._separate_audio(original_audio, original_sr)

        # 儲存選擇的 stems
        stem_keys = ['vocal', 'drums', 'bass', 'other']
        for key in stem_keys:
            if output_options.get(key) and key in stems:
                output_path = os.path.join(output_dir, f"{key}.wav")
                self._save_audio(stems[key], sample_rate, output_path)
                output_paths[key] = output_path

        # 合成 music.wav
        if output_options.get('music'):
            music_audio = None  # 音樂合成音訊
            for key in ['drums', 'bass', 'other']:
                if key in stems:
                    if music_audio is None:
                        music_audio = stems[key].copy()
                    else:
                        music_audio = music_audio + stems[key]
            if music_audio is not None:
                # 正規化防止爆音
                max_val = np.max(np.abs(music_audio))
                if max_val > 1.0:
                    music_audio = music_audio / max_val * 0.95
                music_path = os.path.join(output_dir, 'music.wav')
                self._save_audio(music_audio, sample_rate, music_path)
                output_paths['music'] = music_path

        return output_paths


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    separator = AudioSeparator()
    # 測試用：separator.process_video("input.mp4", "output/stems")
