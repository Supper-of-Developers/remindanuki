# coding=utf-8
from linebot.models import (TextSendMessage)
from linebot import (LineBotApi)

from pytz import timezone
from datetime import datetime
import mysql.connector
import config
import function as func

line_bot_api = LineBotApi(config.ACCESS_TOKEN)

# mysqlに接続
mysql_connection = func.getMysqlPoolConnection()
cursor = mysql_connection.cursor(dictionary=True)

#データを取得
sql = "SELECT send_id, text, remind_at FROM reminders, senders WHERE reminders.sender_id = senders.id AND remind_at >= CURRENT_DATE() AND remind_at < date_add(CURRENT_DATE(), INTERVAL 1 DAY) ORDER BY remind_at ASC ;"
cursor.execute(sql)
rows = cursor.fetchall()

if rows:
    send_id_dict = {}
    for row in rows:
        if row['send_id'] in send_id_dict:
            send_id_dict[row['send_id']] = send_id_dict[row['send_id']] +"\n"+ str(row['remind_at'].strftime("%H:%M")) +" "+  row['text']
        else:
            send_id_dict[row['send_id']] = '本日の予定一覧たぬ！'+ "\n"+ str(row['remind_at'].strftime("%H:%M")) +" "+ row['text']
    for key, value in send_id_dict.items():
        line_bot_api.push_message(key, TextSendMessage(text=value))

# mysqlから切断
cursor.close()
mysql_connection.close()