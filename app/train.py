import urllib3
import json
#pushメッセージ送る上で必要なインポート
from linebot.models import (TextSendMessage)
from linebot import (LineBotApi)
import mysql.connector
import config
import function as func

line_bot_api = LineBotApi(config.ACCESS_TOKEN)
# mysqlに接続
mysql_connection = func.getMysqlPoolConnection()
cursor = mysql_connection.cursor(dictionary=True)

#jsonデータの読み込み
http = urllib3.PoolManager()
r = http.request('Get','https://rti-giken.jp/fhc/api/train_tetsudo/delay.json')
train_datas = json.loads(r._body)

#ここでlines_nameをappendでjsonのURLから線路名を取得
lines_name = []
advertising_lines = ["丸の内線", "有楽町線",'千代田線','銀座線','東西線','副都心線','半蔵門線','京浜東北線','横須賀線','中央線快速電車','中央･総武各駅停車','埼京線','池袋線']
for train_data in train_datas:
    lines_name.append(train_data['name']) 

#jsonのデータと指定した路線図を一致したものをmatched_linesというリストに加える 
lname_set = set(lines_name)
adv_set = set(advertising_lines)
matched_lines = list(lname_set & adv_set)
matched_lines = ",".join(matched_lines)

#dbからとってきた個別のユーザーに遅延情報を教える
sql = "SELECT send_id FROM senders;"
cursor.execute(sql)
rows = cursor.fetchall()
if rows:
    if not matched_lines:
        for row in rows:
            line_bot_api.push_message(row['send_id'], TextSendMessage(text= "どこも遅延してないぽん"))
    else:
        for row in rows:
            line_bot_api.push_message(row['send_id'], TextSendMessage(text= matched_lines + "が遅延しているぽん。狐くらい腹たつぽん"))
        
# mysqlから切断
cursor.close()
mysql_connection.close()