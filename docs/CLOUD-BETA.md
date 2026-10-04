# 本次云端内测配置

后端准备部署到 Render，新应用工程单独存放在 GitHub；不改动现有网页数据库。`render.yaml` 的所有资源明确使用 free，并限制数据库、Redis 的公网访问。免费数据库只有 30 天期限；免费 Web 空闲时休眠，首次连接可能较慢。这是内测，不是长期生产保障。

Expo 已建立 `determine123/hupiao-treehole` 项目。APK 使用 preview 配置和 HTTPS API 地址，生成后可直接下载到 Android 手机安装，不需要 Google Play 账号。

部署需要 Render API 授权。`scripts/render-authorization.ps1` 只在本机接受令牌和公开邮箱，使用 Windows DPAPI 加密保存到用户目录下 `.codex/private/hupiao/render-auth.json`；不放进工程、不提交 GitHub、不发送聊天。请勿把账户密码填入该窗口。

上线后保存数据库备份、管理员密钥与 APK 签名密钥。删除/重建数据库或改变 TOKEN_PEPPER 会使旧匿名凭证失效；不能把重新部署误当成可以任意轮换身份摘要密钥。
