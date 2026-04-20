from typing import Any, Dict
import requests


def code_runner(code: str, stdin: str = "", language: str = "Python3_12") -> Dict[str, Any]:
    """
    调用本地代码运行服务，并将结果返回。

    参数:
        code: 要执行的代码
        stdin: 传给程序的标准输入
        language: 语言类型，例如 Python3_12 / Cpp17 / Java17

    返回:
        成功时:
        {
            "success": True,
            "result": {
                ... 服务原始返回 JSON ...
            }
        }

        失败时:
        {
            "success": False,
            "error": "错误信息"
        }
    """
    url = "http://127.0.0.1:8090/api/run"
    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "language": language,
        "code": code,
        "stdin": stdin
    }

    try:
        response = requests.post(
            url=url,
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()

        result = response.json()

        return {
            "success": True,
            "result": result
        }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "请求超时"
        }
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "error": "连接失败，请确认服务是否已启动，且 127.0.0.1:8090 可访问"
        }
    except requests.exceptions.HTTPError as e:
        return {
            "success": False,
            "error": f"HTTP错误: {e}"
        }
    except ValueError:
        return {
            "success": False,
            "error": "返回结果不是合法 JSON"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"请求失败: {e}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"未知错误: {e}"
        }