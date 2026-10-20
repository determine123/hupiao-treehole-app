# 发布步骤和当前限制

## 后端

准备 Linux Docker 主机和 API 域名。在 `deploy` 复制 `.env.example` 为 `.env`，设置域名、真实客服/举报邮箱、独立随机密钥。数据库密码使用 URL 安全字符，如随机十六进制字符串。运行 `docker compose up -d --build`，检查 `/health`、`/ready`、`/config`。Caddy 提供 HTTPS；不要公开数据库、Redis 或 API 内部端口。

上线前验证 PostgreSQL/Redis 的集成行为、审核流程和备份恢复。当前 Windows 环境没有 Docker，部署集群尚未实际运行验证。默认内容待审核；需指定真实审核人员与响应时限。备份脚本不会自动加密或清理文件，运营方须确定加密和留存期限，并发布最终隐私政策。

## Android / iOS 云构建

需要自己的 Expo 账号。iOS 真机/TestFlight/App Store 需要 Apple 开发者账号和签名，Google Play 需要开发者账号。Windows 可通过 EAS 触发云端构建。

```sh
cd mobile
npx eas-cli@latest login
npx eas-cli@latest init
# 在构建环境设置真实 HTTPS 的 EXPO_PUBLIC_API_URL
npx eas-cli@latest build --platform android --profile preview
npx eas-cli@latest build --platform ios --profile ios-simulator
npx eas-cli@latest build --platform android --profile production
npx eas-cli@latest build --platform ios --profile production
```

Android preview 生成内部测试 APK；ios-simulator 仅供模拟器，不能安装到普通 iPhone。iOS 真机内测使用签名构建通过 TestFlight 分发，或配置 Ad Hoc 并注册设备。确认包名 `com.determine123.hupiao`、EAS projectId、隐私政策 URL、截图、客服联系方式和审核说明后，再提交商店。

## 前端 OTA 更新

EAS Update 只分发 JavaScript、样式和静态资源。Python 后端仍需单独部署；原生依赖、权限、包名或 Expo SDK 改动必须重新构建并安装 APK/IPA。当前配置使用 `appVersion` 作为运行时版本，只有运行时版本相同的平台安装包会接收对应更新。

预览 APK 使用 `preview` channel，正式包使用 `production` channel。首次启用或升级 `expo-updates` 后，先分别为需要测试的平台构建并安装新包；之前发布的 1.0.2 安装包没有这次加入的原生更新模块，不能接收 OTA。

每次发布 OTA 前，在 Expo 项目 `preview` 环境设置 `EXPO_PUBLIC_API_URL=https://hupiao-api-beta.onrender.com`，再运行：

```sh
cd mobile
npx eas-cli@latest update --channel preview --environment preview --message "简述本次变更"
```

先用 `preview` channel 验证内测包。确认无误后，再为 `production` 环境配置生产 API 地址，用 `production` channel 发布。不要把测试环境的后端地址发布给生产用户。每次更新前记录 EAS update group ID 和改动内容；发现问题时运行 `npx eas-cli@latest update:rollback`，按提示选择回退到上一个兼容更新或内置版本。原生代码改动不能通过 OTA 回滚，需重新构建。

OTA 更新在应用启动时会自动检查并下载，通常下次启动后生效；“我的”页面也提供手动检查与立即重启入口。EAS Update API 的完整行为要在安装过 preview 或 production 的 release APK/IPA 上验证，开发服务器和 Expo Go 不能代表真机发布行为。

## 尚未通过的发布门槛

- 本机没有 Android SDK / Xcode，安卓通过 EAS 云构建；iOS 尚未构建，也没有完成真机内测。
- Python 后端已部署 Render 内测实例并通过 PostgreSQL/Redis 公网验证；长期生产资源尚未配置。旧网站没有切换或迁移数据。
- 2026-10-04 npm 审计仍有 19 个 high 条目，主要沿依赖链传播自 braces、node-forge，当时注册表最新版仍受影响。已经更新 decode-uri-component 和 uuid 的兼容覆盖版本。正式发布前需要升级或安全修复并重新验证，不能宣称审计通过；不要强制降级整套 Expo。
- 需要人工审核运营与正式隐私政策。举报/屏蔽入口不保证 Apple 接受匿名 UGC 应用。

[EAS 官方指南](https://docs.expo.dev/build/setup/) · [Apple 审核规则](https://developer.apple.com/app-store/review/guidelines/)

补充依赖范围核对：本机 Android 正式资源导出的 source map 包含 1,249 个模块，未包含 braces 或 node-forge（见 `runtime-dependency-scope.json`）。目前剩余 npm 问题涉及构建依赖；此检查不是完整 APK 原生安全审计，也不能替代构建工具升级。
