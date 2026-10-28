# A股月线MACD自动选股（手机云端版）

专为手机使用：BaoStock沪深A股月线 + GitHub Actions自动扫描 + GitHub Pages手机选股页面。

## 固定参数：MACD（10、22、8）

- DIF = EMA(CLOSE, 10) - EMA(CLOSE, 22)
- DEA = EMA(DIF, 8)
- MACD柱 = 2 × (DIF - DEA)
- 筛选最近3根已完成月K线中的DIF上穿DEA，且最新月线仍保持DIF>DEA。
- 当月尚未收盘的临时金叉不算已确认。
- 价格数据采用BaoStock前复权；如与证券软件有差异，请检查复权方式和EMA初始值。

## 筛选范围和输出

沪深A股（不含北交所）；排除ST及退市名称。
基于最近36个月价格位置、近12个月涨幅、零轴下金叉、金叉月份进行技术观察排序。
手机网页支持搜索代码/名称、排序、仅看零轴下金叉、CSV导出。

注意：暂未加入盈利、国资控股、估值、社保持仓等基本面过滤；技术观察分不是投资评级。

## 苹果手机首次启动

1. 打开仓库 Settings → Pages，将 Build and deployment 中的 Source 选为 GitHub Actions。
2. 打开 Actions → A-share monthly MACD scanner → Run workflow。
3. 选择 main 分支，max_stocks 填 0（0 表示沪深全市场，50 等非0数字只用于抽样调试）。
4. 点击 Run workflow；等待运行完成后，再查看状态（绿色表示成功）。
5. 成功后手机打开 https://uiknbbtuknbg875356-glitch.github.io/-626/ 。

## 定期运行与维护

- 默认每周一北京时间19:25计划运行（GitHub不保证准时）。
- 数据覆盖不足80%或行情接口失败时拒绝发布新数据；请核对网页生成时间和扫描数量。
- GitHub可能暂停长期不活跃仓库的定时运行，应定期检查 Actions。
- 不要往公开仓库上传证券账户、资金、交易成本或其他个人信息。
- 失败排查位置：https://github.com/uiknbbtuknbg875356-glitch/-626/actions
- 核心计算：screener.py；单元测试：tests/test_signals.py；手机页面：docs/index.html。
- 本地测试命令：python -m unittest discover -s tests -v

后续可增加MACD多参数、自定义周月日、公司财务指标和国资机构筛选。
