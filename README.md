# auto-shell-gpt

Shell-GPT 自动安装和配置工具,专门为**国内教学场景**优化。

接入 [SiliconFlow](https://siliconflow.cn/) 的 LLM API,**全程走国内镜像源**,在严格白名单网络下也能装上。

## 特性

- 🐍 **Portable Python 3.12** — 从国内大学镜像(USTC/NJU/TUNA/SJTU/BFSU/HFUT)下载独立 Python,绕开系统 Python 版本不兼容
- 🌐 **多源 PyPI failover** — 8 个国内 PyPI 镜像自动按速度排序,挂一个自动切下一个
- 🧠 **真实模型可用性检测** — 并发 ping 候选模型,只保留实际能调用的
- 🎯 **白名单模型** — 10 个 SiliconFlow 候选模型(默认 DeepSeek-V4-Pro，另含 DeepSeek-V4-Flash、Qwen3.6、GLM-4.5、Step-3.5 等)
- 🔒 **安全** — 配置文件自动 chmod 600,API key 不会被同机器其他用户读到
- 🧹 **一键卸载** — 完全恢复安装前状态,不留痕

## 快速开始(第一次安装)

```bash
pip install --no-warn-script-location -i https://repo.huaweicloud.com/repository/pypi/simple auto-shell-gpt && \
  export PATH="$HOME/.local/bin:$PATH" && \
  auto-shell-gpt --auto --key sk-YOUR_SILICONFLOW_KEY
```

三步 `&&` 串联:静默装包 → 临时给当前 shell 的 PATH 加上 `~/.local/bin` → 直接跑 `auto-shell-gpt`。

**为什么需要 `export PATH`**:pip `--user` 把 CLI 入口装到 `~/.local/bin/`,但**新建账号第一次登录时这个目录还不存在**,所以 `.profile` 跳过了把它加进 PATH 的判断。`export` 那一步在**当前 shell**临时补上,跑完之后 v1.12.1 的脚本**会自动把这行 export 持久化到 `~/.bashrc`**,**下次新开终端就再也不用这一步**。

## 之后任何时候(新 shell 直接短命令)

```bash
sgpt --code 'solve fizz buzz problem using python'
sgpt --shell '帮我生成10个file开头的文件'

# 切模型 / 重设 key / 查看配置
auto-shell-gpt

# 完全卸载
auto-shell-gpt --uninstall
```

会清理:`~/.config/shell_gpt/`、`/tmp/chat_cache_*`、`/tmp/cache_*`、`~/.cache/shell_gpt`、`~/.local/share/sgpt-portable-python/`、`~/.local/bin/sgpt`。

## 注册获取 API key

新用户用以下链接注册可获得**双倍免费额度**:

🔗 https://cloud.siliconflow.cn/i/pnTWTpiB

## 详细文档 & 源码

https://github.com/JohnnyChen1113/biotrainee

## License

MIT
