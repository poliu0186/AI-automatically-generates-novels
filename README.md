# AI 小说创作助手 (AI Novel Writing Assistant)

一个基于ai +提示词 的智能小说创作生产力工具，
已经有数百家工作室和个人作者通过该工具实现了快速、批量生成小说。
通过 AI 技术提升创作效率以及完善的提示词管理功能，实现智能拆书、智能生书名简介、正文润色、shift+L快捷词条 等效率提升20倍，让写作更轻松、更专业。现已升级到 v5.2。
```
【重要必读】
**支持思维导图构建总纲、章节
**支持AI自我优化小说【探索性质】
**支持写作知识库管理**
**在文本输入域支持shift+L快捷词条输入** 方便解决大量重复性的输入
**支持任何主流大模型接入**
**支持自定义肤色、提示词导入导出**
**支持超大字数长文本记忆**
**支持选中大纲、章节、正文右键润色、扩写、去AI味**
**支持多套小说提示词库管理**
**支持拆书功能**


/gen接口这个可以是效果比较好的模型接口，用于大纲、章节、正文的生成
/gen2这个可以自己替换低成本模型的接口，用于AI批量自我迭代【探索】和拆书

知识库管理相关数据存储于基础配置-->知识库中 。如果您不经常用用知识库，那么可以在此文本填充相关剧情，同样也会被引用组装到提示词中
思维导图构建总纲、章节非常实用

```





在线体验 http://ssss.baby:20000




```
赛博朋克修仙世界：氪金飞升指南
——“你的灵根余额不足，请充值。”

核心矛盾：灵能资本主义
修仙不再是逆天改命的玄学，而是被巨型企业垄断的“付费订阅制服务”。

灵根即VIP会员：灵根需通过基因改造或义体移植获得，价格从“996福报套餐”（劣质五灵根）到“天道至尊黑卡”（天灵根）分三六九等，充值越多，修炼速度越快。

功法按字节收费：功法被加密成数据包，按章节付费解锁，修炼到关键段落弹出广告：“充值648灵石，立即跳过金丹心魔劫！”

渡劫靠众筹：突破境界需租用企业“云端渡劫矩阵”，算力按秒计费。穷修士常因余额不足被雷劫劈成灰，富豪则用“渡劫险”对冲风险。

社会结构：赛博宗门与赛博朋克贫民窟
宗门即企业：

九天科技集团：垄断灵根移植技术，广告词：“没有灵根？氪金就能逆天改命！”

万符银行：发行“灵币”数字货币，修士每日打坐产生的灵力自动抵扣贷款利息。

丹鼎直播平台：网红修士直播渡劫，观众打赏“避雷针”“护心丹”道具帮主播渡劫，榜一大哥可定制双修服务。

底层蝼蚁的挣扎：

黑市灵根贩子：贫民窟提供非法灵根移植，副作用包括灵力泄漏、妖兽化，但广告宣称：“比房贷便宜，比打工体面！”

灵力贷陷阱：年轻人借贷购买“筑基套餐”，还不上钱则被抽干灵力成为企业电池，美其名曰“福报修仙”。

赛博功德系统：穷人靠给企业点赞、转发修仙广告赚取“微功德”，攒够10万功德可兑换一粒劣质辟谷丹。

科技与修仙的魔幻缝合
义体修真：

机械灵根（需每月续费，否则自动锁死修为）。

电子飞剑（内置导航和付费皮肤，御剑时强制播放企业广告）。

虚拟心魔体验舱（付费消除心魔，但可能被植入消费欲望病毒）。

赛博天劫：
企业用纳米雷云技术控制天劫强度，充值用户可享受“天劫美容服务”——雷劈后皮肤自动美颜，附带金光特效。

区块链修仙：
修士的修炼数据被上传至“天道链”，企业通过AI分析剥削剩余价值。偷挖“灵力矿”的散修会被全网封杀。

经典剧情模板
《重生之我在赛博仙界当黑奴》：
主角因买不起“元婴保险”渡劫失败，重生后绑定“白嫖修仙系统”，专薅企业羊毛：盗版功法、走私灵药、用病毒瘫痪企业护山大阵。

《霸道总裁的电子炉鼎》：
女主为还债成为企业CEO的“灵力充电宝”，却发现对方是千年僵尸，靠吸食打工人灵力续命，最终联合AI器灵反杀。

《修仙朋克2077》：
佣兵接单暗杀企业高层，发现目标竟是自己的克隆体。真相是宗门用凡人肉身培养“人形渡劫替身”，专替富豪扛雷劫。

世界细节：资本异化的修仙日常
修士见面不问境界，只问：“您灵根年费多少？”

宗门招聘要求：“35岁以下金丹，996修炼制，会御剑加班、辟谷抗饿。”

贫民窟墙上涂鸦：“不氪金，毋宁死！” 旁边贴着小额贷广告：“今日借贷，明日飞升！”

总结：
这个世界里，修仙是巨型企业的谎言，飞升只是VIP用户的专属幻觉。但总有人不信命——他们黑入企业服务器、劫持灵能运输舰、用盗版功法修炼成“赛博天魔”，在霓虹与血光中嘶吼：
“修仙，是TM的免费开源项目！”
```


**app.py 接入相关的模型，请使用chatgpt来生成相关的和模型想匹配的代码**

## 可以直接利用带后缀的的 app-xxx.py
##  如果接入不了，请使用app.py 生成提示词 
```
 $app.py源码
 api地址 http://XXXX
 ai模型为XXXX 
 根据这个，请帮我生成【deepseek v3|阿里千问|文心一言|豆包】相关的api，同样需要支持流，要注意可能的参数 私钥参数等不一样。原来的返回格式最好和我给你的兼容，这个需要特别注意
```
## 功能速览
思维导图.png

![主页面预览](jpg/思维导图.png)
*可拖拽的思维导图*


![主页面预览](jpg/AI迭代2.png)
*智能按照句子、段落、字符数智能切割 和预览*

![主页面预览](jpg/ai迭代1.png)
*设定好分数和迭代次数*

![主页面预览](jpg/主界面.png)
*完整功能界面，支持多种智能写作辅助功能*

![右键预览](jpg/右键功能.png)
*智能右键润色功能*


![最终提示词](jpg/提示词最终预览修改.png)
*智能AI右键润色功能*

![智能书名生成](jpg/ai生成书名.png)
*AI智能书名生成功能展示*

![智能简介生成](jpg/ai生成简介.png)
*AI智能简介生成功能展示*



## 核心特色：专业提示词系统

### 1. 多层级提示词体系
- **大纲提示词**：专业策划角度的故事结构设计
  ```
  作为一名专业的网络小说策划，基于背景、人物、关系等信息设计...
  1. 提炼核心冲突，设计多重矛盾
  2. 设计3-5个重大转折点
  3. 人物塑造要立体，性格鲜明
  ...
  ```

- **章节提示词**：精确的章节结构规划
  ```
  每章节包含：
  - 核心看点
  - 情节线索
  - 感情线发展
  - 伏笔设置
  ...
  ```

- **内容提示词**：专业写作技巧指导
  ```
  多感官描写要求：
  - 视觉：场景细节、人物表情
  - 听觉：环境声音、语气语调
  - 触觉：物理感受、温度变化
  ...
  ```

### 2. 智能右键菜单系统
每个创作环节都配备专门的右键优化菜单：

- **大纲优化菜单**
  - AI评分
  - 深化冲突
  - 增加伏笔
  - 完善人物动机
  - 强化感情线
  - 优化节奏
  - 扩充细节
  - 提升高潮

- **章节优化菜单**
  - 章节评分
  - 深化情节
  - 强化冲突
  - 优化结构
  - 增加细节
  - 完善对话
  - 设置伏笔
  - 强化感情

- **正文优化菜单**
  - 文字评分
  - 优化文笔
  - 扩写对话
  - 强化情感
  - 添加细节
  - 改写视角
  - 去除说教
  - 润色升华

### 3. 变量系统
灵活的变量替换系统，支持：
- `${background}` - 背景设定
- `${characters}` - 人物设定
- `${relationships}` - 角色关系
- `${plot}` - 剧情架构
- `${style}` - 写作风格
- `${outline}` - 当前大纲
- `${chapter_outline}` - 章节大纲

## 其他核心功能

1. **智能创作功能**
   - AI智能起名
   - 完善相关知识库，支持长章节记忆
   - 自动生成简介
   - 同窗口AI助手
   - 自动字数统计
   - 快键键词条功能shift+L，随时插入关键卡片

2. **主题切换功能**
   - 支持明暗主题
   - 护眼模式
   - 自定义主题色
   - 支持专业模式、简易模式

3. **数据管理**
   - 本地数据存储
   - 配置导入导出
   - 自动保存功能
   - 方便随时写作

## 使用教程

### 1. 基础配置
1. 配置基础信息：
   - 填写小说背景
   - 设置人物设定
   - 定义角色关系
   - 规划核心剧情
   - 选择写作风格

2. 配置提示词：
   - 根据需要修改大纲提示词
   - 调整章节提示词
   - 自定义内容提示词

3. 配置右键菜单：
   - 设置大纲优化选项
   - 配置章节优化选项
   - 定制正文优化选项
   - 在大纲、章节、文本框中选中文本进行润色、改写等

### 2. 创作流程
1. 使用AI助手生成书名和简介
2. 利用提示词生成大纲
3. 展开章节细纲
4. 生成章节内容
5. 使用右键菜单优化文本

## 安装说明

```bash
git clone https://github.com/wfcz10086/AI-automatically-generates-novels.git
cd AI-automatically-generates-novels
pip install -r requirements.txt
python app.py
```

访问：http://localhost:20000

## Linux 生产部署（推荐）

建议使用 Linux + Gunicorn + Nginx + systemd。

### 公网 HTTPS 与安全配置（强烈建议）

若部署在公网，务必启用 HTTPS。项目已提供可直接改造的 Nginx 模板：

- `deploy/nginx-ai-novel.conf`

关键步骤：

1. 准备域名并解析到云服务器。
2. 申请证书（推荐 Let's Encrypt + certbot）。
3. 修改 `deploy/nginx-ai-novel.conf` 中证书路径：
  - `ssl_certificate`
  - `ssl_certificate_key`
4. 重载 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

建议在 `.env` 中显式开启：

```bash
ENVIRONMENT=production
FORCE_HTTPS=1
TRUST_PROXY=1
SESSION_COOKIE_SECURE=1
REMEMBER_COOKIE_SECURE=1
SESSION_COOKIE_SAMESITE=Lax
ADMIN_2FA_ENABLED=1
ADMIN_OTP_TTL_SECONDS=300
ADMIN_OTP_RESEND_COOLDOWN_SECONDS=60
ADMIN_OTP_LENGTH=6
```

说明：

- 已支持 HTTP 自动 301 跳转 HTTPS。
- Flask 层会在生产下强制 HTTPS（可通过 `FORCE_HTTPS=0` 临时关闭）。
- 会自动下发常见安全响应头（HSTS、X-Frame-Options、nosniff、Referrer-Policy 等）。
- 管理员登录支持邮箱验证码二次验证（默认开启，可通过 `ADMIN_2FA_ENABLED` 控制）。

附加检查：

- 安全检查清单：`deploy/SECURITY_CHECKLIST.md`
- 一键检查脚本：`deploy/security-check.sh`

### 敏感密钥避免明文（推荐）

为避免在 `.env` 中出现明文密钥，项目已支持两种兼容方案（旧配置仍可运行）：

1. `*_FILE`：把密钥放在受限权限文件中。
2. `ENC:...`：把密钥加密后写入 `.env`，运行时自动解密。

示例：

```bash
API_KEY_1_FILE=/run/secrets/api_key_1
API_KEY_2=ENC:gAAAAAB...
ALIPAY_PRIVATE_KEY=ENC:gAAAAAB...
MAIL_PASSWORD=ENC:gAAAAAB...
```

如果使用 `ENC:...`，请把主密钥放在系统环境变量（不要写入 `.env`）：

```bash
export APP_CONFIG_MASTER_KEY='你的Fernet主密钥'
# 或
export APP_CONFIG_MASTER_KEY_FILE=/run/secrets/app_config_master_key
```

生成主密钥和密文：

```bash
# 1) 生成主密钥
python deploy/encrypt_secret.py --generate-key

# 2) 生成密文，输出 ENC:...
python deploy/encrypt_secret.py --key '你的主密钥' --value '真实明文密钥'
```

迁移建议：

- `.env` 只保留 `ENC:...` 或 `*_FILE`，不保留明文。
- 主密钥仅放系统环境变量或 root 权限文件。
- 迁移完成后轮换一次旧 API Key/支付私钥/邮箱密码。

### 1. 启动多实例 Worker（Gunicorn）

项目已提供：

- `wsgi.py`
- `gunicorn.conf.py`
- `deploy/ai-novel.service`
- `deploy/nginx-ai-novel.conf`

示例命令：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
gunicorn -c gunicorn.conf.py wsgi:app
```

可通过环境变量调优：

```bash
export GUNICORN_BIND=127.0.0.1:60001
export GUNICORN_WORKERS=4
export GUNICORN_WORKER_CLASS=gevent
export GUNICORN_TIMEOUT=120
```

### 2. 配置 systemd 托管

```bash
sudo cp deploy/ai-novel.service /etc/systemd/system/ai-novel.service
sudo systemctl daemon-reload
sudo systemctl enable ai-novel
sudo systemctl start ai-novel
sudo systemctl status ai-novel
```

注意：将 service 文件中的路径改为你的真实部署路径（默认示例为 `/opt/ai-novel`）。

### 3. 配置 Nginx 反向代理

```bash
sudo cp deploy/nginx-ai-novel.conf /etc/nginx/conf.d/ai-novel.conf
sudo nginx -t
sudo systemctl reload nginx
```

如果你需要 HTTPS，请再接入证书（例如 certbot）。





## 重要特性：多模型支持系统

### 支持的AI模型

本系统支持多种主流AI模型，您可以根据需求选择不同的模型：

### 模型切换使用说明

```

1. **配置模型参数**
- 复制对应的模型配置文件（例如 `app-chatgpt.py`）到 `app.py`
- 或重命名为 `app.py` 替换原文件
- 配置相应的 API 密钥和参数

2. **启动服务**1
```bash
python app.py
```



## 版本历史
### v5.1(2025.1.23)
- 修复小bug
- 新增谷歌大模型、deepseek v3 大模型
- 新增提示词使用说明


### v5.0(2024.12.12)
- 新增可拖拽的思维导图生成大纲、章节功能
- 修复显示 文本域重叠问题
- 支持提示词和思维导图结合
- 修复其他诸多bug




### v4.0(2024.12.9)
- 新增ai根据自我评分实现迭代功能
- 智能分割、预览、评分
- 修正一些体验性、操作舒服点 


### v3.0 (2024.12.8)
- 增加提交前的所有提示词预览修改
- 优化显示
- 增加词条卡，shift+l 触发。
- 增加知识库 和json方式存储
- 修复其他bug


### v2.0 (2024.12.5)
- 新增主题切换
- 添加字数统计
- 集成AI助手
- 增强提示词系统
- 优化用户界面

### v1.0 (2024.11)
- 首次发布

## 许可证

MIT License

## 问题反馈

![图片](jpg/二维码.png)

- 项目主页：[GitHub](https://github.com/wfcz10086/AI-automatically-generates-novels)
- 问题反馈：[Issues](https://github.com/wfcz10086/AI-automatically-generates-novels/issues)
