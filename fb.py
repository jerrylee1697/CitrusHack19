import ast
import json
import pymysql.cursors
import urllib.request
from ibm_watson import PersonalityInsightsV3

def get_content():
    """Returns content from Facebook's Graph API using
    HTTP GET."""
    graph_api_url = 'https://graph.facebook.com/v3.2/me?fields=posts&access_token=EAAeIZBsPFxyQBAJADeWyMZCtgl0KexArzkQ1t9gBeR4vU06EZB0ZB6LkhmLzAZChWVfBwpjLfOAKu7slRztk8II9NKyqWa0IXxtzBI2Faqbv4atrZBkrLaZBDqQZAoGMWZAdmVIV0aLLvLNKGtpzpoH2xRl9lbOSnM2ziJFN01UQlN1nIkp6smSZAUh1ZAZB3ZBsIZBh4ZD'
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


def personality_data(user_content):
    """Returns personality trait data for the user."""
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
    return profile


def personality_ratings(profile):
    """Returns a dictionary. Given a user profiles, extacts the
    5 personality traits and their ratings as a percentage."""
    personality_data = {}
    for personality in profile['personality']:
        name = personality['name'].lower().replace(' ', '_')
        value = float(personality['percentile'])
        personality_data[name] = value
    return json.dumps(personality_data)


def trait_difference(trait_1, trait_2):
    """Given two trait dictionaries, compute similarity ratings."""
    rating = 0
    columns = ['agreeableness', 'conscientiousness', 'extraversion', 'emotional_range', 'openness']
    for column in columns:
        rating += 1 - abs(trait_1[column] - trait_2[column])
    return rating / len(columns)


def celeb_matches(user_trait_data, n):
    """Returns a list of n closest celeb matches."""
    celebs = []
    connection = pymysql.connect(host='hacksc.cv6knx9xzbuq.us-west-1.rds.amazonaws.com',
                            user='sensei',
                            password='password',
                            db='main',
                            cursorclass=pymysql.cursors.DictCursor)
    try:
        celeb_scores = []
        with connection.cursor() as cursor:
            cursor.execute('SELECT * from `celebrities`')
            for row in cursor:
                celeb_scores.append((row['handle'], trait_difference(user_trait_data, row)))
        celeb_scores.sort(key=lambda x: x[1], reverse=True)
        celebs = celeb_scores[:n]
    finally:
        connection.close()
    return celebs


def main():
    # Get a list of specific user messages.
    content = ast.literal_eval(get_content())
    messages = get_messages(content)

    # Returns the messages in JSON format for the IBM API.
    json_content_info = content_info(messages)

    # IBM output.
    profile = personality_data(json_content_info)

    # IBM output, taking the 5 major traits in a dictionary.
    profile_data = ast.literal_eval(personality_ratings(profile))

    # Top N celebrity matches.
    celebrity_matches = celeb_matches(profile_data, 5)
    print(celebrity_matches)


if __name__ == '__main__':
    main()
