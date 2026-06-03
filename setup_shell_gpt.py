#!/usr/bin/env python3
"""
Shell-GPT 自动安装和配置脚本
为Linux新手用户提供一键安装和配置Shell-GPT的便捷工具

@Author: 卖萌哥
@Version: 1.12.1
@Date: 2026-06-03
@Description: 支持自动安装requests依赖、模型切换、API密钥设置等功能
@Update: v1.12.1 - 新增 deepseek-ai/DeepSeek-V4-Pro，并设置为默认优先模型
         v1.12.0 - 新增 _ensure_local_bin_in_path()：main() 启动时自动检测
                  ~/.local/bin 是否在 PATH 里，缺则幂等追加 export 到 ~/.bashrc / ~/.zshrc，
                  解决 pip --user 装 CLI entry script 后新 shell command not found 的痛点。
                  学生第一次跑用 export PATH 临时救场，本函数永久持久化，第二次新 shell 直接短命令。
         v1.11.1 - 修复安装后读取 shell-gpt 版本时误触发交互式 API key 输入：
                  不再通过 `import sgpt` 获取版本号，改用 `python -m pip show shell-gpt`；
                  fallback 补丁定位也改为读取安装元数据，避免导入 sgpt 包产生副作用
         v1.11.0 - 修复 portable Python 镜像下载和模型探测稳定性：
                  1) tarball URL 不再把文件名里的 + 编成 %2B；
                     国内 github-release 镜像的反代路径对这两种写法不总是等价，
                     编码后可能返回 200 HTML 错误页而不是真正的 .tar.gz
                  2) 镜像测速、目录读取、tarball 下载优先走系统 curl（学生环境已验证可用），
                     curl 不存在或失败时再退回 urllib，实现无新依赖兜底
                  3) 模型真实可用性探测改成限流友好：并发从 8 降到 3，
                     对 429/5xx/网络异常做指数退避重试，并打印 HTTP 失败原因
         v1.10.0 - portable Python 路径稳定性大幅提升：
                  1) 所有 HTTP 请求改用完整浏览器 UA + Accept-Encoding: identity，
                     避开 USTC 等镜像对 Python-urllib/简短 UA 的 403 反爬，
                     同时阻止服务端对 .tar.gz 文件再套一层传输 gzip 编码
                  2) 下载完成后用 magic byte (1f 8b) 验证是不是真 gzip，
                     反爬返回的 HTML challenge 现在能识破并自动切下一个镜像
                  3) github-release 镜像列表不再过滤掉测速失败的项，
                     全保留并按延迟排序，让下载阶段能再试一次（HEAD 失败不等于 GET 失败）
                  4) 从 PIP_MIRRORS 移除中科大（实测同步不稳）
         v1.9.0  - 新增 Portable Python 3.12 路径：直接从国内大学镜像（USTC/NJU/TUNA/SJTU/BFSU/HFUT）
                  下载 python-build-standalone tarball 解压到 ~/.local/share/sgpt-portable-python/，
                  在其中 pip install shell-gpt 1.5.x（不存在 1.4.x 的流尾 IndexError bug），
                  写包装脚本 ~/.local/bin/sgpt。系统 Python 是 3.8/3.9 也能用上最新 shell-gpt。
                  Fallback：portable 失败时退回系统 pip + 1.4.x + 自动 patch handler.py。
                  github-release 镜像并发测速取最快，不绑死单一镜像。
                  卸载已覆盖 portable python 目录和包装脚本。
         v1.8.0 - 新增完全卸载选项（菜单 5 / --uninstall）：pip 卸 shell-gpt 包 +
                  删 ~/.config/shell_gpt + 删 /tmp 缓存目录 + 删 ~/.cache/shell_gpt
                  PyPI 镜像清单扩充：撤掉国内不通的 PyPI官方 和 同步不稳的 PKU，
                  新增 华为云 / 网易 / 北外 / 南大 ；默认镜像改阿里云
         v1.7.0 - pip 安装过程 spinner 静默化：捕获所有 stdout/stderr，只显示转动图标 + 计时
                  多镜像 failover：当前镜像挂了自动切下一个，告别 TUNA 抽风导致整条挂掉
                  pip 增加 --timeout 30 --retries 3 扛短时网络抖动
                  DISABLE_STREAMING 默认改 true：绕开 shell-gpt 1.4.x 对 SiliconFlow
                  最终 usage chunk (choices=[]) 的 IndexError bug
         v1.6.0 - 尝试 uv 装独立 Python 3.12 → 放弃：uv 拉 Python 必须走 GitHub releases，
                  国内反代镜像（TUNA/BFSU/USTC/kkgithub/ghproxy）实测都不可靠或不存在
         v1.5.0 - API_BASE_URL 修正为 https://api.siliconflow.cn/v1（之前少 /v1 会导致 sgpt 404）
                  配置文件写入后 chmod 600，避免多用户机上 API key 被旁人读取
                  OPENAI_USE_FUNCTIONS 根据所选模型动态：R1/4.5V 等不支持 tools 的模型置 false
                  抽出 update_config_keys() 统一改 .sgptrc，create_config_file 与 switch_model 共用
                  同 session 内按 api_key 缓存已验证的可用模型列表，避免重复 ping
                  pip 安装 shell-gpt 时直通输出，消除"卡住"假象
         v1.4.0 - 真实可用性检测：仅靠 /v1/models 的目录无法反映 key 实际能调用哪些模型，
                  现在通过并发 max_tokens=1 的 chat completions 探测，保留真正 200 的模型
                  显式白名单 ALLOWED_MODELS 替代厂商关键字匹配（共 10 个模型）
                  默认模型改为 deepseek-ai/DeepSeek-V4-Flash（SF 默认即非思考模式）
         v1.3.0 - 代码重构优化：缓存镜像检测结果、合并API请求函数、简化验证流程
         v1.2.0 - 新增pip镜像源速度检测功能，自动选择最快镜像安装
         v1.1.0 - 新增API密钥输入时的实时星号显示（输入时显示*，完成后显示首尾马赛克）
                  新增模型选择时的主动返回功能（输入0/back/cancel返回主菜单）
"""

import os
import sys
import shutil
import threading
import itertools
import subprocess
import argparse
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple, Dict

# pip 镜像源列表（拿掉 PyPI 官方、PKU、中科大：前者国内基本不通；PKU/USTC 实测同步不稳）
PIP_MIRRORS: Dict[str, str] = {
    "阿里云":   "https://mirrors.aliyun.com/pypi/simple",
    "腾讯云":   "https://mirrors.cloud.tencent.com/pypi/simple",
    "华为云":   "https://repo.huaweicloud.com/repository/pypi/simple",
    "网易":     "https://mirrors.163.com/pypi/simple",
    "北外BFSU": "https://mirrors.bfsu.edu.cn/pypi/web/simple",
    "南京大学": "https://mirrors.nju.edu.cn/pypi/web/simple",
    "清华大学": "https://pypi.tuna.tsinghua.edu.cn/simple",
}

# 默认镜像（当检测失败时使用）—— 选阿里云，独立 CDN 不依赖 TUNA
DEFAULT_PIP_MIRROR = ("阿里云", "https://mirrors.aliyun.com/pypi/simple")

# 缓存最快镜像结果，避免重复检测
_cached_fastest_mirror: Optional[Tuple[str, str]] = None


def test_pip_mirror_speed(name: str, url: str, timeout: int = 5) -> Tuple[str, str, float]:
    """
    测试单个pip镜像源的响应速度

    Args:
        name: 镜像源名称
        url: 镜像源URL
        timeout: 超时时间（秒）

    Returns:
        (名称, URL, 响应时间)，失败时响应时间为 float('inf')
    """
    try:
        start_time = time.time()
        req = urllib.request.Request(url, method='HEAD')
        req.add_header('User-Agent', 'pip/24.0')
        with urllib.request.urlopen(req, timeout=timeout) as response:
            elapsed = time.time() - start_time
            return (name, url, elapsed)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, Exception):
        return (name, url, float('inf'))


def get_pip_mirrors_sorted(show_progress: bool = False) -> List[Tuple[str, str]]:
    """返回按响应速度升序排列的可用镜像列表 [(name, url), ...]。"""
    results: List[Tuple[str, str, float]] = []
    with ThreadPoolExecutor(max_workers=len(PIP_MIRRORS)) as executor:
        futures = {
            executor.submit(test_pip_mirror_speed, name, url): name
            for name, url in PIP_MIRRORS.items()
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda x: x[2])
    return [(name, url) for name, url, elapsed in results if elapsed != float('inf')]


def find_fastest_pip_mirror(show_progress: bool = True, use_cache: bool = True) -> Tuple[str, str]:
    """
    并发测试所有pip镜像源，返回最快的一个

    Args:
        show_progress: 是否显示检测进度
        use_cache: 是否使用缓存结果（默认True）

    Returns:
        (镜像名称, 镜像URL)
    """
    global _cached_fastest_mirror

    # 如果有缓存且允许使用缓存，直接返回
    if use_cache and _cached_fastest_mirror is not None:
        if show_progress:
            print(f"✨ 使用已检测的最快镜像: {_cached_fastest_mirror[0]}")
        return _cached_fastest_mirror

    if show_progress:
        print("🔍 正在检测pip镜像源速度...")

    results: List[Tuple[str, str, float]] = []

    with ThreadPoolExecutor(max_workers=len(PIP_MIRRORS)) as executor:
        futures = {
            executor.submit(test_pip_mirror_speed, name, url): name
            for name, url in PIP_MIRRORS.items()
        }

        for future in as_completed(futures):
            name, url, elapsed = future.result()
            results.append((name, url, elapsed))

            if show_progress:
                if elapsed == float('inf'):
                    print(f"  ❌ {name}: 连接失败")
                else:
                    print(f"  ✅ {name}: {elapsed*1000:.0f}ms")

    # 按响应时间排序
    results.sort(key=lambda x: x[2])

    if show_progress:
        print("\n📊 镜像源速度排名:")
        for i, (name, url, elapsed) in enumerate(results, 1):
            if elapsed == float('inf'):
                print(f"  {i}. {name}: 不可用")
            else:
                marker = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
                print(f"  {marker} {i}. {name}: {elapsed*1000:.0f}ms")

    # 返回最快的可用镜像
    for name, url, elapsed in results:
        if elapsed != float('inf'):
            if show_progress:
                print(f"\n✨ 已选择最快镜像: {name}")
            _cached_fastest_mirror = (name, url)
            return _cached_fastest_mirror

    # 所有镜像都不可用，返回默认值
    if show_progress:
        print(f"\n⚠️  所有镜像源都不可用，使用默认镜像: {DEFAULT_PIP_MIRROR[0]}")
    _cached_fastest_mirror = DEFAULT_PIP_MIRROR
    return _cached_fastest_mirror

# 尝试导入requests，如果失败则自动安装
try:
    import requests
except ImportError:
    print("📦 检测到缺少requests模块，正在自动安装...")
    try:
        # 检测最快的pip镜像源
        mirror_name, mirror_url = find_fastest_pip_mirror(show_progress=True)
        print(f"📦 使用 {mirror_name} 镜像安装 requests...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "-i", mirror_url,
            "--trusted-host", mirror_url.split("//")[1].split("/")[0],
            "requests"
        ])
        import requests
        print("✅ requests模块安装成功!")
    except Exception as e:
        print(f"❌ 无法自动安装requests模块: {e}")
        print("请手动运行: pip install requests")
        sys.exit(1)


def secure_input_with_stars(prompt: str = "请输入: ") -> str:
    """
    安全输入函数：输入时显示星号*
    支持退格键删除
    """
    import termios
    import tty

    print(prompt, end='', flush=True)

    # 获取终端文件描述符
    fd = sys.stdin.fileno()
    # 保存原始终端设置
    old_settings = termios.tcgetattr(fd)

    password = []

    try:
        # 设置终端为原始模式（关闭回显）
        tty.setraw(fd)

        while True:
            # 读取一个字符
            char = sys.stdin.read(1)

            # 处理回车键（Enter）
            if char in ('\r', '\n'):
                sys.stdout.write('\n')
                sys.stdout.flush()
                break

            # 处理退格键（Backspace/Delete）
            elif char in ('\x7f', '\x08'):
                if password:
                    password.pop()
                    # 退格：\b 移动光标，空格覆盖星号，再 \b 回到位置
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()

            # 处理 Ctrl+C
            elif char == '\x03':
                sys.stdout.write('\n')
                sys.stdout.flush()
                raise KeyboardInterrupt

            # 处理普通字符
            elif char >= ' ' and char <= '~':
                password.append(char)
                sys.stdout.write('*')
                sys.stdout.flush()

    finally:
        # 恢复终端设置
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    return ''.join(password)


def mask_api_key(api_key: str) -> str:
    """
    将API密钥进行马赛克处理，显示前5位和后4位，中间用***代替
    例如: sk-abcdefghijklmnopqrstuvwxyz123456 -> sk-ab***3456
    """
    if len(api_key) <= 9:
        # 如果密钥太短，只显示前3位
        return api_key[:3] + "***"

    # 显示前5位 + *** + 后4位
    return api_key[:5] + "***" + api_key[-4:]


def get_api_key_from_config() -> Optional[str]:
    """从配置文件读取API密钥"""
    home_dir = Path.home()
    config_file = home_dir / '.config' / 'shell_gpt' / '.sgptrc'

    if not config_file.exists():
        return None

    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('OPENAI_API_KEY='):
                    return line.split('=', 1)[1]
    except Exception:
        return None

    return None


def get_api_key(provided_key: str = None) -> Optional[str]:
    """获取API密钥，优先级：命令行参数 > 配置文件"""
    # 1. 优先使用命令行提供的密钥
    if provided_key:
        return provided_key

    # 2. 从配置文件读取
    return get_api_key_from_config()


def test_api_connection(api_key: str, return_models: bool = False):
    """
    测试API连接是否正常，可选返回模型列表

    Args:
        api_key: API密钥
        return_models: 如果为True，成功时返回模型列表；否则返回True/False

    Returns:
        return_models=False: bool (成功/失败)
        return_models=True: List[str] (模型列表，失败返回空列表)
    """
    url = "https://api.siliconflow.cn/v1/models?sub_type=chat"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        if return_models:
            data = response.json()
            return [model['id'] for model in data.get('data', [])]
        return True
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else None
        if status_code == 401:
            print("❌ API密钥无效（认证失败）")
            print("💡 请检查: 密钥是否完整、有无多余空格、是否已过期")
            print("📋 正确格式: sk-xxxxxxxxxxxxxxxxxxxxxxxx")
            print("🔗 获取密钥: https://cloud.siliconflow.cn/i/pnTWTpiB")
        elif status_code == 403:
            print("❌ API密钥权限不足（403）")
            print("💡 请检查账户额度或权限")
        elif status_code == 429:
            print("❌ 请求过于频繁（429 限流），请稍后再试")
        elif status_code is not None:
            print(f"❌ API请求失败（HTTP {status_code}）")
        else:
            print("❌ API请求失败（无法获取响应）")
        return [] if return_models else False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到SiliconFlow服务器")
        print("💡 请检查: 网络连接、防火墙设置")
        print("🔧 排查: ping api.siliconflow.cn 或浏览器访问 cloud.siliconflow.cn")
        return [] if return_models else False
    except requests.exceptions.Timeout:
        print("❌ 连接超时，请稍后重试")
        return [] if return_models else False
    except Exception as e:
        print(f"❌ 未知错误: {e}")
        return [] if return_models else False


_TRANSIENT_MODEL_HTTP_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def _short_response_error(response) -> str:
    """Return a compact, non-sensitive reason for a failed model probe."""
    reason = f"HTTP {response.status_code}"
    try:
        data = response.json()
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict):
            message = err.get("message") or err.get("type") or err.get("code")
        else:
            message = data.get("message") if isinstance(data, dict) else None
        if message:
            message = str(message).replace("\n", " ").strip()
            return f"{reason}: {message[:100]}"
    except Exception:
        pass
    return reason


def verify_model_availability_with_reason(
    api_key: str,
    model: str,
    timeout: int = 20,
    attempts: int = 3,
) -> Tuple[bool, str]:
    """
    通过最小化的 chat completion 请求探测模型是否真正可调用。
    /v1/models 只是目录，不代表当前 key 有权限或额度，此函数才是真实可用性。
    对限流/服务端抖动做少量重试，避免并发探测时把临时 429/5xx 误判成模型不可用。
    """
    url = "https://api.siliconflow.cn/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
        "stream": False,
    }
    last_reason = "unknown"
    for attempt in range(attempts):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code == 200:
                return True, "ok"
            last_reason = _short_response_error(response)
            if response.status_code not in _TRANSIENT_MODEL_HTTP_STATUS:
                return False, last_reason
        except requests.exceptions.Timeout:
            last_reason = "timeout"
        except requests.exceptions.ConnectionError:
            last_reason = "connection error"
        except requests.RequestException as e:
            last_reason = e.__class__.__name__

        if attempt < attempts - 1:
            time.sleep(0.8 * (2 ** attempt))
    return False, last_reason


def verify_model_availability(api_key: str, model: str, timeout: int = 20) -> bool:
    """Backward-compatible boolean wrapper around the detailed probe."""
    ok, _ = verify_model_availability_with_reason(api_key, model, timeout=timeout)
    return ok


def verify_models_in_parallel(
    api_key: str,
    models: List[str],
    show_progress: bool = True,
    max_workers: int = 3,
) -> List[str]:
    """
    并发探测模型可用性，返回真正可调用的子集（保持输入顺序）。
    """
    if not models:
        return []

    if show_progress:
        print(f"🔬 正在验证 {len(models)} 个模型的真实可用性（限流友好并发，每个仅消耗1 token）...")

    results: Dict[str, bool] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(models))) as executor:
        futures = {
            executor.submit(verify_model_availability_with_reason, api_key, m): m
            for m in models
        }
        for future in as_completed(futures):
            model = futures[future]
            ok = False
            reason = "unknown"
            try:
                ok, reason = future.result()
            except Exception as e:
                ok = False
                reason = e.__class__.__name__
            results[model] = ok
            if show_progress:
                suffix = "" if ok else f" ({reason})"
                print(f"  {'✅' if ok else '❌'} {model}{suffix}")

    return [m for m in models if results.get(m)]


ALLOWED_MODELS: List[str] = [
    "deepseek-ai/DeepSeek-V4-Pro",
    "deepseek-ai/DeepSeek-V4-Flash",
    "MiniMaxAI/MiniMax-M2.5",
    "deepseek-ai/DeepSeek-V3.2",
    "Qwen/Qwen3.6-35B-A3B",
    "Qwen/Qwen3.6-27B",
    "deepseek-ai/DeepSeek-R1",
    "stepfun-ai/Step-3.5-Flash",
    "zai-org/GLM-4.5-Air",
    "zai-org/GLM-4.5V",
]

# 不支持 function/tool calling 的模型：R1 是 reasoning 模型，4.5V 是视觉模型，
# 启用 OPENAI_USE_FUNCTIONS=true 会让 sgpt 强制带 tools 字段，触发 400。
MODELS_WITHOUT_FUNCTIONS: set = {
    "deepseek-ai/DeepSeek-R1",
    "zai-org/GLM-4.5V",
}

# 同 session 内缓存某 key 已验证的可用模型，避免重复 ping。
_cached_available_models: Dict[str, List[str]] = {}


def model_supports_functions(model: str) -> bool:
    return model not in MODELS_WITHOUT_FUNCTIONS


def get_available_models_cached(api_key: str, show_progress: bool = True) -> List[str]:
    """获取真实可用模型列表（同 session 内缓存按 api_key 命中）。"""
    if api_key in _cached_available_models:
        cached = _cached_available_models[api_key]
        if show_progress:
            print(f"✨ 使用已检测的可用模型列表（{len(cached)}个）")
        return cached

    all_models = test_api_connection(api_key, return_models=True)
    if not all_models:
        return []
    candidates = filter_models(all_models)
    if not candidates:
        return []
    verified = verify_models_in_parallel(api_key, candidates, show_progress=show_progress)
    _cached_available_models[api_key] = verified
    return verified


def filter_models(available_models: List[str]) -> List[str]:
    """按显式白名单过滤，保持 ALLOWED_MODELS 中的顺序作为展示顺序。"""
    catalog = set(available_models)
    return [m for m in ALLOWED_MODELS if m in catalog]


def select_default_model(available_models: List[str]) -> str:
    """默认模型 = ALLOWED_MODELS 中第一个真实可用的（即 DeepSeek-V4-Pro 优先）。"""
    return available_models[0] if available_models else "deepseek-ai/DeepSeek-V4-Pro"


"""
Portable Python 3.12 路径（首选）：
  - 直接从国内大学镜像（USTC/NJU/TUNA/SJTU 的 github-release 板块）下载
    python-build-standalone tarball（~30MB stripped）
  - 解压到 ~/.local/share/sgpt-portable-python/
  - 在这个独立 Python 里 pip install shell-gpt → 拿到 1.5.1（不存在 1.4.x 那个流尾 IndexError bug）
  - 在 ~/.local/bin/sgpt 写包装脚本，学生直接敲 sgpt 就行
  - 与系统 Python / conda 完全隔离

Fallback 路径：portable 这条路全失败时，回退到系统 pip + shell-gpt 1.4.x，
并自动 patch handler.py 加一行 `if not chunk.choices: continue` 修 bug。
"""

PORTABLE_PYTHON_VERSION = "3.12"
PORTABLE_PYTHON_DIR = Path.home() / ".local" / "share" / "sgpt-portable-python"
SGPT_WRAPPER = Path.home() / ".local" / "bin" / "sgpt"

# 国内 github-release 镜像候选（覆盖 astral-sh/python-build-standalone）。
# 不预先排序，每次都并发测速，按延迟取最快的可用项。
GITHUB_RELEASE_MIRRORS: Dict[str, str] = {
    "USTC":  "https://mirrors.ustc.edu.cn/github-release/astral-sh/python-build-standalone",
    "NJU":   "https://mirrors.nju.edu.cn/github-release/astral-sh/python-build-standalone",
    "TUNA":  "https://mirrors.tuna.tsinghua.edu.cn/github-release/astral-sh/python-build-standalone",
    "SJTU":  "https://mirror.sjtu.edu.cn/github-release/astral-sh/python-build-standalone",
    "BFSU":  "https://mirrors.bfsu.edu.cn/github-release/astral-sh/python-build-standalone",
    "HFUT":  "https://mirrors.hfut.edu.cn/github-release/astral-sh/python-build-standalone",
}


# urllib 兜底请求头。实测部分 github-release 镜像会对 urllib 返回 200 HTML，
# 所以镜像目录和 tarball 下载优先走 curl；这些 header 只用于 curl 不可用时的备用路径。
# Accept-Encoding: identity 可避免 urllib 兜底时遇到传输层二次 gzip 编码。
_BROWSER_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Encoding": "identity",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
}


def _curl_bin() -> Optional[str]:
    """Return curl path if available. Linux/macOS teaching machines usually have it."""
    return shutil.which("curl")


def _curl_common_args(timeout: int) -> List[str]:
    return [
        "--fail",
        "--location",
        "--silent",
        "--show-error",
        "--connect-timeout", str(min(timeout, 10)),
        "--max-time", str(timeout),
    ]


def _detect_platform_triple() -> Optional[str]:
    """识别 python-build-standalone 的 target triple。"""
    import platform
    machine = platform.machine().lower()
    system = platform.system().lower()
    if system == "linux":
        if machine in ("x86_64", "amd64"):
            return "x86_64-unknown-linux-gnu"
        if machine in ("aarch64", "arm64"):
            return "aarch64-unknown-linux-gnu"
    elif system == "darwin":
        if machine in ("arm64", "aarch64"):
            return "aarch64-apple-darwin"
        if machine in ("x86_64", "amd64"):
            return "x86_64-apple-darwin"
    return None


def _probe_release_mirror(name: str, base: str, timeout: int = 5) -> Tuple[str, str, float]:
    """
    用 GET 探测 github-release 镜像延迟。
    不用 HEAD：部分镜像（NJU 等）对 HEAD 反爬更严格。
    优先用 curl：学生环境里 curl 已验证能正常访问这些镜像，urllib 会被部分站点区别对待。
    """
    curl = _curl_bin()
    if curl:
        try:
            start = time.time()
            r = subprocess.run(
                [curl, *_curl_common_args(timeout), "--output", os.devnull, base + "/"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout + 2,
            )
            if r.returncode == 0:
                return (name, base, time.time() - start)
        except Exception:
            pass

    try:
        start = time.time()
        req = urllib.request.Request(base + "/", headers=_BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 400:
                resp.read(1)  # 真正建立连接但不读全内容
                return (name, base, time.time() - start)
    except Exception:
        pass
    return (name, base, float("inf"))


def get_release_mirrors_sorted() -> List[Tuple[str, str, float]]:
    """
    并发测速所有 github-release 镜像，按延迟升序返回。
    探测失败的镜像也保留在列表末尾（latency=inf），让下载阶段还能再试一次 ——
    HEAD/GET 测速失败不代表真实文件下载也失败（CDN 行为可能不同）。
    """
    results: List[Tuple[str, str, float]] = []
    with ThreadPoolExecutor(max_workers=len(GITHUB_RELEASE_MIRRORS)) as exe:
        futs = {exe.submit(_probe_release_mirror, n, u): n for n, u in GITHUB_RELEASE_MIRRORS.items()}
        for f in as_completed(futs):
            results.append(f.result())
    results.sort(key=lambda x: x[2])
    return results


def _http_get_text(url: str, timeout: int = 15) -> Optional[str]:
    curl = _curl_bin()
    if curl:
        try:
            r = subprocess.run(
                [curl, *_curl_common_args(timeout), url],
                capture_output=True,
                timeout=timeout + 2,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout.decode("utf-8", errors="replace")
        except Exception:
            pass

    try:
        req = urllib.request.Request(url, headers=_BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception:
        return None


def _is_valid_gzip(path: Path) -> bool:
    """检查文件是不是 gzip（前 2 字节 = 1f 8b）。被反爬返回 HTML 时能识破。"""
    try:
        with open(path, "rb") as f:
            return f.read(2) == b"\x1f\x8b"
    except Exception:
        return False


def _find_latest_python_tarball(mirror_base: str, triple: str) -> Optional[Tuple[str, str]]:
    """
    在镜像里找最新 Python 3.12 tarball。两种策略：
      1) 镜像如果有 LatestRelease/ 软链（USTC 实测有），直接用它，省事
      2) 否则抓 dir listing，找最近的 8 位日期 tag 下匹配 triple 的 install_only tarball
    返回 (tag, filename)；找不到返回 None。
    """
    import re
    py_v_re = re.escape(PORTABLE_PYTHON_VERSION)
    triple_re = re.escape(triple)
    # 优先 stripped（更小），找不到再退到 install_only
    filename_patterns = [
        rf'cpython-{py_v_re}\.\d+\+(\d{{8}})-{triple_re}-install_only_stripped\.tar\.gz',
        rf'cpython-{py_v_re}\.\d+\+(\d{{8}})-{triple_re}-install_only\.tar\.gz',
    ]

    # 策略 1：LatestRelease/
    latest_html = _http_get_text(f"{mirror_base}/LatestRelease/")
    if latest_html:
        for pat in filename_patterns:
            m = re.search(pat, latest_html)
            if m:
                return (m.group(1), m.group(0))

    # 策略 2：扫 dir listing 找 8 位日期 tag
    root_html = _http_get_text(f"{mirror_base}/")
    if not root_html:
        return None
    # 兼容绝对/相对路径两种 href：href="20260510/" 或 href="/.../20260510/"
    tags = sorted(set(re.findall(r'(\d{8})/', root_html)), reverse=True)
    for tag in tags[:3]:
        tag_html = _http_get_text(f"{mirror_base}/{tag}/")
        if not tag_html:
            continue
        for pat in filename_patterns:
            m = re.search(pat, tag_html)
            if m:
                return (m.group(1), m.group(0))
    return None


def _download_with_progress(url: str, dest: Path, label: str) -> bool:
    """下载文件，spinner 同时显示已下载 MB / 总 MB / 百分比 / 秒数。"""
    curl = _curl_bin()
    if curl:
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            curl,
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--retry", "2",
            "--connect-timeout", "10",
            "--max-time", "300",
            "--output", str(dest),
            url,
        ]
        spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        start = time.time()
        while proc.poll() is None:
            mb = dest.stat().st_size / 1024 / 1024 if dest.exists() else 0
            elapsed = time.time() - start
            sys.stdout.write(f"\r  {next(spinner)} {label}: {mb:.1f}MB ({elapsed:.0f}s)   ")
            sys.stdout.flush()
            time.sleep(0.1)
        _out, err = proc.communicate()
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
        if proc.returncode == 0 and dest.exists() and dest.stat().st_size > 0:
            return True
        msg = err.decode(errors="replace").strip()
        if msg:
            print(f"  ❌ curl 下载失败: {msg.splitlines()[-1]}")
        else:
            print(f"  ❌ curl 下载失败（退出码 {proc.returncode}）")
        if dest.exists() and dest.stat().st_size == 0:
            dest.unlink(missing_ok=True)

    # curl 不可用或失败时，再退回 urllib。部分镜像会拒绝 urllib，失败后主循环会切下一个源。
    try:
        req = urllib.request.Request(url, headers=_BROWSER_HEADERS)
        resp = urllib.request.urlopen(req, timeout=30)
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        return False

    total = int(resp.getheader("Content-Length", "0") or 0)
    dest.parent.mkdir(parents=True, exist_ok=True)
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    done = threading.Event()
    state = {"bytes": 0}

    def _spin():
        start = time.time()
        while not done.is_set():
            mb = state["bytes"] / 1024 / 1024
            tot_mb = total / 1024 / 1024 if total else 0
            pct = f"{state['bytes']*100/total:.0f}%" if total else "?%"
            t = time.time() - start
            sys.stdout.write(f"\r  {next(spinner)} {label}: {mb:.1f}/{tot_mb:.0f}MB ({pct}, {t:.0f}s)   ")
            sys.stdout.flush()
            time.sleep(0.1)

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    ok = True
    try:
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                state["bytes"] += len(chunk)
    except Exception as e:
        ok = False
        print(f"\r  ❌ 下载中断: {e}" + " " * 30)
    finally:
        done.set()
        t.join(timeout=0.5)
    sys.stdout.write("\r" + " " * 80 + "\r")
    sys.stdout.flush()
    return ok and dest.exists() and dest.stat().st_size > 0


def install_portable_python() -> Optional[str]:
    """
    从国内大学镜像下载并解压 portable Python 3.12 到 ~/.local/share/sgpt-portable-python/。
    返回 python3 可执行文件路径；全部失败时返回 None。
    """
    python_bin = PORTABLE_PYTHON_DIR / "python" / "bin" / "python3"
    if python_bin.exists():
        print(f"✨ 已检测到 portable Python: {python_bin}")
        return str(python_bin)

    triple = _detect_platform_triple()
    if not triple:
        print("❌ 当前平台无 python-build-standalone 预编译版本（仅支持 linux x86_64/aarch64 和 macOS）")
        return None

    print(f"\n🔍 测速国内 github-release 镜像...")
    mirror_results = get_release_mirrors_sorted()
    for name, url, latency in mirror_results:
        if latency == float("inf"):
            print(f"  ⚠️  {name}: 测速失败（仍会尝试下载）")
        else:
            print(f"  ✅ {name}: {latency*1000:.0f}ms")

    print(f"\n📦 平台: {triple}")
    print(f"💡 任何一个镜像装成功就停；全部失败才回退到 fallback 模式")

    for name, base, latency in mirror_results:
        print(f"\n🔍 {name}: 查找最新 Python {PORTABLE_PYTHON_VERSION}...")
        info = _find_latest_python_tarball(base, triple)
        if not info:
            print(f"  ❌ 找不到匹配版本（dir listing 失败或镜像同步滞后）")
            continue
        tag, fname = info
        # 不要 URL-encode 文件名：python-build-standalone 文件名包含 '+',
        # 多个 github-release 镜像的反代对原始 '+' 和 '%2B' 并不等价。
        url = f"{base}/{tag}/{fname}"
        print(f"  📌 {fname} (release {tag})")

        tarball = PORTABLE_PYTHON_DIR / "_download.tar.gz"
        # 干净起手：上一次试错可能留下半截文件
        if tarball.exists():
            tarball.unlink()
        if not _download_with_progress(url, tarball, f"下载 Python ({name})"):
            continue

        # ❶ 用 magic byte 检查：反爬可能返回 HTML challenge，需要识破
        if not _is_valid_gzip(tarball):
            head = tarball.read_bytes()[:160] if tarball.exists() else b""
            print(f"  ❌ 下载内容不是 gzip 文件（疑似反爬 HTML / 空响应）")
            print(f"     文件头: {head[:80]!r}")
            tarball.unlink(missing_ok=True)
            continue

        size_mb = tarball.stat().st_size / 1024 / 1024
        print(f"  📦 解压 {size_mb:.1f}MB → {PORTABLE_PYTHON_DIR}/python/ ...")
        try:
            import tarfile
            with tarfile.open(tarball, "r:gz") as tar:
                tar.extractall(PORTABLE_PYTHON_DIR)
            tarball.unlink()
        except Exception as e:
            print(f"  ❌ 解压失败: {e}")
            tarball.unlink(missing_ok=True)
            continue

        if python_bin.exists():
            v = subprocess.run([str(python_bin), "--version"], capture_output=True, text=True, timeout=5)
            print(f"  ✅ Python 就绪: {python_bin}")
            print(f"     版本: {(v.stdout + v.stderr).strip()}")
            return str(python_bin)
        print(f"  ❌ 解压完没找到 {python_bin}")

    return None


def _create_sgpt_wrapper(python_bin: str) -> None:
    """在 ~/.local/bin/sgpt 写包装脚本，让学生直接敲 sgpt 就调用 portable Python 里的 sgpt。"""
    portable_sgpt = Path(python_bin).parent / "sgpt"
    SGPT_WRAPPER.parent.mkdir(parents=True, exist_ok=True)
    SGPT_WRAPPER.write_text(
        "#!/bin/bash\n"
        "# Wrapper created by setup_shell_gpt.py — invokes shell-gpt in portable Python 3.12.\n"
        f'exec "{portable_sgpt}" "$@"\n'
    )
    SGPT_WRAPPER.chmod(0o755)


def _get_installed_package_version(python_bin: str, package: str) -> str:
    """通过 pip 元数据读取版本号，避免 import 包时触发交互式初始化。"""
    try:
        r = subprocess.run(
            [python_bin, "-m", "pip", "show", package],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return ""
    if r.returncode != 0:
        return ""
    for line in r.stdout.splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
    return ""


def _get_shell_gpt_handler_path(python_bin: str) -> Optional[Path]:
    """定位 sgpt/handlers/handler.py，不 import sgpt，避免安装阶段再次询问 API key。"""
    try:
        r = subprocess.run(
            [python_bin, "-m", "pip", "show", "shell-gpt"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        r = None
    if r and r.returncode == 0:
        location = ""
        for line in r.stdout.splitlines():
            if line.startswith("Location:"):
                location = line.split(":", 1)[1].strip()
                break
        if location:
            handler_py = Path(location) / "sgpt" / "handlers" / "handler.py"
            if handler_py.exists():
                return handler_py

    # 兜底：通过 importlib.metadata 定位 distribution 文件，不导入 sgpt 包本体。
    script = (
        "import importlib.metadata as m\n"
        "dist = m.distribution('shell-gpt')\n"
        "for f in dist.files or []:\n"
        "    if str(f).replace('\\\\', '/').endswith('sgpt/handlers/handler.py'):\n"
        "        print(dist.locate_file(f))\n"
        "        break\n"
    )
    try:
        r = subprocess.run(
            [python_bin, "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return None
    if r.returncode == 0 and r.stdout.strip():
        handler_py = Path(r.stdout.strip())
        if handler_py.exists():
            return handler_py
    return None


def install_shell_gpt_into_portable(python_bin: str) -> bool:
    """用 portable Python 的 pip 装 shell-gpt 1.5.x，然后写包装脚本。"""
    mirrors = get_pip_mirrors_sorted()
    if not mirrors:
        mirrors = [DEFAULT_PIP_MIRROR]

    for name, url in mirrors:
        host = url.split("//")[1].split("/")[0]
        print(f"\n📦 用 {name} 镜像装 shell-gpt 进 portable Python...")
        cmd = [
            python_bin, "-m", "pip", "install",
            "--upgrade",
            "-i", url,
            "--trusted-host", host,
            "--timeout", "30",
            "--retries", "3",
            "--disable-pip-version-check",
            "shell-gpt",
        ]
        if _run_with_spinner(cmd, label=f"装 shell-gpt ({name})"):
            _create_sgpt_wrapper(python_bin)
            version = _get_installed_package_version(python_bin, "shell-gpt")
            print(f"✅ shell-gpt 安装成功！包装脚本: {SGPT_WRAPPER}")
            print(f"   shell-gpt 版本: {version or '(取版本失败)'}")
            if shutil.which("sgpt") is None:
                print("💡 提示: ~/.local/bin 不在 PATH，请加上:")
                print('   echo \'export PATH="$HOME/.local/bin:$PATH"\' >> ~/.bashrc && source ~/.bashrc')
            return True
        print(f"⚠️  {name} pip 镜像不稳定，自动切下一个...")
    return False


def patch_shell_gpt_1_4_bug(python_bin: str) -> bool:
    """
    给 1.4.x 的 sgpt/handlers/handler.py 打补丁，跳过 choices=[] 的流尾 chunk：
        for chunk in response:
            if not chunk.choices:     # ← 新加这两行
                continue
            delta = chunk.choices[0].delta
    成功或已经打过补丁都返回 True；找不到目标代码段返回 False。
    """
    handler_py = _get_shell_gpt_handler_path(python_bin)
    if not handler_py:
        return False
    content = handler_py.read_text()
    if "if not chunk.choices:" in content:
        return True  # 已打补丁
    needle = "for chunk in response:\n            delta = chunk.choices[0].delta"
    if needle not in content:
        return False
    patched = content.replace(
        needle,
        "for chunk in response:\n"
        "            if not chunk.choices:  # patched: skip SiliconFlow's trailing usage-only chunk\n"
        "                continue\n"
        "            delta = chunk.choices[0].delta",
    )
    handler_py.write_text(patched)
    return True


def install_shell_gpt_via_pip_with_patch() -> bool:
    """Fallback：系统 pip 装 shell-gpt（1.4.x for Python 3.8/3.9），并自动打补丁修 IndexError。"""
    mirrors = get_pip_mirrors_sorted()
    if not mirrors:
        mirrors = [DEFAULT_PIP_MIRROR]
    for name, url in mirrors:
        host = url.split("//")[1].split("/")[0]
        print(f"\n📦 用 {name} 镜像装 shell-gpt（fallback 模式）...")
        cmd = [
            sys.executable, "-m", "pip", "install",
            "-i", url, "--trusted-host", host,
            "--timeout", "30", "--retries", "3",
            "--disable-pip-version-check",
            "shell-gpt",
        ]
        if _run_with_spinner(cmd, label=f"装 shell-gpt ({name})"):
            patched = patch_shell_gpt_1_4_bug(sys.executable)
            if patched:
                print("✅ shell-gpt 安装成功 + 已打补丁修复流尾 chunk IndexError")
            else:
                print("⚠️  shell-gpt 安装成功，但补丁未应用（版本可能已变化，建议手动检查 handler.py）")
            return True
        print(f"⚠️  {name} 不稳定，切下一个...")
    return False


def _run_with_spinner(cmd, env=None, label: str = "处理中") -> bool:
    """
    后台跑命令并显示 spinner；标准输出/错误全部捕获，
    只有失败时才打印日志（避免 pip retry 之类的噪声吓到新手）。
    """
    proc = subprocess.Popen(
        cmd, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
    done = threading.Event()

    def _spin():
        start = time.time()
        while not done.is_set():
            elapsed = int(time.time() - start)
            sys.stdout.write(f"\r  {next(spinner)} {label}... ({elapsed}s)")
            sys.stdout.flush()
            time.sleep(0.1)

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        out, _ = proc.communicate()
    finally:
        done.set()
        t.join(timeout=0.5)
    # 清掉 spinner 这一行
    sys.stdout.write("\r" + " " * 70 + "\r")
    sys.stdout.flush()

    if proc.returncode != 0:
        print(f"❌ {label} 失败 (退出码 {proc.returncode})")
        print("---- 详细日志 ----")
        print(out.decode(errors="replace") if out else "(无输出)")
        print("------------------")
        return False
    return True


def install_shell_gpt():
    """
    优先 portable Python 3.12 路径（拿到 shell-gpt 1.5.1，无 IndexError bug）；
    全部失败再 fallback 到系统 pip + 1.4.x + 自动 patch handler.py。
    """
    print("\n🎯 优先尝试 portable Python 3.12 路径...")
    python_bin = install_portable_python()
    if python_bin and install_shell_gpt_into_portable(python_bin):
        return True

    print("\n⚠️  portable Python 路径不通，回退到系统 Python + shell-gpt 1.4.x + 自动补丁...")
    return install_shell_gpt_via_pip_with_patch()


def _get_config_path() -> Path:
    return Path.home() / '.config' / 'shell_gpt' / '.sgptrc'


def update_config_keys(updates: Dict[str, str]) -> bool:
    """
    更新 .sgptrc 中的若干键值（保留其他行不变；不存在的键追加到末尾），
    并把文件权限收紧到 600。配置文件不存在时返回 False。
    """
    config_file = _get_config_path()
    if not config_file.exists():
        return False

    with open(config_file, 'r') as f:
        lines = f.readlines()

    remaining = dict(updates)
    new_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if '=' in stripped and not stripped.startswith('#'):
            key = stripped.split('=', 1)[0]
            if key in remaining:
                new_lines.append(f"{key}={remaining.pop(key)}\n")
                continue
        new_lines.append(line)

    for key, value in remaining.items():
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines.append('\n')
        new_lines.append(f"{key}={value}\n")

    with open(config_file, 'w') as f:
        f.writelines(new_lines)
    os.chmod(config_file, 0o600)
    return True


def create_config_file(api_key: str, default_model: str):
    """创建shell-gpt配置文件"""
    # 获取用户信息
    username = os.getenv('LOGNAME') or os.getenv('USER') or 'default_user'
    home_dir = Path.home()
    config_dir = home_dir / '.config' / 'shell_gpt'
    config_file = config_dir / '.sgptrc'

    # 创建配置目录
    config_dir.mkdir(parents=True, exist_ok=True)

    use_functions = "true" if model_supports_functions(default_model) else "false"

    config_content = f"""CHAT_CACHE_PATH=/tmp/chat_cache_{username}
CACHE_PATH=/tmp/cache_{username}
CHAT_CACHE_LENGTH=100
CACHE_LENGTH=100
REQUEST_TIMEOUT=60
DEFAULT_MODEL={default_model}
DEFAULT_COLOR=magenta
ROLE_STORAGE_PATH={home_dir}/.config/shell_gpt/roles
DEFAULT_EXECUTE_SHELL_CMD=false
DISABLE_STREAMING=true
CODE_THEME=dracula
OPENAI_FUNCTIONS_PATH={home_dir}/.config/shell_gpt/functions
OPENAI_USE_FUNCTIONS={use_functions}
SHOW_FUNCTIONS_OUTPUT=false
API_BASE_URL=https://api.siliconflow.cn/v1
PRETTIFY_MARKDOWN=true
USE_LITELLM=false
OPENAI_API_KEY={api_key}
SHELL_INTERACTION=true
OS_NAME=auto
SHELL_NAME=auto"""

    with open(config_file, 'w') as f:
        f.write(config_content)
    os.chmod(config_file, 0o600)

    print(f"✅ 配置文件已创建: {config_file} (权限 600)")
    print(f"📁 使用的默认模型: {default_model}")
    print(f"🛠️  function calling: {use_functions}")
    print(f"👤 用户名: {username}")

    # 创建必要的缓存目录
    cache_dirs = [f"/tmp/chat_cache_{username}", f"/tmp/cache_{username}"]
    for cache_dir in cache_dirs:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            print(f"📁 创建缓存目录: {cache_dir}")
        except PermissionError:
            print(f"⚠️  警告: 无法创建缓存目录 {cache_dir}，运行时可能会自动创建")


def _get_cleanup_targets() -> List[Tuple[str, Path]]:
    """所有由安装流程创建、卸载时需要清理的文件/目录。"""
    username = os.getenv('LOGNAME') or os.getenv('USER') or 'default_user'
    home = Path.home()
    return [
        ("配置目录",              home / ".config" / "shell_gpt"),
        ("聊天缓存",              Path(f"/tmp/chat_cache_{username}")),
        ("通用缓存",              Path(f"/tmp/cache_{username}")),
        ("shell-gpt 内部缓存",    home / ".cache" / "shell_gpt"),
        ("Portable Python",       PORTABLE_PYTHON_DIR),
        ("sgpt 包装脚本",         SGPT_WRAPPER),
    ]


def uninstall_shell_gpt():
    """
    彻底清理 shell-gpt 安装痕迹：
      1. pip 卸载 shell-gpt 包（用 sys.executable，所以请在装它的同一个 Python 环境里运行）
      2. 删除 ~/.config/shell_gpt 整个目录（含 .sgptrc、roles/、functions/）
      3. 删除 /tmp/chat_cache_<user>/ 和 /tmp/cache_<user>/
      4. 删除 ~/.cache/shell_gpt（如果存在）
    本脚本从未改过 .bashrc/.zshrc，所以不存在 PATH 残留。
    """
    print("\n🧹 完全卸载 Shell-GPT")
    print("=" * 40)

    targets = _get_cleanup_targets()
    print("将会执行：")
    print("  • pip uninstall -y shell-gpt （用 当前 Python:", sys.executable, "）")
    for label, p in targets:
        status = "存在" if p.exists() else "不存在"
        marker = "🗑️" if p.exists() else "  "
        print(f"  {marker} 删除 {label}: {p}  [{status}]")

    print("\n⚠️  如果你当时是在某个 conda 环境里装的 shell-gpt，")
    print("    请先 `conda activate <那个环境>` 再回来跑这个清理，否则 pip 卸不掉包。")

    try:
        confirm = input("\n确认清理？(yes/no): ").strip().lower()
    except KeyboardInterrupt:
        print("\n操作已取消")
        return
    if confirm not in ('y', 'yes', '是'):
        print("已取消，未做任何改动")
        return

    # 1. pip uninstall —— 静默执行，最后只报告结果
    print("\n1️⃣ 卸载 shell-gpt 包...")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "shell-gpt"],
        capture_output=True, text=True,
    )
    if r.returncode == 0:
        print("   ✅ pip uninstall 成功")
    elif "not installed" in (r.stderr + r.stdout).lower() or "Skipping" in r.stdout:
        print("   ⏭️  当前 Python 环境里没有 shell-gpt 包，跳过")
    else:
        print(f"   ⚠️  pip uninstall 返回 {r.returncode}（可能是装在别的 Python 环境）")
        for line in (r.stderr or r.stdout).splitlines()[-3:]:
            print(f"     | {line}")

    # 2. 删目录
    import shutil as _sh
    print("\n2️⃣ 删除文件和目录...")
    for label, p in targets:
        if not p.exists():
            print(f"   ⏭️  {label} 不存在: {p}")
            continue
        try:
            _sh.rmtree(p)
            print(f"   ✅ 已删除 {label}: {p}")
        except Exception as e:
            print(f"   ❌ 删除 {p} 失败: {e}")

    # 3. 顺手清掉 session 内的可用模型缓存，避免后续重装时残留
    _cached_available_models.clear()

    print("\n✅ 清理完成！系统已恢复到安装 shell-gpt 之前的状态")
    print("💡 本脚本从未改过你的 .bashrc/.zshrc，所以没有 PATH 残留要清")


def show_menu():
    """显示主菜单"""
    print("\n🎯 请选择操作:")
    print("1️⃣  自动安装并配置Shell-GPT")
    print("2️⃣  选择/切换模型")
    print("3️⃣  重新设置API密钥")
    print("4️⃣  显示当前配置")
    print("5️⃣  🧹 完全卸载（删除所有安装痕迹）")
    print("0️⃣  退出")
    print("-" * 30)


MENU_CHOICES = {str(i) for i in range(6)}


def get_user_choice() -> str:
    """获取用户选择"""
    while True:
        choice = input("请输入选项 (0-5): ").strip()
        if choice in MENU_CHOICES:
            return choice
        print("❌ 无效选择，请输入0-5之间的数字")


def interactive_set_api_key(allow_cancel: bool = False, test_connection: bool = True) -> Optional[str]:
    """
    交互式设置API密钥（带实时星号显示）
    输入时显示*，输入完成后自动测试连接

    Args:
        allow_cancel: 是否允许取消操作
        test_connection: 是否测试API连接（默认True）
    """
    print("\n🔑 设置API密钥")
    print("-" * 30)
    print("💡 提示: 输入时会显示星号*")
    if allow_cancel:
        print("💡 提示: 输入 'cancel' 可以取消操作")

    while True:
        try:
            # 使用星号显示输入
            api_key = secure_input_with_stars("请输入你的API密钥: ").strip()

            # 检查是否取消
            if allow_cancel and api_key.lower() == 'cancel':
                return None

            # 简单验证长度
            if len(api_key) < 10:
                print("❌ API密钥似乎太短（至少10个字符），请重新输入")
                continue

            # 显示马赛克版本
            masked_key = mask_api_key(api_key)
            print(f"✅ 已接收密钥: {masked_key}")

            # 测试API连接
            if test_connection:
                print("🔗 正在验证API密钥...")
                if test_api_connection(api_key):
                    print("✅ API密钥验证成功!")
                    return api_key
                else:
                    # test_api_connection 已打印详细错误，这里只需提示重新输入
                    continue
            else:
                return api_key

        except KeyboardInterrupt:
            print("\n操作已取消")
            if allow_cancel:
                return None
            raise


def show_current_config(api_key: Optional[str] = None):
    """显示当前配置"""
    home_dir = Path.home()
    config_file = home_dir / '.config' / 'shell_gpt' / '.sgptrc'

    print("\n📋 当前配置信息:")
    print("-" * 30)

    if not config_file.exists():
        print("⚠️  配置文件尚未创建")
        if api_key:
            print("\n💡 当前会话信息:")
            masked = mask_api_key(api_key)
            print(f"🔑 API密钥: {masked}")
            print(f"📌 状态: 内存中（尚未保存到配置文件）")
            print("\n💡 提示: 请选择选项 1 进行自动安装，将配置保存到文件")
        else:
            print("💡 提示: 请先选择选项 1 进行自动安装")
        return

    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DEFAULT_MODEL='):
                    model = line.split('=', 1)[1]
                    print(f"🤖 当前模型: {model}")
                elif line.startswith('OPENAI_API_KEY='):
                    key = line.split('=', 1)[1]
                    # 使用马赛克显示
                    masked = mask_api_key(key)
                    print(f"🔑 API密钥: {masked}")
                elif line.startswith('API_BASE_URL='):
                    url = line.split('=', 1)[1]
                    print(f"🌐 API地址: {url}")
        print(f"\n📁 配置文件位置: {config_file}")
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")


def switch_model(api_key: str):
    """选择/切换模型"""
    print("\n🔄 选择/切换模型")
    print("-" * 20)

    available_models = get_available_models_cached(api_key, show_progress=True)
    if not available_models:
        print("❌ 没有任何模型通过可用性检测（可能额度耗尽或 key 权限受限）")
        return

    print(f"\n📋 可用模型 ({len(available_models)}个):")
    for i, model in enumerate(available_models, 1):
        print(f"{i:2d}. {model}")

    print("\n🎯 推荐模型:")
    recommended_models = [
        'deepseek-ai/DeepSeek-V4-Pro',
        'deepseek-ai/DeepSeek-V4-Flash',
        'deepseek-ai/DeepSeek-V3.2',
    ]
    for model in recommended_models:
        if model in available_models:
            print(f"⭐ {model}")

    while True:
        try:
            choice = input("\n请输入模型编号 (1-{}) 或直接输入模型名称 (输入 0/back/cancel 返回): ".format(len(available_models))).strip()

            # 检查是否要返回主菜单
            if choice.lower() in ['0', 'back', 'cancel', '返回']:
                print("↩️  返回主菜单")
                return

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(available_models):
                    selected_model = available_models[idx]
                    break
                else:
                    print("❌ 编号超出范围，请重新输入")
                    continue
            else:
                if choice in available_models:
                    selected_model = choice
                    break
                else:
                    print("❌ 未找到该模型，请重新输入")
                    continue
        except KeyboardInterrupt:
            print("\n↩️  操作已取消，返回主菜单")
            return

    use_functions = "true" if model_supports_functions(selected_model) else "false"
    try:
        if not update_config_keys({
            "DEFAULT_MODEL": selected_model,
            "OPENAI_USE_FUNCTIONS": use_functions,
        }):
            print("❌ 配置文件不存在，请先进行完整安装")
            return
        print(f"✅ 模型已切换为: {selected_model}")
        print(f"🛠️  function calling: {use_functions}")
    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")


def auto_install(api_key: str) -> bool:
    """自动安装流程"""
    print("\n🚀 开始自动安装Shell-GPT")
    print("=" * 40)

    # 1. 获取可用模型（API已在main()中验证过）
    print("1️⃣ 获取可用模型...")
    available_models = get_available_models_cached(api_key, show_progress=True)
    if not available_models:
        print("⚠️  警告: 无可用模型，将使用默认配置")
        default_model = "deepseek-ai/DeepSeek-V4-Pro"
    else:
        default_model = select_default_model(available_models)
        print(f"✅ 找到 {len(available_models)} 个真实可用模型")

    # 2. 安装shell-gpt
    print("\n2️⃣ 安装shell-gpt...")
    if not install_shell_gpt():
        return False

    # 3. 创建配置文件
    print("\n3️⃣ 创建配置文件...")
    create_config_file(api_key, default_model)

    # 4. 提供测试用例
    print("\n🎉 安装配置完成!")
    print("=" * 40)
    print("🧬 生物信息学测试用例:")
    print("sgpt --code 'solve fizz buzz problem using python'")
    print("sgpt --shell '帮我生成10个file开头的文件'")
    print("sgpt --shell '从Data文件夹中读取Homo_sapiens.GRCh38.102.chromosome.Y.gff3.gz并且用awk的if模式数第三列是gene的行有多少行'")
    print("sgpt --shell '使用conda的rna环境下的fastqc，对Data文件夹里的reads.1.fq.gz和reads.2.fq.gz生成报告'")
    print("sgpt --shell '使用conda的rna环境下的multiqc, 把Data文件夹里fastqc的报告合并成一个'")

    return True


def _ensure_local_bin_in_path() -> None:
    """
    确保 ~/.local/bin 在 PATH 里：
      - 新建账号第一次登录时 ~/.local/bin 不存在，.profile/.bashrc 的检查会跳过它
      - pip --user 装完包后 ~/.local/bin 才出现，但当前 shell 的 PATH 已定型
      - 后续学生敲 auto-shell-gpt 会 command not found

    本函数幂等地把 export 行追加到 ~/.bashrc 和 ~/.zshrc（仅当后者已存在）。
    完成后打印一行提示。已经配好的不打扰。
    """
    local_bin = str(Path.home() / ".local" / "bin")
    current_path = os.environ.get("PATH", "")
    # 已在当前 PATH 里 → 啥都不用做
    if local_bin in current_path.split(":"):
        return

    export_line = 'export PATH="$HOME/.local/bin:$PATH"'
    rc_files: List[Path] = [Path.home() / ".bashrc"]
    zshrc = Path.home() / ".zshrc"
    if zshrc.exists():
        rc_files.append(zshrc)

    updated: List[str] = []
    for rc in rc_files:
        try:
            existing = rc.read_text() if rc.exists() else ""
        except Exception:
            existing = ""
        # 幂等检查：精确匹配那一行（含/不含 export 关键字、有无前导空格都算）
        if any(line.strip() == export_line for line in existing.splitlines()):
            continue
        # 追加到末尾，前面带一个空行作分隔，加个注释让用户知道是谁加的
        try:
            with open(rc, "a") as f:
                f.write("\n# Added by auto-shell-gpt: 让 pip --user 装的 CLI 命令进入 PATH\n")
                f.write(export_line + "\n")
            updated.append(str(rc))
        except Exception:
            pass

    if updated:
        print(f"💡 已把 ~/.local/bin 加进 {', '.join(updated)}")
        print(f"   下次新开终端可以直接敲 'auto-shell-gpt' / 'sgpt-installer'，不用绝对路径")


def main():
    """主函数"""
    _ensure_local_bin_in_path()
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='Shell-GPT 自动安装配置脚本 v1.12.1',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python setup_shell_gpt.py                        # 交互式菜单
  python setup_shell_gpt.py --key sk-xxx           # 直接指定API密钥
  python setup_shell_gpt.py --auto --key sk-xxx    # 自动安装模式
  python setup_shell_gpt.py --uninstall            # 完全卸载（不需要API密钥）
        """
    )

    parser.add_argument('--key', '-k', help='API密钥')
    parser.add_argument('--auto', '-a', action='store_true', help='自动安装模式（跳过菜单）')
    parser.add_argument('--uninstall', action='store_true', help='完全卸载，不需要API密钥')

    args = parser.parse_args()

    print("🚀 Shell-GPT 自动安装配置脚本 v1.12.1")
    print("🔒 隐私保护 | 🚄 自动选择最快pip镜像")
    print("=" * 50)

    # 卸载模式：不需要 API key，直接走清理流程
    if args.uninstall:
        uninstall_shell_gpt()
        return True

    # 获取并验证API密钥
    api_key = get_api_key(args.key)

    if api_key:
        # 找到已有密钥，验证是否有效
        masked = mask_api_key(api_key)
        print(f"🔍 找到API密钥: {masked}")
        print("🔗 验证中...")

        if test_api_connection(api_key):
            print("✅ API连接正常")
        else:
            # 验证失败，需要重新输入
            api_key = None

    if not api_key:
        # 需要用户输入密钥
        print("❌ 需要有效的API密钥")
        print("\n📊 如何获取API密钥:")
        print("🎁 新用户福利: 使用下面的链接注册可以获得双倍免费额度!")
        print("🔗 注册地址: https://cloud.siliconflow.cn/i/pnTWTpiB")

        try:
            api_key = interactive_set_api_key(allow_cancel=False, test_connection=True)
            if not api_key:
                print("\n操作已取消")
                return False
        except KeyboardInterrupt:
            print("\n操作已取消")
            return False

    # 如果指定了自动模式，直接安装
    if args.auto:
        return auto_install(api_key)

    # 交互式菜单模式
    while True:
        show_menu()
        try:
            choice = get_user_choice()

            if choice == '0':
                print("👋 再见!")
                break
            elif choice == '1':
                auto_install(api_key)
            elif choice == '2':
                switch_model(api_key)
            elif choice == '3':
                new_key = interactive_set_api_key(allow_cancel=True, test_connection=True)
                if new_key:
                    api_key = new_key
                    print("✅ API密钥已更新并验证成功")
                else:
                    print("❌ 操作已取消，保持原有设置")
            elif choice == '4':
                show_current_config(api_key)
            elif choice == '5':
                uninstall_shell_gpt()

        except KeyboardInterrupt:
            print("\n\n👋 操作已取消，再见!")
            break

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n👋 程序已退出")
        sys.exit(0)
