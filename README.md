# Music Production Agent

面向 Synthesizer V Studio 2 Pro 与 REAPER 的音乐制作 Agent 工作流。覆盖歌词与旋律对齐、声库调参、编曲混音、原生导出和已有工程续作。

**这是工作流与本地工具集成模板。** 使用者需自行安装 DAW、取得声库/插件许可，并连接对应 MCP 桥。仓库不包含歌曲素材、声库、插件、个人安装清单或制作会话。

## 工作方式

- 主控理解需求并交付；规划者只做必要规划和资料诊断；执行者连续实施。
- 同一时刻只允许一个 DAW/UI 写入者，避免焦点、剪贴板和工程冲突。
- 以已有工程和最新用户反馈接续工作，不因旧状态表重新制作。
- 频谱、波形和数值只解决具体问题，不冒充试听或证明发音自然。
- 音量包络区分 dB、线性增益和宿主推子刻度；比较人声与伴奏时使用同一信号阶段。
- 只做与改动相关的必要确认，不把阶段记录变成反复验收门槛。

## 目录

| 目录 | 内容 |
| --- | --- |
| `skills/` | 音乐总流程、REAPER、SynthV 三个技能入口 |
| `docs/` | 对齐、SynthV 调参、混音与恢复经验 |
| `agents/` | 规划者与执行者角色模板 |
| `config/` | Codex 项目配置范例 |
| `scripts/music_job.py` | 本地状态与交接记录工具；不操作 DAW、不调用模型 |
| `integrations/reaper/` | 推子刻度修复补丁及应用说明 |
| `tests/` | 状态脚本的离线测试 |

## 使用

1. 将仓库放入独立目录，先读 [工作流](docs/workflow.md)。
2. 按 [Reaper-MCP](https://github.com/xDarkzx/Reaper-MCP) 和 [SynthV Agent Bridge](https://github.com/SynthVCopilot/synthv-agent-bridge) 的说明安装并配置桥接；需要旧版刻度修复时见 [补丁说明](integrations/reaper/README.md)。
3. 按 `config/codex.example.toml` 的注释配置自己的项目。模型沿用会话配置，或选用当前账户实际可用的模型；本项目不要求特定型号。
4. 在 Codex 中打开仓库，让 Agent 读取 `AGENTS.md`。若使用技能发现机制，将这些技能按宿主支持的方式注册；保留它们与 `docs/` 的相对位置。
5. 把真实素材、工程与生成内容放在被 Git 忽略的目录或仓库外。描述当前目标、权威工程、需要的输出及具体听感反馈。

配置字段以 [OpenAI 官方配置参考](https://learn.chatgpt.com/docs/config-file/config-reference) 为准；角色配置的相对路径以声明它的配置文件为基准。

查看状态脚本参数：

```sh
python3 scripts/music_job.py --help
```

状态工具记录进度，不代表任何阶段听感通过。制作不需要运行代码测试；修改该辅助脚本时可运行其离线测试。

## 发布边界

已将个人路径改为相对引用或配置占位符；未包含历史提交、歌曲材料或运行日志。后续提交请遵循 [隐私说明](PRIVACY.md)。第三方来源与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
