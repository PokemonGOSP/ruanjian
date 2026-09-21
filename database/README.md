# Database

数据库固定为 MySQL 8，不使用 SQLite。

推荐流程：

```powershell
docker compose up -d mysql
cd backend
Copy-Item .env.example .env
alembic upgrade head
python -m app.db.seed
```

- `schema.sql` 是便于审阅或普通 MySQL 环境初始化的参考 DDL。
- Alembic 是团队开发时的正式 Schema 迁移入口。
- `seed.sql` 是可选 SQL Seed；`python -m app.db.seed` 是推荐 Seed 命令。
- Seed 数据全部虚构，账号只允许用于本地开发。
- 空库先运行 migration，再运行 seed；不要手工逐表创建。
