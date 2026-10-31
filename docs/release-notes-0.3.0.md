# WeChat Files Organize 0.3.0

发布日期：2026-11-01

## 新增

- 支持扫描和导出微信文档、压缩包、音频与其他普通文件
- 新增文档、压缩包、音频、其他文件分类筛选项
- 文件按月份、类型和 SHA-256 去重结果统一管理
- 文件导出目录新增 `Documents`、`Archives`、`Audio` 和 `Files`
- 微信已保存文档目录新增 `Documents/WeChat` 与 `Download/WeChat` 自动发现
- 增加文件数量和文件占用统计
- 普通文件单击后下载并调用 Windows 默认应用打开

## 安全边界

- 微信内部日志、配置、数据库和索引文件不会进入文件列表。
- 微信私有应用沙盒中的文件仍受普通 ADB 权限限制。
- 文件清理与媒体清理使用相同的本地备份和 SHA-256 校验流程。

## 发布文件

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| `WeChat-Files-Organize-Setup-0.3.0.exe` | 85,768,888 bytes | `EAF317EB2A088156B7887099BF5E6154FBAC67FEBCE8D4BED8E5ADBC68DBC10F` |
| `WeChat-Files-Organize-Portable-0.3.0.exe` | 84,290,646 bytes | `0922C0966531153BC948EFBF9C6AD3EC8975570817F79B38BA6F7C510D04B847` |
