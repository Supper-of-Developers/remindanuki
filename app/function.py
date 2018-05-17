# coding=utf-8
from pytz import timezone
from datetime import datetime
from linebot import (
    LineBotApi
)
from linebot.models import (
    TextSendMessage, TemplateSendMessage, ButtonsTemplate, DatetimePickerTemplateAction
)
import mysql.connector
import sqlalchemy.pool as pool
import redis
import config

line_bot_api = LineBotApi(config.ACCESS_TOKEN)

def reply_message(reply_token, message_object):
    """
    LINEメッセージ返信method
    Args:
        reply_token (str): 返信用トークン
        message_object (linebot.models.send_messages.SendMessage): 返信メッセージオブジェクト
    """
    line_bot_api.reply_message(
            reply_token,
            message_object)

def getMysqlConnection():
    con = mysql.connector.connect(**config.MYSQL_CONFIG)
    return con

def getMysqlPoolConnection():
    mypool = pool.QueuePool(getMysqlConnection, max_overflow=10, pool_size=5)
    con = mypool.connect()
    return con

def create_datepicker(context):
    """
    datepickerオブジェクト作成method
    Args:
        context (str): 会話から受け取った予定
    Rerurns:
        linebot.models.template.TemplateSendMessage: datepickerオブジェクト
    """
    now_date = datetime.now(timezone('Asia/Tokyo')).strftime("%Y-%m-%dt%H:%M")
    date_picker = TemplateSendMessage(
        alt_text='「' + context + '」をいつ教えてほしいぽん？',
        template=ButtonsTemplate(
            text= '「' + context + '」をいつ教えてほしいぽん？\n「キャンセル」って言ってくれればやめるたぬ～',
            actions=[
                DatetimePickerTemplateAction(
                    label='設定',
                    data='action=buy&itemid=1',
                    mode='datetime',
                    initial=now_date,
                    min=now_date,
                    max='2099-12-31t23:59'
                )
            ]
        )
    )

    return date_picker

def get_send_id(event):
    """
    送信元タイプを利用して送信元IDを特定するmethod
    Args:
        event (linebot.models.events.MessageEvent): LINE Webhookイベントオブジェクト
    Returns:
        str: send_id 送信元ID
    """
    send_id = ""
    if event.source.type == 'user':
        send_id = event.source.user_id
    elif event.source.type == 'group':
        send_id = event.source.group_id
    elif event.source.type == 'room':
        send_id = event.source.room_id

    return send_id

def get_remind_list(send_id):
    """
    リマインダーリスト取得method
    Args:
        send_id (str): 送信元ID
    Return:
        list: list 現在日時から近い予定から最大5件のリスト
    """
    # mysqlに接続
    mysql_connection = getMysqlPoolConnection()
    cursor = mysql_connection.cursor(dictionary=True)

    # 現在日時を取得
    now_date = datetime.now(timezone('Asia/Tokyo')).strftime("%Y-%m-%d %H:%M:%s")

    sql = ('SELECT '
           'reminders.remind_at, reminders.text '
           'FROM '
           'reminders, senders '
           'WHERE '
           'reminders.sender_id = senders.id AND senders.send_id = %s AND reminders.remind_at > %s '
           'ORDER BY reminders.remind_at '
           'LIMIT 5;')

    cursor.execute(sql, (send_id,now_date))

    ret_list = []
    rows = cursor.fetchall()
    if rows:
        print(rows)
        for row in rows:
            # 日付文字列をフォーマット
            text = row['text']
            hiduke = row['remind_at'].strftime('%Y年%m月%d日 %H時%M分')
            ret_list.append(TextSendMessage(text=hiduke + "\n「" + text + "」を予定しているぽん！"))
    else:
        ret_list.append(TextSendMessage(text="君に教えることは何もないぽん\n「新しいリマインダ」と入力して予定を入力して欲しいぽん"))
    # mysqlから切断
    cursor.close()
    mysql_connection.close()

    return ret_list

    

def regist_reminder(event, send_id, remind_at):
    """
    リマインダー登録method
    Args:
        event (linebot.models.events.MessageEvent): LINE Webhookイベントオブジェクト
        send_id (str): 送信元ID
        remind_at (datetime): 会話から受け取ったリマインド時刻
    Return:
        str: context 会話から受け取った予定
    """
    # mysqlに接続
    mysql_connection = getMysqlPoolConnection()
    cursor = mysql_connection.cursor(dictionary=True)

    # redisから入力された予定を取得
    redis_connection = redis.StrictRedis(host=config.REDIS_URL, port=config.REDIS_PORT, db=0)
    if redis_connection.get(send_id):
        context = redis_connection.get(send_id).decode('utf-8')
    else:
        # リマインダ設定フロー以外のpostbackはスルー
        return

    # 送信元IDが未登録なら登録、登録済みなら取得のみ
    id = check_sender_id(mysql_connection, cursor, send_id)
    # リマインダーを登録
    insert_reminder(mysql_connection, cursor, id, context, remind_at)

    # mysqlから切断
    cursor.close()
    mysql_connection.close()

    # redisの値を削除
    redis_connection.delete(send_id)

    return context

def check_sender_id(mysql_connection, cursor, send_id):
    """
    送信元をチェックし、DB登録に未登録なら登録して送信元管理IDを返し、登録済みなら取得した送信元管理IDを返すmethod
    Args:
        mysql_connection (mysql.connector.connect): MySQLコネクター
        cursor (mysql.connector.connect.cursor): MySQLカーソル
        send_id (str): 送信元ID
    Returns:
        int: id 送信元管理ID
    """
    id = 0
    # 送信元が登録済みか確認
    cursor.execute("SELECT id FROM senders WHERE send_id = %s;", (send_id,))
    row = cursor.fetchone()
    if row is None:
        # 未登録の送信元だったら登録する
        cursor.execute('INSERT INTO senders (send_id) VALUES (%s);', (send_id,))
        mysql_connection.commit()
        # insertしたIDを取得
        cursor.execute("SELECT LAST_INSERT_ID() as id;")
        row = cursor.fetchone()
        id = row['id']
    else:
        id = row['id']

    return id

def insert_reminder(mysql_connection, cursor, sender_id, context, remind_at):
    """
    リマインダー登録SQL実行method
    Args:
        mysql_connection (mysql.connector.connect): MySQLコネクター
        cursor (mysql.connector.connect.cursor): MySQLカーソル
        send_id (str): 送信元ID
        context (str): 会話から受け取った予定
        remind_at (datetime): 会話から受け取ったリマインド時刻
    """
    cursor.execute('INSERT INTO reminders (sender_id, text, remind_at) VALUES (%s, %s, %s);', (sender_id, context, remind_at))
    mysql_connection.commit()

# def inform_weather(self):
#     text = "[{0}]\n".format(self.data)
#     text += "{0}".format(self.telop)
    
#     print("本日の天気")
    
#     temp = ""
#     if self.temp_max:
#         temp += "\n"
#         temp = "最高気温{0}度".format(self.temp_max)

#     if self.temp_min:
#         if temp:
#             temp += "\n"
#         temp += "最低気温{0}度だぽん".format(self.temp_min)

#     else:
#         return #いまどこにリターンすべきか考えてる、とりあえず保留