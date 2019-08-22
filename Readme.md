# なん実V DiscordBot
----

## How about this

なんでも実況Vの非公式Discordチャンネル上で動作しているとあるBotのソースコード。

python3で作成してpython3で動作確認等したけど、他で動くかはわからないです。

## How to use

pythonが動作する環境と、
設定等を記載した`account.json`を作成・編集すればOK

一応初回起動時にaccount.json新規作成機能があり、27行目付近
```python
# 設定ファイル.json
setting_json = "./account.json"
```
を編集すれば好きな名前で保存できます。

最低限discordライブラリは別途インストール必須です。

> pip install discord

インストールすれば、

> python discordbot.py

で動作します。

**Linux**環境を推奨しています。

**Windows**環境でも動きそうですが、文字コードの問題で動作しなかったのは確認しています。

### その他

下の方にある2ch読み込みはテストで入れて、動作しないことを確認したまま放置しています。

鏡置き場から接続通知が来た際に、ソケット通信にて受け取り、discord上に投稿するカタチを取っていますが、
雑実装なので、めちゃプロセス立ち上げて重いと思います。
誰か直して
