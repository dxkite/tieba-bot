# 贴吧机器人 

- 关键字删帖、封禁、黑名单


## 安装

### 1 安装依赖包

```
pip install -r requirements.txt
```

### 2 安装 chromedriver

根据 chrome 版本选择 chromedriver [下载地址](https://chromedriver.chromium.org/downloads)
本人 chrome 为 97，下载 [chromedriver for 97](https://chromedriver.storage.googleapis.com/index.html?path=91.0.4472.19/) 下载对应版本，下载完成后解压，复制  `chromedriver` 到代码目录


### 3 运行

以上步骤完成之后，直接运行命令即可，初次会需要扫码登录，登录完成之后即可处理帖子。

```
python main.py --page 2
```

## Usage

```
usage: main.py [-h] [--name NAME] [--page PAGE] [--cookies COOKIES]
               [--web-driver WEB_DRIVER] [--rules RULES] [--words WORDS]

Tieba Bot v1.0

optional arguments:
  -h, --help            show this help message and exit
  --name NAME           scan tieba name
  --page PAGE           scan pages
  --cookies COOKIES     cookies path
  --web-driver WEB_DRIVER
                        used web driver path
  --rules RULES         tieba keyword rules
  --words WORDS         jieba words list
```