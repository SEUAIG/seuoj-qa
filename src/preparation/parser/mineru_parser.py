# -*- coding: utf-8 -*-
"""
MinerU Document Parser

Use MinerU API to convert PPT, PDF and other documents to Markdown format.

API Docs: https://mineru.net/
GitHub: https://github.com/opendatalab/MinerU
"""

import time
import requests
from pathlib import Path
from typing import Literal
from dataclasses import dataclass


@dataclass
class MinerUConfig:
    """MinerU API Configuration"""
    token: str = ""
    api_url: str = "https://mineru.net/api/v4/extract/task"
    batch_url_url: str = "https://mineru.net/api/v4/file-urls/batch"
    model_version: Literal["vlm", "ocr"] = "vlm"
    poll_interval: int = 2
    max_poll_time: int = 300


class MinerUParser:
    """MinerU Document Parser"""

    def __init__(
        self,
        token: str = None,
        output_dir: str = "data/preparation/parsed",
        config: MinerUConfig = None
    ):
        """
        Initialize parser

        Args:
            token: MinerU API token (load from config if not provided)
            output_dir: Output directory for parsed results
            config: Configuration object
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        if config:
            self.config = config
        else:
            self.config = MinerUConfig(token=token or self._load_token())

    def _load_token(self) -> str:
        """Load token from config file"""
        # Get project root (4 levels up from this file)
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / "config" / "base.yaml"
        if config_path.exists():
            import yaml
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
                return cfg.get("mineru", {}).get("token", "")
        return ""

    def parse_by_url(
        self,
        url: str,
        output_name: str = None,
        poll: bool = True
    ) -> dict:
        """
        Parse document by URL

        Args:
            url: Public accessible document URL
            output_name: Output filename (without extension)
            poll: Whether to poll for result

        Returns:
            API response data
        """
        if not self.config.token:
            raise ValueError("MinerU API token not configured")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.token}"
        }

        data = {
            "url": url,
            "model_version": self.config.model_version
        }

        response = requests.post(
            self.config.api_url,
            headers=headers,
            json=data
        )

        if response.status_code != 200:
            raise RuntimeError(f"MinerU API request failed: {response.status_code} - {response.text}")

        result = response.json()
        data = result.get("data", {})

        if poll:
            task_id = data.get("task_id")
            if task_id:
                data = self._poll_result(task_id)

        if output_name:
            self._save_result(data, output_name)

        return {
            "code": result.get("code"),
            "msg": result.get("msg"),
            "data": data
        }

    def parse_by_file(
        self,
        file_path: str,
        output_name: str = None,
        poll: bool = True
    ) -> dict:
        """
        Parse local file (two steps: get upload URL, then PUT upload)

        Args:
            file_path: Local file path
            output_name: Output filename
            poll: Whether to poll for result

        Returns:
            API response data
        """
        if not self.config.token:
            raise ValueError("MinerU API token not configured")

        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Step 1: Get upload URL
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.token}"
        }

        data_id = file_path.stem
        data = {
            "files": [
                {"name": file_path.name, "data_id": data_id}
            ],
            "model_version": self.config.model_version
        }

        print(f"Applying for upload URL: {file_path.name}")

        response = requests.post(
            self.config.batch_url_url,
            headers=headers,
            json=data
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to apply upload URL: {response.status_code} - {response.text}")

        result = response.json()
        if result.get("code") != 0:
            raise RuntimeError(f"Failed to apply upload URL: {result.get('msg', 'Unknown error')}")

        batch_data = result.get("data", {})
        batch_id = batch_data.get("batch_id")
        upload_urls = batch_data.get("file_urls", [])

        if not upload_urls:
            raise RuntimeError("No upload URL returned")

        upload_url = upload_urls[0]
        print(f"Got upload URL (batch_id: {batch_id})")

        # Step 2: PUT upload file
        print(f"Uploading file...")

        with open(file_path, "rb") as f:
            upload_response = requests.put(upload_url, data=f)

        if upload_response.status_code != 200:
            raise RuntimeError(f"File upload failed: {upload_response.status_code}")

        print(f"File uploaded successfully")

        response_data = {"data_id": data_id}

        if poll:
            response_data = self._poll_result(data_id)

        if output_name is None:
            output_name = file_path.stem

        if output_name:
            self._save_result(response_data, output_name)

        return {
            "code": 0,
            "msg": "success",
            "data": response_data
        }

    def _poll_result(self, task_id: str) -> dict:
        """
        Poll for task result

        Args:
            task_id: Task ID

        Returns:
            Task result data
        """
        status_url = f"https://mineru.net/api/v4/extract/task/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.config.token}"
        }

        start_time = time.time()

        while time.time() - start_time < self.config.max_poll_time:
            response = requests.get(status_url, headers=headers)

            if response.status_code != 200:
                print(f"DEBUG: Response: {response.text}")
                raise RuntimeError(f"Failed to query task status: {response.status_code}")

            result = response.json()
            # Debug: print full response on first try
            if time.time() - start_time < 5:
                print(f"DEBUG: API response: {result}")

            data = result.get("data", {})
            status = data.get("status")

            if status == "success":
                print(f"Task completed: {task_id}")
                return data
            elif status == "failed":
                raise RuntimeError(f"Task failed: {data.get('error', 'Unknown error')}")
            elif status in ("pending", "processing"):
                print(f"Processing... ({status})")
                time.sleep(self.config.poll_interval)
            else:
                print(f"Unknown status: {status}, full response: {result}")
                time.sleep(self.config.poll_interval)

        raise TimeoutError(f"Task timeout: {task_id}")

    def _save_result(self, data: dict, output_name: str) -> str:
        """
        Save parsing result

        Args:
            data: API response data
            output_name: Output filename

        Returns:
            Saved file path
        """
        markdown_content = data.get("content", "")
        output_path = self.output_dir / f"{output_name}.md"
        output_path.write_text(markdown_content, encoding="utf-8")

        json_output = self.output_dir / f"{output_name}_raw.json"
        import json
        json_output.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(f"Markdown saved: {output_path}")
        print(f"Raw data saved: {json_output}")

        return str(output_path)

    def get_task_status(self, task_id: str) -> dict:
        """
        Query task status

        Args:
            task_id: Task ID

        Returns:
            Task status info
        """
        status_url = f"https://mineru.net/api/v4/extract/task/{task_id}"
        headers = {
            "Authorization": f"Bearer {self.config.token}"
        }

        response = requests.get(status_url, headers=headers)
        response.raise_for_status()

        return response.json()

    @staticmethod
    def demo():
        """Demo usage"""
        parser = MinerUParser(token="your_token_here")

        result = parser.parse_by_url(
            url="https://cdn-mineru.openxlab.org.cn/demo/example.pdf",
            output_name="demo_output"
        )

        print("Parse result:")
        print(result["data"]["content"])


def parse_file(
    file_path: str,
    token: str = None,
    output_name: str = None,
    model_version: str = "vlm"
) -> dict:
    """
    Quick parse local file

    Args:
        file_path: Local file path
        token: MinerU API token
        output_name: Output filename
        model_version: Model version (vlm/ocr)

    Returns:
        API response data
    """
    config = MinerUConfig(token=token, model_version=model_version)
    parser = MinerUParser(config=config)
    return parser.parse_by_file(file_path, output_name)


if __name__ == "__main__":
    """
    Main function - hardcoded test PPT to Markdown conversion
    """
    PPT_FILE = "/home/guoziyang/AIgorithm_Agent/input/1.导言.ppt"
    OUTPUT_NAME = "1.导言"
    OUTPUT_DIR = "/home/guoziyang/AIgorithm_Agent/src/preparation/parser/tmp"

    print("=" * 60)
    print("MinerU PPT to Markdown Converter")
    print("=" * 60)
    print(f"Input file: {PPT_FILE}")
    print(f"Output name: {OUTPUT_NAME}")
    print("-" * 60)

    if not Path(PPT_FILE).exists():
        print(f"Error: File not found - {PPT_FILE}")
        exit(1)

    parser = MinerUParser(output_dir=OUTPUT_DIR)

    try:
        result = parser.parse_by_file(
            file_path=PPT_FILE,
            output_name=OUTPUT_NAME,
            poll=True
        )

        print("-" * 60)
        print("Parse completed!")
        print(f"Return code: {result.get('code')}")
        print(f"Message: {result.get('msg')}")

        content = result.get("data", {}).get("content", "")
        if content:
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"\nContent preview:\n{preview}")

    except Exception as e:
        print(f"Error: {e}")
        exit(1)
