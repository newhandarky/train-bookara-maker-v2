"""
Audio separator using Demucs model
Phase 1.2: 去除人聲伴奏提取 - 簡化版

策略：
1. 分離音訊為 vocal 軌
2. 計算 accompaniment = original_audio - vocal
3. 直接輸出單個伴奏 WAV

優點：
- 時間長度正確（等於原始音訊）
- 音樂完整（all frequencies preserved）
- 人聲去除乾淨
- 簡單穩定
"""

import os
import logging
from typing import Tuple

import numpy as np

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
    """音源分離 - 提取伴奏軌"""

    def __init__(self, model_name: str = 'htdemucs'):
        """
        初始化
        
        Args:
            model_name: Demucs 模型名稱
        """
        self.model_name = model_name
        self.model = None
        self.device = None
        logger.info(f"Initializing AudioSeparator with model: {model_name}")

    def _load_model(self):
        """延遲加載模型"""
        if self.model is not None:
            return
        
        logger.info(f"Loading Demucs model: {self.model_name}")
        try:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"Using device: {self.device}")
            
            self.model = get_model(self.model_name)
            self.model = self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"Model loaded successfully on {self.device}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def separate(self, video_path: str) -> Tuple[np.ndarray, int]:
        """
        分離音訊並提取伴奏軌
        
        策略：original_audio - vocal = accompaniment
        
        Args:
            video_path: MP4 文件路徑
        
        Returns:
            (伴奏音訊, 採樣率)
        """
        self._load_model()
        
        # 提取音訊 (單聲道)
        logger.info(f"Extracting audio from: {video_path}")
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        try:
            # 讀取原始音訊 (保留所有資訊)
            audio, sr = librosa.load(video_path, sr=None, mono=True)
            original_audio = audio.copy()
            
            logger.info(f"Original audio: shape={audio.shape}, sr={sr}, duration={len(audio)/sr:.2f}s")
            
            # 轉為 torch tensor
            audio_tensor = torch.from_numpy(audio).float()
            audio_tensor = audio_tensor.unsqueeze(0).unsqueeze(0)  # (1, 1, samples)
            
            logger.info(f"Tensor shape before convert: {audio_tensor.shape}")
            
            # 轉為 Demucs 標準格式 (16kHz, 2 channel)
            audio_tensor = convert_audio(
                audio_tensor,
                sr,              # 原始採樣率
                16000,           # Demucs 標準採樣率
                2                # Demucs 標準通道數
            )
            
            audio_tensor = audio_tensor.to(self.device)
            
            logger.info(f"Tensor shape after convert: {audio_tensor.shape}")
            
            # 使用 Demucs 分離
            logger.info("Starting vocal separation...")
            with torch.no_grad():
                # stems: (batch=1, stems=4, channels=2, samples)
                # stems[0, 0] = vocal channel
                stems = apply_model(self.model, audio_tensor)
            
            # 提取 vocal 軌 (index 0)
            vocal_stereo = stems[0, 0]  # (2, samples) @ 16kHz
            
            # 取左聲道或平均
            if vocal_stereo.shape[0] == 2:
                vocal = vocal_stereo.mean(dim=0)  # 立體聲轉單聲道
            else:
                vocal = vocal_stereo.squeeze()
            
            vocal = vocal.cpu().detach().numpy()
            
            logger.info(f"Vocal extracted: shape={vocal.shape} @ 16kHz")
            
            # 重新採樣到原始採樣率
            vocal = librosa.resample(
                vocal,
                orig_sr=16000,
                target_sr=sr
            )
            
            logger.info(f"Vocal resampled: shape={vocal.shape} @ {sr}Hz")
            
            # 確保長度對齊
            min_len = min(len(original_audio), len(vocal))
            original_audio = original_audio[:min_len]
            vocal = vocal[:min_len]
            
            # 計算伴奏 = 原始 - 人聲
            # 乘以 0.95 是因為 vocal 可能會過估，預留一點空間
            accompaniment = original_audio - vocal * 0.95
            
            # 正規化 (防止爆音)
            max_val = np.max(np.abs(accompaniment))
            if max_val > 1.0:
                accompaniment = accompaniment / max_val * 0.95
            
            logger.info(f"Accompaniment: shape={accompaniment.shape}, max={np.max(np.abs(accompaniment)):.4f}")
            logger.info(f"Duration: {len(accompaniment)/sr:.2f}s (vs original {len(original_audio)/sr:.2f}s)")
            
            return accompaniment, sr
        
        except Exception as e:
            logger.error(f"Separation failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def save_accompaniment(self, accompaniment: np.ndarray, sr: int, output_path: str):
        """
        保存伴奏為 WAV 檔
        
        Args:
            accompaniment: 伴奏音訊陣列
            sr: 採樣率
            output_path: 輸出路徑 (自動加上 .wav 副檔名)
        """
        # 確保有副檔名
        if not output_path.endswith('.wav'):
            output_path = output_path + '.wav'
            logger.info(f"Auto-appending .wav extension: {output_path}")
        
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")
        
        logger.info(f"Saving accompaniment to: {output_path}")
        
        try:
            # 驗證數據
            if np.isnan(accompaniment).any() or np.isinf(accompaniment).any():
                logger.warning("Found NaN/Inf values in audio, replacing with zeros")
                accompaniment = np.nan_to_num(accompaniment, nan=0.0, posinf=1.0, neginf=-1.0)
            
            # 轉為 int16
            accompaniment_int16 = np.clip(accompaniment * 32767, -32768, 32767).astype(np.int16)
            
            logger.info(f"Converting to int16: min={accompaniment_int16.min()}, max={accompaniment_int16.max()}")
            
            # 保存
            sf.write(output_path, accompaniment_int16, sr)
            
            logger.info(f"Saved successfully: {output_path}")
            file_size_mb = os.path.getsize(output_path) / 1024 / 1024
            logger.info(f"File size: {file_size_mb:.2f} MB")
            
        except Exception as e:
            logger.error(f"Failed to save: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise

    def process_video(self, video_path: str, output_path: str) -> str:
        """
        完整流程：提取 → 分離 → 保存
        
        Args:
            video_path: 輸入 MP4 路徑
            output_path: 輸出路徑 (自動加上 .wav 副檔名)
        
        Returns:
            輸出檔案路徑
        """
        logger.info(f"Processing video: {video_path}")
        logger.info(f"Output path (before auto-extension): {output_path}")
        
        # 分離
        accompaniment, sr = self.separate(video_path)
        
        # 保存
        self.save_accompaniment(accompaniment, sr, output_path)
        
        # 返回最終路徑 (含副檔名)
        final_path = output_path if output_path.endswith('.wav') else output_path + '.wav'
        logger.info(f"Processing complete. Output: {final_path}")
        return final_path


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    separator = AudioSeparator()
    # result = separator.process_video("input.mp4", "output/accompaniment")
    # print(result)