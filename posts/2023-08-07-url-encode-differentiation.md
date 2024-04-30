---
title: 不同高级语言的 URL 编码差异
categories: Misc
tags: []
created: 2023-08-07 20:00:00
---

水群时看到有群友遇到了因 URL 对字符 `*` 的编码不符合预期问题导致的程序错误，便做此篇测试部分高级语言的 URL 编码实现有何不同。

## 相关标准

由于 [RFC 1738: Uniform Resource Locators (URL)](https://datatracker.ietf.org/doc/html/rfc1738) 并非互联网标准 (Internet Standard)，故本文参考互联网标准 [RFC 3986: Uniform Resource Identifier (URI): Generic Syntax](https://datatracker.ietf.org/doc/html/rfc3986) 编写。该标准推荐使用通用术语 "URI"，而不是限制性更强的术语 "URL" 和 "URN" [(RFC3305)](https://datatracker.ietf.org/doc/html/rfc3305)。

RFC 3986 对 URI 中非保留字符的定义如下：

```text
unreserved  = ALPHA / DIGIT / "-" / "." / "_" / "~"
```

在 URI 编码时，对于非保留字符 `unreserved` 应保持不进行转义，但是该标准同样说明了如果遇到了转义了这些字符的 URI 编码，在解码时仍需要将其恢复为原字符。

```text
URIs that differ in the replacement of an unreserved character with
its corresponding percent-encoded US-ASCII octet are equivalent: they
identify the same resource.  However, URI comparison implementations
do not always perform normalization prior to comparison (see Section
6).  For consistency, percent-encoded octets in the ranges of ALPHA
(%41-%5A and %61-%7A), DIGIT (%30-%39), hyphen (%2D), period (%2E),
underscore (%5F), or tilde (%7E) should not be created by URI
producers and, when found in a URI, should be decoded to their
corresponding unreserved characters by URI normalizers.
```

该标准中同样指出了 `~` 字符在旧的 URI 编码实现中经常转义为 `%7E`。

```text
For example, the octet
corresponding to the tilde ("~") character is often encoded as "%7E"
by older URI processing implementations; the "%7E" can be replaced by
"~" without changing its interpretation.
```

对于可能需要转义的保留字符，该标准将其分为两类：

```text
reserved    = gen-delims / sub-delims
gen-delims  = ":" / "/" / "?" / "#" / "[" / "]" / "@"
sub-delims  = "!" / "$" / "&" / "'" / "(" / ")"
            / "*" / "+" / "," / ";" / "="
```

其中 `gen-delims` 和 URI 的结构相关，必须要进行转义，而 `sub-delims` 是否需要需要根据所在位置判断。特别地，由于转义使用 `%` 符号，所以 `%` 符号自身也需要进行转义。

典型的 URI 组成部分如下：

```text
      foo://example.com:8042/over/there?name=ferret#nose
      \_/   \______________/\_________/ \_________/ \__/
       |           |            |            |        |
    scheme     authority       path        query   fragment
       |   _____________________|__
      / \ /                        \
      urn:example:animal:ferret:nose
```

与 `sub-delims` 相关的文法片段如下：

```text
authority     = [ userinfo "@" ] host [ ":" port ]
userinfo      = *( unreserved / pct-encoded / sub-delims / ":" )

host          = IP-literal / IPv4address / reg-name
IP-literal    = "[" ( IPv6address / IPvFuture  ) "]"
IPvFuture     = "v" 1*HEXDIG "." 1*( unreserved / sub-delims / ":" )
reg-name      = *( unreserved / pct-encoded / sub-delims )

path          = path-abempty    ; begins with "/" or is empty
              / path-absolute   ; begins with "/" but not "//"
              / path-noscheme   ; begins with a non-colon segment
              / path-rootless   ; begins with a segment
              / path-empty      ; zero characters
path-abempty  = *( "/" segment )
path-absolute = "/" [ segment-nz *( "/" segment ) ]
path-noscheme = segment-nz-nc *( "/" segment )
path-rootless = segment-nz *( "/" segment )
path-empty    = 0<pchar>
segment       = *pchar
segment-nz    = 1*pchar
segment-nz-nc = 1*( unreserved / pct-encoded / sub-delims / "@" )
              ; non-zero-length segment without any colon ":"
pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"

query         = *( pchar / "/" / "?" )

fragment      = *( pchar / "/" / "?" )
```

如果按照以上文法推导，`sub-delims` 中的字符在 `authority` `path` `query` `fragment` 中均可能保持原样。

另外，空格字符在 `application/x-www-form-urlencoded` 类型中编码为 `+`，而在 RFC 3986 中的编码为 `%20`。

为找出不同高级语言对这些字符转义处理的差别，下面进行了一个简单的测试，先给出了测试结果，具体的测试代码及输出在最后给出。

## 测试结果

仅测试了在 `query` 段中的编码和解码情况，在所有编码测试中，以 `sub-delims` 中的字符均已编码，`unreserved` 中的特殊字符均未编码为参考结果，标注与参考结果有差别的字符表，另外单列了对空格的转义情况。解码测试使用全部特殊字符转义的字符串，由于解码结果均相同，不额外展示在表格中。

| 语言       | Module / Function                                 | `sub-delims`<br/> 未被转义 | `unreserved` <br/>被转义 | SP 编码 |       `+` 解码        |
| ---------- | ------------------------------------------------- | :------------------------: | :----------------------: | :-----: | :-------------------: |
| Python 3   | `urllib.parse`                                    |                            |                          |   `+`   | 需使用 `unquote_plus` |
| Go         | `net/url`                                         |                            |                          |   `+`   |                       |
| Java       | `java.net.URLEncoder` <br/> `java.net.URLDecoder` |            `*`             |           `~`            |   `+`   |                       |
| JavaScript | `URLSearchParams`                                 |            `*`             |           `~`            |   `+`   |                       |
| JavaScript | `encodeURIComponent`<br/> `decodeURIComponent`    |            `*`             |           `~`            |  `%20`  |     无法解码 `+`      |
| Node.js    | `querystring`                                     |          `!'()*`           |                          |  `%20`  |                       |
| C#         | `System.Net.WebUtility`                           |           `!()*`           |                          |   `+`   |                       |
| PHP        | `urlencode` <br/> `urldecode`                     |                            |           `~`            |   `+`   |                       |
| PHP        | `rawurlencode`<br/> `rawurldecode`                |                            |                          |  `%20`  |     无法解码 `+`      |

虽然编码时对符号的转义处理不同，但是使用全部转义的 `sub-delims` 以及 `unreserved` 中的特殊字符进行测试时被测程序都能正确进行解码。

## 测试代码

Python 3:

```python
from urllib.parse import urlencode, unquote, unquote_plus

print(urlencode({"param":" !$&'()*+,;=-._~"}))
print(unquote("param=a+b"))
print(unquote_plus("param=a+b"))
```

```text
param=+%21%24%26%27%28%29%2A%2B%2C%3B%3D-._~
param=a+b
param=a b
```

Go:

```go
package main

import (
    "fmt"
    "net/url"
)

func main() {
    fmt.Println(url.QueryEscape(" !$&'()*+,;=-._~"))
    fmt.Println(url.QueryUnescape("a+b"))
}
```

```text
+%21%24%26%27%28%29%2A%2B%2C%3B%3D-._~
a b <nil>
```

Java:

```java
import java.io.UnsupportedEncodingException;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

public class Main {
    public static void main(String[] args) throws UnsupportedEncodingException {
        System.out.println(URLEncoder.encode(" !$&'()*+,;=-._~", StandardCharsets.UTF_8.toString()));
        System.out.println(URLDecoder.decode("a+b", StandardCharsets.UTF_8.toString()));
    }
}
```

```text
+%21%24%26%27%28%29*%2B%2C%3B%3D-._%7E
a b
```

JavaScript:

```js
const encode = new URLSearchParams();
encode.set("param", " !$&'()*+,;=-._~");
console.log(encode.toString());
const decode = new URLSearchParams("param=a+b");
console.log(decode.get("param"));
console.log(encodeURIComponent(" !$&'()*+,;=-._~"));
console.log(decodeURIComponent("a+b"));
```

```text
param=+%21%24%26%27%28%29*%2B%2C%3B%3D-._%7E
a b
%20!%24%26'()*%2B%2C%3B%3D-._~
a+b
```

Node.js:

```js
const querystring = require("querystring");
console.log(querystring.stringify({ param: " !$&'()*+,;=-._~" }));
console.log(querystring.parse("param=a+b").param);
```

```text
param=%20!%24%26'()*%2B%2C%3B%3D-._~
a b
```

C#:

```cs
using System;

class Program
{
    static void Main()
    {
        Console.WriteLine(System.Net.WebUtility.UrlEncode(" !$&'()*+,;=-._~"));
        Console.WriteLine(System.Net.WebUtility.UrlDecode("a+b"));
	}
}
```

```text
+!%24%26%27()*%2B%2C%3B%3D-._%7E
a b
```

PHP:

```php
<?php
echo urlencode(" !$&'()*+,;=-._~") . "\n";
echo urldecode("a+b") . "\n";
echo rawurlencode(" !$&'()*+,;=-._~") . "\n";
echo rawurldecode("a+b") . "\n";
?>
```

```text
+%21%24%26%27%28%29%2A%2B%2C%3B%3D-._%7E
a b
%20%21%24%26%27%28%29%2A%2B%2C%3B%3D-._~
a+b
```
