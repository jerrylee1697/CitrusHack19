import ast
import fb
import pymysql.cursors
from twitterscraper.query import query_tweets_from_user

def get_tweets(username, limit):
    """Given a Twitter username, return a list of their most recent tweets."""
    tweets = []
    for tweet in query_tweets_from_user(username, limit):
        tweets.append(tweet.text)
    return tweets


def insert(user, data):
    """Hacky way of inserting data into the project database."""
    try:
        connection = pymysql.connect(host='hacksc.cv6knx9xzbuq.us-west-1.rds.amazonaws.com',
                                    user='sensei',
                                    password='password',
                                    db='main',
                                    cursorclass=pymysql.cursors.DictCursor)
        with connection.cursor() as cursor:
            sql = "INSERT INTO `celebrities` (`handle`, `agreeableness`, `conscientiousness`, `extraversion`, `emotional_range`, `openness`) VALUES ('%s', '%s', '%s', '%s', '%s', '%s')" % (user, data['agreeableness'], data['conscientiousness'], data['extraversion'], data['emotional_range'], data['openness'])
            cursor.execute(sql)
            connection.commit()
    finally:
        connection.close()


def get_twitter_user_data(username):
    data = get_tweets(username, 150)
    json_content_info = fb.content_info(data)
    profile = fb.personality_data(json_content_info)
    profile_dict = ast.literal_eval(fb.personality_ratings(profile))
    profile_dict['user_id'] = username
    profile_dict['name'] = query_tweets_from_user(username, 5)[0].fullname
    return profile_dict


def main():
    # Add Single User
    # data = get_tweets('FLOTUS', 100)
    # json_content_info = fb.content_info(data)
    # profile = fb.personality_data(json_content_info)
    # profile_dict = ast.literal_eval(fb.personality_ratings(profile))
    # insert('FLOTUS', profile_dict)

    print(get_twitter_user_data('ellamai'))

if __name__ == '__main__':
    main()
