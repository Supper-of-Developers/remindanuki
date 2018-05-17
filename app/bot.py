# coding=utf-8
import logging
from flask import Flask, request, abort
from datetime import datetime

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, PostbackEvent, Postback, TemplateSendMessage, ButtonsTemplate, DatetimePickerTemplateAction
)
import redis
import config
import function as func

import weather

app = Flask(__name__)

handler = WebhookHandler(config.CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    """
    メインメソッド /callbackにアクセスされた時に実行される
    """
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """
    messageイベントを受け取るmethod
    Args:
        event (linebot.models.events.MessageEvent): LINE Webhookイベントオブジェクト
    """
    # 送信元
    send_id = func.get_send_id(event)

    # redisに接続
    redis_connection = redis.StrictRedis(host=config.REDIS_URL, port=config.REDIS_PORT, db=0)

    context = ""
    if redis_connection.get(send_id):
        context = redis_connection.get(send_id).decode('utf-8')

    if event.message.text == "新しいリマインダ" :
        func.reply_message(event.reply_token, TextSendMessage(text="リマインドして欲しい予定を入力するぽん！\n例：「お買い物」「きつねさんとランチ」「お金の振り込み」"))
    elif context != "" and event.message.text == "キャンセル":
        # redisのコンテキストを削除
        redis_connection.delete(send_id)
        func.reply_message(event.reply_token, TextSendMessage(text="また何かあったら言って欲しいたぬ～"))
    elif event.message.text == "一覧を見る":
        # DBからその送信元に紐づくリマインダーを現在日時に近いものから最大5件取得する
        remind_list = func.get_remind_list(send_id)
        func.reply_message(event.reply_token, remind_list)
    elif event.message.text == "お天気":
        #お天気の情報を取得して表示
        forecast_info = weather.weather_infomation()
        func.reply_message(event.reply_token, TextSendMessage(text = forecast_info))
        #リプライメッセージを書いてあげる,戻り値を返してあげる

    else :
        # redisにコンテキストを保存
        redis_connection.set(send_id, event.message.text)
        # datepickerの作成
        date_picker = func.create_datepicker(event.message.text)
        func.reply_message(event.reply_token, date_picker)

@handler.add(PostbackEvent)
def handle_datetime_postback(event):
    """
    datetimeのpostbackイベントを受け取るmethod
    Args:
        event (linebot.models.events.MessageEvent): LINE Webhookイベントオブジェクト
    """
    # 送信元
    send_id = func.get_send_id(event)

    # 日付文字列をdatetimeに変換
    date = event.postback.params['datetime'].replace('T', ' ')
    remind_at = datetime.strptime(date, "%Y-%m-%d %H:%M")

    # リマインド内容を保存する
    context = func.regist_reminder(event, send_id, remind_at)

    # 登録完了メッセージを返す
    hiduke = remind_at.strftime('%Y年%m月%d日 %H時%M分')
    func.reply_message(event.reply_token, TextSendMessage("了解だぽん！\n" + hiduke + "に「" + context + "」のお知らせをするぽん！"))

# Gunicorn用Logger設定
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# Flask利用のため
if __name__ == "__main__":
    app.run(port=3000)
