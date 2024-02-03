from googleapiclient.discovery import build
import pymongo
import psycopg2 
import pandas as pd
import streamlit as st

#API key connection 

def Api_connect():
    Api_Id= "AIzaSyCVuwqSXvVQy_8L2Ism7uqRZq8ijmZJZ-w"
    
    api_service_name = "youtube"

    api_version = "v3"

    youtube = build(api_service_name, api_version, developerKey= Api_Id )

    return youtube

youtube= Api_connect()

#get channel information 

def get_channel_info(channel_id):

        request= youtube.channels().list(
                part="snippet,contentDetails,Statistics",
                id=channel_id
                )
        response1=request.execute()
        
        for i in range(0,len(response1['items'])):
                data=dict(
                        Channel_Name=response1["items"][i]["snippet"]["title"],
                        Channel_Id=response1["items"][i]["id"],
                        Subscription_Count=response1["items"][i]["statistics"]["subscriberCount"],
                        Views=response1["items"][i]["statistics"]["viewCount"],
                        Total_Videos=response1["items"][i]["statistics"]["videoCount"],
                        Channel_Description=response1["items"][i]["snippet"]["description"],
                        Playlist_Id=response1["items"][i]["contentDetails"]["relatedPlaylists"]["uploads"])
        return(data)
        

#get video ids

def get_channel_videos(channel_id):
    video_ids = []
    # get Uploads playlist id
    res = youtube.channels().list(id=channel_id, 
                                  part='contentDetails').execute()
    playlist_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    next_page_token = None
    
    while True:
        res = youtube.playlistItems().list( 
                                           part = 'snippet',
                                           playlistId = playlist_id, 
                                           maxResults = 50,
                                           pageToken = next_page_token).execute()
        
        for i in range(len(res['items'])):
            video_ids.append(res['items'][i]['snippet']['resourceId']['videoId'])
        next_page_token = res.get('nextPageToken')
        
        if next_page_token is None:
            break
    return video_ids


#get video information

def get_video_info(video_ids):

    video_data = []

    for video_id in video_ids:
        request = youtube.videos().list(
                    part="snippet,contentDetails,statistics",
                    id= video_id)
        response = request.execute()

        for item in response["items"]:
            data = dict(Channel_Name = item['snippet']['channelTitle'],
                        Channel_Id = item['snippet']['channelId'],
                        Video_Id = item['id'],
                        Title = item['snippet']['title'],
                        Tags = item['snippet'].get('tags'),
                        Thumbnail = item['snippet']['thumbnails']['default']['url'],
                        Description = item['snippet']['description'],
                        Published_Date = item['snippet']['publishedAt'],
                        Duration = item['contentDetails']['duration'],
                        Views = item['statistics']['viewCount'],
                        Likes = item['statistics'].get('likeCount'),
                        Comments = item['statistics'].get('commentCount'),
                        Favorite_Count = item['statistics']['favoriteCount'],
                        Definition = item['contentDetails']['definition'],
                        Caption_Status = item['contentDetails']['caption']
                        )
            video_data.append(data)
    return video_data

#get comment information
def get_comment_info(video_ids):
        Comment_Information = []
        try:
                for video_id in video_ids:

                        request = youtube.commentThreads().list(
                                part = "snippet",
                                videoId = video_id,
                                maxResults = 50
                                )
                        response5 = request.execute()
                        
                        for item in response5["items"]:
                                comment_information = dict(
                                        Comment_Id = item["snippet"]["topLevelComment"]["id"],
                                        Video_Id = item["snippet"]["videoId"],
                                        Comment_Text = item["snippet"]["topLevelComment"]["snippet"]["textOriginal"],
                                        Comment_Author = item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
                                        Comment_Published = item["snippet"]["topLevelComment"]["snippet"]["publishedAt"])

                                Comment_Information.append(comment_information)
        except:
                pass
                
        return Comment_Information

#connect to mongoDB

client=pymongo.MongoClient("mongodb://localhost:27017")
db=client["Youtube_data"]

def channel_details(channel_id):
    ch_details = get_channel_info(channel_id)
    vi_ids = get_channel_videos(channel_id)
    vi_details = get_video_info(vi_ids)
    com_details = get_comment_info(vi_ids)

    coll1 = db["channel_details"]
    coll1.insert_one({"channel_information":ch_details,"video_information":vi_details,
                    "comment_information":com_details})

    return "upload completed successfully"
    

def data_into_sql(c_id):
    #fetching data from mongodb

    coll1 = db["channel_details"]
    data = coll1.find_one({"channel_information.Channel_Id":c_id})

    mydb = psycopg2.connect(host="localhost",
            user="postgres",
            password="3000",
            database= "youtube_data",
            port = "5432"
            )
    cursor = mydb.cursor()

    val =tuple( data["channel_information"].values())
    insert_query = '''INSERT into channels(Channel_Name,
                                                        Channel_Id,
                                                        subscribers,
                                                        Views,
                                                        Total_Videos,
                                                        Channel_Descriptions,
                                                        Playlist_Id)
                                            VALUES(%s,%s,%s,%s,%s,%s,%s)'''

    cursor.execute(insert_query,val)
    mydb.commit()

    insert_query = '''
                INSERT into videos (Channel_Name,
                Channel_Id,
                Video_Id, 
                Title, 
                Tags,
                Thumbnail,
                Description, 
                Published_at,
                Duration, 
                Views, 
                like_count,
                Comment_count,
                Favorite_Count, 
                Definition, 
                Caption_Status 
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)'''

    for i in data["video_information"]:
        val = tuple(i.values())
        cursor.execute(insert_query,val)
        mydb.commit()

    insert_query = '''
                INSERT INTO comments (Comment_Id,
                                      Video_Id ,
                                      Comment_Text,
                                      Comment_Author,
                                      Comment_Publishedat)
                VALUES (%s, %s, %s, %s, %s)'''

    for i in data["comment_information"]:
        val = tuple(i.values())
        cursor.execute(insert_query,val)
        mydb.commit()
    
def channels_table():
    ch_list = []
    db = client["Youtube_data"]
    coll1 = db["channel_details"] 
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    channels_table = st.dataframe(ch_list)
    return channels_table

def videos_table():
    vi_list = []
    db = client["Youtube_data"]
    coll2 = db["channel_details"]
    for vi_data in coll2.find({},{"_id":0,"video_information":1}):
        for i in range(len(vi_data["video_information"])):
            vi_list.append(vi_data["video_information"][i])
    videos_table = st.dataframe(vi_list)
    return videos_table

def comments_table():
    com_list = []
    db = client["Youtube_data"]
    coll3 = db["channel_details"]
    for com_data in coll3.find({},{"_id":0,"comment_information":1}):
        for i in range(len(com_data["comment_information"])):
            com_list.append(com_data["comment_information"][i])
    comments_table = st.dataframe(com_list)
    return comments_table

def tables():
    channels_table()
    videos_table()
    comments_table()
    return "Tables Created successfully"

with st.sidebar:
    st.title(":yellow[YOUTUBE DATA HARVESTING AND WAREHOUSING]")

    
c_id = st.text_input("Enter the Channel id")
channels = c_id.split(',')
channels = [ch.strip() for ch in channels if ch]

if st.button("Collect and Store data"):
    for channel in channels:
        ch_ids = []
        db = client["Youtube_data"]
        coll1 = db["channel_details"]
        for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
            ch_ids.append(ch_data["channel_information"]["Channel_Id"])
        if channel in ch_ids:
            st.success("Channel details of the given channel id: " + channel + " already exists")
        else:
            output = channel_details(channel)
            st.success(output)
            
if st.button("Migrate to SQL"):
    display = tables()
    st.success(display)
    
show_table = st.radio("SELECT THE TABLE FOR VIEW",("channels","videos","comments"))

if show_table == "channels":
    channels_table()
elif show_table =="videos":
    videos_table()
elif show_table == "comments":
    comments_table()

mydb = psycopg2.connect(host="localhost",
            user="postgres",
            password="3000",
            database= "youtube_data",
            port = "5432"
            )
cursor = mydb.cursor()
    
question = st.selectbox(
    'Please Select Your Question',
    ('1. All the videos and the Channel Name',
     '2. Channels with most number of videos',
     '3. 10 most viewed videos',
     '4. Comments in each video',
     '5. Videos with highest likes',
     '6. likes of all videos',
     '7. views of each channel',
     '8. videos published in the year 2022',
     '9. average duration of all videos in each channel',
     '10. videos with highest number of comments'))

if question == '1. All the videos and the Channel Name':
    query1 = "select Title as videos, Channel_Name as ChannelName from videos;"
    cursor.execute(query1)
    mydb.commit()
    t1=cursor.fetchall()
    st.write(pd.DataFrame(t1, columns=["Video Title","Channel Name"]))

elif question == '2. Channels with most number of videos':
    query2 = "select Channel_Name as ChannelName,Total_Videos as NO_Videos from channels order by Total_Videos desc;"
    cursor.execute(query2)
    mydb.commit()
    t2=cursor.fetchall()
    st.write(pd.DataFrame(t2, columns=["Channel Name","No Of Videos"]))

elif question == '3. 10 most viewed videos':
    query3 = '''select Views as views , Channel_Name as ChannelName,Title as VideoTitle from videos 
                        where Views is not null order by Views desc limit 10;'''
    cursor.execute(query3)
    mydb.commit()
    t3 = cursor.fetchall()
    st.write(pd.DataFrame(t3, columns = ["views","channel Name","video title"]))

elif question == '4. Comments in each video':
    query4 = "select Comments as No_comments,Title as VideoTitle from videos where Comments is not null;"
    cursor.execute(query4)
    mydb.commit()
    t4=cursor.fetchall()
    st.write(pd.DataFrame(t4, columns=["No Of Comments", "Video Title"]))

elif question == '5. Videos with highest likes':
    query5 = '''select Title as VideoTitle, Channel_Name as ChannelName, Likes as LikesCount from videos 
                       where Likes is not null order by Likes desc;'''
    cursor.execute(query5)
    mydb.commit()
    t5 = cursor.fetchall()
    st.write(pd.DataFrame(t5, columns=["video Title","channel Name","like count"]))

elif question == '6. likes of all videos':
    query6 = '''select Likes as likeCount,Title as VideoTitle from videos;'''
    cursor.execute(query6)
    mydb.commit()
    t6 = cursor.fetchall()
    st.write(pd.DataFrame(t6, columns=["like count","video title"]))

elif question == '7. views of each channel':
    query7 = "select Channel_Name as ChannelName, Views as Channelviews from channels;"
    cursor.execute(query7)
    mydb.commit()
    t7=cursor.fetchall()
    st.write(pd.DataFrame(t7, columns=["channel name","total views"]))

elif question == '8. videos published in the year 2022':
    query8 = '''select Title as Video_Title, Published_Date as VideoRelease, Channel_Name as ChannelName from videos 
                where extract(year from Published_Date) = 2022;'''
    cursor.execute(query8)
    mydb.commit()
    t8=cursor.fetchall()
    st.write(pd.DataFrame(t8,columns=["Name", "Video Publised On", "ChannelName"]))

elif question == '9. average duration of all videos in each channel':
    query9 =  "SELECT Channel_Name as ChannelName, AVG(Duration) AS average_duration FROM videos GROUP BY Channel_Name;"
    cursor.execute(query9)
    mydb.commit()
    t9=cursor.fetchall()
    t9 = pd.DataFrame(t9, columns=['ChannelTitle', 'Average Duration'])
    T9=[]
    for index, row in t9.iterrows():
        channel_title = row['ChannelTitle']
        average_duration = row['Average Duration']
        average_duration_str = str(average_duration)
        T9.append({"Channel Title": channel_title ,  "Average Duration": average_duration_str})
    st.write(pd.DataFrame(T9))

elif question == '10. videos with highest number of comments':
    query10 = '''select Title as VideoTitle, Channel_Name as ChannelName, Comments as Comments from videos 
                       where Comments is not null order by Comments desc;'''
    cursor.execute(query10)
    mydb.commit()
    t10=cursor.fetchall()
    st.write(pd.DataFrame(t10, columns=['Video Title', 'Channel Name', 'NO Of Comments']))
