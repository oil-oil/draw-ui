# 生成工具与接口边界

用户指定服务和模型时使用相应能力；同时指定其他生成 Skill 时遵循它的鉴权和调用流程。其余情况使用宿主内置生图工具，无需额外 Key。固定路径通过生成后复制文件完成；不因路径、尺寸或质量偏好自动切换 API。随附脚本仅在用户明确选择外部服务或同意备用 API 路径后调用。不要把一次体验中的质量或速度比较写成永久的模型优劣结论。

命令示例显式使用bash，避免下载压缩包安装时丢失可执行权限。

脚本默认使用 ZenMux，默认模型为 `openai/gpt-image-2`；可用 `--model` 显式覆盖。调用前按当前服务目录确认用户指定的模型ID，遇到歧义先解析，不猜测收费版本。

```bash
node "$SKILL_DIR/scripts/credential-ui/src/profile.ts" run default -- bash "$SKILL_DIR/scripts/ask_draw.sh" --type wide --name "dashboard" --prompt "页面提示词"
node "$SKILL_DIR/scripts/credential-ui/src/profile.ts" run default -- bash "$SKILL_DIR/scripts/ask_draw.sh" --frame /path/to/reference.png --type wide --name "dashboard" --prompt "保留固定区域的页面提示词"
```

| 参数 | 作用 |
| --- | --- |
| `--type` | `ultrawide` 21:9、`wide` 16:9、`classic` 4:3、`square` 1:1、`portrait` 3:4；默认wide |
| `--frame` / `--ref` | 固定框架参考图 / 可重复传入的参考图 |
| `--name` / `-o` | 文件名 / 输出路径 |
| `--model` | 模型ID覆盖 |
| `--provider` | `zenmux` 或 `codex`，后者是脚本保留的 OpenAI Responses API 适配器名称 |
| `--mode` | `normal`、`replicate`、`frame-lock`、`asset-redraw` |

`portrait` 是画布预设，不能直接代表真实手机视口或完整长页。脚本的 ZenMux OpenAI 分支使用 `generate_images/edit_image` 时未传比例参数；返回尺寸不能由 `--type` 或元数据中的 `aspect_ratio` 推断。需要精确尺寸时使用宿主已有、已确认支持尺寸参数的调用方式；完成后读取实际图片尺寸。不要为修正比例而拉伸图片。

优先通过已有安全凭据管理在运行时注入环境变量，不新建明文凭据文件。ZenMux 密钥兼容脚本的查找顺序：`ZENMUX_API_KEY`、项目及上层 `.env.local`、`~/.config/see/api_key`。使用其他宿主的 ZenMux 工具时沿用其安全凭据管理，不复制密钥或新建明文副本。

OpenAI Responses API 适配器通过 `--provider codex` 选择，读取 `OPENAI_IMAGE_API_KEY` 或 `OPENAI_API_KEY`，不复用宿主登录凭据。Windows 使用 `scripts/ask_draw.ps1`，macOS/Linux 使用 `scripts/ask_draw.sh`。需要设置密钥时按 [API Key 配置](api-key-setup.md) 复用现成入口或展示固定页面，不输出密钥值。选择 `--provider codex` 时使用 `run openai` 包装；默认适配器使用 `run default`。

生图成功会输出 `output_path` 和 `metadata_path`。实际打开并检查文件；记录使用的模型、提示词、参考、真实尺寸和待修正项。已有文件应使用新路径保留，不静默覆盖。

失败时保留原始错误与有效产物。鉴权、余额、参数或型号错误先解决原因；只对明确暂时性错误做有上限、已授权的重试，不把所有断连都认作正常现象。对结果不满意的重画属于新的生成，不伪装成网络重试。

## 参考图能力核验

用户提供视觉参考时，分别核验模型、服务接口和当前脚本能否接收图片。脚本没有参考图参数不等于模型不支持；先查对应服务官方接口，再决定是否通过已有SDK或任务内适配器传入。未实际提交图片时，只能称为文字提炼参考，不能说模型看过原图。

ZenMux的OpenAI兼容接口公开支持POST /images/edits；本地参考图优先使用multipart/form-data上传实际文件，文件字段为image[]；JSON请求使用images数组，每项为image_url，可传base64 data URL。不要误用generations接口或将路径字符串冒充图像输入。区分请求封装、传输形式与模型能力，按当前接口返回验证成功，不能根据一种格式的失败断言整个模型不支持参考图。当前具体模型仍需校验，并检查响应。接口依据：https://zenmux.ai/docs/api/openai/create-image-edit.html 。有图与纯文字测试分组记录，两模型使用相同参考图片字节、顺序、提示词与参数；只改变模型。
