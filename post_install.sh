#!/bin/bash
# ============================================================================
# 🍎 Python 3.12 装好后，自动配置项目环境
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_step() { echo -e "\n${BLUE}━━━ $1 ━━━${NC}"; }
print_ok()   { echo -e "${GREEN}✓ $1${NC}"; }
print_warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
print_err()  { echo -e "${RED}✗ $1${NC}"; }

# ─────────────────────────────────────────────
# 1. 找 Python 3.12
# ─────────────────────────────────────────────
print_step "1/5：定位 Python 3.12"

if ! command -v python3.12 &> /dev/null; then
    print_err "找不到 python3.12！"
    echo "官方 .pkg 默认装到：/Library/Frameworks/Python.framework/Versions/3.12/bin/python3.12"
    exit 1
fi

PY312_PATH="$(command -v python3.12)"
PY312_BIN="$(dirname "$PY312_PATH")"
print_ok "Python 3.12 路径：$PY312_PATH"
print_ok "Python 版本：$(python3.12 --version)"

# ─────────────────────────────────────────────
# 2. 配 PATH（按 shell 自动选文件）
# ─────────────────────────────────────────────
print_step "2/5：配置 PATH"

# 决定 shell rc 文件
if [[ "$SHELL" == */bash ]]; then
    SHELL_RC="$HOME/.bash_profile"
    [[ ! -f "$SHELL_RC" ]] && SHELL_RC="$HOME/.bashrc"
else
    SHELL_RC="$HOME/.zshrc"
fi
print_ok "当前 shell: $SHELL → 写入: $SHELL_RC"

# 检查是否已经配置过
if grep -qF "$PY312_BIN" "$SHELL_RC" 2>/dev/null; then
    print_ok "PATH 已配置，跳过"
else
    {
        echo ""
        echo "# Python 3.12（手机号去重工具需要）"
        echo "export PATH=\"$PY312_BIN:\$PATH\""
        echo "alias python3=\"python3.12\""
        echo "alias pip=\"python3.12 -m pip\""
    } >> "$SHELL_RC"
    print_ok "已写入 $SHELL_RC"
fi

# 当前 shell 立即生效
export PATH="$PY312_BIN:$PATH"
alias python3="python3.12" 2>/dev/null || true

# 验证
PY_AFTER=$(which python3)
PY_VER_AFTER=$(python3 --version)
print_ok "python3 → $PY_AFTER  ($PY_VER_AFTER)"

# ─────────────────────────────────────────────
# 3. 升级 pip
# ─────────────────────────────────────────────
print_step "3/5：升级 pip"

python3.12 -m pip install --upgrade --quiet --disable-pip-version-check pip 2>&1 | tail -2
print_ok "pip：$(python3.12 -m pip --version | head -c 50)..."

# ─────────────────────────────────────────────
# 4. 装项目依赖
# ─────────────────────────────────────────────
print_step "4/5：安装项目依赖"

cd "$(dirname "$0")"
print_ok "项目目录：$(pwd)"

if [[ ! -f "requirements.txt" ]]; then
    print_err "找不到 requirements.txt"
    exit 1
fi

echo -e "${YELLOW}安装中（约 30-60 秒）...${NC}"
python3.12 -m pip install --quiet --disable-pip-version-check -r requirements.txt
print_ok "依赖装完"

# ─────────────────────────────────────────────
# 5. 自测服务能起
# ─────────────────────────────────────────────
print_step "5/5：自测（不真启动）"

# 检查关键文件
for f in server.py start.py config.py requirements.txt; do
    if [[ -f "$f" ]]; then
        print_ok "$f 存在"
    else
        print_err "$f 缺失！"
    fi
done

# 验证关键包
for pkg in pandas numpy fastapi uvicorn; do
    if python3.12 -c "import $pkg; print('$pkg', $pkg.__version__)" 2>/dev/null; then
        :
    else
        print_err "$pkg 没装上！"
    fi
done

# ─────────────────────────────────────────────
echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🎉 配置完成！现在可以启动了${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "下一步："
echo -e "  ${BLUE}cd ~/Desktop/手机号${NC}"
echo -e "  ${BLUE}python3 server.py${NC}"
echo ""
echo "或者（推荐，自动打开浏览器）："
echo -e "  ${BLUE}python3 start.py${NC}"
echo ""
