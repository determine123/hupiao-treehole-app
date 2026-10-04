# 发布步骤和当前限制

## 后端

准备 Linux Docker 主机和 API 域名。在 `deploy` 复制 `.env.example` 为 `.env`，设置域名、真实客服/举报邮箱、独立随机密钥。数据库密码使用 URL 安全字符，如随机十六进制字符串。运行 `docker compose up -d --build`，检查 `/health`、`/ready`、`/config`。Caddy 提供 HTTPS；不要公开数据库、Redis 或 API 内部端口。

上线前验证 PostgreSQL/Redis 的集成行为、审核流程和备份恢复。当前 Windows 环境没有 Docker，部署集群尚未实际运行验证。默认内容待审核；需指定真实审核人员与响应时限。备份脚本不会自动加密或清理文件，运营方须确定加密和留存期限，并发布最终隐私政策。

## Android / iOS 云构建

需要自己的 Expo 账号。iOS 真机/TestFlight/App Store 需要 Apple 开发者账号和签名，Google Play 需要开发者账号。Windows 可通过 EAS 触发云端构建。

```sh
cd mobile
npx eas-cli login
npx eas-cli init
# 在构建环境设置真实 HTTPS 的 EXPO_PUBLIC_API_URL
npx eas-cli build --platform android --profile preview
npx eas-cli build --platform ios --profile ios-simulator
npx eas-cli build --platform android --profile production
npx eas-cli build --platform ios --profile production
```

Android preview 生成内部测试 APK；ios-simulator 仅供模拟器，不能安装到普通 iPhone。iOS 真机内测使用签名构建通过 TestFlight 分发，或配置 Ad Hoc 并注册设备。确认包名 `com.determine123.hupiao`、EAS projectId、隐私政策 URL、截图、客服联系方式和审核说明后，再提交商店。

## 尚未通过的发布门槛

- 本机没有 Android SDK / Xcode，尚未生成 APK/AAB/IPA，也没有完成真机内测。
- Python 后端没有正式服务器，不能以现有网站地址替代新 API；旧网站没有切换或迁移数据。
- 2026-10-04 npm 审计仍有 19 个 high 条目，主要沿依赖链传播自 braces、node-forge，当时注册表最新版仍受影响。已经更新 decode-uri-component 和 uuid 的兼容覆盖版本。正式发布前需要升级或安全修复并重新验证，不能宣称审计通过；不要强制降级整套 Expo。
- 需要人工审核运营与正式隐私政策。举报/屏蔽入口不保证 Apple 接受匿名 UGC 应用。

[EAS 官方指南](https://docs.expo.dev/build/setup/) · [Apple 审核规则](https://developer.apple.com/app-store/review/guidelines/)
