import urllib3
import json
#pushメッセージ送る上で必要なインポート
from linebot.models import (TextSendMessage)
from linebot import (LineBotApi)
import mysql.connector
import config
import function as func

line_bot_api = LineBotApi(config.ACCESS_TOKEN)

#お天気の情報を取得
def weather_information():
    http = urllib3.PoolManager()
    r = http.request('Get','http://weather.livedoor.com/forecast/webservice/json/v1?city=130010')
    r = json.loads(r._body)

    date = r['forecasts'][0]['dateLabel']
    weather = r['forecasts'][0]['telop']
    temp = r['forecasts'][0]['temperature']['max']['celsius']
    weather_news = date + "の東京の天気は" + weather + "\n" + "最高気温は" + temp + "度"
    return weather_news
#cron用の天気予報
def morning_news():
    weather_info = weather_information()
    rows = func.get_sql_send_id()
    if rows:
        for row in rows:
            line_bot_api.push_message(row['send_id'], TextSendMessage(text= weather_info + "だぽん"))
    
morning_news()
