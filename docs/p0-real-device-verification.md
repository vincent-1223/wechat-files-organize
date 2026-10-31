# P0 真机验证记录

验证时间：2026-11-01  
设备：OPPO Find X9（ADB 型号 `PLJ110`）  
系统：Android 17  
微信：8.0.79  
连接方式：USB + ADB，无 Root

## 可访问内容

| 类型 | 数量 |
|---|---:|
| 图片 | 184 |
| 视频 | 15 |
| 文档 | 2 |
| 待识别 | 103 |
| 疑似缩略图 | 3 |
| 图片/视频容量 | 513,078,047 bytes |
| 全部可访问内容容量 | 587,631,978 bytes |

## 目录结果

| 目录 | 状态 | 文件数 |
|---|---|---:|
| `/storage/emulated/0/Pictures/WeiXin` | 可读取 | 100 |
| `/storage/emulated/0/Download/Weixin` | 可读取 | 2 |
| `/storage/emulated/0/Android/data/com.tencent.mm` | 部分可读 | 202 |
| `/storage/emulated/0/tencent/MicroMsg` | 目录为空 | 0 |
| `/storage/emulated/0/Android/media/com.tencent.mm` | 不存在 | 0 |
| `/storage/emulated/0/DCIM/WeChat` | 不存在 | 0 |
| `/storage/emulated/0/DCIM/Weixin` | 不存在 | 0 |

## 关键结论

1. 这台 OPPO 的微信已保存媒体目录为 `Pictures/WeiXin`，大写 `X`。仅使用 `Pictures/Weixin` 会漏掉文件。
2. 微信外部存储位于 `Android/data/com.tencent.mm`，ADB 可以读取其中一部分，但存在子目录权限不足。
3. `tencent/MicroMsg` 目录存在但没有可扫描文件；不能仅凭该目录状态判断微信没有媒体。
4. `Android/data` 中存在大量无扩展名缓存、日志和业务文件，当前标记为“待识别”，不会冒充原图，也不会进入安全清理列表。
5. 扫描全程只读，没有删除、修改或上传手机文件。
6. 工具会读取无扩展名文件的文件头，补充识别不在扩展名白名单内的图片、视频、文档和压缩包。
7. `/data/user/0/com.tencent.mm` 为微信私有应用沙盒，普通 ADB 返回权限不足。聊天记录中仍保存在该沙盒内的图片和视频无法完整导出。
8. 在 `Download/Weixin` 中真实发现并分类出 2 个 `.doc` 微信文件。

## 单文件导出校验

选取扫描结果中体积最小的一个缓存图片进行真实 `adb pull`，导出到本地
`WeChatBackup/SmokeTest/2026/10/Images/vuserpic_8.png`。手机端与电脑端 SHA-256
均为 `a97ea232976b5047b763fdb1ab82e9fa10e992801c41703397655249083df949`，校验通过。

该文件仅用于本地功能验证，`WeChatBackup/` 已加入 `.gitignore`，不会提交到代码仓库。

随后又选取最小的微信 `.doc` 文件执行真实导出，保存到
`WeChatBackup/SmokeTest-file/2026/05/Documents/`。手机端和电脑端 SHA-256 均为
`d20bd0eedf5880565c7087280f98b0ec2618508dffe2345e710faf1cf9b47f27`，文件导出校验通过。

机器可读报告和完整文件清单保存在本地 `reports/` 目录，并已加入 `.gitignore`，不会把个人媒体路径提交到 Git 仓库。
