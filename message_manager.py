import time
import datetime
import os
import json
import sqlite3
import openai
from user_context import UserContext,log
from openai_parser import OpenAIParser

class MessageManager:
    def __init__(self):
        self.openai_parser = OpenAIParser()

        self.userDict = {} #记录用户对话 context 的字典，核心功能数据
        with open("config.json") as f:
            config_dict = json.load(f)
        self.img_limit   = config_dict["image_generation_limit_per_day"]
        self.super_users = config_dict["super_users"]

        self.__init_usage_table("chat")
        self.__init_usage_table("dalle")

        # #本意是记录用户使用，但似乎未完成
        # self.user_chat_usage_dict = {}
        # (image_usage_file_name, now) = self.__get_usage_filename_and_key("image")
        # if not os.path.exists("./usage"):
        #     os.makedirs("./usage")
        # if os.path.exists("./usage/" + image_usage_file_name):
        #     with open("./usage/" + image_usage_file_name) as f:
        #         self.user_image_generation_usage_dict = json.load(f)
        # else:
        #     self.user_image_generation_usage_dict = {}

        # # Fixed by @Flynn
        # if now not in self.user_image_generation_usage_dict:
        #     self.user_image_generation_usage_dict[now] = {}

    def get_response(self, chatid, user, message):
        """
            user 仅用于记录使用情况
        """
        t = time.time()
        if chatid not in self.userDict:
            self.userDict[chatid] = UserContext(t)

        self.userDict[chatid].update(t, message, "user")
        answer,tokenum = self.openai_parser.get_response(chatid, self.userDict[chatid].messageList)
        self.userDict[chatid].update(t, answer, "assistant")

        try:
            self.__update_usage(user,tokenum,1,"chat")
        except:
            log("write usage count failed",l=3)

        return answer

    def clear_context(self, chatid):
        if chatid not in self.userDict:
            self.userDict[chatid].clear_context(time.time())

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
            return self.openai_parser.speech_to_text(user, audio_file)
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

    # def __check_image_generation_limit(self, user):
    #     (_, now) = self.__get_usage_filename_and_key("image")
    #     if now not in self.user_image_generation_usage_dict:
    #         self.__update_dict("image")
    #     if user not in self.user_image_generation_usage_dict[now]:
    #         used_num = 0
    #     else:
    #         used_num = self.user_image_generation_usage_dict[now][user]
    #     return used_num

    # def __get_usage_filename_and_key(self, chatORimage):
    #     if chatORimage == "chat":
    #         filename = "_char_usage.json"
    #     elif chatORimage == "image":
    #         filename = "_image_generation_usage.json"
    #     return (datetime.datetime.now().strftime("%Y%m") + filename,
    #             datetime.datetime.now().strftime("%Y-%m-%d"))

    # def __update_dict(self, chatORimage):
    #     (filename, now) = self.__get_usage_filename_and_key(chatORimage)
    #     if not os.path.exists("./usage/" + filename):
    #         if chatORimage == "image":
    #             self.user_image_generation_usage_dict = {}
    #         elif chatORimage == "chat":
    #             self.user_chat_usage_dict = {}
    #         return
    #     if chatORimage == "image" and now not in self.user_image_generation_usage_dict:
    #         self.user_image_generation_usage_dict[now] = {}
    #     elif chatORimage == "chat" and now not in self.user_chat_usage_dict:
    #         self.user_chat_usage_dict[now] = {}

    # def __update_usage_info(self, user, used_num, chatORimage):
    #     (filename, now) = self.__get_usage_filename_and_key(chatORimage)
    #     if now not in self.user_image_generation_usage_dict:
    #         self.__update_dict(chatORimage)
    #     if chatORimage == "image":
    #         self.user_image_generation_usage_dict[now][user] = used_num
    #         with open("./usage/" + filename, "w") as f:
    #             json.dump(self.user_image_generation_usage_dict, f)
    #     elif chatORimage == "chat":
    #         self.user_chat_usage_dict[now][user] = used_num
    #         # with open("./usage/" + filename, "w") as f:
    #         #     json.dump(self.user_chat_usage_dict, f)
