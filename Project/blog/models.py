from py2neo import Graph, Node, Relationship
from passlib.hash import bcrypt
from datetime import datetime
import os, random
import uuid

url = os.environ.get('GRAPHENEDB_URL', 'http://localhost:7474')
username = os.environ.get('NEO4J_USERNAME')
password = os.environ.get('NEO4J_PASSWORD')

graph = Graph(url + '/db/data/', username=username, password=password)

class User:
    def __init__(self, username):
        self.username = username

    def find(self):
        """Finds the current User"""
        user = graph.find_one('User', 'username', self.username)
        return user

    def register(self, password):
        """Checks if the user already exists. If user exists, return False.
        If user does not exist, create user and return true."""
        if not self.find():
            user = Node('User', username=self.username, password=bcrypt.encrypt(password), bio="Cool person!", upvote=0, url="default" + str(random.randint(0, 10)) + ".jpg")
            graph.create(user)
            return True
        else:
            return False

    def change_pic_url(self, saved_path):
        """Change the URL link to the user's profile picture."""
        user = self.find()
        graph.run("MERGE (n:User {username: {username}}) SET n.url = {picurl}",
        {"username": self.username, "picurl": saved_path})

    def get_pic_url(self):
        """Gets the URL link to the user's profile picture."""
        user = self.find()
        query = '''
	       MATCH (u:User)
	       WHERE u.username = {username}
	       RETURN u.url
	    '''
        pp_url = graph.run(query, username=self.username).data()
        return pp_url[0]["u.url"]

    def get_bio(self):
        """Gets the user's bio."""
        user = self.find()
        query = '''
            MATCH (u:User)
            WHERE u.username = {username}
            RETURN u.bio
        '''
        user_bio = graph.run(query, username=self.username).data()
        return user_bio[0]["u.bio"]

    def change_bio(self, new_bio):
        """Changes the user's bio."""
        user = self.find()
        graph.run("MERGE (n:User {username: {username}}) SET n.bio = {bio}",
        {"username": self.username, "bio": new_bio})

    def change_password(self, password):
        """Changes the user's password, encrypting the password with bcrypt."""
        user = self.find()
        graph.run("MERGE (n:User {username: {username}}) SET n.password = {password}",
        {"username": self.username, "password": bcrypt.encrypt(password)})


    def verify_password(self, password):
        """Uses bcrypt to verify if the given String matches the user's password."""
        user = self.find()
        if user:
            return bcrypt.verify(password, user['password'])
        else:
            return False



    def addTags(self, tags):
        """Creates a relationship between the user and the given tags.
        Tags are sent as a String, seperated with a " ", example "Tag1 Tag2"."""
        user = self.find()
        tags = [x.strip() for x in tags.lower().split(' ')]
        for name in set(tags):
            tag = Node('Tag', name=name)
            graph.merge(tag)
            rel = Relationship(tag, 'TAGGED', user)
            graph.create(rel)

    def removeTags(self, tags):
        """Removes all relationships the user has with any tags."""
        user = self.find()
        query = '''
        MATCH (:Tag)-[r:TAGGED]-(user:User)
        WHERE user.username = {username}
        DELETE r
        '''
        graph.run(query, username=self.username)


    def add_question(self, title, tags, text):
        """Creates a question, and then creates a relationship between the user
        and the question, where User - PUBLISHED -> Question. Then all the tags
        are linked to the question as well."""
        user = self.find()
        question = Node(
            'Question',
            id=str(uuid.uuid4()),
            title=title,
            text=text,
            timestamp=timestamp(),
            date=date(),
            update_timestamp=timestamp(),
            update_date=date(),
            upvote=0
        )
        rel = Relationship(user, 'PUBLISHED', question)
        graph.create(rel)
        tags = [x.strip() for x in tags.lower().split(' ')]
        for name in set(tags):
            tag = Node('Tag', name=name)
            graph.merge(tag)
            rel = Relationship(tag, 'TAGGED', question)
            graph.create(rel)

    def update_question(self, question_id):
        """Updates a timestamp inside the question with id=question_id. Used to
        determine when last a question was modified."""
        user = self.find()
        graph.run("MERGE (n:Question {id: {question_id}}) SET n.update_timestamp = {timestamp}, n.update_date = {date}",
        {"question_id": question_id, "timestamp": timestamp(), "date": date()})

    def add_answer(self, question_id, text):
        """Creates an Answer node, and relates it to the user. Then relates it to
        the question with id=question_id."""
        user = self.find()
        answer = Node(
            'Answer',
            id=str(uuid.uuid4()),
            text=text,
            timestamp=timestamp(),
            date=date()
        )
        rel = Relationship(user, 'PUBLISHED', answer)
        graph.create(rel)
        question = graph.find_one('Question', 'id', question_id)
        rel = Relationship(answer, 'ANSWERED', question)
        graph.create(rel)
        self.update_question(question_id)

    def follow_user(self, username_him):
        """Creates a one-way follow relationship between this user and another,
        with relation self - FOLLOW -> other."""
        user_me=self.find()
        user_him=do_search(username_him)
        rel = Relationship(user_me, 'FOLLOW', user_him)
        graph.create(rel)

    def suggest_follow(self):
        """Finds all users which are followed by the users this users follow, if
        this user does not follow them. Users are ranked via total amount of upvotes."""
        query = '''
            MATCH (user:User)-[:FOLLOW]->(:User)-[:FOLLOW]->(n:User)
            WHERE user.username = {username} AND NOT (user:User)-[:FOLLOW]->(n:User) AND NOT user=n
            RETURN n.username AS username
            ORDER BY n.upvote DESC
        '''
        return graph.run(query, username=self.username)

    def bookmark_question(self, question_id):
        """Creats a bookmark relationship between this user and question with
        id=question_id."""
        user = self.find()
        question = graph.find_one('Question', 'id', question_id)
        graph.merge(Relationship(user, 'BOOKMARK', question))

    def upvote_answer(self, answer_id):
        """If an answer is upvoted, the question the answer is directed at is found
        and its total upvotes is incremented. Then the user who published the answer
        is found and its total upvotes is incremented. This is done to mark ranking via
        upvote easier. Then finally a relationship is created between this user
        and the answer: self - UPVOTE -> answer."""
        user = self.find()
        answer = graph.find_one('Answer', 'id', answer_id)
        query = '''
	       MATCH (a:Answer)-[:ANSWERED]-(q:Question)
	       WHERE a.id = {answer_id}
	       RETURN q.id
	    '''
        question = graph.run(query, answer_id=answer_id).data()
        graph.run("MERGE (n:Question {id: {question_id}}) SET n.upvote=n.upvote+1",
        {"question_id": question[0]["q.id"]})
        query = '''
	       MATCH (a:Answer)-[:PUBLISHED]-(u:User)
	       WHERE a.id = {answer_id}
	       RETURN u.username
	    '''
        use_id = graph.run(query, answer_id=answer_id).data()
        graph.run("MERGE (n:User {username: {username}}) SET n.upvote=n.upvote+1",
        {"username": use_id[0]["u.username"]})
        graph.merge(Relationship(user, 'UPVOTE', answer))

    def bookmark_question(self, question_id):
        """Creates a bookmark relationship between a user and a question."""
        user = self.find()
        question = graph.find_one('Question', 'id', question_id)
        graph.merge(Relationship(user, 'BOOKMARK', question))



    def get_recent_questions(self):
        """Finds all questions this user has published, ranks them according
        to time, and delivers the latest 5."""
        query = '''
            MATCH (user:User)-[:PUBLISHED]->(question:Question)<-[:TAGGED]-(tag:Tag)
            WHERE user.username = {username}
            RETURN user.username AS username, question, COLLECT(tag.name) AS tags
            ORDER BY question.date DESC, question.timestamp DESC LIMIT 5
        '''
        return graph.run(query, username=self.username)

    def get_bookmarks(self):
        """Gets all the questions this user has bookmarked, and their tags. Then
        gets the users who published those questions."""
        query = '''
            MATCH (user:User)-[:BOOKMARK]-(question:Question)<-[:TAGGED]-(tag:Tag)
            MATCH (question:Question) -[:PUBLISHED] - (u:User)
            WHERE user.username = {username}
            RETURN u.username AS username, question, COLLECT(tag.name) AS tags
            ORDER BY question.timestamp DESC
        '''
        return graph.run(query, username=self.username)



    def get_timeline(self):
        """Step 1: Find all questions posted by those this user is following.
        Step 2: Store the user, question and tag data in a list for use in the next query.
        Step 3: Find all questions posted that are linked to this user via a tag.
        Step 4: Store the user, question and tag data in a list, and add it to previous lists.
        Step 5: Unwind all lists back into records.
        Step 6: Remove duplicates by ensuring only records where a user published that question
                gets selected.
        Step 7: Return data, ordered as most recently modified, either via being asked or answered,
                as highest.
        """
        query = '''
            MATCH (u:User) -[:FOLLOW] -> (user:User) - [:PUBLISHED] -(question:Question)
            MATCH (question:Question) - [:TAGGED] - (tag:Tag)
            WHERE u.username={username} AND NOT u=user
            WITH  COLLECT(user) AS use, COLLECT(question) AS quest, COLLECT(tag) AS t
            MATCH (u:User) -[:TAGGED] - (:Tag) -[:TAGGED] - (question:Question) - [:PUBLISHED] - (user:User)
            MATCH (question:Question) - [:TAGGED] - (tag:Tag)
            WHERE u.username={username} AND NOT u=user
            WITH use + COLLECT(user) AS use, quest +  COLLECT(question) AS quest2, t+COLLECT(tag) as t2
            UNWIND quest2 AS question
            UNWIND use AS user
            UNWIND t2 AS tag
            WITH DISTINCT user, question, tag
            WHERE (user:User) - [:PUBLISHED] -(question:Question)
            RETURN distinct user.username AS username, question, COLLECT(tag.name) AS tags
            ORDER BY question.update_date, question.update_timestamp DESC LIMIT 10
        '''

        return graph.run(query, username=self.username)

    def get_voteline(self):
        """Step 1: Find all questions posted by those this user is following.
        Step 2: Store the user, question and tag data in a list for use in the next query.
        Step 3: Find all questions posted that are linked to this user via a tag.
        Step 4: Store the user, question and tag data in a list, and add it to previous lists.
        Step 5: Unwind all lists back into records.
        Step 6: Remove duplicates by ensuring only records where a user published that question
                gets selected.
        Step 7: Return data, ordered as question with most upvotes being highest.
        """
        query = '''
            MATCH (u:User) -[:FOLLOW] -> (user:User) - [:PUBLISHED] -(question:Question)
            MATCH (question:Question) - [:TAGGED] - (tag:Tag)
            WHERE u.username={username} AND NOT u=user
            WITH  COLLECT(user) AS use, COLLECT(question) AS quest, COLLECT(tag) AS t
            MATCH (u:User) -[:TAGGED] - (:Tag) -[:TAGGED] - (question:Question) - [:PUBLISHED] - (user:User)
            MATCH (question:Question) - [:TAGGED] - (tag:Tag)
            WHERE u.username={username} AND NOT u=user
            WITH use + COLLECT(user) AS use, quest +  COLLECT(question) AS quest2, t+COLLECT(tag) as t2
            UNWIND quest2 AS question
            UNWIND use AS user
            UNWIND t2 AS tag
            WITH DISTINCT user, question, tag
            WHERE (user:User) - [:PUBLISHED] -(question:Question)
            RETURN distinct user.username AS username, question, COLLECT(tag.name) AS tags
            ORDER BY question.upvote DESC LIMIT 10
        '''
        return graph.run(query, username=self.username)

    def get_following_feed(self):
        """Step 1: Find all questions posted by those this user is following.
        Step 2: Store the user, question and tag data in a list for use in the next query.
        Step 3: Find all questions posted that are linked to this user via a tag.
        Step 4: Store the user, question and tag data in a list, and add it to previous lists.
        Step 5: Unwind all lists back into records.
        Step 6: Remove duplicates by ensuring only records where a user published that question
                gets selected.
        Step 7: Return data, ordered as question with most upvotes being highest.
        """
        query = '''
            MATCH (u:User) -[:FOLLOW] -> (:User) -[:FOLLOW] -> (user:User) - [:PUBLISHED] -(question:Question)
            MATCH (question:Question) - [:TAGGED] - (tag:Tag)
            WHERE u.username={username} AND NOT u=user
            WITH  COLLECT(user) AS use, COLLECT(question) AS quest, COLLECT(tag) AS t
            MATCH (u:User) -[:FOLLOW] -> (:User) -[:TAGGED] - (:Tag) -[:TAGGED] - (question:Question) - [:PUBLISHED] - (user:User)
            MATCH (question:Question) - [:TAGGED] - (tag:Tag)
            WHERE u.username={username} AND NOT u=user
            WITH use + COLLECT(user) AS use, quest +  COLLECT(question) AS quest2, t+COLLECT(tag) as t2
            UNWIND quest2 AS question
            UNWIND use AS user
            UNWIND t2 AS tag
            WITH DISTINCT user, question, tag
            WHERE (user:User) - [:PUBLISHED] -(question:Question)
            RETURN distinct user.username AS username, question, COLLECT(tag.name) AS tags
            ORDER BY question.upvote DESC LIMIT 10
        '''
        return graph.run(query, username=self.username)

    def test_follow(self, user_him):
        """Tests to see if this user is following another user."""
        user_me = self.find()
        user_him = graph.find_one('User', 'username', user_him)
        Find = graph.match_one(start_node=user_me, rel_type='FOLLOW', end_node=user_him)
        if (type(Find) == Relationship):
            return True
        else:
            return False

    def get_similar_users(self):
        """Find three users who are most similar to the logged-in user
        based on tags they've both blogged about. Came from tutorial."""
        query = '''
            MATCH (you:User)-[:PUBLISHED]->(:Question)<-[:TAGGED]-(tag:Tag),
                (they:User)-[:PUBLISHED]->(:Question)<-[:TAGGED]-(tag)
            WHERE you.username = {username} AND you <> they
            WITH they, COLLECT(DISTINCT tag.name) AS tags
            ORDER BY SIZE(tags) DESC LIMIT 3
            RETURN they.username AS similar_user, tags
        '''
        return graph.run(query, username=self.username)

    def get_commonality_of_user(self, other):
        """Find how many of the logged-in user's posts the other user
        has liked and which tags they've both blogged about. Came from tutorial."""
        query = '''
        MATCH (they:User {username: {they} })
        MATCH (you:User {username: {you} })
        OPTIONAL MATCH (they)-[:PUBLISHED]->(:Question)<-[:TAGGED]-(tag:Tag),
                       (you)-[:PUBLISHED]->(:Question)<-[:TAGGED]-(tag)
        RETURN SIZE((they)-[:LIKED]->(:Question)<-[:PUBLISHED]-(you)) AS likes,
               COLLECT(DISTINCT tag.name) AS tags
        '''
        return graph.run(query, they=other.username, you=self.username).next




def get_todays_recent_questions():
    """Gets the most recent questions published, regardless of who posted them."""
    query = '''
        MATCH (user:User)-[:PUBLISHED]->(question:Question)<-[:TAGGED]-(tag:Tag)
        WHERE question.date = {today}
        RETURN user.username AS username, question, COLLECT(tag.name) AS tags
        ORDER BY question.timestamp DESC LIMIT 5
    '''
    return graph.run(query, today=date())

def get_question(question_id):
    """Gets data about the question with id=question_id, including data outside
    the question node, such as who posted it and the tagged tags."""
    query = '''
        MATCH (user:User)-[:PUBLISHED]->(question:Question)<-[:TAGGED]-(tag:Tag)
        WHERE question.id = {question_id}
        RETURN user.username AS username, question, COLLECT(tag.name) AS tags
        ORDER BY question.timestamp DESC LIMIT 5
    '''
    return graph.run(query, question_id=question_id)

def get_answers(question_id):
    """Gets all the answers to a question with id=question_id, including the posting user."""
    query = '''
        MATCH (user:User)-[:PUBLISHED]-(question:Question)-[:ANSWERED]-(answer:Answer) - [:PUBLISHED] - (u:User)
        WHERE question.id = {question_id}
        RETURN u.username AS username, answer
        ORDER BY question.up, question.timestamp DESC
    '''
    return graph.run(query, question_id=question_id)

def do_search(username):
    """Searches for and returns a user with username=username."""
    user = graph.find_one('User', 'username', username)
    return user

def timestamp():
    """Generic timestamp"""
    epoch = datetime.utcfromtimestamp(0)
    now = datetime.now()
    delta = now - epoch
    return delta.total_seconds()

def date():
    """Generic date."""
    return datetime.now().strftime('%Y-%m-%d')
