import json
import copy

import time,sys,traceback,math

LOGLEVEL = {0:"DEBUG",1:"INFO",2:"WARN",3:"ERR",4:"FATAL"}
LOGFILE  = "bot.log"

def log(*msg,l=1,end="\n",logfile=LOGFILE):
    msg=", ".join(map(str,msg))
    st=traceback.extract_stack()[-2]
    lstr=LOGLEVEL[l]
    now_str="%s %03d"%(time.strftime("%y/%m/%d %H:%M:%S",time.localtime()),math.modf(time.time())[0]*1000)
    perfix="%s [%s,%s:%03d]"%(now_str,lstr,st.name,st.lineno)
    if l<3:
        tempstr="%s %s%s"%(perfix,str(msg),end)
    else:
        tempstr="%s %s:\n%s%s"%(perfix,str(msg),traceback.format_exc(limit=5),end)
    print(tempstr,end="")
    if l>=1:
        with open(logfile,"a") as f:
            f.write(tempstr)

class UserContext:
    def __init__(self, contactTime):
        self.__messageList = []
        self.__latestTime = contactTime

        with open("config.json") as f:
            self.config_dict = json.load(f)

        self.summarymode = False
    
    @property
    def messageList(self):
        return self.__messageList

    @property
    def latestTime(self):
        return self.__latestTime
    
    def update(self, contactTime, message, source):
        if (source == "user") and (contactTime - self.__latestTime > self.config_dict["wait_time"]) :
            self.clear_context(contactTime)

        self.__messageList.append({"role": source, "content": message})
        
    # def clear_context(self, clear_time):
    #     self.__latestTime = clear_time
    #     self.__messageList.clear()
    #     self.summarymode = False
