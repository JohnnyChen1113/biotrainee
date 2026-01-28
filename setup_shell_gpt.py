#!/usr/bin/env python3
"""
Shell-GPT 自动安装和配置脚本
为Linux新手用户提供一键安装和配置Shell-GPT的便捷工具

@Author: 卖萌哥
@Version: 1.3.0
@Date: 2025-11-18
@Description: 支持自动安装requests依赖、模型切换、API密钥设置等功能
@Update: v1.3.0 - 代码重构优化：缓存镜像检测结果、合并API请求函数、简化验证流程
         v1.2.0 - 新增pip镜像源速度检测功能，自动选择最快镜像安装
         v1.1.0 - 新增API密钥输入时的实时星号显示（输入时显示*，完成后显示首尾马赛克）
                  新增模型选择时的主动返回功能（输入0/back/cancel返回主菜单）
"""

import os
import sys
import subprocess
import argparse
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional, Tuple, Dict

# pip 镜像源列表
PIP_MIRRORS: Dict[str, str] = {
    "PyPI官方": "https://pypi.org/simple",
    "清华大学": "https://pypi.tuna.tsinghua.edu.cn/simple",
    "阿里云": "https://mirrors.aliyun.com/pypi/simple",
    "腾讯云": "https://mirrors.cloud.tencent.com/pypi/simple",
    "北京大学": "https://mirrors.pku.edu.cn/pypi/web/simple",
    "中科大": "https://pypi.mirrors.ustc.edu.cn/simple",
}

# 默认镜像（当检测失败时使用）
DEFAULT_PIP_MIRROR = ("清华大学", "https://pypi.tuna.tsinghua.edu.cn/simple")

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
    url = "https://api.siliconflow.cn/v1/models"
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


def filter_models(available_models: List[str]) -> List[str]:
    """过滤模型，只显示指定的四家厂商模型，按顺序排列"""
    # 按优先级分组
    deepseek_models = []
    kimi_models = []
    qwen_models = []
    minimax_models = []

    for model in available_models:
        model_lower = model.lower()

        # 过滤掉Pro、Plus等高级付费模型
        if 'pro' in model_lower or 'plus' in model_lower:
            continue

        # 过滤掉Qwen2.5，只保留Qwen3
        if 'qwen' in model_lower and ('2.5' in model_lower or 'qwen2' in model_lower):
            continue

        if 'deepseek' in model_lower:
            deepseek_models.append(model)
        elif 'kimi' in model_lower:
            kimi_models.append(model)
        elif 'qwen' in model_lower:
            qwen_models.append(model)
        elif 'minimax' in model_lower:
            minimax_models.append(model)

    # 按指定顺序返回：DeepSeek > Kimi > Qwen > MiniMax
    return deepseek_models + kimi_models + qwen_models + minimax_models


def select_default_model(available_models: List[str]) -> str:
    """选择默认模型（优先级：Kimi-K2 > DeepSeek-V3.1 > 列表第一个）"""
    # 优先选择的模型列表
    preferred = ['moonshotai/Kimi-K2-Instruct', 'deepseek-ai/DeepSeek-V3.1']

    for preferred_model in preferred:
        for model in available_models:
            if preferred_model in model:
                return model

    # 返回列表第一个（已按 DeepSeek > Kimi > Qwen > MiniMax 排序）
    return available_models[0] if available_models else "moonshotai/Kimi-K2-Instruct"


def install_shell_gpt():
    """安装shell-gpt"""
    # 检测最快的pip镜像源
    mirror_name, mirror_url = find_fastest_pip_mirror(show_progress=True)

    print(f"\n📦 使用 {mirror_name} 镜像安装 shell-gpt...")
    try:
        cmd = [
            sys.executable, "-m", "pip", "install",
            "-i", mirror_url,
            "--trusted-host", mirror_url.split("//")[1].split("/")[0],
            "shell-gpt"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ shell-gpt 安装成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ shell-gpt 安装失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False


def create_config_file(api_key: str, default_model: str):
    """创建shell-gpt配置文件"""
    # 获取用户信息
    username = os.getenv('LOGNAME') or os.getenv('USER') or 'default_user'
    home_dir = Path.home()
    config_dir = home_dir / '.config' / 'shell_gpt'
    config_file = config_dir / '.sgptrc'

    # 创建配置目录
    config_dir.mkdir(parents=True, exist_ok=True)

    # 配置内容
    config_content = f"""CHAT_CACHE_PATH=/tmp/chat_cache_{username}
CACHE_PATH=/tmp/cache_{username}
CHAT_CACHE_LENGTH=100
CACHE_LENGTH=100
REQUEST_TIMEOUT=60
DEFAULT_MODEL={default_model}
DEFAULT_COLOR=magenta
ROLE_STORAGE_PATH={home_dir}/.config/shell_gpt/roles
DEFAULT_EXECUTE_SHELL_CMD=false
DISABLE_STREAMING=false
CODE_THEME=dracula
OPENAI_FUNCTIONS_PATH={home_dir}/.config/shell_gpt/functions
OPENAI_USE_FUNCTIONS=true
SHOW_FUNCTIONS_OUTPUT=false
API_BASE_URL=https://api.siliconflow.cn
PRETTIFY_MARKDOWN=true
USE_LITELLM=false
OPENAI_API_KEY={api_key}
SHELL_INTERACTION=true
OS_NAME=auto
SHELL_NAME=auto"""

    # 写入配置文件
    with open(config_file, 'w') as f:
        f.write(config_content)

    print(f"✅ 配置文件已创建: {config_file}")
    print(f"📁 使用的默认模型: {default_model}")
    print(f"👤 用户名: {username}")

    # 创建必要的缓存目录
    cache_dirs = [f"/tmp/chat_cache_{username}", f"/tmp/cache_{username}"]
    for cache_dir in cache_dirs:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            print(f"📁 创建缓存目录: {cache_dir}")
        except PermissionError:
            print(f"⚠️  警告: 无法创建缓存目录 {cache_dir}，运行时可能会自动创建")


def show_menu():
    """显示主菜单"""
    print("\n🎯 请选择操作:")
    print("1️⃣  自动安装并配置Shell-GPT")
    print("2️⃣  选择/切换模型")
    print("3️⃣  重新设置API密钥")
    print("4️⃣  显示当前配置")
    print("0️⃣  退出")
    print("-" * 30)


def get_user_choice() -> str:
    """获取用户选择"""
    while True:
        choice = input("请输入选项 (0-4): ").strip()
        if choice in ['0', '1', '2', '3', '4']:
            return choice
        print("❌ 无效选择，请输入0-4之间的数字")


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

    # 获取可用模型
    print("正在获取可用模型列表...")
    all_models = test_api_connection(api_key, return_models=True)

    if not all_models:
        print("❌ 无法获取模型列表")
        return

    # 过滤模型
    available_models = filter_models(all_models)
    if not available_models:
        print("❌ 未找到支持的模型")
        return

    print(f"\n📋 可用模型 ({len(available_models)}个):")
    for i, model in enumerate(available_models, 1):
        print(f"{i:2d}. {model}")

    print("\n🎯 推荐模型:")
    # 显示推荐模型
    recommended_models = ['moonshotai/Kimi-K2-Instruct', 'deepseek-ai/DeepSeek-V3.1']
    for model in recommended_models:
        if any(model in m for m in available_models):
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

    # 更新配置文件
    home_dir = Path.home()
    config_file = home_dir / '.config' / 'shell_gpt' / '.sgptrc'

    if not config_file.exists():
        print("❌ 配置文件不存在，请先进行完整安装")
        return

    try:
        # 读取现有配置
        with open(config_file, 'r') as f:
            lines = f.readlines()

        # 更新DEFAULT_MODEL行
        with open(config_file, 'w') as f:
            for line in lines:
                if line.strip().startswith('DEFAULT_MODEL='):
                    f.write(f"DEFAULT_MODEL={selected_model}\n")
                else:
                    f.write(line)

        print(f"✅ 模型已切换为: {selected_model}")

    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")


def auto_install(api_key: str) -> bool:
    """自动安装流程"""
    print("\n🚀 开始自动安装Shell-GPT")
    print("=" * 40)

    # 1. 获取可用模型（API已在main()中验证过）
    print("1️⃣ 获取可用模型...")
    all_models = test_api_connection(api_key, return_models=True)
    if not all_models:
        print("⚠️  警告: 无法获取模型列表，将使用默认配置")
        default_model = "moonshotai/Kimi-K2-Instruct"
    else:
        available_models = filter_models(all_models)
        default_model = select_default_model(available_models)
        print(f"✅ 找到 {len(available_models)} 个可用模型")

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


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='Shell-GPT 自动安装配置脚本 v1.3.0',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python setup_shell_gpt.py                        # 交互式菜单
  python setup_shell_gpt.py --key sk-xxx           # 直接指定API密钥
  python setup_shell_gpt.py --auto --key sk-xxx    # 自动安装模式
        """
    )

    parser.add_argument('--key', '-k', help='API密钥')
    parser.add_argument('--auto', '-a', action='store_true', help='自动安装模式（跳过菜单）')

    args = parser.parse_args()

    print("🚀 Shell-GPT 自动安装配置脚本 v1.3.0")
    print("🔒 隐私保护 | 🚄 自动选择最快pip镜像")
    print("=" * 50)

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
