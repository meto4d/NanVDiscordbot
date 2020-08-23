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
import tempfile # TempFile (diskに負荷かけない？大丈夫？)
#import pycurl #curl

# VoiceTextWebAPI用のクラス
class VoiceTextWebAPI:
    # VoiceTextWebAPIの基本メンバ
    apikey = "" #API key for VoiceTextWebAPI
    path = "" #PATH for save voice data
    guild = None #discord server's guild
    text_channels = {} #text channnels object {channel.id: channel.name}

    # VoiceChat用のメンバ
    vclient = None # Voice Channel client
    read_channnels = (None, ) # read text channels : tuple
    playfile = None
    vc_uptime = None
    vc_limit_time = 2 * 60 # minutes
    vc_author = None
    vc_speaker = "show"

    def __init__(self, apikey, path, guild, limit_time = 2 * 60, speaker="show", ):
        self.apikey = apikey
        self.path = path
        self.guild = guild
        self.vc_limit_time = limit_time
        self.vc_speaker = speaker

    # ショー君の音声データを取ってきて、保存し、ファイル名を返す
    #  通常は拡張子のないファイル名、temp=TrueでTempFileオブジェクトが返る
    async def GetShowkunDataPath(self, text, fnSend, sp="show", fm="mp3", temp=False):
        if(fm not in ["mp3", "wav", "ogg"]):
            return ''
        res = await BasicReq(self.apikey, "", self.ShowkunURL(text, sp, fm), fnSend)
        if res != b'':
            return self.SaveShowkun(res, fm, self.path) if not temp else self.SaveTempShowkun(res)
        return ''

    # ショー君の音声データを保存
    def SaveShowkun(self, res, fm, path):
        # ほぼ後の実装のため（トラフィック量増加などによる重複IDを避けやすいように）
        name = uniqueName(3 if False else 2)
        mp3name = path + name + "." + fm
        # fname += name +".wav"
        with open(mp3name, mode="wb") as fmp3:
            fmp3.write(res)
        return name
            
    # ショーくんの音声データを一時ファイルで保存
    def SaveTempShowkun(self, res):
        tf = tempfile.TemporaryFile()
        tf.write(res)
        tf.seek(0)
        return tf

    # ShowkunのURLを作成する
    def ShowkunURL(self, text, speaker, fm):
        url = "https://api.voicetext.jp/v1/tts"
        text = "text=" + urllib.parse.quote(self.normTextShowkun(text), encoding='utf-8')
        speak = "speaker=" + speaker
        fmat = "format=" + fm
        url += "?" + text + "&" + speak + "&" + fmat
        #print(url)
        return url

    # ショー君に読み込ませる文章を整形し、200文字以下に
    def normTextShowkun(self, text):
        # チャンネル名をIDから保管
        if not self.text_channels :
            self.text_channels = dict(map(lambda x: [int(x.id), x.name], self.guild.text_channels))
        text = re.sub(r"<#(\d+)>" , lambda match: (self.text_channels[self.int_parse(match.group(0))] + "チャンネル" ) if self.int_parse(match.group(0)) in self.text_channels else "", text)
        if len(text) > 191 :
            text = text[:190] + "。以下省略"
        return text
    
    # int.parse
    def int_parse(self, string):
        return int(re.sub(r"\D*(\d+)\D*", "\\1", string))

    # ボイスチャンネルに接続して、準備ができているか
    def is_ready_vc(self):
        if self.vclient is None:
            return False
        return True
    
    # 接続時間制限
    # connect time than limit time is 1
    # less than 0
    # not ready -1
    def is_limit_time(self):
        if self.is_ready_vc():
            now = datetime.datetime.now()
            if (now - self.vc_uptime).seconds / 60 > self.vc_limit_time:
                return 1
            else:
                return 0
        return -1

    # ショーくんをVCに召喚する
    async def connect_vc(self, msg, read_channels, limit_time = 2 * 60):
        if self.vclient is not None :
            return -1
        try:
            self.vclient = await msg.author.voice.channel.connect()
        except discord.ClientException as e:
            msg.channel.send("ボイスチャンネルへの接続に失敗しました。ボイスチャンネルへの参加が可能か、設定を見直してください。")
            print(e)
            return
        except:
            msg.channel.send("ボイスチャンネルへの接続に失敗しました。ボイスチャンネルへの参加が可能か、設定を見直してください。")
            return
        self.read_channels = read_channels
        self.text_channels = dict(map(lambda x: [int(x.id), x.name], msg.guild.text_channels))
        self.vc_uptime = datetime.datetime.now()
        self.vc_limit_time = limit_time
        self.vc_author = msg.author
        return 0
    
    # ショーくんをVCから切断する
    async def disconnect_vc(self):
        if self.vclient is None:
            return -1
        await self.playing()
        await self.vclient.disconnect()
        self.vclient = None
        self.read_channels = (None, )
        self.text_channels = {}
        self.vc_connect_uptime = None
        return 0

    # VC内でチャット内容を読み上げる
    async def play(self, msg):
        if self.vclient is None:
            return
        text = self.vc_normTextShowkun(msg)
        temp = await self.GetShowkunDataPath(text, msg.channel.send, sp=self.vc_speaker, temp=True)
        await self.play_file(temp, close=True)

    # VC用の追加パラメータを設定
    def set_options(self, speaker="show", limit_time= 2 * 60):
        self.vc_speaker = speaker
        self.vc_limit_time = limit_time

    # fileをvoice chatで再生する
    # close = Trueでfileをcloseする
    async def play_file(self, file, close=False):
        await self.playing()
        self.playfile = file
        self.vclient.play(self.pcmdata(file, close), after= (
            lambda error: print(error) if error else self.after_play_fn(close))
        )
        
    def after_play_fn(self, close):
        if close:
            self.playfile.close()

    # discord.pyで扱えるpcmに変換する
    def pcmdata(self, file, fileio):
        return discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(file, pipe=fileio))

    # VC用のテキスト整形
    def vc_normTextShowkun(self, msg):
        text = msg.author.name + "、" + msg.content
        text = self.normTextShowkun(text)
        return text

    # ショーくんが読み上げ中は待機
    async def playing(self):
        while(self.vclient.is_playing()):
            # wait 1 second
            await asyncio.sleep(1)


# 非同期処理
asyncLoop = asyncio.get_event_loop()

# test:True
_Debug = False

# 設定ファイル.json
setting_json = "./account.json"

# 検索文字列パターン集（account.jsonに追加したほうがいいか？）
kgmPattern = r"(かがみ|カガミ|鏡|鑑|加賀美|加々美|ｋａｇａｍｉ|ＫＡＧＡＭＩ|kagami)"
helpPattern = r"(help|(へ|ヘ)(る|ル)(ぷ|プ))"
steamPattern = r"^https?://.+steampowered\.com/([\w./?%&=]*)?"
dicePattern = r"^(\d+)D(\d+)([\s　]*\+[\s　]*(\d+))?([\s　]*-[\s　]*(\d+))?([\s　]*\+[\s　]*(\d+))?"
showkunPattern = r"^/(show|haruka|hikari|takeru|santa|bear)kun(\s+)(.+)"
#vcPattern = r"^/vccon(nect)?\s+((#.+)\s?)+$"
vcPattern = r"^/vccon(nect)?(\s|　)+((<#\d+>\s*)+)$"
vcdPattern = r"^/vcdis(connect)?"

# トークンjson読み込み
df = {}
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
        # Sqlite3
        "sqlite3": "./discordbot.sqlite3",
        #signature
        "sign": "signature",
        #help
        "help": {
            "title": "help string",
            "embed": {
                "title": "help embed title",
                "desp": ["help embed description"] #Array for new lines
            }
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
        },
        #OpusLib
        "OpusLib": {
            "libPath": "Path to libopus"
        }
    }
    with open(setting_json, mode='w') as f:
        json.dump(df, f, indent=4, ensure_ascii=False)

if not df:
    print("setting file is incorrect. please check 'setting_json':{setting_json}")
    sys.exit()

# Discord token
auth_token = df['test' if _Debug else 'prod']['token']

# 更新日時
update_date = str(datetime.datetime.fromtimestamp(os.stat(__file__).st_ctime))[:10]

print('ログイン中...')
client = discord.Client() #接続に使用するオブジェクト

# Socket data
socketData = ""
socketFlag = True

# DB sqlite
sql = sqlite3.connect(df["sqlite3"])
sqltable = "vtwa"
sqlc = sql.cursor()
sqlc.execute(f"CREATE TABLE IF NOT EXISTS {sqltable} (name text, date integer, long integer)")
# TABLE vtwa
# name: TEXT
# data: INT
# long: INT(BOOL)

# VoiceTextWebAPI
discord.opus.load_opus(df["OpusLib"]["libPath"])
if not discord.opus.is_loaded():
    print("Opusライブラリのロードに失敗しました。一部の機能が制限されます。")
showkun = {}
showkun_token = df['VoiceTextAPI']['token']
showkun_dir = df["VoiceTextAPI"]["dir"]

# 起動時に通知してくれる処理
@client.event
async def on_ready():
    print(client.user.name + " " + str(client.user.id))
    # vcshowkun
    for guild in client.guilds:
        print(f"connect {guild.name} : {guild.id}")
        showkun[guild.id] = VoiceTextWebAPI(showkun_token, showkun_dir, guild)
    print(showkun.keys())
    print('ログインしました')
    asyncLoop.create_task( WaitSocketData())

# メッセージを受信したときの処理
@client.event
async def on_message(message):
    # steamURL が発言されたら steam:// でURLを返す処理
    asyncLoop.create_task( SteamLink(message) )
    asyncLoop.create_task( DiceRoll(message) )
    asyncLoop.create_task( VoiceTextShowKun(message) )
    asyncLoop.create_task( ShowkunVoicechat(message) )
    #asyncLoop.create_task( CountDown(message) )
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
    if message.content.startswith(f"<@!{client.user.id}>"):
        if (await KgmMention(message, client)):
            pass
        else:
            reply = f'{message.author.mention} コマンドが認識できませんでした'
            await message.channel.send(reply)

###################
# 
###################

# 特定の鯖でメンションが来たとき
async def KgmMention(msg, cl):
    server_id = df['test' if _Debug else 'prod']['id']
    if (int(msg.guild.id) == server_id):
        kgmMatch = re.search(kgmPattern, msg.content, re.IGNORECASE)
        helpMatch = re.search(helpPattern, msg.content, re.IGNORECASE)
        if kgmMatch:
            await Kagami(msg)
            return True
        elif helpMatch:
            await HelpMsg(msg, cl)
            return True
    return False

# Help
async def HelpMsg(msg, cl):
    s = parseHelp(df['help']['title'], msg, cl)
    title = parseHelp(df['help']['embed']['title'], msg, cl)
    des = parseHelp("\n".join(df['help']['embed']['desp']), msg, cl)
    em = discord.Embed(title=title, description=des)
    await msg.channel.send(s, embed=em)

def parseHelp(src, msg, cl):
    return src.replace("<date>", str(update_date)).replace("<id>", str(cl.user.id))

# Steam Link 書き換え
async def SteamLink(msg):
    # steamURL が発言されたら steam:// でURLを返す処理
    matchOB = re.match(steamPattern, msg.content, re.IGNORECASE)
    if matchOB:
        reply = 'steam://openurl/' + matchOB.group()
        em = discord.Embed()
        await msg.channel.send(reply, embed=em)

# サイコロ
async def DiceRoll(msg):
    matchOB = re.match(dicePattern, msg.content, re.IGNORECASE)
    if matchOB:
        num = int(matchOB.group(1))
        if num > 100:
            await msg.channel.send("101以上は実行できません")
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
        if matchOB.group(3) is not None:
            randsum += int(matchOB.group(4))
            randlist += '+' + str(matchOB.group(4))
        if matchOB.group(5) is not None:
            randsum -= int(matchOB.group(6))
            randlist += '-' + str(matchOB.group(6))
        if matchOB.group(7) is not None:
            randsum += int(matchOB.group(8))
            randlist += '+' + str(matchOB.group(8))
        em = discord.Embed(description=randlist)
        await msg.channel.send(str(randsum), embed=em)

# ショー君URL送信
async def VoiceTextShowKun(msg):
    matchOB = re.match(showkunPattern, msg.content, re.IGNORECASE)
    if matchOB:
        global showkun
        if msg.guild.id not in showkun:
            return
        vcshowkun = showkun[msg.guild.id]
        text = matchOB.group(3)
        sp = matchOB.group(1)
        name = await vcshowkun.GetShowkunDataPath(text, msg.channel.send, sp=sp)
        if name != '':
            await msg.channel.send(df["VoiceTextAPI"]["server_url"].replace("<name>", name))
        else:
            await msg.channel.send("音声ファイル生成失敗")


# ショー君VoiceChat参加読み上げ機能
async def ShowkunVoicechat(msg):
    # VC参加していない時、VC参加リクエスト文字列を待機
    global showkun
    if msg.guild.id not in showkun:
        return
    #vcshowkun = showkun[msg.guild.id]
    matchConOB = re.match(vcPattern, msg.content, re.IGNORECASE)
    if not showkun[msg.guild.id].is_ready_vc():
        #print(msg.content)
        if (matchConOB):
            if(msg.author.voice):
                # VC参加リクエストメッセージ送信者がVCにいるかどうか
                # チャンネルリスト作成    
                text = matchConOB.group(3).split(" ")
                channellist = tuple(map(lambda x: int(x[2:-1]),filter(lambda c: len(c) > 1 and c[1] == '#', text)))
                if await showkun[msg.guild.id].connect_vc(msg, channellist):
                    msg.channel.send("ボイスチャット接続に失敗しました。")
            else:
                #print("you are not in VC")
                await msg.channel.send("VC接続コマンド使用者がボイスチャンネルにいる必要があります。")

    # VC参加時
    else:
        if showkun[msg.guild.id].is_limit_time() > 0:
            await showkun[msg.guild.id].disconnect_vc()
        if(matchConOB):
            await msg.channel.send("すでに通話中です。")
        # 登録チャンネル判定
        elif(msg.channel.id in showkun[msg.guild.id].read_channels):
            # VC離脱リクエスト文字列を待機
            matchDisOB = re.match(vcdPattern, msg.content, re.IGNORECASE)
            if matchDisOB:
                await showkun[msg.guild.id].disconnect_vc()
            else:
                # bot自身以外
                if(msg.author != client.user):
                    #await msg.channel.send("This is test:" + msg.content)
                    await showkun[msg.guild.id].play(msg)

# 鏡を借りる
async def Kagami(msg):
    kgmPtrn = r"(http|mms).?://.*:\d+.?(\s|　)*"
    kgmPush = r"(push|プッ?シュ|ぷっ?しゅ|(ｐ|Ｐ)(ｕ|Ｕ)(ｓ|Ｓ)(ｈ|Ｈ)|ぷｓｈ)(\s|　)*"
    forceConn = r"^(force|f)"
    kgmForce = True if re.search(forceConn, msg.content, re.IGNORECASE) else False

    kgmMatch = re.search(kgmPtrn, msg.content, re.IGNORECASE)
    port_str = str(df["okiba"]["port"][0])
    kagami = urllib.parse.urlparse(df["okiba"]["url"])
    kagami = kagami.scheme + "://" + kagami.hostname + ":"

    # pull接続
    if kgmMatch:
        comment = "" if kgmMatch.end() >= len(msg.content) else msg.content[kgmMatch.end():] + " "
        password = randomname(10)
        kgmUrl = await KgmUrl(port_str, True, password, comment, msg.author.name, url=kgmMatch.group(0), force=kgmForce)
        if(_Debug):
            em = discord.Embed(title=kgmMatch.group(0) + "\n┗"+kagami+port_str, description=kgmUrl)
            await msg.channel.send(comment, embed=em)
        else:
            await KgmHTTP(kgmUrl, msg.channel.send)
            # DM 送信
            await msg.author.send(DmMsg(port_str, password))
            em = discord.Embed(title=kgmMatch.group(0) + "\n┗"+kagami+port_str)
            await msg.channel.send("鏡を " + kgmMatch.group(0) + " に接続しました\nパスワードと接続設定はDMを確認してください", embed=em)
    else:
        # push待機
        kgmMatch = re.search(kgmPush, msg.content, re.IGNORECASE)
        if kgmMatch:
            comment = "" if kgmMatch.end() >= len(msg.content) else msg.content[kgmMatch.end():] + " "
            password = randomname(10)
            kgmUrl = await KgmUrl(port_str, False, password, comment, msg.author.name, force=kgmForce)

            if(_Debug):
                em = discord.Embed(title="push\n"+kagami+port_str, description=kgmUrl)
                await msg.channel.send(comment, embed=em)
            else:
                await KgmHTTP(kgmUrl, msg.channel.send)
                # DM 送信
                em = discord.Embed(title="push\n"+kagami+port_str)
                await msg.author.send(DmMsg(port_str, password))

                await msg.channel.send("鏡をpush待機させました\nパスワードと接続設定はDMを確認してください", embed=em)
        else:
            await msg.channel.send("urlが判別できませんでした")

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
async def KgmHTTP(url, fnSendMsg):
    try:
        res = urllib.request.urlopen(url, timeout=1).read()
    except (urllib.request.HTTPError, urllib.request.URLError) as error:
        await fnSendMsg(ch, error + "によってデータ取得に失敗しました")
    except timeout:
        await fnSendMsg(ch, "タイムアウトしました")

# Wait for Socket data
async def WaitSocketData():
    global socketData
    global socketFlag
    if socketFlag:
        socketFlag = False
        while True:
            await asyncio.sleep(10)
            if socketData != "":
                await sendNanV(socketData)
                socketData = ""

# bot用チャンネルに鏡情報を送信
async def sendNanV(Msg, enc = 0):
    okiba = df['conKgm']
    channel = client.get_channel(df['test' if _Debug else 'prod']['channel'])
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
            await channel.send(msg, embed=em)
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
            await channel.send(msg, embed=em)


# logs_from test
async def testLogs(msg):
    if msg.content.startswith('!test'):
        counter = 0
        msg_tmp = await msg.channel.send('Calculating messages...')
        async for log in msg.channel.history(limit=100):
            if log.author == msg.author:
                counter += 1
        await msg_tmp.edit('You have {} messages.'.format(counter))

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
    values = {'sid': sid, 'hobo': hobo, 'appkey': AppKey}
    headers = {
        'User-Agent': dat_UA,
        'Connection': 'close',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept-Encoding': 'gzip'}
    data = urllib.parse.urlencode(values).encode('ascii')
    req = urllib.request.Request(dat_url, data, headers)
    res = urllib.request.urlopen(req)
    dat = res.read() #.decode('UTF-8')

    print(dat)


# ユニークネーム設定　
# SQLに登録し、重複チェック
def uniqueName(num):
    name = randomname(num)
    sqlc.execute(f"SELECT * FROM {sqltable} where name='{name}'")
    fetchone = sqlc.fetchone()
    date = int(datetime.datetime.now().timestamp())
    if fetchone:
        if date > fetchone[1] + 60 * 60 * 24 * 7:
            long_ = 1 if num == 3 else 0
            sqlc.execute(f"UPDATE {sqltable} SET date = {date} WHERE name = '{name}'")
            sql.commit()
            return name

        uniqueName(num)
    else:
        long_ = 1 if num == 3 else 0
        sqlc.execute(f"INSERT INTO {sqltable} VALUES ('{name}', {date}, {long_})")
        sql.commit()
        return name

###################################
# Basic認証
# ref: https://www.yoheim.net/blog.php?q=20181003
async def BasicReq(user, pas, url, SendMsg):
    bas = base64.b64encode((user +':'+ pas).encode('utf-8'))
    headers = {"Authorization": "Basic " + bas.decode('utf-8')}
    try:
        req = urllib.request.Request(url, headers=headers, method="POST")
        return urllib.request.urlopen(req).read()
    except urllib.request.HTTPError as e:
        await SendMsg("HTTP Error "+e.code+ " :"+e.read())
        return b''
    except (urllib.request.HTTPError, urllib.request.URLError) as error:
        await SendMsg(error + "によってデータ取得に失敗しました")
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
