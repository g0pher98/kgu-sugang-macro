import requests
import time
import json
import re

from fake_useragent import UserAgent

from requests.models import LocationParseError



class Macro():
    def __init__(self, profile_path = "./profile.json", host = "http://sugang.kyonggi.ac.kr", debug = False):
        '''
        debug: all, login, basket, req
        '''
        self.initial_time = self.get_time(forward = 30)
        self.session = requests.Session()
        self.debug = debug
        self.host = host
        self.referer = ''
        self.path = {
            'login': '/login?attribute=loginChk&lang={}&fake={}&callback=jQuery112401948917635895624_1628649765381',
            'basket_list': '/sugang?attribute=sugangBasketListJson&lang={}&fake={}&_search={}&nd={}&rows={}&page={}&sidx={}&sord={}',
            'sugang_list': '/sugang?attribute=sugangListJson&lang={}&fake={}&_search={}&nd={}&rows={}&page={}&sidx={}&sord={}',
            'sugang_mode': '/sugang?attribute=sugangMode&lang={}&fake={}&mode={}&fake={}'
        }
        self.user_agent = UserAgent().random
        self.blacklist = []

        # 로그인 정보 로드
        with open(profile_path, 'r') as fp:
            self.profile = json.load(fp)

        return
    
    def request(self, path, header={}, body=None):
        header['Referer'] = self.referer
        header['Accept-Language'] = 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,und;q=0.6'
        header['User-Agent'] = self.user_agent
        
        if not body:
            return self.session.get(self.host + path, headers = header)
        else:
            return self.session.post(self.host + path, headers = header, data = body)


    def login(self):
        '''
        경기대학교 수강신청 홈페이지에 로그인하는 함수
        '''
        url = self.path['login'].format(self.profile['lang'], self.initial_time)
        self.debug in ['all', 'login'] and print(f"[DEBUG] {url}")

        resp = self.request(url, body=self.profile)

        # 응답 데이터 중 실질적으로 필요한 부분만 파싱 후 처리
        result = re.findall('\{.*\}', resp.text)
        if result:
            json_result = json.loads(result[0])
            if json_result['code'] == '1':
                print(f"[*] login: {json_result['msg']}")
            else:
                print(f"[!] login: {json_result['msg']}")
                return False
        else:
            print('[!] login: nothing in response')
            return False

        # sync
        resp = self.request(f"/core?attribute=coreFrame_{self.profile['lang']}&fake={self.get_time()}")
        links = re.findall("\/core\?attribute=core[a-zA-Z0-9_=:/.?& ]+", resp.text)
        if links and len(links) >= 2:
            if "coreMain" in links[0]:
                self.referer = self.host + links[0]
            elif "coreMain" in links[1]:
                self.referer = self.host + links[1]

        return True
    
    def load_basket_list(self):
        '''
        수강신청을 위해 소망가방 리스트를 가져오는 함수
        '''
        # sync_url = "{}/core?attribute=lectListJson&lang={}&fake={}&menu=2&initYn=N&div_cd=C&_search=false&nd={}&rows=-1&page=1&sidx=&sord=asc".format(self.host, self.profile['lang'], self.initial_time, self.get_time())

        # self.session.get(sync_url, headers = {
        #     'Referer': self.referer,
        #     'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7,und;q=0.6'
        # })

        url = self.path['basket_list'].format(
            self.profile['lang'], self.initial_time,
            'false', self.get_time(), -1, 1, '', 'asc'
        )
        self.debug and print(f"[DEBUG] {url}")

        resp = self.request(url)
        self.basket_list = resp.json()
        
        self.debug and print(self.basket_list)

        # 목록 출력
        print(f"[+] 소망가방 목록")
        for row in self.basket_list['rows']:
            print(f"    [-] {row['gwamok_kname']} - {row['prof_name']}")

        return self.basket_list
    
    def load_sugang_list(self):
        '''
        기 수강신청된 리스트를 가져오는 함수
        '''
        url = self.path['sugang_list'].format(
            self.profile['lang'], self.initial_time,
            'false', self.get_time(), -1, 1, '', 'asc'
        )
        self.debug and print(f"[DEBUG] {url}")

        resp = self.request(url)
        self.sugang_list = resp.json()
        
        self.debug and print(self.basket_list)

        # 목록 출력
        print(f"[+] 수강신청 목록")
        for row in self.sugang_list['rows']:
            print(f"    [-] {row['gwamok_kname']} - {row['prof_name']}")

        return self.basket_list
    

    def reqeust_all(self):
        '''
        소망가방 리스트에 있는 과목들을 일괄 신청하는 함수
        '''
        already_sugang_list = []

        # 이미 수강중인 과목은 삭제
        for row in self.sugang_list['rows']:
            if row["wait_no"] == 0:
                already_sugang_list.append(row['gyoyuk_haksu'].split('-')[1])


        # run!!
        print('[+] 수강신청 시작')
        for row in self.basket_list['rows']:
            if row['haksu_cd'] in already_sugang_list:
                continue
            url = self.path['sugang_mode'].format(
                self.profile['lang'], self.initial_time, 'insert', self.get_time()
            )
            self.debug and print(f"[DEBUG] {url}")
            request_subject = {
                'params': row['params'],
                'retake_yn': 'N' #row['retake_yn']
            }
            self.debug and print(f"[DEBUG] {request_subject}")

            resp = self.request(url, body = request_subject)
            result = resp.json()
            print(f"    [+] {row['gwamok_kname']}")
            print(f"        [-] {result['msg']}")

        return

    def get_time(self, forward = 0):
        return int((time.time() - forward) * 1000)




if __name__ == "__main__":
    while True:
        try:
            print('[*] =============== macro start =============== ')

            macro = Macro()

            if macro.login():
                macro.load_basket_list()
                macro.load_sugang_list()
                macro.reqeust_all()

            print('[*] =============== macro end =============== ')
            break
        except Exception as e:
            print('[!] =============== macro error =============== ')
            print(e)
            
