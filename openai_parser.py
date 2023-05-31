#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ChatGPT Telegram Bot

Description to be added.

__author__ = Zhiquan Wang
__copyright__ = Copyright 2023
__version__ = 1.0
__maintainer__ = Zhiquan Wang
__email__ = contact@flynmail.com
__status__ = Dev
"""

import openai, json, os
import datetime, time
from utils import log

class OpenAIParser:
    def __init__(self,):
        with open("config.json") as f:
            self.config_dict = json.load(f)
        # openai.organization = self.config_dict["ORGANIZATION"] if "ORGANIZATION" in self.config_dict else "Personal"
        openai.api_key = self.config_dict["openai_api_key"]
    
    def get_response(self, context_messages, model):
        "return message and number of tokens used"
        #log('using %s'%(model))
        if len(context_messages)==0 or context_messages[0]["role"]!="system":
            context_messages.insert(0, {"role": "system", "content": "You are a helpful assistant"})

        try:
            # check https://platform.openai.com/docs/guides/chat/response-format for the format
            response  = openai.ChatCompletion.create(model = model, messages = context_messages)
            msg       = response["choices"][0]["message"]["content"]
            freason   = response["choices"][0]["finish_reason"]
            if freason!="stop":
                msg  += "\nFinish because %s"%(freason)

            if model.startswith('gpt-4'):
                token_num = response["usage"]["prompt_tokens"]*15 + response["usage"]["completion_tokens"]*30
            else:
                token_num = response["usage"]["prompt_tokens"] + response["usage"]["completion_tokens"]

            return msg,token_num
        except Exception as e:
            log(e,l=2)
            return str(e) + "\nPlease try again later.", 0

    def speech_to_text(self, audio_file):
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript["text"]

    def image_generation(self, userid, prompt):
        response = openai.Image.create(prompt = prompt, n=1, size = "1024x1024", user = userid)
        image_url = response["data"][0]["url"]
        return image_url

def test_lantency():
    context_messages = []
    context_messages.append({'role': 'system', 'content': '''
You will be asked a series of questions about Python.
Please try your best to be helpful.'''})
    questions = ["""
1. 如何在一个函数内部修改全局变量
2. 列出5个python标准库
3. 字典如何删除键和合并两个字典
4. 谈下python的GIL
5. python实现列表去重的方法"""]
    for i,q in enumerate(questions):
        context_messages.append({'role': 'user', 'content': '%d: %s'%(i,q)})
    openai_parser = OpenAIParser()
    for model in ['gpt-3.5-turbo-0301','gpt-3.5-turbo','gpt-4-0314','gpt-4']:
        log("testing %s"%(model))
        tik = time.time()
        msg,token_num = openai_parser.get_response(context_messages,model)
        tok = time.time()
        log("msg: %s"%(msg))
        log('time of %s: %.2fs, %.2fms'%(model,tok-tik,1000*(tok-tik)/token_num))

if __name__ == "__main__":
    # openai_parser = OpenAIParser()
    # print(openai_parser.get_response([{"role": "user", "content": "Tell me a joke."}]))
    test_lantency()