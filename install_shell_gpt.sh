#!/bin/bash
#
# Shell-GPT 一键安装脚本
# 支持 Gitee / GitCode / jsDelivr / GitHub 多源下载，自动选择可用源
#
# 使用方法:
#   bash <(curl -fsSL https://gitee.com/JohnnyChen1113/biotrainee/raw/main/install_shell_gpt.sh)
#   bash <(curl -fsSL https://gitcode.com/JohnnyChen1113/biotrainee/raw/main/install_shell_gpt.sh)
#   bash <(curl -fsSL https://cdn.jsdelivr.net/gh/JohnnyChen1113/biotrainee@main/install_shell_gpt.sh)
#
# @Author: 卖萌哥
# @Version: 1.0.2
#

echo "========================================"
echo "   Shell-GPT 一键安装脚本"
echo "========================================"
echo ""

REPO_OWNER="${SGPT_REPO_OWNER:-JohnnyChen1113}"
REPO_NAME="${SGPT_REPO_NAME:-biotrainee}"
REPO_BRANCH="${SGPT_REPO_BRANCH:-main}"
SETUP_FILE="setup_shell_gpt.py"

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

check_curl() {
    if ! command -v curl &> /dev/null; then
        echo "❌ 未检测到 curl，无法自动下载安装脚本"
        echo "安装建议:"
        echo "  Ubuntu/Debian: sudo apt install curl"
        echo "  CentOS/RHEL:   sudo yum install curl"
        echo "  macOS:         brew install curl"
        exit 1
    fi
}

build_script_urls() {
    # 如果用户指定了 SGPT_SETUP_URL，只从这个地址下载，方便把脚本挂到任意托管站。
    if [ -n "${SGPT_SETUP_URL:-}" ]; then
        printf '%s\n' "$SGPT_SETUP_URL"
        return
    fi

    cat <<EOF
https://gitee.com/${REPO_OWNER}/${REPO_NAME}/raw/${REPO_BRANCH}/${SETUP_FILE}
https://gitcode.com/${REPO_OWNER}/${REPO_NAME}/raw/${REPO_BRANCH}/${SETUP_FILE}
https://cdn.jsdelivr.net/gh/${REPO_OWNER}/${REPO_NAME}@${REPO_BRANCH}/${SETUP_FILE}
https://raw.githubusercontent.com/${REPO_OWNER}/${REPO_NAME}/${REPO_BRANCH}/${SETUP_FILE}
EOF
}

# 尝试从多个源下载
download_script() {
    local tmp_file
    tmp_file="$(mktemp "/tmp/setup_shell_gpt_XXXXXX.py")" || return 1

    while IFS= read -r url; do
        [ -z "$url" ] && continue
        # 提取域名用于显示
        local domain=$(echo "$url" | sed -E 's|https?://([^/]+)/.*|\1|')
        echo "📥 尝试下载: $domain ..." >&2

        if curl -fsSL "$url" -o "$tmp_file" --connect-timeout 10 --max-time 60 2>/dev/null; then
            # 验证下载的文件是否为有效的 Python 脚本
            if (head -1 "$tmp_file" 2>/dev/null | grep -q "python" || head -5 "$tmp_file" 2>/dev/null | grep -q "Shell-GPT") \
                && PYTHONPYCACHEPREFIX=/tmp "$PYTHON_CMD" -m py_compile "$tmp_file" 2>/dev/null; then
                echo "✅ 下载成功!" >&2
                echo "$tmp_file"
                return 0
            else
                echo "⚠️  下载的文件无效或语法校验失败，尝试下一个源..." >&2
                : > "$tmp_file"
            fi
        else
            echo "⚠️  下载失败，尝试下一个源..." >&2
        fi
    done <<EOF
$(build_script_urls)
EOF

    echo "" >&2
    echo "❌ 所有下载源都失败了" >&2
    echo "" >&2
    echo "请尝试手动下载运行:" >&2
    echo "  curl -fsSL -o setup_shell_gpt.py https://gitee.com/${REPO_OWNER}/${REPO_NAME}/raw/${REPO_BRANCH}/${SETUP_FILE}" >&2
    echo "  python3 setup_shell_gpt.py" >&2
    rm -f "$tmp_file"
    return 1
}

# 主流程
main() {
    check_python
    check_curl
    echo ""

    # 下载脚本
    SCRIPT_FILE=$(download_script)
    if [ $? -ne 0 ] || [ -z "$SCRIPT_FILE" ]; then
        exit 1
    fi

    echo ""
    echo "🚀 启动安装程序..."
    echo ""

    # 运行 Python 脚本，传递所有参数
    PYTHONPYCACHEPREFIX=/tmp "$PYTHON_CMD" "$SCRIPT_FILE" "$@"
    EXIT_CODE=$?

    # 清理临时文件
    rm -f "$SCRIPT_FILE"

    exit $EXIT_CODE
}

main "$@"
