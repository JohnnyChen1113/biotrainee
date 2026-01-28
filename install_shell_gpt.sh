#!/bin/bash
#
# Shell-GPT 一键安装脚本
# 支持多源下载，自动选择可用源
#
# 使用方法:
#   bash <(curl -fsSL https://cdn.jsdelivr.net/gh/JohnnyChen1113/biotrainee@main/install_shell_gpt.sh)
#
# @Author: 卖萌哥
# @Version: 1.0.0
#

set -e

echo "========================================"
echo "   Shell-GPT 一键安装脚本"
echo "========================================"
echo ""

# 检查 Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        echo "✓ 检测到 Python: $(python3 --version)"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        echo "✓ 检测到 Python: $(python --version)"
    else
        echo "❌ 未检测到 Python，请先安装 Python 3.8+"
        echo ""
        echo "安装建议:"
        echo "  Ubuntu/Debian: sudo apt install python3"
        echo "  CentOS/RHEL:   sudo yum install python3"
        echo "  macOS:         brew install python3"
        exit 1
    fi
}

# 下载脚本的多个源
SCRIPT_URLS=(
    "https://cdn.jsdelivr.net/gh/JohnnyChen1113/biotrainee@main/setup_shell_gpt.py"
    "https://raw.githubusercontent.com/JohnnyChen1113/biotrainee/main/setup_shell_gpt.py"
    "https://gitcode.com/JohnnyChen1113/biotrainee/raw/main/setup_shell_gpt.py"
)

# 尝试从多个源下载
download_script() {
    local tmp_file="/tmp/setup_shell_gpt_$$.py"

    for url in "${SCRIPT_URLS[@]}"; do
        echo "📥 尝试下载: ${url%%/setup*}..."
        if curl -fsSL "$url" -o "$tmp_file" --connect-timeout 10 2>/dev/null; then
            # 验证下载的文件是否为有效的 Python 脚本
            if head -1 "$tmp_file" | grep -q "python" 2>/dev/null || head -5 "$tmp_file" | grep -q "Shell-GPT" 2>/dev/null; then
                echo "✅ 下载成功!"
                echo "$tmp_file"
                return 0
            else
                echo "⚠️  下载的文件无效，尝试下一个源..."
                rm -f "$tmp_file"
            fi
        else
            echo "⚠️  下载失败，尝试下一个源..."
        fi
    done

    echo ""
    echo "❌ 所有下载源都失败了"
    echo ""
    echo "请尝试手动下载运行:"
    echo "  curl -O ${SCRIPT_URLS[0]}"
    echo "  python3 setup_shell_gpt.py"
    return 1
}

# 主流程
main() {
    check_python
    echo ""

    # 下载脚本
    SCRIPT_FILE=$(download_script)
    if [ $? -ne 0 ]; then
        exit 1
    fi

    echo ""
    echo "🚀 启动安装程序..."
    echo ""

    # 运行 Python 脚本，传递所有参数
    $PYTHON_CMD "$SCRIPT_FILE" "$@"
    EXIT_CODE=$?

    # 清理临时文件
    rm -f "$SCRIPT_FILE"

    exit $EXIT_CODE
}

main "$@"
