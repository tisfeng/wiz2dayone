# 将为知笔记迁移到 Day One

之前写过一篇 [将简书日记迁移到 Day One](https://github.com/tisfeng/jianshu2dayone) 的文章，与之类似，这里记录了将为知笔记迁移到 Day One 的过程。

与简书不同的是，为知笔记多了一些额外的转化优化步骤。

下面用到的 Python 脚本都是在 GitHub Copilot 的帮助下完成的，感谢它的帮助。


## 1. 为知笔记导出

为知笔记官方没有提供全量导出功能，只能单篇单篇的导出，太麻烦了。

我们可以借助开源项目 [wiz-export](https://github.com/dumbdonkey/wiz-export) 实现全量导出 html 文件。

1. 首先需要下载为知笔记客户端版本，这是为了将为知笔记数据下载到本地。
2. 下载为知笔记导出工具 wiz-export-1.0-SNAPSHOT.jar
```bash
wget "https://raw.github.com/zuochangan/wiz-export/master/bin/wiz-export-1.0-SNAPSHOT.jar"
```
1. 使用 Java 运行 wiz-export-1.0-SNAPSHOT.jar，导出为知笔记数据到本地。
```bash
java -jar wiz-export-1.0-SNAPSHOT.jar -i 索引文件位置 -d 数据文件位置 -t html存储目录  
```

为知笔记位于 ~/.wiznote/ 目录下，下面有个以用户名命名的文件夹，索引文件为 data/index.db，数据文件为 data/notes。


## 2. 文件格式转换

为知笔记导出的文件是 html 格式，Day One 支持导入的是 [纯文本格式](https://dayoneapp.com/blog/help_guides/importing-data-from-plain-text/) 的 txt 文件，而且这个 txt 文件需要符合一定的格式要求，例如必须包含一个特定格式的 Date 字段。

如果想一次导入多个文件到 Day One 中，还需将这些文件合并成一个 txt 文件，每篇文章都要包含一个 Date 字段，并用 `\n\n` 分隔。

比较蛋疼的一点是，为知笔记导出的 html 文件中并没有 Date 字段，我们只能自己想办法补全 Date，或者简单使用一个固定的日期。

只是如果使用一个固定的日期，那么所有的文章都会显示为同一天的日期，这样就没办法在 Day One 中按日期排序了。

### 2.1 html 转换为 markdown

首先实现一个 html2markdown.py 脚本，用于递归遍历为知笔记导出的文件夹，在当前目录下生成一个 html2markdown 文件夹，里面是将 html 转换为 markdown 的文件，并确保前后文件目录结构一致。

需要注意的一点是，为知笔记导出的 html 文件中，图片是本地的，转换为 markdown 文件后，图片链接还是本地的，如果直接导入到 Day One 中，图片是无法显示的。

因此我们需要将本地图片转换为网络图片，并替换 markdown 文件中的图片链接。

我这里使用 [uPic](https://github.com/gee1k/uPic) 命令行工具将本地图片上传到网络。

Usage: 

```bash
python html2markdown.py <path_to_wiznote_html_folder>
```

### 2.2 markdown 文件内容优化

optimize_markdown.py 脚本 ，用于优化 html2markdown 文件夹中的所有 markdown 文件，主要包括：
1. 为知笔记【我的日记】下，笔记内容中日期格式的优化。
2. 为 markdown 文件内容添加标题 # title

Usage:
```bash
python optimize_markdown.py <path_to_html2markdown_folder>
```

### 2.3 合并 markdown 文件

接下来实现一个 merge_markdown.py 脚本，用于将 html2markdown 文件夹中的所有 markdown 文件合并成一个 merged_result.txt 文件，并在每个文件前添加一个 Date 字段。

Usage:
```bash
python merge_markdown.py <path_to_html2markdown_folder>
```


### 3. Day One 导入

前面我为省事，使用了固定日期，这里为了避免导入的为知笔记文章扰乱现有的 Day One 日记，我选择新建一个日记本，专门用来存放这些迁移过来的文章。

将新建的为知笔记日志日记本放到第一个位置，因为 Day One 会默认将第一个日记本作为当前日记本，所以在导入时会自动选择这个日记本。

然后就是常规的 Day One 导入操作了，【文件】->【导入】->【纯文本文件】-> 选择刚刚生成的 merged_result.txt 文件即可。

![](https://raw.githubusercontent.com/tisfeng/ImageBed/main/uPic/ITc0IY.png)