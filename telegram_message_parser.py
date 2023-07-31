#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TelegramMessageParser

Enter description of this module

__author__ = Zhiquan Wang, Sun Youran
__copyright__ = Copyright 2022
__version__ = 1.0
__maintainer__ = Zhiquan Wang
__email__ = i@flynnoct.com
__status__ = Dev
"""

helpmsg = """发送语音可以转文字并回复
/clear 清空上下文（十分钟不活跃也会自动清除）
/gpt4 当前对话将使用 GPT4, 注意 GPT4 的延时是 GPT3.5 的 4 倍, 收费是 30 倍, 所以请谨慎使用
/summarymode 打开总结模式
/dalle 描述：将描述转为图片"""

dosmsg = "Sorry, you are not allowed to use this bot. Please contact @fuckkwechat for more information."
errmsg = "Sorry, some error occured, please try again later."

import json
import os
import re
import time
import telegram
import subprocess
import asyncio
import httpx
from multiprocessing import Process,Queue
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from utils import log
from message_manager import MessageManager


class TelegramMessageParser:
    def __init__(self):
        # load config
        with open("config.json") as f:
            self.config_dict = json.load(f)
        
        # init bot
        self.bot = ApplicationBuilder().token(self.config_dict["telegram_bot_token"]).build()

        # init MessageManager
        self.message_manager = MessageManager()

    def _check_user_allowed(self, userid):
        with open("config.json") as f:
            config_dict = json.load(f)
        return True if userid in config_dict["allowed_users"] else False

    async def chat_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.effective_message.text
        groupmsg = update.effective_chat.type == "group" or update.effective_chat.type == "supergroup"
        if groupmsg and not ("@" + context.bot.username) in message:
            return
        elif not self._check_user_allowed(str(update.effective_chat.id)):
            await context.bot.send_message(chat_id=update.effective_chat.id,text=dosmsg)
            return

        if groupmsg:
            message = message.replace("@" + context.bot.username, "")

        await self._reply_answer(message,update,context)

    async def chat_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # check if user is allowed to use this bot
        if not self._check_user_allowed(str(update.effective_chat.id)):
            await context.bot.send_message(chat_id=update.effective_chat.id,text=dosmsg)
            return

        try:
            # sending typing action
            await context.bot.send_chat_action(chat_id=update.effective_chat.id,action="typing")

            file_id = update.effective_message.voice.file_id
            new_file = await context.bot.get_file(file_id)
            await new_file.download_to_drive(file_id + ".ogg")

            subprocess.call(['ffmpeg', '-i', file_id + '.ogg', file_id + '.wav'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            with open(file_id + ".wav", "rb") as audio_file:
                transcript = self.message_manager.get_transcript(str(update.effective_chat.id), audio_file)
            os.remove(file_id + ".ogg")
            os.remove(file_id + ".wav")

            # send transcripted text
            await update.message.reply_text("\"" + transcript + "\"")

        except Exception as e:
            await update.message.reply_text("Sorry, something went wrong. Please try again later.")
            log("something went wrong",l=3)
            return

        await self._reply_answer(transcript,update,context)

    async def _reply_answer(self,msg,update,context):
        # naive 版本
        # response = self.message_manager.get_response(str(update.effective_chat.id), str(update.effective_user.id), msg)

        # 带typing版本
        chatid = str(update.effective_chat.id)
        userid = str(update.effective_user.id)
        q = Queue()
        def get_response():
            try:
                response = self.message_manager.get_response(chatid,userid,msg)
                q.put((response,self.message_manager.userDict[chatid]))
            except Exception as e:
                response = "error happend in subprocess: %s"%(e)
                q.put((response,self.message_manager.userDict[chatid]))

        p1 = Process(target=get_response)
        p1.start()
        for i in range(3000):
            if p1.is_alive():
                if i%60==0:
                    try:
                        await context.bot.send_chat_action(chat_id=update.effective_chat.id,action="typing")
                    except:
                        pass
                await asyncio.sleep(0.1)
            else:
                break
        p1.join()
        response,self.message_manager.userDict[chatid] = q.get()

        # reply response to user
        try:
            mkd = re.search(r"```[^`]+?```|`[^`]+?`|\|[ :]{0,2}-+[ :]{0,2}\|",response)
            if mkd:
                response = response.split('`')
                for i in range(0,len(response),2):
                    response[i] = response[i].replace("_",r"\_").replace("*",r"\*")
                response = "`".join(response)

            if len(response.encode())<4096:
                await update.message.reply_text(response,parse_mode="Markdown" if mkd else None)
            else:
                await update.message.reply_document(response.encode(), filename="%s.txt"%(msg[0:10]))
            return
        except telegram.error.TelegramError:
            log("failed to send:\n%s"%(response),l=3)
        except:
            log("",l=3)
            await update.message.reply_text(errmsg)
            return

        try:
            if len(response.encode())<4000:
                await update.message.reply_text(response)
            else:
                await update.message.reply_document(response.encode(), filename="%s.txt"%(msg[0:10]))
            return
        except telegram.error.TelegramError:
            log("failed to send again:\n%s"%(response),l=3)
            await update.message.reply_text(errmsg)
        except:
            log("",l=3)
            await update.message.reply_text(errmsg)

    async def dump(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        chatid = str(update.effective_chat.id)
        userid = str(update.effective_user.id)
        if chatid in self.message_manager.userDict:
            ud = self.message_manager.userDict[chatid]
            info = ["model: %s"%(ud.model),
                    "summarymode: %s"%(ud.summarymode),
                    "livetime: %d (expire: %d)"%(time.time()-ud.latestTime,ud.wait_time),
                    "msgs len: %d\n%s"%(len(ud.messageList),ud.messageList[:2])]
            await update.message.reply_text("\n".join(info))
        else:
            await update.message.reply_text("no chat info for this user so far")

    async def send_test_msg(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # todo: `` 表示 ` 但 tg 不支持
        #response = "这样就可以对应任何数字而不只是 3500 了。注意使用模板字面量 `` ` `` 来包含变量。"
        # todo: [ 表示链接，不配对所以报错
        #response = "[0, 1) `torch.rand_like()`"
        # 这个也可能出问题
        #response = "```"
        try:
            mkd = re.search(r"```[^`]+?```|`[^`]+?`|\|[ :]{0,2}-+[ :]{0,2}\|",response)
            if mkd:
                log('markdown detected')
                response = response.split('`')
                for i in range(0,len(response),2):
                    response[i] = response[i].replace("_",r"\_").replace("*",r"\*")#.replace("[",r"\[")
                log(response)
                response = "`".join(response)
                log(response)

            await update.message.reply_text(response,parse_mode="Markdown" if mkd else None)
        except:
            log("",l=3)

    async def echo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.effective_message.text
        log("got in echo: %s"%(message))
        message = message.replace("/echo","")
        await update.message.reply_text(message)
        await update.message.reply_text(message,parse_mode="Markdown")

    async def summarymode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        r = self.message_manager.summarymode(str(update.effective_chat.id))
        if r==0:
            await context.bot.send_message(chat_id=update.effective_chat.id,text="Into summary mode.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,text="Already in summary mode.")

    async def gpt4(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        r = self.message_manager.set_gpt4(str(update.effective_chat.id))
        if r==0:
            await context.bot.send_message(chat_id=update.effective_chat.id,text="Into GPT4 mode.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,text="Already in GPT4 mode.")

    async def clear_context(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.message_manager.clear_context(str(update.effective_chat.id))
        await context.bot.send_message(chat_id=update.effective_chat.id,text="Context cleared.")

    async def check_clear_context(self, context: ContextTypes.DEFAULT_TYPE):
        self.message_manager.check_clear_context()

    async def image_generation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._check_user_allowed(str(update.effective_user.id)):
            await context.bot.send_message(chat_id=update.effective_chat.id,text=dosmsg)
            return

        # remove dalle command from message
        message = update.effective_message.text.replace("/dalle", "")

        # send prompt to openai image generation and get image url
        image_url, prompt = self.message_manager.get_generated_image_url(str(update.effective_user.id), message)

        # if exceeds use limit, send message instead
        if image_url is None:
            # sending typing action
            await context.bot.send_chat_action(chat_id=update.effective_chat.id,action="typing")
            await context.bot.send_message(chat_id=update.effective_chat.id,text=prompt)
        else:
            # sending typing action
            await context.bot.send_chat_action(chat_id=update.effective_chat.id,action="upload_photo")
            # send image to user
            await context.bot.send_photo(chat_id = update.effective_chat.id,photo = image_url,caption = prompt)

    async def chat_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,text="Sorry, I can't handle files and photos yet.")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Hello, I'm a ChatGPT bot.\n"+helpmsg
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(helpmsg)

    async def get_user_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="```\nuser id: %d\nchat id: %d```"%(update.effective_user.id,update.effective_chat.id),
            parse_mode="Markdown"
        )

    async def notify_users(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = "增加了一个 /gpt4 命令，可以使当前对话暂时使用 GPT4, 否则默认是 GPT3.5, 因为 4 太慢了。"
        with open("config.json") as f:
            config_dict = json.load(f)

        for userid in config_dict["allowed_users"]:
            if not userid.isnumeric():
                log("skip %s"%(userid))
                continue
            log("sending msg to %s"%(userid))
            try:
                await context.bot.send_message(userid,msg,disable_notification=True)
                time.sleep(1)
            except:
                log("",l=3)

    async def error_handler(self,update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if isinstance(context.error,httpx.LocalProtocolError):
            return
        log("Exception: %s"%(str(context.error).strip(),),l=3)

    def add_handlers(self):
        self.bot.add_handler(CommandHandler("start", self.start))
        self.bot.add_handler(CommandHandler("help", self.help))
        self.bot.add_handler(CommandHandler("clear", self.clear_context))
        self.bot.add_handler(CommandHandler("summarymode", self.summarymode))
        self.bot.add_handler(CommandHandler("gpt4", self.gpt4))
        self.bot.add_handler(CommandHandler("getid", self.get_user_id))
        self.bot.add_handler(CommandHandler("dump", self.dump))
        #self.bot.add_handler(CommandHandler("notify", self.notify_users))
        #self.bot.add_handler(CommandHandler("test",self.send_test_msg))
        self.bot.add_handler(CommandHandler("echo",self.echo))

        if self.config_dict["enable_voice"]:
            self.bot.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.VOICE, self.chat_voice))

        if self.config_dict["enable_dalle"]:
            self.bot.add_handler(CommandHandler("dalle", self.image_generation))

        self.bot.add_handler(MessageHandler(filters.ChatType.PRIVATE & (filters.PHOTO | filters.AUDIO | filters.VIDEO), self.chat_file))
        self.bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), self.chat_text))
        self.bot.job_queue.run_repeating(self.check_clear_context,15*60,first=15*60)
        self.bot.add_error_handler(self.error_handler)

    def run_polling(self):
        # add handlers
        self.add_handlers()

        # start bot
        self.bot.run_polling()
        log("started")

if __name__ == "__main__":
    t = TelegramMessageParser()
    t.run_polling()

