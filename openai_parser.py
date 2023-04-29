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
import datetime
from utils import log

class OpenAIParser:
    def __init__(self,model="gpt-4-0314"):
        self.model = model
        with open("config.json") as f:
            self.config_dict = json.load(f)
        # openai.organization = self.config_dict["ORGANIZATION"] if "ORGANIZATION" in self.config_dict else "Personal"
        openai.api_key = self.config_dict["openai_api_key"]
    
    def get_response(self, context_messages):
        "return message and number of tokens used"
        if len(context_messages)==0 or context_messages[0]["role"]!="system":
            context_messages.insert(0, {"role": "system", "content": "You are a helpful assistant"})

        try:
            # check https://platform.openai.com/docs/guides/chat/response-format for the format
            response  = openai.ChatCompletion.create(model = self.model, messages = context_messages)
            token_num = response["usage"]["prompt_tokens"] + response["usage"]["completion_tokens"]//2
            msg       = response["choices"][0]["message"]["content"]
            freason   = response["choices"][0]["finish_reason"]
            if freason!="stop":
                msg  += "\nFinish because %s"%(freason)
            return msg,token_num
        except Exception as e:
            log(e,l=2)
            return str(e) + "\nSorry, I am not feeling well. Please try again later.", 0

    def speech_to_text(self, audio_file):
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        return transcript["text"]

    def image_generation(self, userid, prompt):
        response = openai.Image.create(prompt = prompt, n=1, size = "1024x1024", user = userid)
        image_url = response["data"][0]["url"]
        return image_url

if __name__ == "__main__":
    openai_parser = OpenAIParser()
    print(openai_parser.get_response([{"role": "user", "content": "Tell me a joke."}]))