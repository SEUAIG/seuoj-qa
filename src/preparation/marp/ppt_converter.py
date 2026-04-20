"""
PPT 转换器

将 Marp Markdown 转换为 PPT 或 PDF 格式。
"""

import subprocess
import os
from pathlib import Path
from typing import Optional


class PPTConverter:
    """PPT 转换器"""

    def __init__(self, output_dir: str = "data/preparation/slides"):
        """
        初始化转换器

        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def convert_to_pptx(
        self,
        marp_path: str,
        output_name: Optional[str] = None
    ) -> str:
        """
        将 Marp Markdown 转换为 PPTX

        Args:
            marp_path: Marp 文件路径
            output_name: 输出文件名（不含扩展名）

        Returns:
            生成的 PPTX 文件路径
        """
        marp_path = Path(marp_path)
        if not marp_path.exists():
            raise FileNotFoundError(f"Marp 文件不存在: {marp_path}")

        if output_name is None:
            output_name = marp_path.stem

        output_path = self.output_dir / f"{output_name}.pptx"

        # 使用 Marp CLI 转换
        try:
            subprocess.run(
                [
                    "marp",
                    str(marp_path),
                    "--pptx",
                    "-o", str(output_path)
                ],
                check=True,
                capture_output=True
            )
            return str(output_path)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Marp 转换失败: {e.stderr.decode()}") from e
        except FileNotFoundError:
            # Marp CLI 不可用时的处理
            return self._mock_convert(marp_path, output_path, ".pptx")

    def convert_to_pdf(
        self,
        marp_path: str,
        output_name: Optional[str] = None
    ) -> str:
        """
        将 Marp Markdown 转换为 PDF

        Args:
            marp_path: Marp 文件路径
            output_name: 输出文件名（不含扩展名）

        Returns:
            生成的 PDF 文件路径
        """
        marp_path = Path(marp_path)
        if not marp_path.exists():
            raise FileNotFoundError(f"Marp 文件不存在: {marp_path}")

        if output_name is None:
            output_name = marp_path.stem

        output_path = self.output_dir / f"{output_name}.pdf"

        try:
            subprocess.run(
                [
                    "marp",
                    str(marp_path),
                    "--pdf",
                    "-o", str(output_path)
                ],
                check=True,
                capture_output=True
            )
            return str(output_path)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Marp PDF 转换失败: {e.stderr.decode()}") from e
        except FileNotFoundError:
            return self._mock_convert(marp_path, output_path, ".pdf")

    def _mock_convert(self, marp_path: Path, output_path: Path, ext: str) -> str:
        """
        Mock 转换（开发测试用）

        Args:
            marp_path: Marp 文件路径
            output_path: 输出路径
            ext: 扩展名

        Returns:
            输出路径（只是复制文件）
        """
        # 创建一个说明文件
        content = f"""这是一个模拟的 {ext} 文件。

原始 Marp 文件: {marp_path.name}

Marp CLI 未安装，无法进行实际转换。
请安装 Marp CLI: npm install -g @marp-team/marp-cli
"""
        output_path.with_suffix(ext).write_text(content, encoding="utf-8")
        return str(output_path.with_suffix(ext))

    def is_marp_available(self) -> bool:
        """
        检查 Marp CLI 是否可用

        Returns:
            是否可用
        """
        try:
            result = subprocess.run(
                ["marp", "--version"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
