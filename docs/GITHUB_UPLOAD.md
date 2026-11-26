# 把项目上传到 GitHub（并保证账户安全）

> 前提：**只在 `physics-lab-tool` 这个目录里执行 `git init`。**
> 不要在 `default-workspace` 根目录初始化仓库 —— 那里有你的其他个人文件
> （cookie、笔记、临时脚本），一旦 `git add -A` 就会全部上传。

> 装好 Git 之后，也可以直接运行一键脚本：
> `powershell -ExecutionPolicy Bypass -File scripts\push_to_github.ps1`
> 它会自动做密钥扫描、检查不该提交的文件，再提示你粘贴仓库地址。

---

## 0. 先确认你在正确的目录

```powershell
pwd
# 应该输出 ...\physics-lab-tool
```

如果不是，先 `cd` 进去。

---

## 1. 提交前自检（最重要的一步）

```powershell
python scripts/check_secrets.py
git status
```

`git status` 里**绝对不能出现**：

- `.env`
- `data/` 下的 CSV
- `reports/` 下的 docx / png
- 任何 `models/`、`knowledge/`
- 任何你不确定来源的文件

如果出现了，先检查 `.gitignore` 是否生效，再执行 `git rm --cached <文件>`。

---

## 2. 本地初始化并提交

```powershell
git init -b main
git add .
git status                # 再确认一次文件清单
git commit -m "feat: 实验数据台 v0.1（模板/拟合/不确定度/报告）"
```

建议先把提交邮箱设成 GitHub 的 noreply 邮箱，避免真实邮箱进提交历史：

```powershell
git config --global user.name "你的名字"
git config --global user.email "12345678+用户名@users.noreply.github.com"
```

（GitHub → Settings → Emails 里可以找到这个地址。）

---

## 3. 在 GitHub 创建仓库

1. 打开 <https://github.com/new>；
2. 仓库名：`physics-lab-tool`；
3. **先选 Private**（确认没问题再改 Public）；
4. **不要**勾选 "Add a README / .gitignore / license"（本地已经有了，勾了会冲突）。

---

## 4. 选一种安全的认证方式

### 方式 A：SSH（推荐，长期用）

```powershell
ssh-keygen -t ed25519 -C "你的GitHub邮箱"
# 一路回车，默认保存在 ~/.ssh/id_ed25519

Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

把输出的公钥整段复制到 GitHub → Settings → SSH and GPG keys → New SSH key。

验证：

```powershell
ssh -T git@github.com
# 看到 "Hi 你的用户名! You've successfully authenticated" 即可
```

### 方式 B：Fine-grained PAT（临时、最小权限）

GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens：

- **只授权 `physics-lab-tool` 这一个仓库**；
- 权限只给 **Contents: Read and write**；
- 有效期设 **30 天**；
- 生成后**不要**粘贴到聊天、Issue、代码或命令行历史里。

推送时让 Git Credential Manager 弹窗输入，或使用 `gh auth login`。

---

## 5. 关联远程仓库并推送

```powershell
# SSH
git remote add origin git@github.com:<你的用户名>/physics-lab-tool.git

# 或者 HTTPS
# git remote add origin https://github.com/<你的用户名>/physics-lab-tool.git

git push -u origin main
```

---

## 6. 推送后立刻验证

在 GitHub 网页上逐项检查：

- [ ] 文件列表里**没有** `.env`
- [ ] 没有 `data/`、`reports/` 里的内容
- [ ] 提交历史里没有出现 Key、密码、身份证、手机号
- [ ] 仓库是 Private（暂不公开）

---

## 7. 想改成 Public 之前

- [ ] 再跑一次 `python scripts/check_secrets.py`
- [ ] 把 `README.md` 里的个人信息（学号、真实姓名、手机号）删掉或替换
- [ ] 确认 `docs/screenshots/` 里的截图没有露出账号、聊天记录、桌面文件
- [ ] 确认没有同学的真实实验数据（涉及隐私）

---

## 8. 万一误提交了密钥

**顺序不能错：**

1. **立刻吊销**：GitHub Token 页面删除；大模型平台后台删除/轮换 Key；
2. 假设它已经泄露，检查账单和调用记录；
3. 再清理 Git 历史（`git filter-repo` 或 BFG），然后强制推送；
4. 通知协作者重新克隆。

`git rm` 只是删掉最新一次提交里的文件，**历史里还在**，所以必须吊销。

---

## 9. 账户安全清单（贴在显示器上）

- [ ] GitHub 开启 **2FA**（Settings → Password and authentication）
- [ ] 密码唯一，用密码管理器，不和学校账号共用
- [ ] 提交邮箱用 **noreply** 地址
- [ ] 不在公共电脑保存 Git 凭据；用完 `git credential-manager logout`
- [ ] Token 只给**单个仓库**、**最小权限**、**短有效期**
- [ ] 不把 Token 写进 URL（`https://token@github.com/...` 会留在历史里）
- [ ] 每次 `git add` 后先 `git status` / `git diff --cached`
- [ ] 开启 **Secret scanning** 和 **Push protection**（仓库 Settings → Code security）
- [ ] 怀疑泄露：先吊销，再清理，不要先删文件

---

## 10. 日常提交流程（建议）

```powershell
python scripts/check_secrets.py
git status
git add <具体文件>          # 尽量不用 git add -A
git diff --cached           # 看一眼到底提交了什么
git commit -m "feat: 说明这次改了什么"
git push
```

每周的 commit 记录就是周报里"开发过程"的证据，建议 commit message 写清楚
`feat:` / `fix:` / `docs:` 前缀，方便截图。
