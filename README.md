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
usage: main.py [-h] [--name NAME] [--page PAGE] [--cookies COOKIES] [--web-driver WEB_DRIVER] [--rules RULES] [--words WORDS]

贴吧机器人 v1.0

optional arguments:
  -h, --help            show this help message and exit
  --name NAME           贴吧名称
  --page PAGE           机器人浏览的页数
  --cookies COOKIES     登录Cookie保存文件位置
  --web-driver WEB_DRIVER
                        ChromeDriver文件位置
  --rules RULES         关键字检索规则
  --words WORDS         特殊分词规则文件
```

## 规则说明

```jsonc
{ 
    // 黑名单，出现的就删除
    "black_list": [
        "/.*小白资源网.*/", // 正则表达式
        "bbs70763246", // 普通模式
    ],
    // 黑名单操作
    "black_list_options": [
        "ban",   // 封号
        "delete" // 删帖
    ],
    // 剔除条件，当满足include时，如果满足exclude的规则则不处理
    "exclude_rules": [
        // 规则单元
        { 
            // 忽略大小写
            "ignore_case": true,
            // 关键字
            "keywords": [
                "c4droid",
                "头文件",
                "gcc",
                "include",
                "处理器",
                "代码",
                "源码",
                "编译",
                "安卓",
                "g++",
                "控制台",
                "编译器",
                "/\\w+\\.h/"
            ],
            // or 表示只要上述关键字只要满足一个即可
            "logic": "or"
        }
    ],
    "thread_rules": [
        {
            "exclude": "@exclude_rules",
            "include": [
                {
                    "ignore_case": true,
                    "keywords": [
                        // 关键字组
                        [
                            "PS",
                            "AI",
                            "AE",
                            "C4D",
                            "影视",
                            "后期",
                            "特效",
                            "模型"
                        ],
                        // 关键字组
                        [
                            "怎么",
                            "请问",
                            "/.*资源/",
                            "/.*教程/",
                            "/.*资料/",
                            "学",
                            "师傅"
                        ]
                    ],
                    // 关键字组中的为or
                    "logic": "and" // 同时满足两个关键字组，既 
                    // PS...怎么 PS...请问 
                    // 会被命中
                    // 如果包含 exclude_rules 中的条件，则不命中
                },
                {
                    "ignore_case": true,
                    "keywords": [
                        "充值",
                        "优惠"
                    ],
                    "logic": "and" // 同时满足两个关键字 既 充值...优惠
                },
                {
                    "ignore_case": true,
                    "keywords": [
                        "小白基地",
                        "建模学习",
                        "企鹅号",
                        "炫云",
                        "培训"
                    ],
                    "logic": "or"
                },
                {
                    "ignore_case": true,
                    "keywords": [
                        "水下",
                        ["切割", "焊接", "检测", "灌浆", "工作"]
                    ],
                    "logic": "and" // 同时满足两个关键字 既 水下...切割 水下...工作
                }
            ],
            "options": [
                "ban",  // 封号
                "delete", // 删帖
                "black" // 加黑名单
            ]
        },
        {
            "exclude": null,
            "include": [
                {
                    "ignore_case": true,
                    "keywords": [
                        "出",
                        "源码"
                    ],
                    "logic": "and"
                }
            ],
            "options": [
                "ban",
                "delete"
            ]
        },
        {
            "exclude": null,
            "include": [
                {
                    "ignore_case": true,
                    "keywords": [
                        [
                            "帮忙",
                            "求助"
                        ],
                        [
                            "作业"
                        ]
                    ],
                    "logic": "and"
                }
            ],
            "options": [
                "delete"
            ]
        },
        {
            "exclude": "@exclude_rules",
            "include": [
                {
                    "ignore_case": true,
                    "keywords": [
                        "c4d"
                    ],
                    "logic": "or"
                }
            ],
            "options": [
                "delete"
            ]
        }
    ],
    // 白名单
    "white_list": [
        "DXKite"
    ]
}
```