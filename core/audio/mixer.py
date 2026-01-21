"""
音訊混音工具
"""

from typing import Dict, Optional
import subprocess


class AudioMixer:
    """多軌混音"""

    def mix_stems(
        self,
        stems: Dict[str, str],
        volumes: Optional[Dict[str, float]] = None,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """使用 FFmpeg 混音並輸出檔案"""
        if not stems:
            return None

        if volumes is None:
            volumes = {name: 1.0 for name in stems.keys()}

        input_args = []
        filter_parts = []
        mix_inputs = []
        for index, (stem_name, stem_path) in enumerate(stems.items()):
            input_args.extend(['-i', stem_path])
            volume = volumes.get(stem_name, 1.0)
            filter_parts.append(f"[{index}:a]volume={volume}[a{index}]")
            mix_inputs.append(f"[a{index}]")

        filter_graph = ";".join(filter_parts) + f";{''.join(mix_inputs)}amix=inputs={len(stems)}[mix]"
        if not output_path:
            return None

        cmd = [
            'ffmpeg',
            *input_args,
            '-filter_complex', filter_graph,
            '-map', '[mix]',
            '-c:a', 'aac',
            '-y',
            output_path,
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return None
        except Exception:
            return None

        return output_path
