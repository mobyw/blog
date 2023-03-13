---
title: 使用开发平台API下载华为云空间文件历史版本
categories: Misc
tags: []
created: 2023-03-13 13:44:00
---

近日有一个回退华为云空间文件版本的需求。虽然客户端上没有恢复版本文件的入口，但在华为开发者联盟上提供了查询文件历史版本的 [API](https://developer.huawei.com/consumer/cn/doc/development/HMSCore-Guides/server-quaring-history-version-0000001064501116) ，故尝试使用该 API 获取文件的历史版本。

## 准备工作

注册华为开发者联盟账号后，需要完成实名认证，并在管理后台创建一个 AppGallery Connect 项目：

![项目创建](https://s2.loli.net/2023/03/13/qQvK7R4ftu9jCXU.png)

在该项目下创建一个应用，只需填写第一步的信息：

![应用创建](https://s2.loli.net/2023/03/13/zb6KhOv2T3PcIBp.png)

创建应用后回到项目页面，在 `API管理` 标签下打开 `云空间` 选项：

![云空间权限使能](https://s2.loli.net/2023/03/13/IwJjXcuExHF4p7a.png)

在应用页面 `常规` 标签下找到 `应用` 栏，添加回调地址，可以使用一个不存在的网站：

![获取应用信息](https://s2.loli.net/2023/03/13/aTjbAuXpvMwDQfN.png)

记录下 `Client ID` 和 `Client Secret`。

## 获取 Access token

此部分参考 [基于OAuth 2.0开放鉴权](https://developer.huawei.com/consumer/cn/doc/development/HMSCore-Guides/open-platform-oauth-0000001053629189) 中的 `授权码扩展模式（PKCE）` 部分。

访问：

<https://oauth-login.cloud.huawei.com/oauth2/v3/authorize?response_type=code&code_challenge=ovoy4lehgHbv8uNmif_hak3bH2_Ylk6_fWP0UL232QQ&code_challenge_method=plain&client_id={{client_id}}&redirect_uri={{redirect_uri}}&scope=openid+https://www.huawei.com/auth/drive>

将 `client_id` 替换为准备工作中获取的 `Client ID`，`redirect_uri` 替换为准备工作中填写的回调地址。

访问后回跳转到回调地址，参数为 `?code=...`，记录 `code` 的内容，作为授权码 Code。

然后需要通过此授权码 Code 换取鉴权令牌：

```http
### Get access token by authorization code
POST https://oauth-login.cloud.huawei.com/oauth2/v3/token HTTP/1.1
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code={{code}}&
client_id={{client_id}}&
client_secret={{client_secret}}&
code_verifier=ovoy4lehgHbv8uNmif_hak3bH2_Ylk6_fWP0UL232QQ&
redirect_uri={{redirect_uri}}
```

填写 `code` `client_id` `client_secret` `redirect_uri`，注意 `code` 需要进行 URL 编码。发送请求，获得的结果如下：

```json
{
    "scope": "https://www.huawei.com/auth/drive openid",
    "access_token": "DA************",
    "token_type": "Bearer",
    "expires_in": 3600,
    "id_token": "..."
}
```

记录 `access_token` 内容，在后续步骤中验证使用。

## 恢复文件

此部分参考 [查询文件历史版本](https://developer.huawei.com/consumer/cn/doc/development/HMSCore-Guides/server-quaring-history-version-0000001064501116) 。

首先需要获取文件 `id`，如果文件较少可直接获取全部文件列表：

```http
### Get file list
GET https://driveapis.cloud.huawei.com.cn/drive/v1/files?fields=* HTTP/1.1
Accept: application/json
Cache-Control: no-cache
Authorization: Bearer {{access_token}}
```

如果文件较多可以参考 [文档](https://developer.huawei.com/consumer/cn/doc/development/HMSCore-References/server-public-info-0000001050159641) 中 `mimeType` 的介绍进行搜索与排序，下面是一个按编辑日期倒序排序 `.docx` 文件的示例：

```http
### Get `.docx` file list ordered by editedTime desc
GET https://driveapis.cloud.huawei.com.cn/drive/v1/files?fields=*&queryParam=mimeType%3D%27application%2Fvnd.openxmlformats-officedocument.wordprocessingml.document%27&orderBy=editedTime%20desc HTTP/1.1
Content-Type: application/json
Authorization: Bearer {{access_token}}
Cache-Control: no-cache
Accept: application/json
```

测试时该接口经常提示无权限，但多次访问后又会正常返回，如果配置信息正确仍提示 `INSUFFICIENT_SCOPE` 就多试几次。

返回结果格式如下：

```json
{
    "files": [
        {
            "fileName": "测试.doc",
            "sha256": "30e0ee3fc2ac07ca2e2fedfa4aad5a293c13a28268f4843f354f2675f78f991d",
            "fileSuffix": "doc",
            "mimeType": "application/octet-stream",
            "lastHistoryVersionId": "1110774401038742656.1110774800504128256",
            "editedByMeTime": "2023-03-13T05:51:14.000Z",
            "createdTime": "2023-03-13T05:50:27.166Z",
            "id": "BoAY1s_TPZKYqq3HJGUtObq9sd5VZTUUm",
            "version": 5,
            "iconDownloadLink": "https://event.dbankcdn.com/filemanagerpic/20191114101425c162.png",
            "editedTime": "2023-03-13T05:51:14.000Z",
            "size": 38912,
            "fullFileSuffix": "doc",
            "category": "drive#file",
        },
        {
            // ...
        }
    ],
    "category": "drive#fileList"
}
```

找到对应的文件并记录其 `id`，然后获取其历史记录：

```http
### Get file history
GET https://driveapis.cloud.huawei.com.cn/drive/v1/files/{{id}}/historyVersions?fields=* HTTP/1.1
Authorization: Bearer {{access_token}}
Cache-Control: no-cache
Accept: application/json
```

返回结果如下：

```json
{
    "historyVersions": [
        {
            "editedTime": "2023-03-13T05:51:15.063Z",
            "size": 38912,
            "sha256": "ce6376d16144b5c36da0414a4666a33bb15624f8b5c0553dad1ae456c64510ac",
            "id": "1110774401038742656.1110774800504128256",
            "mimeType": "application/octet-stream",
            "category": "drive#historyVersion",
            "originalFilename": "nonamea696f86cb6e045d19c696396636595b5"
        },
        {
            // ...
        },
        {
            // ...
        }
    ],
    "category": "drive#historyVersionList"
}
```

根据编辑时间找到需要的版本（UTC 时间），记录下历史文件的 `id`，由于和文件 `id` 重名，在下面表示为 `history_id`。直接下载对应历史版本文件：

```http
### Get file
GET https://driveapis.cloud.huawei.com.cn/drive/v1/files/{{id}}/historyVersions/{{history_id}}?form=content HTTP/1.1
Authorization: Bearer {{access_token}}
Cache-Control: no-cache
Accept: application/json
```
