# 数据快照与空库恢复

`backend/backup.py` 从 PostgreSQL 的只读、可重复读事务导出应用表，逐行压缩写入临时文件，完成后才生成最终备份。SQLite 开发数据库也支持。文件包含匿名身份摘要、内容、反馈、举报及内部审核记录，不含管理员密钥、数据库连接密码或 TOKEN_PEPPER；只能存入私有目录，不要提交或公开分享。

连接地址通过 `HUPIAO_DATABASE_URL` 环境变量提供，不写在命令行。云数据库需使用可访问的外部地址及 TLS。安装后端依赖后运行：

```powershell
python backend/backup.py export C:/private-backups/hupiao.jsonl.gz
```

Windows PowerShell 7 可以使用 `scripts/backup-private.ps1`。它拒绝仓库内的备份目录，导出后用 Windows DPAPI CurrentUser 加密，实际解密并核对 SHA-256，然后清理临时明文。默认保存于当前用户 `.codex/private/hupiao/backups`。DPAPI 文件只能由原 Windows 用户及其有效密钥解密，不能替代跨设备灾备；需要另行保管恢复密钥或使用独立加密的异地备份。

恢复前新建**隔离的空数据库**，使用相同代码执行 `alembic upgrade head`，确认 Alembic 版本与快照一致。将目标连接地址设为 `HUPIAO_DATABASE_URL`，解密后的快照仍放私有目录，再运行：

```powershell
python backend/backup.py restore-empty C:/private-backups/hupiao.jsonl.gz
```

恢复会校验表、列、迁移版本及逐表行数，拒绝任何已有数据的目标；损坏、缺失末尾或不匹配的快照会回滚。PostgreSQL 恢复期间锁定应用表，SQLite 使用写事务。此命令不创建表、不清空原库、不覆盖生产数据，也不迁移版本。数据库角色、服务配置、Redis、上传文件及旧 Sites 数据不在此快照中；备份成功不等于完整灾备已完成。

恢复身份时必须保留原 TOKEN_PEPPER，否则旧手机凭据无法匹配摘要。管理员密钥和 APK 签名密钥需另行安全保管。上线前在隔离环境验证用户凭据、内容数量、外键、审核权限及反馈访问，再决定切换；当前工具没有自动切换或生产恢复步骤。

CI 用 SQLite 和独立 PostgreSQL schema 验证导出恢复、非空目标保护、损坏快照回滚和写入失败清理。备份文件仍可能含已经从在线系统删除的历史数据，运营方须定义保存期限及删除流程。本次不默认建立永久保留或自动定时备份。
