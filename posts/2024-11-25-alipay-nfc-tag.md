---
title: 支付宝“碰一下”原理分析与实现
categories: Misc
tags: []
created: 2024-11-25 20:56:00
---

<!-- markdownlint-disable MD033 -->

支付宝推出“碰一下”收款机器已有一段时间，近期又开始推广融合了“碰一下”功能的收款码与红包码，作为一种比较新奇的支付方式，本文将对其原理进行分析，并尝试自行制作“碰一下”标签。

## 原理分析

在常规的手机 NFC 支付模式（如电子公交卡、电子八达通、Apple Pay 等）中，钱包信息被加密存储在手机本地，支付时通过 NFC 传递支付信息到 POS 机。POS 机再向结算机构发出请求完成支付，整个过程中手机无需联网，部分手机也可实现关机刷卡。而支付宝“碰一下”不同，虽然也是利用 NFC 功能进行支付，但手机并不存储钱包信息，而是先利用 NFC 完成应用跳转，然后与在线支付的操作相同。也就是说，支付宝“碰一下”实际上达到的效果与扫描二维码完全相同，只是在部分场景下减少了用户的操作。

目前已有的支付宝“碰一下”收款方式主要有两种：可以设置收款金额的“碰一下”收款机，以及带有“碰一下”感应标签的需要自行输入金额的收款码。前者需要商家输入收款金额后，用户碰一下收款机即可跳转至定额支付页面；后者则是无需进行外部控制的无源标签，碰一下之后跳转至输入金额支付的页面。除了收款之外，还衍生出了一系列的“碰一下”功能，如“碰一下”红包码、“碰一下”点餐码等。

以上两种“碰一下”方式的原理是相同的，均为手机扫描 NFC 标签后，根据标签内容启动支付宝应用，并根据标签中的链接跳转至指定页面。本文章将直接对支付宝中申请的“碰一下”收款码及红包码进行分析。

![支付宝“碰一下”收款码及红包码](https://s2.loli.net/2024/11/25/N2AcHj84Sh1WDME.jpg)

使用 [NFC TagInfo by NXP](https://play.google.com/store/apps/details?id=com.nxp.taginfolite) 应用，分别对支付宝“碰一下”收款码及红包码进行扫描并查看，可以发现使用的均为复旦微的 NFC 芯片，NDEF 数据中均包含了两条记录，分别为 URI 和 Android Application Record。其中 URI 记录中包含了支付宝相关链接，而 Android Application Record 记录则为支付宝应用的包名。

![支付宝“碰一下”收款码及红包码的 NDEF 数据](https://s2.loli.net/2024/11/25/HMOlogRSkWEvPYe.jpg)

具体分析其 URI 数据，可以发现构成方式如下：

- 收款码：`render.alipay.com/p/s/ulink/sn?s=dc&scheme=alipay%3A%2F%2Fnfc%2Fapp%3Fid%3D10000007%26actionType%3Droute%26codeContent%3D{URL}`
- 红包码：`render.alipay.com/p/s/ulink/nrps?s=dc&scheme=alipay%3A%2F%2Fnfc%2Fapp%3Fid%3D10000007%26actionType%3Droute%26codeContent%3D{URL}`

二者区别在于收款码的 Endpoint 为 `/p/s/ulink/sn`，而红包码的 Endpoint 为 `/p/s/ulink/nrps`。其中 `{URL}` 为 `qr.alipay.com` 域名下的链接经过两次 URL Encode 的结果，扫描对应感应区左侧的二维码可发现与二维码链接相同，只是多了一个 `noT` 参数，包含此参数的交易可享受“碰一下”支付优惠。

## 自制标签

根据以上分析，可以发现只需要有对应的二维码即可自行制作一个“碰一下”标签。首先需要选择合适的标签类型，根据以上读取中的 230+ bytes 数据量，NTAG213 最大 144 bytes 的 User memory 不足够，可以选择 NTAG215 (504 bytes) 或 NTAG216 (888 bytes) 标签。然后使用 [NFC TagWriter by NXP](https://play.google.com/store/apps/details?id=com.nxp.nfc.tagwriter) 应用将数据写入标签。下图为测试时所使用的 NTAG216 贴纸标签。

![NTAG216 标签](https://s2.loli.net/2024/11/25/FUQmejhl8BzyLSk.jpg)

首先获取到收款二维码的链接

```text
https://qr.alipay.com/xxxxxxxxxxxxxxxxxxxxxxx
```

将其进行两次 URL Encode，得到

```text
https%253A%252F%252Fqr.alipay.com%252Fxxxxxxxxxxxxxxxxxxxxxxx
```

使用收款码的 Endpoint 构造完整的 URI 记录

```text
render.alipay.com/p/s/ulink/sn?s=dc&scheme=alipay%3A%2F%2Fnfc%2Fapp%3Fid%3D10000007%26actionType%3Droute%26codeContent%3Dhttps%253A%252F%252Fqr.alipay.com%252Fxxxxxxxxxxxxxxxxxxxxxxx
```

在 NFC TagWriter 中点击 Write Tags，选择 New dataset，然后选择 Launch Application，在应用列表中选择支付宝，或手动输入包名 `com.eg.android.AlipayGphone`，然后依次点击 SAVE&WRITE 和 ADD MORE RECORD，选择 Link，Description 留空，URI type 选择 `https://`，URI data 输入上述构造的 URI 记录，然后依次点击 SAVE&WRITE 和 WRITE，即可贴标签并写入。具体操作可参考下图。

![标签写入操作](https://s2.loli.net/2024/11/25/nbujGxV1Mrl57kU.jpg)

此外，如果将以上链接中的 `{URL}` 替换为其他自定义链接，也可以实现“碰一下”使用支付宝打开对应网页的功能。

如果已经申请了具有“碰一下”功能的收款码或红包码，也可以直接使用 NFC TagWriter 将其复制到其他的标签，并贴在需要的地方。在推广期间支付宝商家服务中有机会免费领取“碰一下”收款码和红包码。
