#  Key-Scanner-Bot 🗝️

这是一个自动化工具，它会利用 GitHub API 搜索公开代码库中特定的字符串（例如 Google API 密钥），并将搜索结果自动保存到本仓库的 `api.txt` 文件中。整个过程由 GitHub Actions 驱动，无需人工干预。

## 它是如何工作的？

1.  **Python 脚本 (`search_keys.py`):** 使用一个 GitHub 个人访问令牌（PAT）向 GitHub API 发送认证请求，搜索预定义的字符串，并处理返回的结果。
2.  **GitHub Actions (`main.yml`):** 一个预设的自动化工作流，会按计划（例如每天一次）运行 Python 脚本，生成或更新 `api.txt` 文件。
3.  **自动提交:** 脚本运行完毕后，工作流会自动将更新后的 `api.txt` 文件提交（Commit）并推送（Push）回本仓库，从而保持结果的最新状态。

---

## 🚀 部署指南 (网页版 GitHub 操作)

请严格按照以下步骤操作，即可轻松部署你自己的扫描机器人。

### 第 1 步：创建 GitHub 个人访问令牌 (PAT)

脚本需要一个 PAT 才能访问 GitHub API。它决定了你的API请求频率上限。

1.  登录你的 GitHub，点击右上角你的头像，选择 **Settings** (设置)。
2.  在左侧菜单滑到底部，选择 **Developer settings** (开发者设置)。
3.  依次点击 **Personal access tokens** -> **Tokens (classic)**。
4.  点击 **"Generate new token"** (生成新令牌)，然后选择 **"Generate new token (classic)"**。

    

5.  **Note** (备注): 给你的令牌起一个容易识别的名字，例如 `KeyScannerBotToken`。
6.  **Expiration** (有效期): 根据你的需要设置，例如90天或“No expiration”(无期限)。
7.  **Select scopes** (选择权限范围): **只需勾选 `public_repo`**。这个权限足以搜索公开仓库。

    

8.  点击页面底部的 **"Generate token"** (生成令牌)。
9.  **⚠️ 重要：** 生成的令牌只会显示一次！请立刻复制它，并保存在一个临时安全的地方，下一步马上会用到。

### 第 2 步：创建你自己的GitHub仓库

1.  在 GitHub 上创建一个新的**私有(Private)**或**公开(Public)**仓库。推荐设为 **私有**，因为 `api.txt` 中可能包含敏感信息。仓库名可以叫 `Key-Scanner-Bot` 或任何你喜欢的名字。
2.  进入你新创建的仓库，点击 **"Add file"** -> **"Create new file"**。
3.  按照上面的文件结构，依次创建 `search_keys.py`, `requirements.txt`, `.gitignore` 文件，并将对应的代码粘贴进去。
4.  创建 `.github/workflows/main.yml` 文件时，你需要先输入 `.github/`，GitHub会自动创建文件夹，然后再输入 `workflows/`，最后输入 `main.yml` 作为文件名，再粘贴代码。

### 第 3 步：将 PAT 添加为仓库的机密 (Secret)

这是最关键的安全步骤，**绝对不能**将令牌直接写在代码里。

1.  在你的仓库页面，点击顶部的 **Settings** (设置) 选项卡。
2.  在左侧菜单中，找到 **Secrets and variables** -> **Actions**。
3.  点击右上角的 **"New repository secret"** (新建仓库机密) 按钮。

    

4.  **Name** (名称): 必须准确无误地填写 `GH_PAT`。
5.  **Secret** (机密值): 粘贴你在第 1 步中复制的个人访问令牌。
6.  点击 **"Add secret"** (添加机密)。这样，我们的自动化工作流就能安全地使用这个令牌了。

### 第 4 步：手动触发工作流

所有文件和设置都已就绪。现在你可以手动运行一次，来验证一切是否正常。

1.  在你的仓库页面，点击顶部的 **Actions** 选项卡。
2.  在左侧，你会看到名为 **"自动搜索API密钥"** 的工作流，点击它。
3.  在右侧，你会看到一个提示 "This workflow has a workflow_dispatch event..."，旁边有一个 **"Run workflow"** 的下拉按钮，点击它，然后再点击绿色的 **"Run workflow"** 按钮。

    

4.  工作流会开始运行。你可以点击正在运行的任务来查看实时日志。几分钟后（取决于搜索结果多少），任务会完成。
5.  任务成功后，回到你的仓库首页。你会发现多了一个由 "GitHub Actions Bot" 创建的提交，并且仓库中已经生成了 `api.txt` 文件，里面包含了搜索到的结果！

至此，你已成功部署了自动扫描机器人！🎉 它之后会按照 `main.yml` 文件中 `cron` 表达式设定的时间自动运行。
