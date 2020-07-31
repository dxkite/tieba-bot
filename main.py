from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException

import time
import jieba
import json
import os
import random
import re
import argparse

# 登陆cookie
COOKIE_FILE = 'cookies.json'
WEB_DRIVER = 'chromedriver.exe'

# 处理规则
NO_MATCH = 0
BREAK_RULE = 1
EXCLUDE_RULE = 2


def save_to_json(file, data):
    """保存文件到JSON"""
    js = json.dumps(data, indent=4, sort_keys=True, ensure_ascii=False)
    with open(file, 'w', encoding='utf-8') as f:
        f.write(js)


def load_from_json(file):
    """从文件载入JSON"""
    with open(file, 'r', encoding='utf-8') as f:
        return json.loads(f.read())


class TiebaOperator:
    driver = None

    def __init__(self, wd):
        self.driver = wd

    def get_login_username(self):
        """获取登陆的用户名"""
        try:
            un = self.driver.find_element_by_css_selector('.u_username_title')
            return un.text
        except NoSuchElementException:
            return None

    def get_login_qrcode(self):
        """获取登陆的验证码"""
        login = WebDriverWait(self.driver, 60) \
            .until(lambda d: d.find_element_by_css_selector('.u_login > .u_menu_item'))
        login.click()
        while True:
            try:
                # 获取加载成功的二维码
                qrcode = self.driver.find_element_by_css_selector('.tang-pass-qrcode-img')
                src = qrcode.get_attribute('src')
                if 'loading' in src:
                    continue
                return src
            except NoSuchElementException:
                pass

    def wait_login(self):
        """等待登陆"""
        img = None
        while True:
            user = self.get_login_username()
            if user is not None:
                return user
            if img is None:
                img = self.get_login_qrcode()
                print('login qrcode', img)

    def open_tieba(self, name, cookie_file):
        """打开贴吧"""
        self.driver.get('https://tieba.baidu.com')
        self.load_cookies(cookie_file)
        self.driver.get('https://tieba.baidu.com/f?kw=' + name + '&fr=index')
        user = self.wait_login()
        print('login user', user)
        self.save_cookie(cookie_file)
        return self

    def save_cookie(self, file):
        """保存cookie到文件"""
        # print('cookies save to', file)
        save_to_json(file, self.driver.get_cookies())

    def load_cookies(self, file):
        """载入cookie"""
        if os.path.isfile(file):
            list_cookies = load_from_json(file)
            for cookie in list_cookies:
                # print('set cookie', cookie['domain'], cookie['name'])
                self.driver.add_cookie({
                    'domain': cookie['domain'],
                    'httpOnly': cookie['httpOnly'],
                    'name': cookie['name'],
                    'secure': cookie['secure'],
                    'path': '/',
                    'value': cookie['value'],
                    'expires': None
                })
        else:
            print('cookies not exist', file)

    def get_thread_list(self):
        """扫描帖子"""
        thread_list = WebDriverWait(self.driver, 60) \
            .until(lambda d: d.find_elements_by_css_selector('#thread_list > .j_thread_list'))
        threads = []
        for thread in thread_list:
            user_info_json = thread.get_attribute('data-field')
            user_info = json.loads(user_info_json)
            title_elem = thread.find_element_by_css_selector('a.j_th_tit')
            text_elem = thread.find_element_by_css_selector('.threadlist_text')
            threads.append({
                'link': title_elem.get_attribute('href'),
                'user_info': user_info,
                'author_name': user_info['author_name'],
                'author_nickname': user_info['author_nickname'],
                'title': title_elem.text,
                'content': text_elem.text,
            })
        return threads

    def get_current_page(self):
        """获取当前页码"""
        page_list = WebDriverWait(self.driver, 60) \
            .until(lambda d: d.find_element_by_css_selector('#frs_list_pager'))
        return int(page_list.find_element_by_css_selector('.pagination-current').text)

    def get_next_page(self):
        """跳转下一页"""
        page_list = WebDriverWait(self.driver, 60) \
            .until(lambda d: d.find_element_by_css_selector('#frs_list_pager'))
        return page_list.find_element_by_css_selector('a.next').get_attribute('href')

    def delete_thread(self, link):
        """删除帖子"""
        self.delete_floor(link, 1)

    def ban_floor_user(self, link, floor, reason):
        """封禁用户"""
        print('ban_floor_user', link, floor, reason)
        # floor = wd.find_element_by_css_selector('.l_post.j_l_post')
        self.driver.get(link)
        # 翻页加载封禁按钮
        body = self.driver.find_element_by_xpath('//body')

        while True:
            bans = self.driver.find_elements_by_css_selector('a.p_post_ban')
            if len(bans) < floor:
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(random.random())
            else:
                ban = bans[floor - 1]
                break

        if ban is None:
            print('find post ban error')
            return

        # 封禁第[floor]楼
        try:
            ban.click()
            dialog = self.driver.find_element_by_css_selector('.uiDialogWrapper')
            reasons = dialog.find_elements_by_css_selector('.b_reason_item')
            reasons[reason - 1].click()
            dialog.find_element_by_css_selector('.b_id_btn').click()
        except NoSuchElementException as e:
            print('ban user error')
            print(e)

    def delete_floor(self, link, index):
        """删除楼层"""
        print('delete_floor', link, index)
        self.driver.get(link)
        # 翻页加载封禁按钮
        body = self.driver.find_element_by_xpath('//body')
        while True:
            bans = self.driver.find_elements_by_css_selector('a.p_post_ban')
            if len(bans) < index:
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(random.random())
            else:
                # 找到了楼层
                break
        if index == 1:
            # 删除1楼
            btn = self.driver.find_element_by_css_selector('.j_thread_delete')
            btn.click()
        else:
            reply = self.driver.find_elements_by_css_selector('.core_reply')
            # 删除别人的楼层
            try:
                btn = reply[index - 1].find_element_by_css_selector('.p_post_del')
                btn.click()
            except NoSuchElementException:
                pass
        # 删除帖子
        dialog = self.driver.find_element_by_css_selector('.dialogJ')
        dialog.find_element_by_css_selector('input[value="确定"]').click()

    @staticmethod
    def get_floor_num(elem: WebElement):
        """获取楼层"""
        floor_info = json.loads(elem.find_element_by_css_selector('.j_lzl_container').get_attribute('data-field'))
        return floor_info['floor_num']


class TiebaBot:
    # 配置
    white_list = []
    black_list = []
    black_list_options = []
    thread_rules = []
    exclude_rules = []
    # Web驱动
    rule_path = None

    def load_config(self,
                    thread_rules_path='rules.json',
                    words_path='words.txt'):
        jieba.load_userdict(words_path)
        rules = load_from_json(thread_rules_path)
        self.thread_rules = rules['thread_rules']
        self.exclude_rules = rules['exclude_rules']
        self.black_list = rules['black_list']
        self.white_list = rules['white_list']
        self.black_list_options = rules['black_list_options']
        self.rule_path = thread_rules_path

    def save_config(self):
        save_to_json(self.rule_path, {
            'thread_rules': self.thread_rules,
            'exclude_rules': self.exclude_rules,
            'black_list': self.black_list,
            'white_list': self.white_list,
        })

    def check_content(self, content):
        """检查内容"""
        catch = None
        result = NO_MATCH

        for thread_rule in self.thread_rules:
            rule = self.check_rules(thread_rule['include'], content)
            if rule is not None:
                catch = rule
                result = BREAK_RULE
                if thread_rule['exclude'] is not None and self.check_rules(thread_rule['exclude'], content) is not None:
                    result = EXCLUDE_RULE
            break

        if catch is None and self.check_rules(self.exclude_rules, content) is not None:
            result = EXCLUDE_RULE

        return catch, result

    @staticmethod
    def check_rules(rules, content):
        for rule in rules:
            if rule['logic'] == 'or':
                if TiebaBot.check_rule_or(content, rule['keywords'], rule['ignore_case']):
                    return rule
            if rule['logic'] == 'and':
                if TiebaBot.check_rule_and(content, rule['keywords'], rule['ignore_case']):
                    return rule
        return None

    def judge_thread(self, thread: dict):
        """根据规则处理帖子"""
        if self.check_rule_or(thread['author_name'], self.white_list):
            print('white list', thread['author_name'])
            return None
        if self.check_rule_or(thread['author_name'], self.black_list):
            print('black list', thread['author_name'], thread['title'])
            return {
                'user': thread['author_name'],
                'type': 'black_list',
                'title': thread['title'],
                'content': thread['content'],
                'link': thread['link'],
                'rule': {
                    'options': self.black_list_options
                }
            }
        rule_t, result_t = self.check_content(thread['title'])
        rule_c, result_c = self.check_content(thread['content'])
        # print(result_t, result_c)
        if EXCLUDE_RULE in [result_c, result_t]:
            return None
        if rule_t is not None:
            return {
                'user': thread['author_name'],
                'type': 'title',
                'title': thread['title'],
                'content': thread['content'],
                'link': thread['link'],
                'rule': rule_t
            }
        if rule_c is not None:
            return {
                'user': thread['author_name'],
                'type': 'content',
                'title': thread['title'],
                'content': thread['content'],
                'link': thread['link'],
                'rule': rule_c
            }
        return None

    def process(self, opt: TiebaOperator, max_page):
        """爬取处理帖子"""
        break_list = []
        while True:
            page = opt.get_current_page()
            thread_list = opt.get_thread_list()
            print('get_current_page', page)
            print('thread_list_length', len(thread_list))
            for thread in thread_list:
                rule = self.judge_thread(thread)
                if rule is not None:
                    print('thread', thread)
                    print('rule', rule)
                    break_list.append(rule)
                    self.save_config()
            if page >= max_page:
                break
            try:
                next_url = opt.get_next_page()
            except NoSuchElementException:
                print('the end')
                break
            print('go_next_page', next_url)
            opt.driver.get(next_url)

        total = len(break_list)
        current = 0
        for item in break_list:
            current += 1
            link = item['link']
            options = item['rule']['options']
            text = str(current) + '/' + str(total)
            if 'black' in options:
                self.black_list.append(item['author_name'])
            if 'ban' in options:
                print(text, 'ban', item)
                opt.ban_floor_user(link, 1, 1)
            if 'delete' in options:
                print(text, 'delete', item)
                opt.delete_thread(link)

        time.sleep(1)
        opt.driver.quit()

    @staticmethod
    def find_in(key, text, ignore_case):
        """关键字查找"""
        lk = len(key)
        # 正则表达式
        if lk > 2 and key.startswith('/') and key.endswith('/'):
            pattern = key[1:lk - 1]
            flag = re.IGNORECASE if ignore_case else 0
            return re.match(pattern, text, flag)
        # 普通分词处理
        if ignore_case:
            return key.lower() in jieba.cut(text.lower())
        return key in jieba.cut(text)

    @staticmethod
    def check_rule_or(content, keywords, ignore_case=True):
        for key in keywords:
            if TiebaBot.find_in(key, content, ignore_case):
                return True
        return False

    @staticmethod
    def check_rule_and(content, keywords, ignore_case=True):
        bc = 0
        for key in keywords:
            if isinstance(key, list):
                if TiebaBot.check_rule_or(content, key, ignore_case):
                    bc += 1
            else:
                if TiebaBot.find_in(content, key, ignore_case):
                    bc += 1
        return bc == len(keywords)


if __name__ == "__main__":
    # 参数处理
    parser = argparse.ArgumentParser(description='Tieba Bot v1.0')
    parser.add_argument('--name', dest='name', default='c4droid', help='scan tieba name')
    parser.add_argument('--page', dest='page', default=1, help='scan pages')
    parser.add_argument('--cookies', dest='cookies', default=COOKIE_FILE, help='cookies path')
    parser.add_argument('--web-driver', dest='web_driver', default=WEB_DRIVER, help='used web driver path')
    parser.add_argument('--rules', dest='rules', default='rules.json', help='tieba keyword rules')
    parser.add_argument('--words', dest='words', default='words.txt', help='jieba words list')
    args = parser.parse_args()
    # 数据操作
    chrome_options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=chrome_options, executable_path=args.web_driver)
    driver.maximize_window()
    tieba_bot = TiebaBot()
    tieba_bot.load_config(args.rules, args.words)
    operator = TiebaOperator(driver)
    operator.open_tieba(args.name, args.cookies)
    tieba_bot.process(operator, int(args.page))

# GLOBAL_EXCEPT = [{
#     'keywords': [
#         'c4droid',
#         '头文件',
#         'gcc',
#         'include',
#         '处理器',
#         '代码',
#         '编译器',
#         '/\\w+\\.h/',
#     ],
#     'logic': 'or',
#     'ignore_case': True,
# }]
#
# THREADS_RULES = [
#     {
#         'exclude': GLOBAL_EXCEPT,
#         'include': [
#             {
#                 'keywords': [['PS', 'AI', 'AE', 'C4D', '影视', '后期', '特效', '模型'],
#                              ['怎么', '请问', '资源', '教程', '资料', '学', '师傅']],
#                 'logic': 'and',
#                 'ignore_case': True,
#             },
#             {
#                 'logic': 'and',
#                 'ignore_case': True,
#                 'keywords': ['充值', '优惠'],
#             },
#             {
#                 'logic': 'or',
#                 'ignore_case': True,
#                 'keywords': ['小白基地', '建模学习', 'c4d', '企鹅号', '炫云'],
#             }
#         ],
#         'options': ['ban', 'delete', 'black'],
#     },
#     {
#         'include': [
#             {
#                 'logic': 'and',
#                 'ignore_case': True,
#                 'keywords': ['出', '源码'],
#             },
#         ],
#         'exclude': None,
#         'options': ['ban', 'delete'],
#     },
#     {
#         'include': [
#             {
#                 'logic': 'and',
#                 'ignore_case': True,
#                 'keywords': [['帮忙', '求助'], ['作业']],
#             },
#         ],
#         'exclude': None,
#         'options': ['delete'],
#     },
# ]
#
# save_to_json('rules.json', {
#     'thread_rules': THREADS_RULES,
#     'exclude_rules': GLOBAL_EXCEPT,
#     'black_list': [],
#     'white_list': [],
# })
#
# 测试匹配
# if __name__ == "__main__":
#     bot = TiebaBot()
#     bot.load_config()
#     # 2
#     print('C4D怎么使用tome.h头文件', bot.check_content('C4D怎么使用tome.h头文件'))
#     # 1
#     print('有没有会c4d的小哥哥小姐姐呀！', bot.check_content('有没有会c4d的小哥哥小姐姐呀！'))
#     # None
#     print(bot.judge_thread({
#         'author_name': 'TTHHR',
#         'title': 'C4D怎么使用啊',
#         'content': '我不会用头文件',
#         'link': 'https://test'
#     }))
#     # 1
#     print(bot.judge_thread({
#         'author_name': 'TTHHR',
#         'title': 'C4D怎么使用啊',
#         'content': '我不会用啊',
#         'link': 'https://test'
#     }))
#     # None
#     print(bot.judge_thread({
#         'author_name': 'TTHHR',
#         'title': 'C4D怎么使用头文件啊',
#         'content': '我不会用啊',
#         'link': 'https://test'
#     }))
