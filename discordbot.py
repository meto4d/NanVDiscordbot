#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import discord # インスコした discord.py
import re # 正規表現
import urllib #http通信
import urllib.request
from socket import timeout # timeout
import os # ファイル削除とか
import datetime
import random, string # ランダム文字列
import asyncio # async-await
import json # authキー用にjsonで
import hmac, hashlib #2ch
import socket #ソケット通信
import threading #スレッド処理
import base64 # Base64
import sqlite3 #SQLite
#import pycurl #curl

# 非同期処理
asyncLoop = asyncio.get_event_loop()

# test:True
_Debug = False

# 設定ファイル.json
setting_json = "./account.json"

# トークンjson読み込み
if os.path.isfile(setting_json):
    with open(setting_json) as f:
        df = json.load(f)
else:
    df = {
        # test
        "test": {
            "token": "test channel token",
            "id": 000000, #INT server id
            "channel": 000000, #INT channel id
            "socket_port": 10000 #INT socket port
        },
        # production
        "prod": {
            "token": "production channel token",
            "id": 000000, #INT server id
            "channel": 000000, #INT channel id
            "socket_port": 20000 #INT socket port
        },
        #signature
        "sign": "signature",
        #help
        "help": "help string",
        "help_embed": {
            "title": "help embed title",
            "desp": ["help embed description"]
        },
        # connect kagamin
        "okiba": {
            "url": "http://localhost:8000",
            "port": [8080]
        },
        # receive kagamin list
        "conKgm": {
            # "receive name": ["server name", "url"],
            "local": ["name", "localhost"],
        },
        #2ch API proxy key
        "chAPI": {
            "AppKey": "",
            "HMKey": "",
            "CT": "",
            "X2chUA": "",
            "dat_UA": ""
        },
        #Voice Text API key
        "VoiceTextAPI": {
            "token": "VoiceTextWebAPI token",
            "dir": "directory saving datas from VoiceTextWebAPI",
            "server_url": "publish URL datas from VoiceTextWebAPI"
        }
    }
    with open(setting_json, mode='w') as f:
        json.dump(df, f, indent=4, ensure_ascii=False)

auth_token = df['test' if _Debug else 'prod']['token']

# 更新日時
update_date = str(datetime.datetime.fromtimestamp(os.stat(__file__).st_ctime))[:10]

print('ログイン中...')
client = discord.Client() #接続に使用するオブジェクト

# socket data
socketData = ""
socketFlag = True

# 起動時に通知してくれる処理
@client.event
async def on_ready():
    print(client.user.name + " " + str(client.user.id))
    print('ログインしました')
    asyncLoop.create_task( LoopRuth(client.send_message))

# メッセージを受信したときの処理
@client.event
async def on_message(message):
    # steamURL が発言されたら steam:// でURLを返す処理
    asyncLoop.create_task( SteamLink(message, client) )
    asyncLoop.create_task( DiceRoll(message, client) )
    asyncLoop.create_task( VoiceTextShowKun(message, client) )
    #asyncLoop.create_task( CountDown(message, client) )
    #asyncLoop.create_task( testLogs(message, client))

    ## メッセージを消すテスト
    #delPattern = r"/neko"
    #delMatch = re.match(delPattern, message.content)
    #if delMatch:
    #    await client.delete_message(message)

    ## メッセージを編集するテスト
    #editPattern = r"/edit"
    #editMatch = re.match(editPattern, message.content)
    #if editMatch:
    #   await client.edit_message(message, "/edited")

    # 行頭でメンションが来たときの処理
    if message.content.startswith("<@"+client.user.id+">"):
        if (await KgmMention(message, client)):
            pass
        else:
            reply = f'{message.author.mention} コマンドが認識できませんでした'
            await client.send_message(message.channel, reply)

###################
#
###################

# 特定の鯖でメンションが来たとき
async def KgmMention(msg, cl):
    server_id = df['test' if _Debug else 'prod']['id']
    if (int(msg.server.id) == server_id):
        kgmPtrn = r"(かがみ|カガミ|鏡|鑑|加賀美|加々美|ｋａｇａｍｉ|ＫＡＧＡＭＩ|kagami)"
        kgmMatch = re.search(kgmPtrn, msg.content, re.IGNORECASE)
        helpPtrn = r"(help|(へ|ヘ)(る|ル)(ぷ|プ))"
        helpMatch = re.search(helpPtrn, msg.content, re.IGNORECASE)
        if kgmMatch:
            await Kagami(msg, cl)
            return True
        elif helpMatch:
            await HelpMsg(msg, cl)
            return True
    return False

# Help
async def HelpMsg(msg, cl):
    s = parseHelp(df['help'], msg, cl)
    title = parseHelp(df['help_embed']['title'], msg, cl)
    des = parseHelp("\n".join(df['help_embed']['desp']), msg, cl)
    em = discord.Embed(title=title, description=des)
    await cl.send_message(msg.channel, s, embed=em)

def parseHelp(src, msg, cl):
    return src.replace("<date>", update_date).replace("<id>", cl.user.id)

# Steam Link 書き換え
async def SteamLink(msg, cl):
    # steamURL が発言されたら steam:// でURLを返す処理
    pattern = r"^https?://.+steampowered\.com/([\w./?%&=]*)?"
    matchOB = re.match(pattern, msg.content, re.IGNORECASE)
    if matchOB:
        reply = 'steam://openurl/' + matchOB.group()
        em = discord.Embed()
        await cl.send_message(msg.channel, reply, embed=em)

# サイコロ
async def DiceRoll(msg, cl):
    pattern = r"^(\d+)D(\d+)"
    matchOB = re.match(pattern, msg.content, re.IGNORECASE)
    if matchOB:
        num = int(matchOB.group(1))
        if num > 100:
            await cl.send_message(msg.channel, "101以上は実行できません")
            return
        cube = int(matchOB.group(2))
        randsum = 0
        randlist = '{'
        for i in range(num):
            tmp = random.randint(1, cube)
            randsum += tmp
            randlist += str(tmp)
            randlist += ','
            if (i != 0) and (i % 50 == 0):
                randlist += '\n'
        randlist = randlist[:len(randlist) - 1]
        randlist += '}'
        em = discord.Embed(description=randlist)
        await cl.send_message(msg.channel, str(randsum), embed=em)

# ショー君
async def VoiceTextShowKun(msg, cl):
    pattern = r"^/(show|haruka|hikari|takeru|santa|bear)kun(\s+)(.+)"
    matchOB = re.match(pattern, msg.content, re.IGNORECASE)
    if matchOB:
        text = matchOB.group(2)
        if(len(text) > 200):
            await cl.send_message(msg.channel, "200文字以下にしてください")
        else:
            await ShowkunBasic((cl, msg), urllib.parse.quote(text, encoding='utf-8'))
         

# ショー君 API + Basic認証 disc=(cl, msg)
async def ShowkunBasic(disc, t, sp="show", fm="mp3"):
    url = "https://api.voicetext.jp/v1/tts"
    text = "text=" + t
    speak = "speaker=" + sp
    fmat = "format=" + fm

    url += "?" + text + "&" + speak + "&" + fmat
    res = await BasicReq(df['VoiceTextAPI'], "", url, disc[0].send_message, disc[1].channel)
    if res != b'':
        await ShowkunSaveEnc(disc, res)


# ショー君 wave file 保存+エンコ(+日時削除)
async def ShowkunSaveEnc(disc, res):
    name = randomname(2)
    fname = df["VoiceTextAPI"]["dir"]
    mp3name = fname + name + ".mp3"
    # fname += name +".wav"
    with open(mp3name, mode="wb") as f:
        f.write(res)

    await ShowkunSendURL(disc, name)

# ショー君 wave file URL送信
async def ShowkunSendURL(disc, name):
    #n = name.split('.')
    url = df["VoiceTextAPI"]["server_url"].replace("<name>", name)
    ## 自動削除タスクを追加
    # autorm(name)

    await disc[0].send_message(disc[1].channel, url)


# カウントダウン
#async def CountDown(message, cl):
#    pattern = r"^カウントダウン"
#    matchOB = re.search(pattern, message.content, re.IGNORECASE)
#if matchOB:
#        for i in range(10000):
#            await cl.send_message(message.author, str(10000 - i))
#            await asyncio.sleep(10)

# 鏡を借りる
async def Kagami(msg, cl):
    kgmPtrn = r"(http|mms).?://.*:\d+.?(\s|　)*"
    kgmPush = r"(push|プッ?シュ|ぷっ?しゅ|(ｐ|Ｐ)(ｕ|Ｕ)(ｓ|Ｓ)(ｈ|Ｈ)|ぷｓｈ)(\s|　)*"
    forceConn = r"^(force|f)"
    kgmForce = True if re.search(forceConn, msg.content, re.IGNORECASE) else False

    kgmMatch = re.search(kgmPtrn, msg.content, re.IGNORECASE)
    port_str = str(df["okiba"]["port"])
    kagami = urllib.parse.urlparse(df["okiba"]["url"])
    kagami = kagami.scheme + "://" + kagami.hostname + ":"

    # pull接続
    if kgmMatch:
        comment = "" if kgmMatch.end() >= len(msg.content) else msg.content[kgmMatch.end():] + " "
        password = randomname(10)
        kgmUrl = await KgmUrl(port_str, True, password, comment, msg.author.name, url=kgmMatch.group(0), force=kgmForce)
        if(_Debug):
            em = discord.Embed(title=kgmMatch.group(0) + "\n┗"+kagami+port_str, description=kgmUrl)
            ##await KgmHTTP(kgmUrl, msg.channel, cl.send_message, kgmForce)
            await cl.send_message(msg.channel, comment, embed=em)
        else:
            await KgmHTTP(kgmUrl, msg.channel, cl.send_message)
            # DM 送信
            await cl.send_message(msg.author, DmMsg(port_str, password))
            em = discord.Embed(title=kgmMatch.group(0) + "\n┗"+kagami+port_str)
            await cl.send_message(msg.channel, "鏡を " + kgmMatch.group(0) + " に接続しました\nパスワードと接続設定はDMを確認してください", embed=em)
    else:
        # push待機
        kgmMatch = re.search(kgmPush, msg.content, re.IGNORECASE)
        if kgmMatch:
            comment = "" if kgmMatch.end() >= len(msg.content) else msg.content[kgmMatch.end():] + " "
            password = randomname(10)
            kgmUrl = await KgmUrl(port_str, False, password, comment, msg.author.name, force=kgmForce)

            if(_Debug):
                em = discord.Embed(title="push\n"+kagami+port_str, description=kgmUrl)
                await cl.send_message(msg.channel, comment, embed=em)
            else:
                await KgmHTTP(kgmUrl, msg.channel, cl.send_message)
                # DM 送信
                em = discord.Embed(title="push\n"+kagami+port_str)
                await cl.send_message(msg.author, DmMsg(port_str, password))

                await cl.send_message(msg.channel, "鏡をpush待機させました\nパスワードと接続設定はDMを確認してください", embed=em)
        else:
            await cl.send_message(msg.channel, "urlが判別できませんでした")

# 鏡接続URL文字列を作成
async def KgmUrl(port, pushll, ps, com, usr, url = "", force = False):
    enusr = urllib.parse.quote(usr, encoding='shift-jis')
    encom = urllib.parse.quote(com, encoding='shift-jis')
    enurl = urllib.parse.quote(url, encoding='shift-jis')
    msg = df["okiba"]["url"] + "/conn.html?Port=" + port
    msg += "&mode=" + ("pull" if pushll else "push")
    msg += "&password=" + ps
    msg += "&comment=" + encom + "byDiscord@" + enusr
    msg += "&radio=on&redir_p=on&redir_c=on"
    msg += (("&address=" + enurl) if pushll else "&url=")
    return msg

# DM メッセージ作成
def DmMsg(port, ps):
# DM作成 送信
    msg = "設定変更URL: "
    msg += df["okiba"]["url"] + "/auth.html?port=" + port
    msg += "\n切断URL: "
    msg += df["okiba"]["url"] + "/dis.html?dis=" + port
    msg += "\nパスワード: " + ps
    return msg

# 鏡置き場HTTP接続部
async def KgmHTTP(url, ch, SendMsg):
    try:
        res = urllib.request.urlopen(url, timeout=1).read()
    except (urllib.request.HTTPError, urllib.request.URLError) as error:
        await SendMsg(ch, error + "によってデータ取得に失敗しました")
    except timeout:
        await SendMsg(ch, "タイムアウトしました")

# Loop DM to Ruth
async def LoopRuth(fnSend):
    global socketData
    global socketFlag
    if socketFlag:
        socketFlag = False
        while True:
            await asyncio.sleep(10)
            if socketData != "":
                await sendNanV(fnSend, socketData)
                socketData = ""

# bot用チャンネルに鏡情報を送信
async def sendNanV(fnSend, Msg, enc = 0):
    okiba = df['conKgm']
    ser = discord.Server(id=df['test' if _Debug else 'prod']['id'])
    server = discord.Channel(id=df['test' if _Debug else 'prod']['channel'], server=ser)
    #print('Msg: '+Msg)
    #await asyncio.sleep(1)
    for m in Msg.split():
        sendMsg = {}
        m = m[m.find('?')+1:]
        lMsg = m.split('&')
        setMsg = lMsg[0].split('=')[1]
        if (setMsg == 'conn') or (setMsg == 'set'):
            sendMsg['set'] = (True if setMsg == 'conn' else False)
            enc = 0
            for llMsg in lMsg:
                cMsg = llMsg.split('=')
                if (cMsg[0] == 'enc'):
                    enc = int(cMsg[1])
            enco = 'shift-jis' if  enc == 0 else 'utf-8'
            for llMsg in lMsg:
                cMsg = llMsg.split('=')
                if (cMsg[0] == 'mode'):
                    sendMsg['mode'] = True if cMsg[1] == 'pull' else False
                elif (cMsg[0] == 'address'):
                    sendMsg['address'] = urllib.parse.unquote(cMsg[1], encoding=enco)
                elif (cMsg[0] == 'Port' or cMsg[0] == 'port'):
                    sendMsg['port'] = cMsg[1]
                elif (cMsg[0] == 'comment'):
                    sendMsg['comment'] = urllib.parse.unquote(cMsg[1], encoding=enco)
                elif (cMsg[0] == 'radio'):
                    sendMsg['radio'] = True if cMsg[1] == 'on' else False
                elif (cMsg[0] == 'l'):
                    sendMsg['server'] = cMsg[1]

            msg = okiba[sendMsg['server']][0] if sendMsg['server'] in okiba.keys() else "鏡置き場"
            msg += "" if sendMsg['set'] else ":設定変更"
            
            ems = ""
            if sendMsg['set']:
                if sendMsg['mode']:
                    ems = sendMsg['address'] if sendMsg['radio'] else "非表示"
                else:
                    ems = "push" if sendMsg['radio'] else "push非表示"
                ems += "\n"

            ems += "┗http://"+(okiba[sendMsg['server']][1] if sendMsg['server'] in okiba.keys() else "localhost")
            ems += ":"+sendMsg['port']+"\n"
            em = discord.Embed(title=sendMsg['comment'], description=ems)
            await fnSend(server, msg, embed=em)
        elif setMsg == 'dis':
            for llMsg in lMsg:
                cMsg = llMsg.split('=')
                if (cMsg[0] == 'Port' or cMsg[0] == 'port'):
                    sendMsg['port'] = cMsg[1]
                elif (cMsg[0] == 'l'):
                    sendMsg['server'] = cMsg[1]
            msg = okiba[sendMsg['server']][0] if sendMsg['server'] in okiba.keys() else "鏡置き場"
            msg += ":切断"
            ems = "┗http://"
            ems += okiba[sendMsg['server']][1] if sendMsg['server'] in okiba.keys() else "localhost"
            ems += ":" + sendMsg['port']
            em = discord.Embed(title="切断", description=ems)
            await fnSend(server, msg, embed=em)


# logs_from test
async def testLogs(msg, cl):
    if msg.content.startswith('!test'):
        counter = 0
        tmp = await cl.send_message(msg.channel, 'Calculating messages...')
        async for log in cl.logs_from(msg.channel, limit=100):
            if log.author == msg.author:
                counter += 1
        await cl.edit_message(tmp, 'You have {} messages.'.format(counter))

# 鏡借りた時のソケット通信待ち
class KgmOkibaSocket(threading.Thread):
    def __init__(self, ctx):
        super(KgmOkibaSocket, self).__init__()
        # メイン終了時にもスレッド終了する
        self.daemon = True
        self.ctx = ctx
    # コルーチン用
    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._run())
        loop.close()
    async def _run(self):
        global socketData
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("localhost", df["test" if _Debug else "prod"]["socket_port"]))
            s.listen(10)
            while True:
                try:
                    conn, addr = s.accept()
                except:
                    break
                
                sumdata = b''
                with conn:
                    while True:
                        data = conn.recv(1024)
                        #print(type(data))
                        if not data:
                            break
                        sumdata += data
                #decode = urllib.parse.unquote(sumdata.decode(), encoding='shift-jis')
                #socketData += decode
                socketData += sumdata.decode() + " "


# 2ch読み込み
# server = "mao", board = "livevenus", thread = "1544221160"
def chRead(server, board, thread):
    api_url = 'http://api.5ch.net/v1/auth/'
    chAPI = df["chAPI"]
    AppKey = chAPI["AppKey"]
    HMKey = chAPI["HMKey"]
    CT = chAPI["CT"]
    X2chUA = chAPI["X2chUA"]
    dat_UA = chAPI["dat_UA"]

    msg = AppKey + CT
    HB = hmac.new(HMKey.encode("ascii"), msg.encode("ascii"), hashlib.sha256).hexdigest()

    values = {'ID': '', 'PW': '', 'KY': AppKey, 'CT': CT, 'HB': HB}
    headers = {'User-Agent': '', 'X-2ch-UA': X2chUA}

    vdata = urllib.parse.urlencode(values).encode('ascii')
    req = urllib.request.Request(api_url, vdata, headers)
    res = urllib.request.urlopen(req)
    sid = res.read().decode('UTF-8')
    sid = sid.split(':')[1]
    #print(sid)

    msg = "/v1/" + server + "/" + board + "/" + thread + sid + AppKey
    hobo = hmac.new(HMKey.encode('ascii'), msg.encode('ascii'), hashlib.sha256).hexdigest()
    dat_url = "https://api.5ch.net" + msg
    values = {'sid': sid, 'hobo': hobo, 'appkey': AppKey }
    headers = {'User-Agent': dat_UA, 'Connection': 'close', 'Content-Type': 'application/x-www-form-urlencoded', 'Accept-Encoding': 'gzip'}
    data = urllib.parse.urlencode(values).encode('ascii')
    req = urllib.request.Request(dat_url, data, headers)
    res = urllib.request.urlopen(req)
    dat = res.read() #.decode('UTF-8')

    print(dat)


###################################
# Basic認証
# ref: https://www.yoheim.net/blog.php?q=20181003
async def BasicReq(user, pas, url, SendMsg, SendPar):
    bas = base64.b64encode((user +':'+ pas).encode('utf-8'))
    headers = {"Authorization": "Basic " + bas.decode('utf-8')}
    try:
        req = urllib.request.Request(url, headers=headers, method="POST")
        return urllib.request.urlopen(req).read()
    except urllib.request.HTTPError as e:
        await SendMsg(SendPar, "HTTP Error "+e.code+ " :"+e.read())
        return b''
    except (urllib.request.HTTPError, urllib.request.URLError) as error:
        await SendMsg(SendPar, error + "によってデータ取得に失敗しました")
        return b''

###################################
# パスワード用のランダム文字列生成
# ref: https://qiita.com/Scstechr/items/c3b2eb291f7c5b81902a
def randomname(n):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

# 2ch 読み込み
chRead("mao", "livevenus", "1546324586")

# ソケット通信スレッド実行
ctx = {"lock":threading.Lock()}
KgmOkibaThread = KgmOkibaSocket(ctx)
KgmOkibaThread.start()

# botの接続と起動
# 
client.run(auth_token)
