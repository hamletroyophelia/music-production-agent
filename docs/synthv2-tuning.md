# Synthesizer V 2 人声调校参考

本参考用于制作决策，不代替当前工程、声库代际和宿主界面的读取。声库支持的 Vocal Modes、参数范围、显示单位与版本能力可能不同；不从其他声库或旧记录复制数值。

## 身份和面板

- Track Header 设置轨道默认 voice database。所选 Note Group 可在 Voice Panel 分配自己的 Vocal；只有组没有单独分配时才继承轨道默认值。因此每次都核对 track 默认与目标 Group 的实际 Vocal/Voice Part。
- Voice Panel 显示当前 Vocal 与完整 Vocal Modes。Parameter Panel 用于基础参数及随时间变化的自动化；Notes Panel 提供 Sing/Rap 和 Expression Pad 等音符级选项；Piano Roll 的 Phoneme Timing Panel 可编辑音素时间/长度/强度及声库支持的细节。
- 具备 CUA 时，执行者自行从原生界面读取目标 Group、声库身份和完整模式面板，不默认要求用户截图。只有界面不可用或无法辨认时，才请用户补充必要信息。
- 官方脚本 API 不一定能可靠读取当前 Vocal 身份或未修改的默认 Vocal Mode。空结果不代表声库没有 modes；track 默认与 Group Vocal 可能不同。改换 Group 或 Vocal 后重新读取。
- 旧代声库在新编辑器中可能只有部分 V2 功能；查看对应代际官方兼容说明以及当前界面提示，不把旧版兼容声库和 V2-native Vocal 混为一谈。

官方界面名称参见 [Track and Voice Setup](https://sv2.docs.dreamtonics.com/en/voice-setup)、[Base Parameters](https://sv2.docs.dreamtonics.com/en/parameters)、[Pitch](https://sv2.docs.dreamtonics.com/en/pitch) 和 [Pronunciation](https://sv2.docs.dreamtonics.com/en/phonemes)。

## 参数作用与边界

| API 名 / UI 名 | 主要作用 | 边界 |
| --- | --- | --- |
| `pitchDelta` / Pitch Deviation | 微调生成后的音高曲线；不是音符移调。 | 八度或调性变化应改 note pitch 或单一 Reference offset。读已有曲线，避免重复叠加。 |
| `loudness` / Loudness | 表达句内动态强弱。 | 不等于音符音高，也不等于轨道或混音增益。 |
| `tension` / Tension | 调整声线的紧张/放松感。 | 先确认音符没有超出目标声库适宜音区，再用小幅调整。 |
| `breathiness` / Breathiness | 调整气声成分。 | 太多可能增加噪声或削弱字头，太少也可能发闷；不能单独保证咬字清楚。 |
| `voicing` / Voicing | 调整有声周期成分比例。 | 降低可更接近 whisper-like，但不保证生成真实耳语，也可能损失可懂度。 |
| `gender` / Gender | 改变音色厚薄/共振峰印象。 | 属于 timbre，不是 MIDI 音高变化。实际方向/单位以当前声库和界面为准。 |
| `toneShift` / Tone Shift | 改变听感的头声/胸声或音区印象，不改变音符 pitch。 | Dreamtonics 参数说明以当前 UI 描述为准；不要拿它代替八度移调，也不要猜组级和 automation 的单位等价。 |

Mode 的 Pitch、Timbre、Pronunciation 三个维度可分别控制其应用程度，但它们不保证最终合成是互不影响的线性相加。组级值与 automation points 是不同存储层；官方文档/API 未必规定统一的相加或覆盖关系。读取二者并以当前宿主呈现/渲染行为为依据，不自行合并数值。

范围和单位必须从当前宿主读取。对 automation，查询当前定义的 `displayName`、`typeName`、`range` 和 `defaultValue`；对未暴露为 automation 的组级控件，从当前 Voice Panel 读取。不要混用 UI 百分比、dB、cents 和归一化 API 值。宿主未提供可确认范围时，不猜测或写入。

参考：[Dreamtonics Base Parameters](https://sv2.docs.dreamtonics.com/en/parameters)、[Automation API](https://resource.dreamtonics.com/scripting/Automation.html)、[NoteGroupReference API](https://resource.dreamtonics.com/scripting/NoteGroupReference.html)。

## 调校顺序

1. **先校时间和歌词。**确认 tempo、目标段落、Group 起止、note onset/duration、语言、歌词/音素映射和休止。歌词关系未明时不靠 Vocal Mode 遮盖错位；见[对齐参考](alignment-and-visual-diagnostics.md)。
2. **再定实际音域。**检查 MIDI note pitch 与伴奏/目标声部。整段八度移调只使用一种方式：改目标音符 pitch，或对对应 NoteGroupReference 设置 `pitchOffset`。`absolutePitch` 已包含 Reference offset；不要在它上面再次扣 offset。`pitchDelta` 也不是八度移调。
3. **然后调声线。**确认当前 Vocal 支持的模式，再根据问题调整 Pitch、Timbre、Pronunciation。之后才考虑 tension、breathiness、voicing、gender、toneShift。每次只改与症状相关的一两个维度，依当前声库的小幅范围推进。
4. **最后修局部音素和表情。**字已落在正确音符但字头不清时，使用 Phoneme Timing Panel 调相邻辅音/元音；不要平移整句来补一个辅音。只对目标问题做一次定向确认，不新增重复试听/全曲 QA 门槛。

## 症状到调整顺序

| 症状 | 顺序 | 证据限制 |
| --- | --- | --- |
| 歌词发音错或不清 | Group Vocal、语言、歌词到 phoneme 映射和 note 时序 → 乐句边界 → Phoneme Timing → 适用时 Pronunciation/Mouth Opening | 波形、频谱和 F0 不能证明咬字自然或可懂。 |
| 旋律太高/太低 | 核对 note pitch 和伴奏 → 决定一个移调位置 → 检查 absolute pitch | 不把 Pitch Deviation 当移调。 |
| 音高正确但听感太亮、太高或太薄 | 先试 Timbre mode，再查 Tone Shift 的音区印象；确有需要才动 Gender | 音色变化不应误改音符 pitch。 |
| 紧、硬或喊 | 排除音域过高 → 适度降低 Tension → 调 Timbre → 少量处理 Breathiness/Loudness | 参数方向与范围需当前宿主确认。 |
| 需要耳语结尾 | 若 Vocal 有 Whisper mode，先确认并只对局部使用；否则谨慎调低 Voicing、少量增 Breathiness、保留字头 | Rap 是说唱音高/语调模式，不是 whisper 开关。低 Voicing 也不保证自然耳语。 |
| 呼吸噪声或闷 | 小幅调整 Breathiness；字头仍不清时检查 phoneme timing/strength | 继续堆气声可能损害可懂度。 |
| 音符曲线生硬 | 确认 Sing/Rap、Expression Pad 和 mode Pitch 维度；需要时按官方功能编辑曲线 | 只对用户授权范围编辑；不例行重抽或重复 QA。 |

读数/写入记录只需说明编辑器版本、track/Group、track 默认与组级 Vocal、模式及其当前维度、宿主返回的参数范围、改动区域和未检查项。不能把数值/频谱结果表述成试听，也不据此声称自然或通过听感验收。

## 官方资料

- Dreamtonics 用户手册：[Track and Voice Setup](https://sv2.docs.dreamtonics.com/en/voice-setup)、[Base Parameters](https://sv2.docs.dreamtonics.com/en/parameters)、[Pitch](https://sv2.docs.dreamtonics.com/en/pitch)、[Pronunciation](https://sv2.docs.dreamtonics.com/en/phonemes)、[Voice compatibility limitations](https://sv2.docs.dreamtonics.com/en/limitation)。
- Dreamtonics scripting API：[Automation](https://resource.dreamtonics.com/scripting/Automation.html)、[NoteGroupReference](https://resource.dreamtonics.com/scripting/NoteGroupReference.html)。
