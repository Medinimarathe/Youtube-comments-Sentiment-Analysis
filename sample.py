# For Fetching Comments 
# -*- coding: utf-8 -*-
import html
import os
from flask import Flask, render_template, request
from googleapiclient.discovery import build 
# For filtering comments 
import re 
from langdetect import detect
# For filtering comments with just emojis 
import emoji
# Analyze the sentiments of the comment
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
# from nltk.sentiment.vader import SentimentIntensityAnalyzer
# For visualization 
import matplotlib.pyplot as plt
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
nltk.download('stopwords')
stop_words = stopwords.words('english')
wnl = WordNetLemmatizer()
API_KEY = 'AIzaSyAtEe86Cr_qWbBtsEIi5IAnwkabtko49eQ'
hyperlink_pattern = re.compile(
    r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
tags_remove_regex=re.compile(r'<.*?>')

app = Flask(__name__)
##########################
def returnytcomments(url):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    # Taking input from the user and slicing for video id
    # video_id = url[-11:]
    match= re.search(r'=(.*)',url)
    if match:
        video_id=match.group(1)
    print("video id: " + video_id)

    # Getting the channelId of the video uploader
    video_response = youtube.videos().list(
        part='snippet',
        id=video_id
    ).execute()
    #Splitting the response for channelID
    video_snippet = video_response['items'][0]['snippet']
    uploader_channel_id = video_snippet['channelId']
    print("channel id: " + uploader_channel_id)
    # Fetch comments
    print("Fetching Comments...")
    comments = []
    nextPageToken = None
    while len(comments) < 600:
        request = youtube.commentThreads().list(
            part='snippet',
            videoId=video_id,
            maxResults=100,  # You can fetch up to 100 comments per request
            pageToken=nextPageToken
        )
        response = request.execute()
        for item in response['items']:
            comment = item['snippet']['topLevelComment']['snippet']
            # Check if the comment is not from the video uploader
            if comment['authorChannelId']['value'] != uploader_channel_id:
                comments.append(comment['textDisplay'])
        nextPageToken = response.get('nextPageToken')
    
        if not nextPageToken:
            break

    return comments

def clean(org_comments):
    threshold_ratio = 0.65
 
    relevant_comments = []
    neutral_comments=[]
    
    # Inside your loop that processes comments
    for comment_text in org_comments:
        comment_text=html.unescape()
        comment_text = comment_text.lower().strip()
    
        emojis = emoji.emoji_count(comment_text)

        # remove tags if any from the comments
        if re.search(r'<.*?>', comment_text):
            # Remove tags
            comment_text = re.sub(r'<.*?>', "", comment_text)
            
        if not emoji.purely_emoji(comment_text):
            try:
                if detect(comment_text) != 'en':
                    comment_text=emoji.replace_emoji(comment_text,'')
                    if not comment_text.replace(' ','').isalpha():
                        neutral_comments.append(comment_text)
                        continue
            except Exception as e:
                 print("Language not detected")
        
        # Count text characters (excluding spaces)
        text_characters = len(re.sub(r'\s', '', comment_text))
    
        if (any(char.isalnum() for char in comment_text)) and not hyperlink_pattern.search(comment_text):
            if emojis == 0 or (text_characters / (text_characters + emojis)) > threshold_ratio:
                relevant_comments.append(comment_text)
    
    # Print the relevant comments
    # relevant_comments[:5]

    f = open("ytcomments.txt", 'w', encoding='utf-8')
    for idx, comment in enumerate(relevant_comments):
        f.write(str(comment)+"\n")
    f.close()
    print("Comments stored successfully!")
    return relevant_comments,neutral_comments

def sentiment_scores(comment, polarity):
 
    # Creating a SentimentIntensityAnalyzer object.
    sentiment_object = SentimentIntensityAnalyzer()
 
    sentiment_dict = sentiment_object.polarity_scores(comment)
    # polarity.append(sentiment_dict['compound'])
    polarity=sentiment_dict['compound']
 
    return polarity

def create_wordcloud(positive_comments,negative_comments,neutral_comments):
    # building our wordcloud and saving it
    

    positive_count = len(positive_comments)
    negative_count = len(negative_comments)
    neutral_count = len(neutral_comments)
    
    # labels and data for Bar chart
    labels = ['Positive', 'Negative', 'Neutral']
    comment_counts = [positive_count, negative_count, neutral_count]
    
    # Creating bar chart
    plt.bar(labels, comment_counts, color=['green', 'red', 'grey'])
    
    # Adding labels and title to the plot
    plt.xlabel('Sentiment')
    plt.ylabel('Comment Count')
    plt.title('Sentiment Analysis of Comments')
    # plt.tight_layout()
    # plt.figure(figsize=(30,20))
    CleanCache(directory='static/images')
    plt.savefig('static/images/woc.png')
    
    # Displaying the chart
    # plt.show()
    plt.close()
    
def returnsentiment(comment):
    polarity = []

    
    # f = open("ytcomments.txt", 'r', encoding='`utf-8')
    # comments = f.readlines()
    # f.close()
    print("Analysing Comments...")
    sentiment_object = SentimentIntensityAnalyzer()
 
    sentiment_dict = sentiment_object.polarity_scores(comment)
    # polarity.append(sentiment_dict['compound'])
    polarity=sentiment_dict['compound']
        # polarity = sentiment_scores(items, polarity)
    if polarity >= 0.05:
            sent = 'Positive'
    elif polarity <=- 0.05:
            sent = 'Negative'
    else:
            sent = 'Neutral'
    return polarity, sent


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/results',methods=['GET'])
def result():    
    url = request.args.get('url')
    
    org_comments = returnytcomments(url)
   
    clean_comments, neutral_comments_first = clean(org_comments)

    # create_wordcloud(clean_comments)
    
    np,nn,nne = 0,0,0

    predictions = []
    scores = []
    positive_comments = []
    negative_comments = []
    neutral_comments = []
    for value in neutral_comments_first:
        neutral_comments.append(value)
    f = open("ytcomments1.txt", 'w', encoding='utf-8')
    f.write(str(neutral_comments)+'\n')
    for i in clean_comments:
        score,sent = returnsentiment(i)
        scores.append(score)
        if sent == 'Positive':
            predictions.append('POSITIVE')
            np+=1
            positive_comments.append(i)
        elif sent == 'Negative':
            predictions.append('NEGATIVE')
            nn+=1
            negative_comments.append(i)
        else:
            predictions.append('NEUTRAL')
            nne+=1
            neutral_comments.append(i)
    f = open("ytcomments2.txt", 'w', encoding='utf-8')
    f.write(str(neutral_comments)+'\n')
    create_wordcloud(positive_comments,negative_comments,neutral_comments)

    avg_polarity = sum(scores)/len(scores)
    if avg_polarity>0.05:
        highest=1
    elif avg_polarity<-0.05:
        highest=-1
    else:
        highest=0
    max_polarity_cmnt=clean_comments[scores.index(max(scores))]
    min_polarity_cmnt=clean_comments[scores.index(max(scores))]

    dic = []
    y_len=len(negative_comments)
    y=0
    for i,cc in enumerate(clean_comments):
        x={}
        x['sent'] = predictions[i]
        x['clean_comment'] = cc
        x['org_comment'] = clean_comments[i]
        x['score'] = scores
        dic.append(x)

    f = open("ytcomments3.txt", 'w', encoding='utf-8')
    for i in dic:
        
        if y<=y_len:
            if i['sent']=='NEUTRAL':
                if i['org_comment'] != neutral_comments[y]:
                    i['neutral']=neutral_comments[y]
                    y+=1
                else:
                     i['neutral']=''

    for i in dic:
         f.write(str(i)+'\n')
    return render_template('result.html',n=len(clean_comments),nn=nn,np=np,nne=nne,dic=dic,highest=highest,max_polarity_cmnt=max_polarity_cmnt,min_polarity_cmnt=min_polarity_cmnt)
    


@app.route('/wc')
def wc():
    return render_template('wc.html')

class CleanCache:
	'''
	this class is responsible to clear any residual csv and image files
	present due to the past searches made.
	'''
	def __init__(self, directory=None):
		self.clean_path = directory
		# only proceed if directory is not empty
		if os.listdir(self.clean_path) != list():
			# iterate over the files and remove each file
			files = os.listdir(self.clean_path)
			for fileName in files:
				print(fileName)
				os.remove(os.path.join(self.clean_path,fileName))
		print("cleaned!")

if __name__ == '__main__':
    app.run(debug=True)