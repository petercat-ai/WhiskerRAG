# 分支策略和部署机制

## 分支保护策略

### 向 main 分支创建 Pull Request 的限制

只有以下分支模式允许向 `main` 分支创建 Pull Request：

- `preview` - 预发布分支
- `preview/*` - 预发布特性分支（如 `preview/feature-x`）

### 自动检查机制

通过 `.github/workflows/pr-branch-protection.yml` 工作流自动检查：
- 当向 `main` 分支创建 PR 时，会自动验证源分支是否符合允许的模式
- 如果源分支不符合规则，PR 检查会失败并显示错误信息
- 只有检查通过的 PR 才能被合并

### 最近修复的问题

- **修复了客户端生成问题**：更新 `swagger-typescript-api` 命令语法以适配最新版本
- **改进了错误处理**：添加了生成文件的验证和更详细的错误信息
- **优化了 TypeScript 配置**：修复了 `tsconfig.json` 中的 `include` 路径配置

## 部署机制

### 触发条件

部署会在以下情况下自动触发：

1. **推送触发** - 当代码被推送到以下分支时：
   - `main` - 触发生产环境部署
   - `preview` - 触发预发布环境部署
   - `preview/*` - 触发预发布环境部署

2. **工作流依赖触发** - 当 `server-ci` 工作流成功完成后自动触发部署

### 重要变更

- ❌ **移除了 Pull Request 触发器** - 创建 PR 时不会触发构建和部署
- ✅ **保留了推送触发器** - 只有在代码实际合并/推送时才会触发部署
- ✅ **保留了预发布机制** - 推送到 `preview` 或 `preview/*` 分支会触发预发布环境部署

### 环境映射

- `main` 分支 → Production 环境
- `preview` 或 `preview/*` 分支 → Preview 环境

## 推荐工作流程

1. **功能开发**：
   ```bash
   # 从 main 创建功能分支
   git checkout -b feature/new-feature main
   
   # 开发完成后，推送到 preview 分支进行测试
   git checkout preview
   git merge feature/new-feature
   git push origin preview  # 触发预发布部署
   ```

2. **预发布验证**：
   ```bash
   # 在预发布环境验证功能
   # 验证通过后，创建 PR 合并到 main
   git checkout preview
   # 通过 GitHub UI 创建 preview → main 的 PR
   ```

3. **生产发布**：
   ```bash
   # PR 合并后自动触发生产环境部署
   git checkout main
   git pull origin main  # 同步最新代码
   ```

## 紧急修复流程

```bash
# 创建紧急修复分支
git checkout -b hotfix/critical-issue main

# 修复完成后直接创建 PR 到 main
# hotfix/* 分支被允许直接向 main 创建 PR
```

这种策略确保了：
- 预发布环境用于功能验证
- 只有经过验证的代码才能进入生产环境
- 紧急情况下可以快速修复
- 避免了不必要的构建触发 