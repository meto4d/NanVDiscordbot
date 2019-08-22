# VoiceTextShowKun
----

## How about this

ショー君に代表される、HOYA株式会社による音声合成VoiceTextの[WebAPI](https://cloud.voicetext.jp/webapi)をpythonで使えるようにしたもの

もともとDiscordBotで動作し、URLリンクの公開や再生を行っていたものを少し整理して、クラス化して公開

そのせいでちょっとだけ変なとこはあります

python3で作成してpython3で動作確認等したけど、他で動くかはわからないです

## How to use

apikeyに[VoiceTextWebAPI](https://cloud.voicetext.jp/webapi)から提供されたAPIキーを入力すると使えます。

コンストラクタ`VTWA(apikey)`でAPIの準備ができて、
喋って欲しい文字列を`SetVTWA()`メソッドに代入し、
`getfile()`メソッドに代入した文字列で音声ファイルが保存されます

`SetVTWA()`メソッドは以下のキーワード引数があり、フォーマットやショー君以外のボイスに変更等できます。
なお、読むテキストはAPI制限的に200以下でなければエラーが帰ってきます

基本的にはAPIマニュアル通りです
- fmat="wav"  
フォーマット `wav` `mp3` `ogg` に対応しています
- speaker="show"
話者一覧　`show` `haruka` `hikari` `takeru` `santa` `bear` の6人が選択できます
- emotion=""
感情一覧 `(なし)` `happiness` `anger` `sadness` の4つが選択できます(話者show以外)
- emotion_level=2
感情のレベルで`1～4`が選択できます
- pitch_level=100
声の高低を指定できます　小さいほど低くなります
- speed_level=100
話す速度を指定できます　小さいほど遅くなります
- volume_level=100
音量を指定します　小さいほど小さくなります

`GetFile()`メソッドはdirnameのキーワード引数で保存先フォルダが指定できます
