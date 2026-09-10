# 一键同步到 GitHub

本文件夹对应仓库：https://github.com/L-kin-trim/CUMCM2026

## 使用方法

在 Windows 中双击本目录的 `一键同步GitHub.cmd`，等待窗口显示 `Sync successful.`（同步成功）。首次使用时，按 Git 的提示登录具有仓库写入权限的 GitHub 账号。

启动脚本使用 ASCII 编码及 Windows CRLF 换行，以避免命令被截断或中文乱码。失败时显示 `Sync failed.`，具体原因见上方错误信息。

也可以在本目录的 PowerShell 中运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\sync-github.ps1
```

需要提前安装 Git，并配置提交身份：

```powershell
git config user.name "你的名字"
git config user.email "你的邮箱"
```

## 同步范围与行为

- 同步本目录及子目录中的新增、修改和删除，包括本说明、脚本、PDF 和 Excel 附件。
- 使用当前分支及 `origin` 远端；本仓库当前为 `main` 分支。
- 有修改时自动创建带时间戳的提交，然后推送；没有修改时也会尝试推送尚未上传的提交。
- Git 内部目录 `.git`、空文件夹及被 Git 忽略的文件不会上传。空文件夹如需保留，可放入 `.gitkeep`。
- 上传前请确认目录内没有密码、令牌或不应公开的资料。删除本地文件后运行脚本，也会在仓库的新版本中删除对应文件。
- 不强制推送。远端有本地尚未包含的提交时，脚本会停止，以避免覆盖他人的更新。

## 远端更新或运行失败

远端领先时，先在本目录运行以下命令，再重新双击脚本：

```powershell
git pull --rebase --autostash origin main
```

如果出现冲突，解决冲突并完成 rebase 后再同步。网络、登录或权限失败时，按窗口中的错误处理后重试；已经创建的本地提交仍会保留。

这是手动一键同步，不会在后台持续监控文件变化。
