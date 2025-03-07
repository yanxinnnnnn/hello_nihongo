# Hello Nihongo

Hello Nihongo 是一个基于 FastAPI 和 DeepSeek 的日语学习辅助工具，提供中日双向翻译、平假名注释、语法解析和中文翻译功能，帮助用户提升日语造句能力。

## 📑 功能特性

- 🌐 **中日双向翻译**: 通过 DeepSeek API 实现精准翻译。
- 📝 **平假名注释**: 对日语句子进行平假名标注，帮助学习者理解发音。
- 📚 **语法解析**: 提供详细的日语语法分析。
- 🚀 **易用的 Web 界面**: 使用 FastAPI 提供简洁直观的用户界面。

---

## 📂 项目结构

```bash
hello_nihongo/
├── app/                # FastAPI 应用目录
│   ├── api/            # API 路由
│   ├── models/         # 数据模型
│   ├── services/       # 业务逻辑
│   ├── templates/      # HTML 模板文件
│   └── static/         # 静态资源 (CSS, JS)
├── config.yaml         # 项目配置文件
├── requirements.txt    # Python 依赖列表
└── README.md           # 项目说明文档
```

---

## ⚙️ 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/您的用户名/hello_nihongo.git
cd hello_nihongo
```

### 2. 创建虚拟环境 & 安装依赖

```bash
python3 -m venv venv
source venv/bin/activate  # 对于 Linux 和 macOS
# venv\Scripts\activate    # 对于 Windows

pip install -r requirements.txt
```

### 3. 配置环境变量

- 在 `config.yaml` 中配置 DeepSeek API 信息：

```yaml
deepseek:
  base_url: "https://api.deepseek.com"
  chat_api: "/chat/completions"
  api_key: "您的API密钥"
  timeout: 30
```

### 4. 启动项目

```bash
uvicorn app.main:app --reload
```

- 访问项目：[http://localhost:8000](http://localhost:8000)

---

## 🚀 使用方法

1. 访问项目主页，选择需要的功能模块。
2. 输入中文或日语句子，点击“翻译”按钮。
3. 查看翻译结果、平假名注释和语法分析。

---

## 📃 配置说明

项目使用 `config.yaml` 进行配置：

```yaml
deepseek:
  base_url: "https://api.deepseek.com"
  chat_api: "/chat/completions"
  api_key: ""
  timeout: 30

app:
  debug: true

logging:
  level: "DEBUG"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "app.log"
```

---

## 🛠️ 维护和更新

- **添加依赖**: 使用 `pip freeze > requirements.txt` 同步依赖。
- **更新代码**:

```bash
git pull origin main
```

---

## 📧 联系方式

如果您在使用中遇到问题或有好的建议，欢迎联系我：

- 📧 邮箱: yourname@example.com
- 💻 GitHub: [您的GitHub用户名](https://github.com/您的GitHub用户名)

---

## 📜 许可证

本项目遵循 [MIT License](LICENSE) 开源许可证。