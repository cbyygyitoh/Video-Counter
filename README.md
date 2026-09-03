# 视频计数器

按下键盘 ↓ 键计数，达到目标后提醒学习的桌面小工具。

![Python](https://img.shields.io/badge/python-3.6+-blue)
![Windows](https://img.shields.io/badge/platform-Windows-lightgrey)

---

## 功能

- 按 `↓` 键减少计数，带滴答音效
- 进度条显示完成百分比
- 归零弹窗提醒 + 音效
- 自由设置目标值（1-9999）
- 窗口置顶，可拖动
- 自动保存使用记录

---

## 快速开始

```bash
# 安装依赖
pip install keyboard

# 运行
python video_counter.py
```

---

## 操作

| 操作 | 说明 |
|------|------|
| `↓` | 计数 -1 |
| 输入框 + ✓ | 设置目标 |
| ↻ | 重置计数 |
| 拖标题栏 | 移动窗口 |

---

## 打包 EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name VideoCounter video_counter.py
```

---

## 技术

- Tkinter + keyboard + winsound
- 动态生成 WAV 音效
- JSON 本地存储

---

## License

MIT
