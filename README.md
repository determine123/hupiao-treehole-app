# 沪漂树洞：Android / iOS 与 Python 后端

Expo + React Native 原生客户端，FastAPI + SQLAlchemy + Alembic 后端。参考 [Anonymous](https://github.com/wu-qing-157/Anonymous) 的匿名社区体验，没有复制 Kotlin 源码。现有网页版及数据未被替换。

已实现多话题、搜索、游标分页、草稿、回复引用、点赞、个人互动列表、安全存储匿名凭证、先审后发、举报、屏蔽、身份删除及私密内测反馈。管理员通过 `/admin` 审核内容、处理举报和答复反馈。

## 本机运行

在工程目录：

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.lock.txt
./scripts/start-backend.ps1
```

API 文档：`http://127.0.0.1:8000/docs`。管理员页面：`http://127.0.0.1:8000/admin`。在 `backend/.env` 设置自己的随机 `ADMIN_TOKEN` 后重启才能管理；密钥不能提交 GitHub。

另开终端：

```powershell
cd mobile
npm ci
Copy-Item .env.example .env
npm start
```

手机上的 localhost 指向手机自己。局域网内测需将 `EXPO_PUBLIC_API_URL` 改为电脑 IP，后端显式以 `--host 0.0.0.0` 启动，仅对受信任测试网络开放；正式版使用真实 HTTPS 域名。使用与 SDK 57 对应的开发构建验证客户端。

## 检查

```powershell
cd backend
../.venv/Scripts/python.exe -m pytest tests -q
../.venv/Scripts/python.exe -m ruff check app tests --select F
cd ../mobile
npm run typecheck
npm run lint
npm run export:mobile
```

[发布步骤](docs/RELEASE.md) · [内测流程](docs/BETA.md) · [数据与性能说明](docs/ARCHITECTURE.md)

安卓签名 APK 已构建并校验：[下载页面](https://github.com/determine123/hupiao-treehole-app/releases/tag/v1.0.2-beta.1)。支持 Android 7.0 及以上，约 93 MiB，已经内置服务器地址。

Python 内测后端已部署到 [Render](https://hupiao-api-beta.onrender.com/health)，已通过公网功能验证及 PostgreSQL CI。iOS 未生成 IPA，两个平台均未提交商店。正式发布仍需真机内测、构建工具升级及长期服务器方案。详见 [本次部署记录](docs/DEPLOYED.md)。

1.0.1 新增沪漂广场、本周热门、等待回应和新手指南，体验参考 [LiteBBS](https://litebbs.com/)。详见 [改进说明](docs/DISCOVERY.md)。

1.0.2 新增作者审核说明与管理员历史查询，内部依据和作者说明严格分开，旧记录不自动公开；详见 [审核记录设计](docs/MODERATION.md)。
