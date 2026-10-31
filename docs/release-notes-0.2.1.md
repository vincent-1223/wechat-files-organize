# WeChat Files Organize 0.2.1

发布日期：2026-10-31

## 修复

- 修复批量加载图片缩略图时频繁闪现 ADB 终端窗口的问题。
- 扫描器现在会读取无扩展名文件头，额外识别出 66 张图片和 1 个视频。
- 扫描报告新增微信私有应用沙盒权限状态。
- 明确提示普通 ADB 无法读取聊天记录中的全部私有媒体。

## 当前媒体读取范围

- 可读取：`Pictures/WeiXin` 中已保存的图片和视频。
- 部分可读：`Android/data/com.tencent.mm` 中普通权限允许访问的外部缓存。
- 无法读取：`/data/user/0/com.tencent.mm` 微信私有应用沙盒。

聊天记录中仍保存在私有沙盒内的媒体无法在不 Root、不破解微信的前提下完整读取。

## 发布文件

| 文件 | 大小 | SHA-256 |
|---|---:|---|
| `WeChat-Files-Organize-Setup-0.2.1.exe` | 85,764,207 bytes | `F1F372F1E14EB3462567FD767DAB8F2FB672F82DBBD8DBE5B6D26DC6725F02C4` |
| `WeChat-Files-Organize-Portable-0.2.1.exe` | 84,287,215 bytes | `2A3F878355DBA5775020AB28F519AC4E189A53D611BDBBF1A36C12BB906F5870` |
