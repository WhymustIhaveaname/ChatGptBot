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

import openai, json
import time
from utils import log


tokenlimits = {
    'gpt-4': 8192,
    'gpt-4-turbo': 128000,
    'gpt-4o': 128000,
    'gpt-4o-mini': 128000,
    'o1': 200000,
    'o1-mini': 128000,
    'o3-mini': 200000,
}

prices = {
    'gpt-4': (30,60),
    'gpt-4-turbo': (10,30), # old model, should not be used
    'gpt-4o': (2.5,10),
    'gpt-4o-mini': (0.15,0.6),
    'o1': (15,60),
    'o1-mini': (1.1, 4.4),
    'o3-mini': (1.1, 4.4),
}

class OpenAIParser:
    def __init__(self,):
        with open("config.json") as f:
            self.config_dict = json.load(f)
        # openai.organization = self.config_dict["ORGANIZATION"] if "ORGANIZATION" in self.config_dict else "Personal"
        openai.api_key = self.config_dict["openai_api_key"]
    
    def get_response(self, context_messages, model):
        "return message and number of tokens used"

        tokenlimit = tokenlimits.get(model,4096)

        token_num = len(str(context_messages))
        if token_num>tokenlimit:
            return "message too long (%d>%d), please /clear the context or try /gpt4"%(token_num,tokenlimit),0

        try:
            # check https://platform.openai.com/docs/guides/chat/response-format for the format
            response  = openai.ChatCompletion.create(model = model, messages = context_messages)
            msg       = response["choices"][0]["message"]["content"]
            freason   = response["choices"][0]["finish_reason"]
            if freason!="stop":
                msg  += "\nFinish because %s"%(freason)

            # the metric is $/M now
            prompt_price, completion_price = prices.get(model, (1,2))
            token_num = response["usage"]["prompt_tokens"]*prompt_price + response["usage"]["completion_tokens"]*completion_price

            return msg,token_num
        except Exception as e:
            log(e,l=2)
            return str(e) + "\nPlease try again later.", token_num*0.15

    def speech_to_text(self, audio_file):
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript["text"]

    def image_generation(self, userid, prompt):
        response = openai.Image.create(model="dall-e-3",prompt = prompt, n=1, size = "1024x1024", user = userid)
        image_url = response["data"][0]["url"]
        return image_url

if __name__ == "__main__":
    openai_parser = OpenAIParser()
    for model, _ in prices.items():
        print("testing %s"%(model))
        tik = time.time()
        msg,token_num = openai_parser.get_response([{"role": "user", "content": "Tell me a joke."}],model)
        tok = time.time()
        log("msg: %s\ntoken_num: %d"%(msg,token_num))
        log('time of %s: %.2fms'%(model,1000*(tok-tik)))
    # test_lantency()
