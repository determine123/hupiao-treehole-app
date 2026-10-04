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

2026-10-04 1.0.1：广场排序后端已上线，公网 latest / hot / unanswered 与临时身份删除验证通过；PostgreSQL CI 通过。安卓构建成功，实际 APK 包名与新旧签名证书一致，versionCode 升到 2，新功能和 HTTPS 地址已在安装包中核对。GitHub 公共下载通过范围请求验证。详见 android-artifact-1.0.1.json 与 DOWNLOAD.md。

审核后台改进：原帖上下文、类型筛选与中文反馈状态已实现，退出和快速切换栏目的迟到响应回归验证通过；此次只更新 Python 服务，APK 1.0.1 可继续使用。已于 2026-10-04 部署上线（dep-db12ft2d0e5s73dpou00），HTTPS 页面与禁止缓存响应头核对通过；CI 37194941615 通过。

2026-10-04 1.0.2：Alembic b39a807de214 已在真实 PostgreSQL 部署升级，dep-db13mie0tbcc739c018g 为 live。CI 37199428279 验证 15 项后端测试（含独立 PostgreSQL schema 内的旧数据迁移）和双平台导出。公网验证作者说明、内部依据隔离、管理员权限和删除后的记录不可见；临时身份与内容已清理。安卓 versionCode 3 签名构建成功，新旧证书一致，GitHub 公开下载已验证；尚未完成完整真机测试。详见 android-artifact-1.0.2.json。
