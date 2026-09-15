#!/bin/bash
# ============================================================================
# 🛠 Mac 开发环境一键配置脚本 - 手机号去重工具
#
# 功能：
#   1. 检查/安装 Homebrew
#   2. 安装 Python 3.12（跳过 brew 自动更新避免卡 GitHub）
#   3. 配置 PATH（bash → ~/.bash_profile / ~/.bashrc，zsh → ~/.zshrc）
#   4. 升级 pip
#   5. 安装项目依赖
#
# 使用方法（在你的 Mac 上运行）：
#   cd ~/Desktop/手机号
#   bash setup_mac.sh
#
# 预计耗时：3-5 分钟（取决于网速）
# ============================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}▶ $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_ok() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warn() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_err() {
    echo -e "${RED}✗ $1${NC}"
}

# 检查是否是 macOS
if [[ "$(uname)" != "Darwin" ]]; then
    print_err "这个脚本只能在 macOS 上运行！"
    exit 1
fi

# 检测用户的 shell，决定 RC 文件写到哪里
# macOS 10.15+ 默认 zsh，但很多用户手动改成 bash
SHELL_RC=""
if [[ "$SHELL" == */bash ]]; then
    if [[ -f "$HOME/.bash_profile" ]]; then
        SHELL_RC="$HOME/.bash_profile"
    else
        SHELL_RC="$HOME/.bashrc"
    fi
elif [[ "$SHELL" == */zsh ]]; then
    SHELL_RC="$HOME/.zshrc"
else
    # 兜底
    SHELL_RC="$HOME/.zshrc"
fi

# ─────────────────────────────────────────────
# 步骤 1：检查 Homebrew
# ─────────────────────────────────────────────
print_step "步骤 1/5：检查 Homebrew"

if command -v brew &> /dev/null; then
    BREW_VERSION=$(brew --version | head -1)
    print_ok "Homebrew 已安装：$BREW_VERSION"
else
    print_warn "Homebrew 未安装，开始安装..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Apple Silicon 上 brew 默认装在 /opt/homebrew，Intel 在 /usr/local
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        print_ok "Homebrew 安装完成（Apple Silicon）"
    else
        eval "$(/usr/local/bin/brew shellenv)" 2>/dev/null || true
        print_ok "Homebrew 安装完成（Intel）"
    fi
fi

# 关掉 brew 自动更新（避免再卡 GitHub Container Registry）
export HOMEBREW_NO_AUTO_UPDATE=1
export HOMEBREW_NO_ENV_HINTS=1

# ─────────────────────────────────────────────
# 步骤 2：安装 Python 3.12
# ─────────────────────────────────────────────
print_step "步骤 2/5：安装 Python 3.12"

if command -v python3.12 &> /dev/null; then
    PY_VERSION=$(python3.12 --version)
    print_ok "Python 3.12 已安装：$PY_VERSION"
else
    print_warn "开始安装 Python 3.12（约 1-2 分钟，不会自动更新 brew）..."
    brew install python@3.12

    # 链接到 brew 的 bin 目录
    brew link python@3.12 --force --overwrite 2>/dev/null || true

    PY_VERSION=$(python3.12 --version)
    print_ok "Python 3.12 安装完成：$PY_VERSION"
fi

# ─────────────────────────────────────────────
# 步骤 3：配置 PATH
# ─────────────────────────────────────────────
print_step "步骤 3/5：配置 PATH（写入 $SHELL_RC）"

# 找 python3.12 的实际 bin 目录
# 优先级：1) command -v  2) brew 已知路径（Intel / Apple Silicon）
PY312_BIN=""

if command -v python3.12 &> /dev/null; then
    PY312_BIN="$(dirname "$(command -v python3.12)")"
fi

if [[ -z "$PY312_BIN" || ! -x "$PY312_BIN/python3.12" ]]; then
    for candidate in \
        "/usr/local/opt/python@3.12/bin" \
        "/opt/homebrew/opt/python@3.12/bin"; do
        if [[ -x "$candidate/python3.12" ]]; then
            PY312_BIN="$candidate"
            break
        fi
    done
fi

if [[ -z "$PY312_BIN" ]]; then
    print_err "找不到 python3.12 的 bin 目录"
    echo "请手动查找：which python3.12"
    exit 1
fi

print_ok "Python 3.12 bin 目录：$PY312_BIN"

# 检查 shell rc 里是否已经有
if grep -qF "$PY312_BIN" "$SHELL_RC" 2>/dev/null; then
    print_ok "$SHELL_RC 里已有 Python 3.12 PATH，跳过"
else
    {
        echo ""
        echo "# Python 3.12（手机号去重工具需要）"
        echo "export PATH=\"$PY312_BIN:\$PATH\""
    } >> "$SHELL_RC"
    print_ok "已把 Python 3.12 加到 $SHELL_RC"
fi

# 关掉 Homebrew 自动更新（避免网络卡顿）
if grep -qF "HOMEBREW_NO_AUTO_UPDATE" "$SHELL_RC" 2>/dev/null; then
    print_ok "HOMEBREW_NO_AUTO_UPDATE 已配置"
else
    {
        echo ""
        echo "# 关闭 Homebrew 自动更新（避免网络卡 GitHub Container Registry）"
        echo "export HOMEBREW_NO_AUTO_UPDATE=1"
        echo "export HOMEBREW_NO_ENV_HINTS=1"
    } >> "$SHELL_RC"
    print_ok "已关掉 Homebrew 自动更新"
fi

# 当前 shell 也生效（不重启终端）
export PATH="$PY312_BIN:$PATH"

# 验证
PY_AFTER=$(which python3)
print_ok "当前 python3 指向：$PY_AFTER"
PY_VER_AFTER=$($PY_AFTER --version)
print_ok "Python 版本：$PY_VER_AFTER"

if [[ "$PY_VER_AFTER" != *"3.12"* ]]; then
    print_err "Python 版本不对！预期 3.12，实际：$PY_VER_AFTER"
    print_warn "请新开一个终端再运行此脚本"
    exit 1
fi

# ─────────────────────────────────────────────
# 步骤 4：升级 pip
# ─────────────────────────────────────────────
print_step "步骤 4/5：升级 pip"

python3 -m pip install --upgrade --quiet --disable-pip-version-check pip 2>&1 | tail -3
PIP_VERSION=$(python3 -m pip --version)
print_ok "pip 版本：$PIP_VERSION"

# ─────────────────────────────────────────────
# 步骤 5：安装项目依赖
# ─────────────────────────────────────────────
print_step "步骤 5/5：安装项目依赖"

cd "$(dirname "$0")"
print_ok "项目目录：$(pwd)"

if [[ ! -f "requirements.txt" ]]; then
    print_err "找不到 requirements.txt！"
    exit 1
fi

echo ""
echo -e "${YELLOW}开始安装依赖（约 30-60 秒）...${NC}"
python3 -m pip install --quiet --disable-pip-version-check -r requirements.txt
print_ok "依赖安装完成"

# ─────────────────────────────────────────────
# 完成
# ─────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 环境配置完成！${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "现在你可以："
echo ""
echo -e "  ${BLUE}# 启动服务（开发模式）${NC}"
echo -e "  cd ~/Desktop/手机号"
echo -e "  python3 server.py"
echo ""
echo -e "${YELLOW}注意：${NC}"
echo -e "  • ${GREEN}HOMEBREW_NO_AUTO_UPDATE=1${NC} 已配，以后 brew 不会再卡"
echo -e "  • 下次打开终端会自动用 Python 3.12"
echo -e "  • 如果浏览器没自动打开，访问 http://localhost:8765"
echo ""
