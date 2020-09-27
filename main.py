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
                qrcode = self.driver.find_element_by_css_selector(
                    '.tang-pass-qrcode-img')
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
        url = 'https://tieba.baidu.com/f?kw=' + name + '&fr=index'
        print('open page', url)
        self.driver.get(url)
        if '安全验证' in self.driver.page_source:
            print('safe check error')
            exit()
        # while True:
            # pass
        # print(self.driver.page_source)
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
        return self.delete_floor(link, 1)

    def ban_floor_user(self, link, floor, reason):
        """封禁用户"""
        print('ban_floor_user', link, floor, reason)
        # floor = wd.find_element_by_css_selector('.l_post.j_l_post')

        current = None
        count = 0

        while link != current or count > 5:
            print('ban_floor_user::open', link, 'current', current, count)
            self.driver.get(link)
            current = self.driver.current_url
        
        if count == 5:
            return False

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
            return False

        # 封禁第[floor]楼
        try:
            ban.click()
            dialog = self.driver.find_element_by_css_selector(
                '.uiDialogWrapper')
            reasons = dialog.find_elements_by_css_selector('.b_reason_item')
            reasons[reason - 1].click()
            dialog.find_element_by_css_selector('.b_id_btn').click()
        except NoSuchElementException as e:
            print('ban user error')
            print(e)
            return False
        return True

    def delete_floor(self, link, index):
        """删除楼层"""
        print('delete_floor', link, index)

        current = None
        count = 0

        while link != current or count > 5:
            print('delete_floor::open', link, 'current', current, count)
            self.driver.get(link)
            current = self.driver.current_url
        
        if count == 5:
            return False

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
            try:
                btn.click()
            except NoSuchElementException:
                return False
        else:
            reply = self.driver.find_elements_by_css_selector('.core_reply')
            # 删除别人的楼层
            try:
                btn = reply[index -
                            1].find_element_by_css_selector('.p_post_del')
                btn.click()
            except NoSuchElementException:
                return False
        # 删除帖子
        try:
            dialog = self.driver.find_element_by_css_selector('.dialogJ')
            dialog.find_element_by_css_selector('input[value="确定"]').click()
        except:
            return False
        return True

    @staticmethod
    def get_floor_num(elem: WebElement):
        """获取楼层"""
        floor_info = json.loads(elem.find_element_by_css_selector(
            '.j_lzl_container').get_attribute('data-field'))
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

    break_list = []

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
            'black_list_options': self.black_list_options,
            'white_list': self.white_list,
        })

    def check_content(self, content):
        """检查内容"""
        catch = None
        result = NO_MATCH

        for thread_rule in self.thread_rules:
            rule = self.check_rules(thread_rule['include'], content)
            if rule is not None:
                catch = {
                    'rule': rule,
                    'options': thread_rule['options']
                }
                result = BREAK_RULE
                if thread_rule['exclude'] is not None:
                    if thread_rule['exclude'] == '@exclude_rules':
                        if self.check_rules(self.exclude_rules, content) is not None:
                            result = EXCLUDE_RULE
                    elif self.check_rules(thread_rule['exclude'], content) is not None:
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
        user = thread['author_name']
        if user is None or len(user) == 0:
            user = str(thread['user_info']['id'])

        print('thread from', user)
        if self.check_rule_or(user, self.white_list):
            print('white list', user)
            return None
        if self.check_rule_or(user, self.black_list):
            print('black list', user, thread['title'])
            return {
                'user': user,
                'type': 'black_list',
                'title': thread['title'],
                'content': thread['content'],
                'link': thread['link'],
                'match': {
                    'rule': 'black_list',
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
                'match': rule_t
            }
        if rule_c is not None:
            return {
                'user': thread['author_name'],
                'type': 'content',
                'title': thread['title'],
                'content': thread['content'],
                'link': thread['link'],
                'match': rule_c
            }
        return None

    def load_process_list(self):
        try:
            self.break_list = load_from_json('process-list.json')
        except:
            self.break_list = []

    def save_process_list(self):
        try:
            return save_to_json('process-list.json', self.break_list)
        except:
            return []

    def scan_list(self, opt: TiebaOperator, max_page):
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
                    self.break_list.append(rule)
                    self.save_config()
                    self.save_process_list()
            if page >= max_page:
                break
            try:
                next_url = opt.get_next_page()
            except NoSuchElementException:
                print('the end')
                break
            print('go_next_page', next_url)
            opt.driver.get(next_url)

    def process(self, opt: TiebaOperator, max_page):
        """爬取处理帖子"""
        self.load_process_list()
        # 没有处理
        if len(self.break_list) <= 0:
            # 添加处理列表
            self.scan_list(opt, max_page)

        total = len(self.break_list)
        current = 0
        error_list = []
        for item in self.break_list:
            current += 1
            link = item['link']
            options = item['match']['options']
            text = str(current) + '/' + str(total)
            if 'black' in options:
                if item['user'] not in self.black_list:
                    self.black_list.append(item['user'])
                    self.save_config()
            if 'ban' in options:
                print(text, 'ban', item)
                if not opt.ban_floor_user(link, 1, 1):
                    error_list.append(item)
            if 'delete' in options:
                print(text, 'delete', item)
                if not opt.delete_thread(link):
                    error_list.append(item)
        self.break_list = error_list
        self.save_process_list()
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
            # print(pattern, text, re.match(pattern, text, flag))
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
                if TiebaBot.find_in(key, content, ignore_case):
                    bc += 1
        return bc == len(keywords)


if __name__ == "__main__":
    # 参数处理
    parser = argparse.ArgumentParser(description='Tieba Bot v1.0')
    parser.add_argument('--name', dest='name',
                        default='c4droid', help='scan tieba name')
    parser.add_argument('--page', dest='page', default=1, help='scan pages')
    parser.add_argument('--cookies', dest='cookies',
                        default=COOKIE_FILE, help='cookies path')
    parser.add_argument('--web-driver', dest='web_driver',
                        default=WEB_DRIVER, help='used web driver path')
    parser.add_argument('--rules', dest='rules',
                        default='rules.json', help='tieba keyword rules')
    parser.add_argument('--words', dest='words',
                        default='words.txt', help='jieba words list')
    args = parser.parse_args()
    # 数据操作
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument('--headless')
    # chrome_options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=chrome_options,
                              executable_path=args.web_driver)
    driver.maximize_window()
    tieba_bot = TiebaBot()
    tieba_bot.load_config(args.rules, args.words)
    operator = TiebaOperator(driver)
    operator.open_tieba(args.name, args.cookies)
    tieba_bot.process(operator, int(args.page))

# # 测试匹配
# if __name__ == "__main__":
#     bot = TiebaBot()
#     bot.load_config()
#     print(bot.judge_thread({
#         'author_name': '小白资源网',
#         'title': '全新平面设计114G超经典视频教程 基础入门班+品牌进阶班+ C4D基',
#         'content': '全新平面设计114G超经典视频教程 基础入门班+品牌进阶班+ C4D基础学习课程 设计师必学',
#         'link': 'https://test'
#     }))
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
