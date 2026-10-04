# 已部署的安卓内测后端

- 源码：https://github.com/determine123/hupiao-treehole-app
- API：https://hupiao-api-beta.onrender.com
- 健康状态：https://hupiao-api-beta.onrender.com/health
- 管理入口：https://hupiao-api-beta.onrender.com/admin
- Expo 项目：https://expo.dev/accounts/determine123/projects/hupiao-treehole

2026-10-04 已完成真实 HTTPS + PostgreSQL + Redis 的端到端验证；检查结果见 `live-smoke-result.json`，测试身份和内容已经删除。GitHub CI 同时通过 PostgreSQL 回归测试和移动端类型检查、lint、双平台资源导出。

客户端 preview 构建已配置该 HTTPS 地址。首次进入需要阅读社区约定并创建匿名身份；帖子和回复需要管理员审核后才公开。“内测反馈”用于提交问题和建议，管理员可回复。

安卓安装包构建成功，包名 `com.determine123.hupiao`、版本 1.0.0、min SDK 24、target SDK 36，支持 ARM 和 x86 的 32/64 位架构。已核对 ZIP 完整性、签名块及实际打包的 API 地址；完整记录见 `android-artifact.json`。这仍不是实际手机内测。

管理员密钥只保存在 Render 环境变量及本机私有目录的 `backend-secrets.json`，没有放入 APK 或仓库。Render 部署账号令牌用 Windows DPAPI 加密。密钥丢失时应通过自己的平台账号恢复，不要从公开聊天索取。

电脑端运行 `scripts/open-admin.ps1` 会打开管理页面，并把管理员密钥复制到本机剪贴板供粘贴；脚本不会在终端打印密钥。登录后清空剪贴板。

免费数据库到期时间：2026-11-03 11:16（上海时间）。到期前需备份和选择续用方案，否则数据库会变得不可用并可能被平台删除。免费 Web 空闲 15 分钟后会休眠，首次连接可能需要约一分钟；此部署用于内测。原 Sites 网站及数据库没有切换。
