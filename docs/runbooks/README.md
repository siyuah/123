# Runbooks

本目录用于保存 Dark Factory 的运维步骤、故障恢复剧本和 operator 可执行流程。

适合写入：

- 本地 preview 启动与验证
- journal backup / retain / verify
- provider shim 监督运行
- release readiness 检查
- 常见故障的诊断和恢复步骤

不适合写入：

- secret 明文
- 临时实验记录
- V3 binding 协议事实
- 只能在单台机器上偶然成立的不可复现命令

runbook 必须尽量包含完整命令、预期输出、失败分类和回滚方式。
