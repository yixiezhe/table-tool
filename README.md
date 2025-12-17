# 表格抽取工具（超详细使用说明）

本目录里有三种用法：

- **网页方式（纯前端，推荐）**：直接打开网页（本地双击或 GitHub Pages），上传文件，填列名/行数，点一下就下载结果（不需要后端）。
- **网页方式（可选后端）**：本机运行 `app.py`（Flask），然后浏览器打开。
- **脚本方式（命令行）**：用 `python` 跑 `cli_extract.py` 生成导出文件。

当前对 **Gamry 的 `.DTA`** 解析最强；其它**文本表格**（CSV/TSV/TXT/DAT 等）会按分隔符自动识别。

---

## 1) 你现在目录里有哪些文件？

关键文件说明：

- `index.html`：GitHub Pages 入口（自动跳转到 `static/index.html`）。
- `static/index.html`：网页前端页面（纯前端本地解析，不依赖后端）。
- `app.py`：可选网页后端（Flask）。
- `cli_extract.py`：命令行脚本（可交互、可先用记事本打开文件）。
- `table_extractor.py`：核心解析/抽取逻辑（网页和命令行都用它）。
- `out\`：命令行导出的文件默认放这里（你也可以改）。

---

## 2) 先确认你电脑能跑 Python

1. 按 `Win + R`
2. 输入 `powershell` 回车（打开 PowerShell）
3. 进入你的脚本目录（按你现在的路径）：

```powershell
cd D:\Data\script
```

4. 看看 Python 版本：

```powershell
python --version
```

能看到 `Python 3.x.x` 就 OK。

---

## 3) 网页怎么运行（最推荐）

你现在的网页已经支持 **纯前端本地解析**，所以：

- 放到 GitHub Pages：可以直接用（GitHub Pages 不支持跑 Python 后端，但我们不需要后端）。
- 在自己电脑上：也可以直接双击打开 `static/index.html` 使用。

### 3.1 纯前端运行（不需要 Flask）

方式 A：本机直接打开（最省事）

- 直接双击打开：`static/index.html`

方式 B：部署到 GitHub Pages（推荐）

1. 把整个项目推到 GitHub 仓库
2. 打开仓库页面 → `Settings` → `Pages`
3. `Build and deployment` 里选择：`Deploy from a branch`
4. Branch 选择你的主分支（比如 `main`），Folder 选 `/(root)`
5. 保存后等待一会儿，GitHub 会给你一个网站地址

打开 Pages 地址后，会自动加载 `index.html` → 跳转到 `static/index.html`。

### 3.2 （可选）运行本机后端 Flask

在 PowerShell 里执行：

```powershell
python -c "import flask; print(flask.__version__)"
```

如果报错 `No module named flask`，就安装：

```powershell
python -m pip install flask
```

> 提示：这一步需要联网（安装依赖）。装一次就够了。

### 3.3 启动网页后端

在 PowerShell（确保还在 `D:\Data\script`）运行：

```powershell
python .\app.py
```

你会看到类似 “Running on http://127.0.0.1:5000/” 的提示。

### 3.4 打开网页

打开浏览器（Edge/Chrome 都行），地址栏输入：

`http://127.0.0.1:5000/`

就能看到网页。

### 3.5 网页里每个输入框什么意思（照着填就行）

- **选择文件**：点一下选择你的文件（可多选）。
  - 多选时：会自动返回一个 `extracted.zip`，里面每个文件对应一个导出结果。
- **列名关键词**：你要提取的列名，用**逗号或空格**分隔。
  - 例 1：`Zreal,Zimag`
  - 例 2：`Idc Vdc IERange Imod`
- **导出格式**：
  - `dat/txt/tsv`：用 **Tab** 分隔，适合 Origin
  - `csv`：逗号分隔，适合 Excel
- **start_row**：从第几行数据开始抽（**数据行从 1 开始数，不算表头**）
  - 对 `.DTA`：通常 `Pt=0` 那一行就是第 1 行，所以一般填 `1`
- **max_rows**：只取前 N 行（比如你要前 70 行就填 `70`）
- **end_row**：抽到第几行结束（包含该行）
  - 一般你只填 `max_rows` 就够了；`end_row` 可留空
- **行关键词**（可选）：只保留“任意单元格包含这个关键词”的行
  - 不需要就留空

### 3.6 点按钮下载

点 “开始抽取并下载”：

- 单文件：直接下载一个导出文件
- 多文件：下载一个 `extracted.zip`

### 3.7 怎么关闭网页服务

回到运行 `python .\app.py` 的那个 PowerShell 窗口：

- 按 `Ctrl + C` 结束

---

## 4) 脚本怎么运行（命令行/批处理）

### 4.1 最简单的命令格式

```powershell
python .\cli_extract.py <文件路径1> <文件路径2...> -c "<列名列表>" -f dat -o out
```

常用参数：

- `-c / --columns`：要抽的列名（逗号/空格分隔）
- `--start-row`：起始数据行（默认 1）
- `--end-row`：结束数据行（可选）
- `--max-rows`：最多抽多少行（可选）
- `-f / --out-fmt`：导出格式（`csv|tsv|txt|dat`）
- `-o / --out-dir`：输出目录（默认 `out`）
- `--interactive`：走交互式提问
- `--notepad`：先用记事本打开文件（配合 `--interactive` 使用最舒服）

### 4.2 你这三个文件的“直接可复制命令”

1) `EIS.DTA`：提取 `Zreal`、`Zimag`

```powershell
python .\cli_extract.py .\EIS.DTA -c "Zreal Zimag" -f dat -o out
```

2) `EIS-CYCLE_#1.DTA`、`EIS-CYCLE_#2.DTA`：提取 `Idc`、`Vdc`、`IERange`、`Imod`，并且“只要前 70 行”

```powershell
python .\cli_extract.py ".\EIS-CYCLE_#1.DTA" ".\EIS-CYCLE_#2.DTA" -c "Idc Vdc IERange Imod" --max-rows 70 -f dat -o out
```

> 注意：你这两份文件实际只有 65 行数据，所以“前 70 行”会自动取到文件末尾（不报错）。

### 4.3 交互式（按提示输入，适合新手）

```powershell
python .\cli_extract.py .\EIS.DTA --interactive --notepad
```

它会：

1. 用记事本打开文件
2. 让你在命令行里逐个输入：列名、导出格式、start_row、max_rows 等
3. 自动生成导出文件到 `out\`

---

## 5) 导出文件怎么在 Origin 打开

最省事方法（通常可以）：

- 直接把导出的 `.dat/.txt/.tsv/.csv` 文件 **拖进 Origin**。

如果拖拽不行，就按菜单导入：

- `File` → `Import` → 选择 `ASCII`（或 `Single ASCII`）
- 对 `dat/txt/tsv`：分隔符选 `Tab`
- 对 `csv`：分隔符选 `Comma`
- 第一行是表头（列名）

---

## 6) 常见问题（照抄就能解决）

### 6.1 网页打不开 / 访问不了 127.0.0.1:5000

先确认你 PowerShell 里 **还在运行**：

```powershell
python .\app.py
```

如果提示端口被占用（Address already in use）：

- 打开 `app.py`，把最后一行的 `port=5000` 改成 `5001` 再运行
- 然后浏览器访问 `http://127.0.0.1:5001/`

### 6.2 提示找不到某一列（比如 “找不到列: 'xxx'”）

原因通常是：

- 你输的列名和真实列名不一致
- 或者你只输了一部分关键词但能匹配到多个列（歧义）

解决方法：

- 打开原始文件，复制粘贴**完整列名**
- 或者把关键词写得更精确

### 6.3 我上传的是 Excel（.xlsx），能不能抽？

目前这个版本**主要支持**：

- `.DTA`（Gamry）
- 以及 CSV/TSV/TXT/DAT 等**文本表格**

如果你确实需要 `.xlsx/.xls`，告诉我你常见的 Excel 格式样例（是否有多 sheet、表头在哪一行），我可以把 Excel 支持也加进去。
