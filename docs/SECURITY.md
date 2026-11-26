# 安全说明（账户 + 数据）

这个项目会碰到三类敏感信息，分别处理：

| 类型 | 例子 | 泄露后果 | 处理方式 |
|---|---|---|---|
| 平台密钥 | 大模型 API Key | 别人用你的额度、产生账单 | 只放环境变量，`.env` 永不提交 |
| 账户凭据 | GitHub 密码、Token、SSH 私钥 | 仓库被改、代码被删 | 2FA + 最小权限 Token + 不写进命令行 |
| 真实数据 | 同学实验数据、姓名学号 | 隐私问题 | 只存本地 `data/`，截图前脱敏 |

---

## 一、仓库层面

- [x] `.env`、`.env.*` 已加入 `.gitignore`
- [x] `data/`、`reports/`、`models/`、`knowledge/` 已忽略
- [x] 提供 `.env.example`，只有变量名没有值
- [x] `scripts/check_secrets.py` 可在提交前扫描
- [x] `.streamlit/config.toml` 关闭了 Streamlit 使用统计

提交前固定动作：

```powershell
python scripts/check_secrets.py
git status
git diff --cached
```

---

## 二、账户层面（GitHub）

1. **开启 2FA**：Settings → Password and authentication。
2. **密码唯一**：不和学校邮箱、微信、QQ 共用。
3. **提交邮箱用 noreply**：Settings → Emails 里找 `xxx@users.noreply.github.com`。
4. **优先 SSH**；用 Token 时选 **Fine-grained**，只授权当前仓库，
   权限只给 Contents，有效期 30 天。
5. **不在公共电脑保存凭据**；用完执行 `git credential-manager logout`。
6. **不把 Token 拼进 URL**：`https://ghp_xxx@github.com/...` 会留在 shell 历史和
   `.git/config` 里。
7. **开启 Secret scanning 和 Push protection**（仓库 Settings → Code security）。
8. **仓库先 Private**，确认无个人信息再改 Public。

---

## 三、数据层面

- 工具默认**不联网**；只有点击"AI 误差分析"才会把计算结果发给你配置的模型接口。
- 发送给模型的内容只有：实验名、拟合参数、不确定度、R²，**不含原始数据文件**。
- 报告和图片只写入本地 `reports/`，已被 `.gitignore` 忽略。
- 如果要交作业截图，注意把姓名、学号、桌面文件名打码。

---

## 四、误提交密钥后的处理顺序

1. **先吊销**：GitHub Token 页面删除；模型平台后台删除/轮换。
2. 检查账单与调用记录（假设已泄露）。
3. 再清理 Git 历史：

```powershell
# 安装 git-filter-repo 后
git filter-repo --path .env --invert-paths
git push --force
```

4. 通知协作者重新克隆（旧克隆里仍有历史）。

> 记住：`git rm .env` 只删掉最新提交，**历史里还在**，所以第一步永远是吊销。

---

## 五、课堂演示前的检查

- [ ] 浏览器书签栏没有私人内容
- [ ] 没有开着 `.env` 或密钥管理页面
- [ ] 录屏时用示例数据，不用同学真实数据
- [ ] 终端历史里没有 Token
- [ ] 仓库是 Private，或已确认可以公开
