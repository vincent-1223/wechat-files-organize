# P0 真机验证记录

验证时间：2026-10-31  
设备：OPPO Find X9（ADB 型号 `PLJ110`）  
系统：Android 17  
微信：8.0.79  
连接方式：USB + ADB，无 Root

## 可访问媒体

| 类型 | 数量 |
|---|---:|
| 图片 | 133 |
| 视频 | 14 |
| 待识别 | 176 |
| 疑似缩略图 | 3 |
| 图片/视频容量 | 500,960,689 bytes |
| 全部可访问文件容量 | 1,029,650,106 bytes |

## 目录结果

| 目录 | 状态 | 文件数 |
|---|---|---:|
| `/storage/emulated/0/Pictures/WeiXin` | 可读取 | 98 |
| `/storage/emulated/0/Android/data/com.tencent.mm` | 部分可读 | 225 |
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

机器可读报告和完整文件清单保存在本地 `reports/` 目录，并已加入 `.gitignore`，不会把个人媒体路径提交到 Git 仓库。
