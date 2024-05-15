import time
import datetime
import os
import json
import copy
import sqlite3
import openai
from utils import log
from openai_parser import OpenAIParser

with open("config.json") as f:
    config_dict = json.load(f)

class UserContext:
    def __init__(self, contactTime):
        self.__latestTime = contactTime
        self.__messageList = [{'role': 'system', 'content': 'You are a helpful assistant'},]
        self.wait_time = config_dict["wait_time"]
        self.summarymode = False
        self.model = "gpt-3.5-turbo"

    @property
    def messageList(self):
        return self.__messageList

    @property
    def latestTime(self):
        return self.__latestTime

    def update(self, contactTime, message, source):
        if (source == "user") and (contactTime - self.__latestTime > self.wait_time) :
            self.__init__(contactTime)
        else:
            self.__latestTime = contactTime

        self.__messageList.append({"role": source, "content": message})

class MessageManager:
    def __init__(self):
        self.openai_parser = OpenAIParser()

        self.userDict = {} #记录用户对话 context 的字典，核心功能数据

        self.img_limit   = config_dict["image_generation_limit_per_day"]
        self.super_users = config_dict["super_users"]

        self.__init_usage_table("chat")
        self.__init_usage_table("dalle")

    def get_response(self, chatid, userid, message):
        """
            chatid 用于追踪上下文
            userid 用于记录使用情况
        """
        t = time.time()
        if chatid not in self.userDict:
            self.userDict[chatid] = UserContext(t)

        self.userDict[chatid].update(t, message, "user")
        answer,tokenum = self.openai_parser.get_response(self.userDict[chatid].messageList,self.userDict[chatid].model)
        self.userDict[chatid].update(t, answer, "assistant")

        try:
            self.__update_usage(userid,tokenum,1,"chat") # 1 是使用次数
        except:
            log("write usage count failed",l=3)

        return answer

    def summarymode(self, chatid):
        if chatid not in self.userDict:
            self.userDict[chatid] = UserContext(time.time())

        if not self.userDict[chatid].summarymode:
            msg = " ".join(["You are a large language model whose expertise is reading and summarizing.",
                            "You will be given a set of materials which may contain knowledge that is unknown to you.",
                            "You must carefully read them and prepare to answer any questions about them."])
            self.userDict[chatid].update(time.time(), msg, "system")
            self.userDict[chatid].summarymode = True
            return 0
        else:
            return 1

    def clear_context(self, chatid):
        if chatid in self.userDict:
            self.userDict.pop(chatid)

    def set_gpt4(self, chatid):
        t = time.time()
        if chatid not in self.userDict:
            self.userDict[chatid] = UserContext(t)
        if self.userDict[chatid].model.startswith('gpt-4'):
            return 1
        else:
            self.userDict[chatid].model = "gpt-4"
            return 0

    def check_clear_context(self):
        t = time.time()
        poping = []
        for i in self.userDict:
            if t - self.userDict[i].latestTime > self.userDict[i].wait_time:
                poping.append(i)
        for i in poping:
            self.userDict.pop(i)

    def get_generated_image_url(self, user, prompt):
        tokenum,usednum = self.__check_usage(user,"dalle")
        if user in self.super_users:
            caption = "Hey boss, it's on your account. 💰"
        elif usednum < self.img_limit:
            caption = "You have used %d/%d times"%(usednum+1,self.img_limit)
        else:
            return (None, "You have reached the limit.")

        try:
            self.__update_usage(user,len(prompt),1,"dalle")
            url = self.openai_parser.image_generation(user, prompt)
        except openai.error.InvalidRequestError as e:
            # "Your request was rejected as a result of our safety system. Your prompt may contain text that is not allowed by our safety system."
            return (None, "Failed because: %s"%(e))

        return (url, caption)

    def get_transcript(self, user, audio_file):
        try:
            return self.openai_parser.speech_to_text(audio_file)
        except Exception as e:
            log(e,l=3)
            return ""

    @staticmethod
    def __check_usage(user, tbname):
        con = sqlite3.connect("usage.db")
        cur = con.cursor()
        cur.execute("SELECT TOKENUM,USEDNUM from %s where userid=? and day=?;"%(tbname),(user,datetime.date.today()))
        ans = cur.fetchone()
        con.close()
        if ans is None:
            return 0,0
        else:
            return ans

    @staticmethod
    def __update_usage(user, tokenum, usednum, tbname):
        con = sqlite3.connect("usage.db")
        cur = con.cursor()
        cur.execute("SELECT TOKENUM,USEDNUM from %s where userid=? and day=?;"%(tbname),(user,datetime.date.today()))
        ans = cur.fetchone()
        if ans is None:
            data = (datetime.date.today(),user,tokenum,usednum)
            cur.execute("INSERT INTO %s VALUES (?,?,?,?);"%(tbname),data)
        else:
            data = (ans[0]+tokenum,ans[1]+usednum,datetime.date.today(),user)
            cur.execute("UPDATE %s SET TOKENUM=?, USEDNUM=? WHERE DAY=? AND USERID=?"%(tbname),data)
        con.commit()
        con.close()

    @staticmethod
    def __init_usage_table(tbname):
        con = sqlite3.connect("usage.db")
        cur = con.cursor()
        cur.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='%s'"%(tbname))
        if cur.fetchone()[0]==1:
            log("table %s exists"%(tbname))
        else:
            cur.execute(""" CREATE TABLE %s(
                            DAY     TIMESTAMP NOT NULL,
                            USERID  INT NOT NULL,
                            TOKENUM INT NOT NULL,
                            USEDNUM INT NOT NULL,
                            PRIMARY KEY(DAY,USERID)
                        );"""%(tbname))
            con.commit()
            con.close()
            log("created table %s"%(tbname))
