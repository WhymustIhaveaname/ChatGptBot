# ChatGPT Bot for Telegram

## 使用

这是一个 Telegram ChatGPT 机器人，它会调用 ChatGPT API 并使用 Telegram 与您交互。

* 私聊调用 chatgpt api 回答问题
* 发送语音先将语音转文字再回答
* `/dalle 文字描述`：将文字描述转为图片
* 在群组中@机器人它也会回复

您需要准备
* Telegram bot 一个以及它的 api token
* ChatGPT api key
* 您自己的 Telegram userid (可以找一些公开机器人或者对这个机器人使用 `/getid` 命令来获得)

并将它们填入 `config.json` 以使用机器人

## 注意

* tg 机器人的创建请找 [@BotFather](https://t.me/BotFather) 自助进行，事后将对应的 API keys 填入 `config.json`
* tg 机器人默认开启隐私模式，也就是不会收到群中的消息，为了让它回复群组中的问题，您可以
  1. 将 bot 设置为管理员，或者
  2. 找 BotFather，Bot Settings --> Group Privacy --> Turn Off

## 相对于原版的更新

* 超长的文字以文件形式发送（而不是失败）
* 增加 Markdown 支持
* 增加了 `summarymode`
* 群组鉴权：在 `config.json` 中的 `allowed_users` 中填 chat id 即可
* 定时清除 Context
* 增加了 /help、日志和 error 记录
* 将使用数统计从混乱的字典记录切换到了 sqlite
* 语音转文字之后先打印结果再试图回复，这样显得反应快一些
* 改了一些小 bug、catch 住了一些 API 调用时的报错
* 将 Windows line ending 改为了 Unix 的，并删除了行尾多余的空白字符

## 文件依赖关系

按自顶向下的顺序
* `telegram_message_parser.py` 负责和 Telegram 的接口，依赖 `message_manager.py`
* `message_manager.py` 负责语境维护，依赖 `user_context.py` 和 `openai_parser.py`
* `user_context.py` 负责语境维护
* `openai_parser.py` 负责 OpenAI 接口

<!--![](/docs/dialog.png)-->

## News

- **DALL·E, the OpenAI Image Generation Model**, is now supported! Send a short prompt to the Bot and get your own painting!
- **Whisper, the OpenAI Intelligent Speech Recognizer**, is now supported! Now chat with the Bot with audio messages!

## Introduction

ChatGPT Bot for Telegram is implemented with [OpenAI ChatGPT API](https://platform.openai.com/docs/guides/chat) released on March 1, 2023. The Telegram integration framework is based on [python-telegram-bot](https://python-telegram-bot.org).

ChatGPT Bot can act as your Telegram contact. You can chat with it either personally or in a group chat. Just like the popular AI on the OpenAI official site, the Bot shares knowledge and inspires exciting new ideas. Many interesting features, such as **DALL·E** and **Whisper** are integrated together to make our Bot smarter and more usable.

We hope you enjoy it!

## Features

The Telegram Bot features the following functions:

- An AI consultant, based on OpenAI ChatGPT, interacts in a conversational way.
- A flexible speech recognizer which supports audio interaction.
- A AI painter reponses to user's requirement prompt.

Additonal functions are also implemented:

- Set the daily limitation of requirements to **DALL·E**.
- Grant more resources to _Super Users_.

## Commands

- `/start`: Start the bot.
- `/clear`: Clear the conversation context.
- `/getid`: Get your Telegram user ID.
- `/dalle <prompt>`: Ask DALL·E for a painting based on your prompt.

## Sample Usage

The Bot works in both personal and group chat of Telegram.
In a personal chat, simply send a message to the Bot and it will reply to you.
In a group chat, you need to tag the message with `@<bot_name>` to invoke the Bot.

### Preparation

1. Create a Telegram bot by [@BotFather](https://t.me/BotFather) and get the token.
2. Create an OpenAI account and get the API key.
3. A Linux VM or a server with Python 3 is needed to run the bot.
4. A practical Internet environment is required.
5. (Optional) [FFmpeg](https://ffmpeg.org) is required for the Bot to handle voice messages with Whisper. If you are not interested in using voice messages, you don't need to install it and **must set `enable_voice` in the config file to False**.

> **Note**: You should disable the privacy mode of the bot. Otherwise the bot will not receive the messages from the group chat. You can do this by sending `/setprivacy` to [@BotFather](https://t.me/BotFather).

### Deployment

Download the latest release version and install the dependencies.

```bash
wget https://github.com/flynnoct/chatgpt-telegram-bot/releases/latest
pip install -r requirements.txt
```

Then, you need to create a config file to manage the Bot. The config file includes sensitive information, such as telegram_token and openai_api_key, and we only release the corresponding template `config.json.template`. Therefore, you need to create a new `config.json` file and replace the relative fields with your own.

```bash
cp config.json.template config.json
```

Follow below procedures to fill you `config.json`:

1. Replace the `telegram_token` and `openai_api_key` with your own.
2. Add allowed users to the `allowed_users` list. You can get your user id by sending `/start` to [@userinfobot](https://t.me/userinfobot) or send `/getid` to the Bot (after you start it).

> Note: the user ID is a series of numbers, you should add it to the `allowed_users` list as a string (add quotation marks around it).

Now, you can run the Bot with `start_bot.sh` and try talk to it. Also, you can invite it to group chats and share with your friends!

To clear ChatGPT conversation context and restart the Bot, run shell script `restart_bot.sh`. To shut down the Bot, run `stop_bot.sh`.

## Release version and notes

The latest released version can be found [here](https://github.com/flynnoct/chatgpt-telegram-bot/releases/latest). More interesting new features are comming soon!

The release notes are [here](/docs/release_notes.md).

## License

[MIT](LICENSE.md)

## Buy Me a Coffee

If you like this project, you can buy me a coffee ❤️ or give this repository a free star ⭐️.

Click [Alipay](donate_code/alipay.jpg) to open QR code.
