# 人声与伴奏对齐及视觉诊断

用于处理音符时间、歌词—音符映射或演唱边界可疑的局部问题。波形、谱图和自动分数提供证据，不等于试听，也不能单独证明音乐正确。

## 快速原则

1. **先统一时间坐标，再移动音符。** 记录 tempo map、拍号、PPQ、弱起、音频零点、小节原点、媒体 position/source offset/playrate，以及各轨是否跟随速度图。PPQ 是 MIDI tick 分辨率，不是速度或歌曲起点。
2. **先判断偏差形状，再决定改动范围。** 残差近似常数时检查全局偏移；随时间增长时检查 tempo map/播放率；在某个小节或乐句突然改变时检查漏数小节、弱起、反复或局部演奏。单个异常不能证明全曲都偏移。
3. **鼓只提供节拍线索。** 鼓点无法推出主唱音高、音域或歌词。鼓和主唱可能切分、前靠或后靠。
4. **区分谱面映射与实际发音。** 已确认的含词 SVP、音节 MIDI 或谱面可以提供计划的字音关系；证明实际演唱的辅音/元音边界则需要对应的人声声学证据。只有伴奏时，不声称恢复了原唱逐字时序。
5. **每轮只解决一个具体问题。** 用稀疏锚点辨认全局/漂移/局部模式，再看存在疑问的乐句。修正解释了观测后停止，不重复同一验证来追求更多数字。

## 1. 时间轴、拍号与残差

用四分音符拍数 `b` 作为内部音乐坐标，以秒 `t` 表示音频时间。恒速段中 `Δt = 60 × Δb / BPM`；变速时按 tempo marker 分段累加。记谱拍感和 MIDI 四分音符速度可能不同，例如复合拍号的强拍感觉不改变 PPQ 的 tick 定义。

开始前记录音频 `t=0` 对应文件头、第一拍、首次可辨识起音或其他事件；记录 `b=0`、小节编号、弱起和不完整小节。确认工程、轨道、媒体项的 timebase 与版本，不能因为项目条目都显示在第一小节就假设时间原点一致。弱起或不完整小节不意味着应把首个声音挪到完整小节线。

选取问题段开头、中部、结尾的多个非重复锚点。锚点可以是清楚的辅音/元音转换、人声 note attack、和弦变化、小节线或非重复的乐器起音。对每点记录计划拍数 `bᵢ`、计划秒数 `tᵢ`、观测时间 `tᵢ(obs)`、证据来源和置信度，并计算 `eᵢ = tᵢ(obs) − tᵢ`。

- **全局偏移：** `eᵢ` 近似常数。先核对文件头静音、弱起、延迟和 item position；有共同偏移证据后才移动一次。
- **线性漂移：** 残差随时间增加/减少。核对四分音符速度口径、tempo map、PPQ 换算和播放率；不要连续切片追赶。
- **局部跳变：** 跳变前后各自稳定。查漏掉的半小节/小节、反复、歌词拆分、休止、变拍和表演处理，只改相关范围。
- **无清楚趋势：** 可能是锚点错误、rubato、切分、瞬态不明显或版本不一致。补一项独立局部证据并降低结论置信度，不立即整体移动或拉伸。

偏差模型是工程诊断方法，不是自动分类定理。演唱会前靠/后靠拍点，观测差异不都意味着 MIDI 或工程错误。

## 2. 波形、谱图与音高证据

REAPER 媒体项谱图和 JS Spectrograph Meter、STFT、CQT/chroma 可作为视觉辅助。FFT 窗口越长，频率分辨率通常越高而时间边界越模糊；短窗适合瞬态。48 kHz 下可把 `n_fft=1024/2048`、`hop=240/480` 作为辅音/瞬态的起始设置，把 `4096` 或更大的窗作为谐波起始设置；按音域、采样率和目标调整。

同一张诊断图至少保持人声、伴奏、拍点、音符和时间轴一致，标出版本、时间范围、采样率、窗长/hop、频率轴、色标和缩放。A/B 不分别自动归一化。FFT 平均谱没有时间位置；频谱峰不能直接视为音符、元音或辅音的精确边界。

| 方法 | 可支持的判断 | 不能单独证明 |
| --- | --- | --- |
| 波形 | 相同录音/同源 stem 的静音、削波、稳定延迟 | 不同录音逐样本对齐、旋律/歌词正确 |
| 谱图 | 能量变化、谐波、辅音瞬态、有声/无声候选 | 歌词可懂、咬字自然、精确 pitch 真值 |
| 起音包络 | 节奏轮廓或候选拍点 | 某一峰就是人声音符起点；鼓、辅音和音色变化都能成峰 |
| 互相关 | 相似信号在有限范围内的共同延迟 | 重复鼓型的唯一偏移、局部漂移；周期信号可产生多峰 |
| DTW/chroma | 相似结构的分段匹配候选 | 正确歌词映射或任意拉伸许可；宽路径可能吞掉错小节 |
| F0 | 清晰单声部或可靠人声 stem 的基频走势 | 多音、合唱、气声、泛音和分离伪影中的真实音高 |

音高曲线需留出低置信和无声帧。Chroma 将不同八度的同音级聚合，适合音级/结构线索，不确定主唱八度。混响、压缩、遮蔽和源分离都可能模糊边界。

## 3. 歌词、旋律与伴奏的证据边界

歌词对齐沿“短语 → 词 → 音节/音素”细化。有参考人声时，先找清楚的爆破、摩擦、鼻音等声母线索，再看元音核、音高转折和延音。字头、辅音起点、MIDI note onset 与元音开始不必重合；不能给所有字套统一辅音提前量。长元音、连音、气声与装饰音会让普通说话模型时长假设失配。

和弦、bass、调内音和 chroma 可作为音乐上下文；旋律可以有经过音、挂留音、非和弦音和八度。鼓可定拍，不可补出主唱高低或逐字歌词。没有主旋律声轨、谱面、MIDI 或可靠人声 stem 时，把结果标为候选，不能宣称精确转写。

### 有含词 SVP 与主旋律 MIDI，但没有原唱录音

1. 分开指定职责：伴奏/工程给时间轴和结构；确认过的 Voice MIDI 给主旋律节奏和音高；含词 SVP 给现有歌词—音符关系。原 SVP 是迁移起点，不保证当前每句都正确；LRC 通常只定位歌词行。
2. 把 SVP Group Reference 时间/移调与 MIDI PPQ 映射到共同四分音符拍数，再按目标 tempo map 换算秒。保留弱起、休止、段落和反复次数。
3. 若同一乐句的音符顺序、音程、相对起音、时值比例和休止一致，直接迁移已有字音关系，仅做坐标换算。不要对唯一匹配的句子运行复杂识别。
4. 拆并不一一对应时，限定在同一乐句和同次反复，按移调不变的音程走势、相对时值、起音间隔、休止和句首/句尾锚点做单调匹配。不得只按音符索引或字符数均分；限制跨休止、跨乐句、跨副歌的匹配。
5. 保留一字多音、多 mora 和源音素顺序。日语拗音等多字符音节不可按 Unicode 字符机械拆开；一字多音延唱通常只保留一次字头辅音。多音节合并只有在旋律时值允许时才做，其余记为局部冲突。
6. 先锁定歌词和音符关系，再调 Phoneme Timing Panel 的目标辅音/元音边界；不要整句平移来修一个辅音。只放大冲突乐句，唯一匹配句进入制作。

映射记录可用：`section / occurrence / phrase / source_note_ids / target_note_ids / lyric / phonemes / beat_on / beat_off / match_reason / unresolved_reason`。匹配分数只用于排序疑点，未经校准不得称为正确率。自身 SynthV 干声与 MIDI 一致只说明渲染遵循工程，不证明歌词原先映射正确。

### 有同版本原唱参考时

用已知歌词、参考人声、主旋律线索和乐句边界做分段对齐。干声优先；使用分离音频时保留原始时间坐标并记录分离不确定性。已知全文约束可以减少重新识别全文造成的错字；模型音素边界仍需对应人声证据，不能强迫它等于 MIDI note onset。

强制对齐工具需确认支持目标语言字典/音素和歌唱时长；一般语音模型不一定适合日语长元音、连音、气声。原唱不存在时继续用谱面和 MIDI 关系，不等待或伪造音频对齐结果。SV2 [Voice-to-MIDI](https://www.dreamtonics.com/voice-to-midi/)可从参考人声生成音符/歌词候选，但属于转写草稿，不等于受已知歌词约束的强制对齐。

## 4. 定向排错和停止

| 问题 | 最小观察 | 有依据的修正 |
| --- | --- | --- |
| 前后都早/晚相近距离 | 多个非重复锚点；文件头、弱起、tempo map、item 起点 | 只在共同坐标确认后做一次整体偏移 |
| 后面逐渐更早/晚 | 残差对时间、PPQ、BPM口径、tempo marker、playrate | 修正实际速度/时间换算；保留 rubato |
| 只有局部歌词行错 | 跳变两侧锚点、休止、重复/变拍、源/目标 note 关系 | 只改边界或字音映射冲突段 |
| 鼓拍齐但人声字头不齐 | 分开标记鼓、辅音、元音、音符起点 | 按人声/谱面证据修音素；无原唱时停止在节拍级判断 |
| 鼓/伴奏有拍点但无主唱来源 | 记录节拍和和声背景，明确是间接证据 | 请求当前范围确需的旋律/歌词来源；不从鼓推音高 |

若用户报告人声缺失或混音异常，应比较对应 vocal stem 与源音频的同一片段、相同增益/处理阶段，再看实际 master 中的人声贡献。不要拿 pre-master vocal stem 与 post-master 伴奏直接比；先修轨道、item、包络、FX 或路由，不用抬 Master 掩盖静音。修复后只做一次目标片段确认，不扩成全曲 QA。数值图不能声称试听、歌词自然或听感通过。

## 5. 参考资料

**标准和软件文档：**[MIDI Association：Standard MIDI Files](https://midi.org/standard-midi-files)；[REAPER User Guide](https://www.cockos.com/reaper/userguide.php) 与 [REAPER Effects Guide](https://www.reaper.fm/guides/ReaEffectsGuide.pdf)；[librosa STFT display](https://librosa.org/doc/0.11.0/auto_examples/plot_display.html)、[onset strength](https://librosa.org/doc/0.11.0/generated/librosa.onset.onset_strength.html)、[DTW](https://librosa.org/doc/0.11.0/generated/librosa.sequence.dtw.html)、[pYIN](https://librosa.org/doc/0.11.0/generated/librosa.pyin.html)；[mir_eval onset](https://mir-eval.readthedocs.io/latest/api/onset.html) 与 [beat metrics](https://mir-eval.readthedocs.io/latest/api/beat.html)。

**教材和论文：**[Müller, FMP: Music Synchronization](https://www.audiolabs-erlangen.de/resources/MIR/FMP/C3/C3.html)；[Ewert, Müller & Grosche: Chroma Onset Features](https://resources.mpi-inf.mpg.de/MIR/SyncRWC60/2009_EwertMuellerGrosche_HighResAudioSync_ICASSP.pdf)；[Mesaros & Virtanen: Automatic Recognition of Lyrics in Singing](https://link.springer.com/article/10.1155/2010/546047)；[Chang & Lee: Vowel Acoustics for Lyrics Alignment](https://doi.org/10.1109/ACCESS.2017.2738558)；[Gong et al.: Melody and Lyrics Alignment](https://www.isca-archive.org/interspeech_2015/gong15_interspeech.html)；[Joint Pitch Detection for Lyrics Alignment](https://doi.org/10.1109/ICASSP43922.2022.9746460)。

这些来源说明了工具能力，不提供统一的音乐合格线。残差形状、锚点数量、容差和停止条件是按本次制作问题设定的工程方法，需如实标记依据和不确定性。
