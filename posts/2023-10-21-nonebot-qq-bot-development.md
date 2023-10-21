---
title: NoneBot QQ 机器人开发指南
categories: Python
tags: [Bot]
created: 2023-10-21 17:15:00
---

[QQ 开放平台](https://q.qq.com/#/) 近期将把之前已经用于频道的 [QQ 机器人](https://bot.q.qq.com/wiki) 扩展到群聊和私聊场景。虽然功能限制较多，但由于其是官方 API，稳定性会比较好。本篇文章为使用 NoneBot 开发 QQ 机器人的教程，阅读本教程需要有一定 Python 开发基础。需要注意，本教程仅为相关文档的补充，请仔细阅读文中引用的文档。

## 前期准备

## 了解机器人能力

QQ 机器人应用于频道和群聊两个主要场景，可以在单聊、群聊、文字子频道、频道私信使用，提供的频道机器人能力可以参考 [API 文档](https://bot.q.qq.com/wiki/develop/api/)；群聊机器人能力暂未公开发布，可先参考 [QQ Bot 开发者文档【内测版】](https://docs.qq.com/doc/DRkVHT1N2a1JYSnVr)。

需要注意的限制有：

- 发送消息文本中的链接需要经过 ICP 备案，并在 QQ 机器人管理端进行根目录文件验证绑定。其他含有格式为 `英文.英文` 的文本也无法发送，如 `bot.self_id`，可以考虑将 `.` 替换为其他符号。
- 无法在群聊和文字子频道接收图片和视频。
- 无法在文字子频道和频道私信收发语音和文件，无法在群聊接收语音和文件。
- 所有群管理能力暂不对外开放。

### 创建沙箱频道

当前 QQ 机器人需要在沙箱频道中进行测试，请确保所使用的开发者 QQ 账号拥有 QQ 频道内测权限，并创建一个频道供机器人测试使用，并确保该频道人数小于 20 人。

### 私域机器人

公域 QQ 机器人只能响应 @机器人 后发送的消息，而频道私域机器人可以响应全量的文字子频道消息，并有额外的频道管理能力（群机器人目前只有公域）。如果想要创建不需要 @机器人 的频道私域机器人，请确保使用频道主的账号进行 QQ 开放平台的注册，并在创建机器人时选择类型为“私域”。

频道私域机器人额外能力：获取频道成员列表、删除指定频道成员、创建子频道、修改子频道信息、删除指定子频道、可以接收频道内发送的所有消息事件。

## QQ 机器人介绍与开通

想要接入 QQ 机器人，首先需要在 QQ 开放平台进行注册，具体流程请查看 QQ 机器人文档的 [接入流程](https://bot.q.qq.com/wiki/#%E6%8E%A5%E5%85%A5%E6%B5%81%E7%A8%8B) 部分，可以使用企业或个人主体入驻（文档中第 2 步或第 3 步）。

完成开发者账号创建后，登录 [QQ 开放平台](https://q.qq.com/#/app/bot) 参考 接入流程 文档的第 4 步创建应用，在 “应用管理” → “机器人” 标签下点击 “创建机器人” 按钮。

成功创建机器人后在 [开发设置](https://q.qq.com/bot/#/developer/developer-setting) 界面获取机器人的 BotAppID、机器人令牌、机器人密钥。

## NoneBot 项目创建与配置

本文中的 NoneBot 均指 NoneBot2。NoneBot2 是一个可扩展的 Python 异步机器人框架，它会对机器人收到的事件进行解析和处理，并以插件化的形式，按优先级分发给事件所对应的事件响应器，来完成具体的功能。

### 测试项目创建

如果未使用过 NoneBot，建议首先创建一个测试用的 Bot 工程以熟悉项目创建流程。

参考 NoneBot 文档的 [快速上手](https://nonebot.dev/docs/quick-start) 章节创建一个基于终端的交互式机器人实例，并测试是否正常工作。

### 项目创建与配置

上述测试成功后便可以创建开发 QQ 机器人使用的工程，命令行跳转到放置工程的目录，按照上述 快速上手 章节中 创建项目 部分的操作步骤，项目模板 选择 `simple（插件开发者）`，并按下面的内容选择驱动器和适配器：

```
[?] 要使用哪些驱动器? HTTPX (HTTPX 驱动器), websockets (websockets 驱动器)
[?] 要使用哪些适配器? QQ (QQ 官方机器人)
```

完成项目创建后，参考 [QQ 适配器文档](https://github.com/nonebot/adapter-qq) 进行 QQ 适配器配置，打开项目目录下的 `.env` 文件（如果没有这个文件，请在创建时选择 `simple` 模板），添加以下内容：

```
QQ_IS_SANDBOX=true
QQ_BOTS='
[
  {
    "id": "xxx",
    "token": "xxx",
    "secret": "xxx",
    "intent": {
      "guild_messages": true,
      "at_messages": false
    }
  }
]
'
```

将 `id` `token` `secret` 分别替换为在 QQ 开放平台获取到的 BotAppID、机器人令牌、机器人密钥。

以上配置为频道私域机器人，接收全量消息无需 @机器人，如果使用频道公域机器人，将 `guild_messages` 值改为 `false`，`at_messages` 值改为 `false`，或删去这两个配置项使用默认值。

完成以上配置后，运行机器人项目，在沙箱频道中 @机器人 并输入 `/echo hello world` 测试，如果收到回复则配置成功（此处需要 @机器人 是因为 `echo` 插件只接受与我相关的消息，文字子频道中需要 @机器人 触发）。

## 插件开发

### 插件编写基础

参考 NoneBot 文档中的 [插件编写准备](https://nonebot.dev/docs/tutorial/create-plugin)、[事件响应器](https://nonebot.dev/docs/tutorial/matcher)、[事件处理](https://nonebot.dev/docs/tutorial/handler)、[获取事件信息](https://nonebot.dev/docs/tutorial/event-data) 四个部分进行示例插件的创建。

按照文档创建的插件是可以提供给任何适配器使用的，所以也适用于 QQ 适配器。这种方式的局限性在于无法适用适配器提供的特殊消息类型，而只能发送纯文本，要实现发送图片之类的功能，则需要根据所使用的适配器对发送的消息进行处理。

### QQ 适配器消息处理

参考 NoneBot 文档中的 [处理消息](https://nonebot.dev/docs/tutorial/message) 部分，文档中是以 `Console` 适配器作为示例，与 QQ 适配器有部分不同，QQ 适配器中提供了以下消息段：

- `MessageSegment.text("abc")`: 文本消息段。
- `MessageSegment.emoji("4")`: QQ 表情，ID 参考 QQ 机器人文档的 [表情对象](https://bot.q.qq.com/wiki/develop/api/openapi/emoji/model.html) 部分。
- `MessageSegment.mention_user("12345")`: 提及 @用户。
- `MessageSegment.mention_channel("123")`: 提及 #子频道。
- `MessageSegment.mention_everyone()`: 提及 @所有人。
- `MessageSegment.image("http://example.com/image.png")`: 网络图片，需要后台绑定域名。
- `MessageSegment.MessageSegment.file_image(image)`: 本地图片，可以传入 `bytes` / `io.BytesIO` / `pathlib.Path`。
- `MessageSegment.ark(ark)`: Ark 消息，私域被动消息有 Ark 权限，参考 QQ 机器人文档的 [发送 ARK 模板消息](https://bot.q.qq.com/wiki/develop/api/openapi/message/post_ark_messages.html) 部分。
- `MessageSegment.embed(embed)`: Embed 消息，[文档](https://bot.q.qq.com/wiki/develop/api/openapi/message/template/embed_message.html)。
- `MessageSegment.markdown(markdown)`: Markdown 模板消息和 Markdown 消息，需要内邀开通，[文档](https://bot.q.qq.com/wiki/develop/api/openapi/message/post_markdown_messages.html)。
- `MessageSegment.keyboard(keyboard)`: Markdown 消息的按钮列表，需要内邀开通，[文档](https://bot.q.qq.com/wiki/develop/api/openapi/message/message_keyboard.html)。

使用以上消息段进行消息拼接，便可以使用 QQ 适配器的特有消息类型进行消息发送和回复。以 NoneBot 文档中的插件示例为例，可以修改为：

```python
from nonebot import on_command
from nonebot.rule import to_me
from nonebot.adapters import Message
from nonebot.params import CommandArg

# 文件系统路径 Python 标准库
# 用于创建本地文件路径
from pathlib import Path

# 从 QQ 适配器导入消息段
from nonebot.adapters.qq import MessageSegment

weather = on_command(
    "天气", rule=to_me(), aliases={"weather", "查天气"}, priority=10, block=True
)

@weather.handle()
async def handle_function(args: Message = CommandArg()):
    # 提取参数纯文本作为地名，并判断是否有效
    if location := args.extract_plain_text():
        image = Path("data/image.png")
        messaege = f"今天{location}的天气是..." + MessageSegment.file_image(image)
        await weather.finish(messaege)
    else:
        messaege = MessageSegment.emoji("123") + "请输入地名"
        await weather.finish(messaege)
```

### QQ 适配器 API 调用

QQ 适配器提供了 API 的封装，可以直接使用 Bot 实例进行调用，QQ 适配器中提供的 API 可在 [API 文档](https://bot.q.qq.com/wiki/develop/api/) 中查看，推荐使用输入关键词加上自动补全（如使用 Visual Studio Code 的 Pylance 扩展）来快速找到对应的 API 封装名称和参数列表，示例如下：

```python
from nonebot import on_command
from nonebot.adapters.qq import Bot, MessageCreateEvent

test = on_command("test")

@test.handle()
async def handle_function(bot: Bot, event: MessageCreateEvent):
    guild = await bot.get_guild(guild_id=event.guild_id)
    member = await bot.get_member(guild_id=guild.id, user_id=event.get_user_id())
    await test.finish(member.json())
```

更加深入的开发请参考 [NoneBot 文档](https://nonebot.dev/docs)。
