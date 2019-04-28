import ast
import fb
import json
import urllib.request
import pymysql.cursors
import twitter
from ibm_watson import PersonalityInsightsV3
from flask import Flask, request, Response
from flask import jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

def get_content():
    """Returns content from Facebook's Graph API using
    HTTP GET."""
    graph_api_url = 'https://graph.facebook.com/v3.2/me?fields=posts&access_token=EAAeIZBsPFxyQBAJrw4nsFLi8ZBLt3yEZCwBD4ts1GqAZBNdXIy7XSWxlWDPDT0tYGvKP5z6qr4kTMBT7EIrHIH03h0h6LxXdZByaEXRxrfO2GpZCyTcBvJAYfZBiJtu7zdZBAnjSZBIpA21ZBsrcqUoeNleW6ZBomrT8WGYEJOPVHLXTtr0Vx1XkWHKC6RwUluo3SkZD'
    return urllib.request.urlopen(graph_api_url).read().decode('utf-8')


def get_messages(content):
    """Returns a list of a user's posts."""
    messages = []
    for post in content['posts']['data']:
        if 'message' in post:
            messages.append(post['message'])
    return messages


def content_info(messages):
    """Returns a JSON object as input for the IBM SDK."""
    content_info = {'contentItems': []}
    for message in messages:
        content_info['contentItems'].append({
            'content': message
        })
    return json.dumps(content_info)


@app.route("/personality_data", methods = ['POST'])
def personality_data():
    """Returns personality trait data for the user."""
    user_content = request.get_data()
    personality_insights = PersonalityInsightsV3(
        version='2017-10-13',
        iam_apikey='m8CcsJovJ2rfO9wpD0eSe0E6EFXTSNTwoc8fGIaj5RrR',
        url='https://gateway.watsonplatform.net/personality-insights/api'
    )
    profile = personality_insights.profile(
        user_content,
        'application/json',
        content_type='application/json',
        consumption_preferences=True,
        raw_scores=True
    ).get_result()
    return jsonify(profile) 


@app.route("/personality_ratings")
def personality_ratings(profile):
    """Given a user profiles, extacts the 5 personality traits and
    their ratings as a percentage."""
    personality_data = {}
    for personality in profile['personality']:
        name = personality['name'].lower().replace(' ', '_')
        value = float(personality['percentile'])
        personality_data[name] = value
    return json.dumps(personality_data)


@app.route("/data")
def get_data_test():
    db = pymysql.connect(
        host="hacksc.cv6knx9xzbuq.us-west-1.rds.amazonaws.com",
        user="sensei",
        password="password",
        db="main")
    cur = db.cursor()
    cur.execute("SELECT * FROM celebrities")
    data = cur.fetchall()
    db.close()
    return jsonify(data)


@app.route("/get_personality/<user_id>")
def get_user_data(user_id):
    # Establish database connection.
    db = pymysql.connect(host="hacksc.cv6knx9xzbuq.us-west-1.rds.amazonaws.com",
                    user="sensei",
                    password="password",
                    db="main")
    cursor = db.cursor()
    to_return = {}

    if len(user_id) > 0 and user_id[0] == '@':
        data = twitter.get_twitter_user_data(user_id[1:])
        to_return['Agreeableness'] = data['agreeableness']
        to_return['Conscientiousness'] = data['conscientiousness']
        to_return['Extraversion'] = data['extraversion']
        to_return['Emotional range'] = data['emotional_range']
        to_return['Openness'] = data['openness']
        to_return['name'] = data['name']
    else:
        # FB profile ID.
        query = "SELECT * FROM user_data WHERE user_id = %s"
        cursor.execute(query, (user_id))
        data = cursor.fetchall()
        if not data:
            return jsonify('Empty')
        data = data[0]
        db.close()
        to_return['Agreeableness'] = data[1]
        to_return['Conscientiousness'] = data[2]
        to_return['Extraversion'] = data[3]
        to_return['Emotional range'] = data[4]
        to_return['Openness'] = data[5]
        to_return['name'] = data[6]
    return jsonify(to_return)


@app.route("/get_all_users")
def get_all_userid():
    db = pymysql.connect(host="hacksc.cv6knx9xzbuq.us-west-1.rds.amazonaws.com",
                     user="sensei",
                     password="password",
                     db="main")
    cur = db.cursor()
    query = "SELECT user_id FROM user_data"
    cur.execute(query)
    data = cur.fetchall()
    db.close()
    return jsonify(data)


@app.route("/get_celebrity/<name>")
def get_celebrity(name):
    db = pymysql.connect(host="hacksc.cv6knx9xzbuq.us-west-1.rds.amazonaws.com",
                     user="sensei",
                     password="password",
                     db="main")
    query = "SELECT * FROM celebrities WHERE handle = %s"
    cur.execute(query, (name))
    data = cur.fetchall()
    db.close()
    return jsonify(data)


@app.route("/save/<user_id>", methods = ['POST'])
def insert(user_id):
    """Hacky way of inserting data into the project database."""
    data = request.get_json()
    try:
        connection = pymysql.connect(host='hacksc.cv6knx9xzbuq.us-west-1.rds.amazonaws.com',
                                    user='sensei',
                                    password='password',
                                    db='main',
                                    cursorclass=pymysql.cursors.DictCursor)
        
        with connection.cursor() as cursor:
            sql = "INSERT INTO `user_data` (`user_id`, `agreeableness`, `conscientiousness`, `extraversion`, `emotional_range`, `openness`, `name`) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s') ON DUPLICATE KEY UPDATE user_id='%s', agreeableness='%s', conscientiousness='%s', extraversion='%s', emotional_range='%s', openness='%s', name='%s'" % (user_id, data['Agreeableness'], data['Conscientiousness'], data['Extraversion'], data['Emotional range'], data['Openness'], data['name'], user_id, data['Agreeableness'], data['Conscientiousness'], data['Extraversion'], data['Emotional range'], data['Openness'], data['name'])
            cursor.execute(sql)
            connection.commit()
        return "Hello World"
    except (ValueError, KeyError, TypeError) as error:
        print(error)
        resp = Response({"JSON Format Error."}, status=400, mimetype='application/json')
        return resp


# Compare's 2 user personalities
# Input: user_id, user_id
# Return: % for each personality trait + overall % match
@app.route("/compare_users/<id1>/<id2>")
def compare_user_personality(id1, id2):
    """Compares two user's personalities"""
    db = pymysql.connect(host="hacksc.cv6knx9xzbuq.us-west-1.rds.amazonaws.com",
                     user="sensei",
                     password="password",
                     db="main")
    cur = db.cursor()
    query = "SELECT * FROM user_data WHERE user_id = %s"
    cur.execute(query, (id1))
    id1_data = cur.fetchall()
    if not id1_data:
        return jsonify('user1 invalid')
    id1_data = id1_data[0]

    cur.execute(query, (id2))
    id2_data = cur.fetchall()
    if not id2_data:
        return jsonify('user2 invalid')
    id2_data = id2_data[0]

    result = {}
    result['Agreeableness'] = 1 - abs(id1_data[1] - id2_data[1])
    result['Conscientiousness'] = 1 - abs(id1_data[2] - id2_data[2])
    result['Extraversion'] = 1 - abs(id1_data[3] - id2_data[3])
    result['Emotional range'] = 1 - abs(id1_data[4] - id2_data[4])
    result['Openness'] = 1 - abs(id1_data[5] - id2_data[5])
    db.close()
    total = 0
    for key, value in result.items():
        total += value
    result['Overall'] = total / 5
    return jsonify(result)


### Insert user values into database ###
@app.route("/save_values/<user_id>", methods = ['POST'])
def insert_user_values(user_id):
    """Hacky way of inserting data into the project database."""
    data = request.get_json()
    try:
        connection = pymysql.connect(host='hacksc.cv6knx9xzbuq.us-west-1.rds.amazonaws.com',
                                    user='sensei',
                                    password='password',
                                    db='main',
                                    cursorclass=pymysql.cursors.DictCursor)
        
        with connection.cursor() as cursor:
            sql = "INSERT INTO `user_values` (`user_id`, \
                `Conservation`, \
                `Openness to change`, \
                `Hedonism`, \
                `Self-enhancement`, \
                `Self-transcendence`) \
                VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" \
                 % (user_id, data['Conservation'], data['Openness to change'], data['Hedonism'], data['Self-enhancement'], data['Self-transcendence'])
            cursor.execute(sql)
            connection.commit()
        return "Hello World"
    except (ValueError, KeyError, TypeError) as error:
        print(error)
        resp = Response({"JSON Format Error."}, status=400, mimetype='application/json')
        return resp


### Insert user needs into database ###
@app.route("/save_needs/<user_id>", methods = ['POST'])
def insert_user_needs(user_id):
    """Hacky way of inserting data into the project database."""
    data = request.get_json()
    try:
        connection = pymysql.connect(host='hacksc.cv6knx9xzbuq.us-west-1.rds.amazonaws.com',
                                    user='sensei',
                                    password='password',
                                    db='main',
                                    cursorclass=pymysql.cursors.DictCursor)
        
        with connection.cursor() as cursor:
            sql = "INSERT INTO `user_needs` (`user_id`, \
                `Challenge`, \
                `Closeness`, \
                `Curiosity`, \
                `Excitement`, \
                `Harmony`, \
                `Ideal`, \
                `Liberty`, \
                `Love`, \
                `Practicality`, \
                `Self-expression`, \
                `Stability`, \
                `Structure`) \
                VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" \
                 % (user_id, data['Challenge'], data['Closeness'], data['Curiosity'], data['Excitement'], \
                 data['Harmony'], data['Ideal'], data['Liberty'], data['Love'], data['Practicality'], \
                 data['Self-expression'], data['Stability'], data['Structure'])
            cursor.execute(sql)
            connection.commit()
        return "Hello World"
    except (ValueError, KeyError, TypeError) as error:
        print(error)
        resp = Response({"JSON Format Error."}, status=400, mimetype='application/json')
        return resp

def main():
    content = ast.literal_eval(get_content())
    messages = get_messages(content)
    json_content_info = content_info(messages)
    profile = personality_data(json_content_info)
    print(personality_ratings(profile))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') 