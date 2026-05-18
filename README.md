# auto-shell-gpt

Shell-GPT 自动安装和配置工具,专门为**国内教学场景**优化。

接入 [SiliconFlow](https://siliconflow.cn/) 的 LLM API,**全程走国内镜像源**,在严格白名单网络下也能装上。

## 特性

- 🐍 **Portable Python 3.12** — 从国内大学镜像(USTC/NJU/TUNA/SJTU/BFSU/HFUT)下载独立 Python,绕开系统 Python 版本不兼容
- 🌐 **多源 PyPI failover** — 8 个国内 PyPI 镜像自动按速度排序,挂一个自动切下一个
- 🧠 **真实模型可用性检测** — 并发 ping 候选模型,只保留实际能调用的
- 🎯 **白名单模型** — 9 个 SiliconFlow 免费模型(DeepSeek-V4-Flash、Qwen3.6、GLM-4.5、Step-3.5 等)
- 🔒 **安全** — 配置文件自动 chmod 600,API key 不会被同机器其他用户读到
- 🧹 **一键卸载** — 完全恢复安装前状态,不留痕

## 快速开始

```bash
pip install -i https://repo.huaweicloud.com/repository/pypi/simple auto-shell-gpt && \
  ~/.local/bin/auto-shell-gpt --auto --key sk-YOUR_SILICONFLOW_KEY
```

> 💡 **不要**用 `python -m setup_shell_gpt`,也不要直接敲 `auto-shell-gpt`,原因:
> - **`python -m setup_shell_gpt`**: 把 cwd 放在 sys.path 第一位,如果当前目录或 home 目录有同名老脚本,会被它覆盖而不是用 pip 装的新版本(教学环境常见预置老脚本就触发这个坑)
> - **直接敲 `auto-shell-gpt`**: 依赖 `~/.local/bin` 在 PATH 里,新建账号第一次登录时这个目录不存在,PATH 里没有它
>
> **直接用绝对路径 `~/.local/bin/auto-shell-gpt`** 同时绕开两个坑:不查 PATH、不走 cwd 模块搜索,**总是**调用 pip 装的最新版。
>
> 如果嫌长,把 `~/.local/bin` 加进 PATH 后可以敲 `auto-shell-gpt`:
> ```bash
> echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
> ```

装完之后:

```bash
sgpt --code 'solve fizz buzz problem using python'
sgpt --shell '帮我生成10个file开头的文件'
```

## 切换模型 / 重设 key / 查看配置

```bash
auto-shell-gpt           # 进入交互菜单
```

## 卸载

```bash
~/.local/bin/auto-shell-gpt --uninstall
```

会清理:`~/.config/shell_gpt/`、`/tmp/chat_cache_*`、`/tmp/cache_*`、`~/.cache/shell_gpt`、`~/.local/share/sgpt-portable-python/`、`~/.local/bin/sgpt`。

## 注册获取 API key

新用户用以下链接注册可获得**双倍免费额度**:

🔗 https://cloud.siliconflow.cn/i/pnTWTpiB

## 详细文档 & 源码

https://github.com/JohnnyChen1113/biotrainee

## License

MIT
