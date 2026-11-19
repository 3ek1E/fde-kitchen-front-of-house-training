# 知味协作台 MVP

FastAPI 同源应用，包含角色登录、SaaS 租户管理、Wiki 草稿与修订发布、租户内 TF-IDF 检索、可配置 LLM 问答、带来源的摘录回退、订单版本冲突处理、前后厅双回执及操作审计。SQLite 使用 Python 标准库访问，单实例部署。

## 本地运行

在仓库根目录执行以下 PowerShell 命令。首次启动时设置至少 12 字符的自选密码。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# 编辑 .env，设置 BOOTSTRAP_PASSWORD
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 http://127.0.0.1:8000 。健康检查为 `/healthz`，API 文档为 `/docs`。

DEMO_MODE=true 时的演示账号包括 `platform@demo.local`、`admin1@demo.local`、`editor1@demo.local`、`front1@demo.local`、`kitchen1@demo.local`。第二租户账号把 1 换成 2。初始密码为你设置的 BOOTSTRAP_PASSWORD。停用 DEMO_MODE 时仅初始化平台管理员，平台管理员可创建租户和租户管理员。

修改 BOOTSTRAP_PASSWORD 不会重置已存在的账户密码。密钥和数据库保存于 DATA_DIR，默认 ./data，目录已加入 Git 忽略。

## 演示顺序

1. 用 editor1 登录，阅读预置 SOP，保存新修订并发布。
2. 用 front1 登录，向知识库提问“纸质加单和系统单冲突怎么办”，点击来源核对。
3. 在订单看板登记 POS 事件和前厅回执，退出后用 kitchen1 确认并登记出品，再用 front1 登记送达。
4. 重复同一事件编号检查去重，发送纸单来源的不同备注制造冲突，用 admin1 复核。
5. 用 front2 检查租户隔离，用 admin1 查看审计。platform 可查看租户并控制启停。

## LLM 与运行限制

配置 LLM_API_KEY、LLM_MODEL、LLM_BASE_URL 可调用兼容的 `/chat/completions` 服务。缺少配置或调用失败时返回带引用的资料摘录，界面会显示模式。线上模型调用需单独验证。

演示资料与订单为合成数据。Wiki 原文按纯文本安全显示，支持粘贴 Markdown。当前通过手工录入模拟 POS，上传、真实 POS 集成、套餐拆单、菜齐聚合、自动过敏检测及生产备份仍需后续实现。冲突复核当前采用所选事件并保留操作记录，食品安全判断由人工负责。

## Harness 验证

```powershell
.venv\Scripts\python.exe -m pytest -q
```

测试在临时数据库运行，覆盖成员权限、跨租户资源与检索隔离、Wiki 新版本发布、引用回跳、事件重复与乱序、冲突处理、前后厅确认、状态迁移、租户停用和跨站请求拒绝。

## Render 部署

仓库提供 render.yaml，可通过 Render Blueprint 创建免费演示服务，构建命令为 `pip install -r requirements.txt`，启动命令为 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`。设置 BOOTSTRAP_PASSWORD 后启动；LLM 配置可留空使用摘录模式。

免费服务使用临时文件系统，重启或重新部署会重建演示数据。需要持续保存数据时，选择带持久化磁盘的服务并将 DATA_DIR 设置为挂载目录，该选项涉及付费服务。部署必须以 Render 实际返回的服务网址和健康检查结果为准。

## Vercel Hobby 演示部署

Vercel 可自动发现 app/main.py 的 FastAPI 入口，仓库提供 vercel.json。部署环境配置 DEMO_MODE=true、COOKIE_SECURE=true、BOOTSTRAP_PASSWORD（至少 12 字符）、JWT_SECRET（随机长字符串）；LLM_API_KEY 与 LLM_MODEL 按需配置。

该部署适用于课程演示。SQLite 保存于实例的 /tmp/kitchen-data，新实例会重新初始化，多个实例之间的新增记录不共享。需要持续保存并跨实例共享用户、Wiki 和订单时，应先接入外部数据库再作为持续运营服务使用。Vercel Hobby 的资格和额度以平台当前规则为准。

## Uppcoder Spark 部署

在 Stacks 创建 FastAPI 应用，连接本仓库的 main 分支。根目录 main.py 提供平台默认的 FastAPI 入口，startup-app.sh 提供启动命令。依赖从 requirements.txt 安装。

使用单实例与平台持久化的应用目录，SQLite 数据保存在应用目录 data/，也可通过 DATA_DIR 指向已确认的持久化卷。首次启动自动生成密码与 JWT 密钥，复用已有配置。登录信息保存在 data/initial-access.txt，仅通过 Uppcoder 登录后的 Terminal 或 Files 查看。该目录已加入 Git 忽略，不通过网站静态目录提供。

应用完成验证后设置 Public，使网站可从普通浏览器访问；平台的 Terminal、Files 与编辑器仍由平台身份保护。真实上线地址、存储挂载和重启后的数据保留应在实际实例中核对。
