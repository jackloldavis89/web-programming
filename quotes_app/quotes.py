from flask import Flask, render_template, request, make_response, redirect
from mongita import MongitaClientDisk
from bson import ObjectId
from passwords import hash_password, check_password 
#hash_password(password) check_password(password, saved_hashed_password, salt)

app = Flask(__name__)

# create a mongita client connection
client = MongitaClientDisk()

# open the quotes database
quotes_db = client.quotes_db
session_db = client.session_db
user_db = client.user_db
comments_db = client.comments_db

import uuid

@app.route("/search", methods=["GET"])
def get_search_results():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    session_collection = session_db.session_collection
    # get the data for this session
    session_data = list(session_collection.find({"session_id": session_id}))[0]
    # open the quotes collection
    quotes_collection = quotes_db.quotes_collection
    # load the data
    data = list(quotes_collection.find({}))
    filtered_data = []
    for item in data:
        item["_id"] = str(item["_id"])
        item["object"] = ObjectId(item["_id"])
        item["comments"] = list(comments_db.comments_collection.find({"quote_id": item["_id"]}))[::-1]
        if item["access"] == "Private" and item["owner"] != session_data["user"]:
            print("Private quote, not displayed")
        else:
            if request.args.get("phrase") in item["text"]:
                filtered_data.append(item)

    html = render_template(
        "quotes.html",
        data=filtered_data[::-1],
        user=session_data["user"],
        page="Search",
    )
    response = make_response(html)
    response.set_cookie("session_id", session_id)
    return response

@app.route("/", methods=["GET"])
@app.route("/quotes", methods=["GET"])
@app.route("/myquotes", methods=["GET"])
def get_quotes():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    # open the session collection
    session_collection = session_db.session_collection
    # get the data for this session
    session_data = list(session_collection.find({"session_id": session_id}))
    if len(session_data) == 0:
        response = redirect("/logout")
        return response
    assert len(session_data) == 1
    session_data = session_data[0]
    # get some information from the session
    user = session_data.get("user", "unknown user")
    # open the quotes collection
    quotes_collection = quotes_db.quotes_collection
    # load the data
    rule = request.url_rule
    page_display = ""
    data = []
    if rule.rule == "/myquotes":
        data = list(quotes_collection.find({"owner": user}))
        page_display = "My Quotes"
    if rule.rule == "/quotes":
        data = list(quotes_collection.find({"access":"Public"}))
        page_display = "Public"
    for item in data:
        item["_id"] = str(item["_id"])
        item["object"] = ObjectId(item["_id"])
        item["comments"] = list(comments_db.comments_collection.find({"quote_id": item["_id"]}))[::-1]
    # display the data
    html = render_template(
        "quotes.html",
        data=data[::-1],
        user=user,
        page=page_display,
    )
    response = make_response(html)
    response.set_cookie("session_id", session_id)
    return response

@app.route("/register", methods=["GET"])
def get_register():
    session_id = request.cookies.get("session_id", None)
    if session_id:
        return redirect("/quotes")
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def post_register():
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    # open the user collection
    user_collection = user_db.user_collection
    user_data = list(user_collection.find({"user": user}))
    if len(user_data) != 0: #if user already exists
        response = redirect("/register")
        response.delete_cookie("session_id")
        return response
    #hash_password(password) check_password(password, saved_hashed_password, salt)
    hashed_password, salt = hash_password(password)
    user_data = {"user": user, "hashed_pass": hashed_password, "salt": salt}
    user_collection.insert_one(user_data)
    print(user_collection.find_one({"hashed_pass": hashed_password}))
    session_id = str(uuid.uuid4())
    # open the session collection
    session_collection = session_db.session_collection
    # insert the user
    session_collection.delete_one({"session_id": session_id})
    session_data = {"session_id": session_id, "user": user}
    session_collection.insert_one(session_data)
    response = redirect("/quotes")
    response.set_cookie("session_id", session_id)
    return response

@app.route("/login", methods=["GET"])
def get_login():
    session_id = request.cookies.get("session_id", None)
    print("Pre-login session id = ", session_id)
    if session_id:
        return redirect("/quotes")
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def post_login():
    user = request.form.get("user", "")
    password = request.form.get("password", "")
    # open the user collection
    user_collection = user_db.user_collection
    # look for the user
    user_data = list(user_collection.find({"user": user}))
    if len(user_data) != 1: #if user not found, or more than one user found
        response = redirect("/register")
        response.delete_cookie("session_id")
        return response
    if(check_password(password, user_data[0]["hashed_pass"], user_data[0]["salt"]) == False): #if password is wrong
        response = redirect("/login")
        response.delete_cookie("session_id")
        return response
    #if all checks (user and password) have passed
    session_id = str(uuid.uuid4())
    # open the session collection
    session_collection = session_db.session_collection
    # insert the user
    session_collection.delete_one({"session_id": session_id})
    session_data = {"session_id": session_id, "user": user}
    session_collection.insert_one(session_data)
    response = redirect("/quotes")
    response.set_cookie("session_id", session_id)
    return response


@app.route("/logout", methods=["GET"])
def get_logout():
    # get the session id
    session_id = request.cookies.get("session_id", None)
    if session_id:
        # open the session collection
        session_collection = session_db.session_collection
        # delete the session
        session_collection.delete_one({"session_id": session_id})
    response = redirect("/login")
    response.delete_cookie("session_id")
    return response

@app.route("/comment", methods=["POST"])
def post_comment():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    # open the session collection
    session_collection = session_db.session_collection
    # get the data for this session
    session_data = list(session_collection.find({"session_id": session_id}))
    if len(session_data) == 0:
        response = redirect("/logout")
        return response
    assert len(session_data) == 1
    session_data = session_data[0]
    # get some information from the session
    user = session_data.get("user", "unknown user")
    text = request.form.get("text", "")
    quote_id = request.form.get("quoteID", "")
    if text != "" and quote_id != "":
        #if quote owner
        quote_collection = quotes_db.quotes_collection
        quote = quote_collection.find_one({"_id": quote_id})
        # open the comments collection
        comments_collection = comments_db.comments_collection
        # insert the comment
        print(quote)
        if quote["allow_comments"] == "true":
            comment_data = {"owner": user, "text": text, "quote_id": quote_id}
            comments_collection.insert_one(comment_data)
            print(comment_data)
        else:
            print("Comments not allowed for this quote")
    # usually do a redirect('....')
    page = request.form.get("page", "")
    if page == "My Quotes":
        return redirect("/myquotes")
    else:
        return redirect("/quotes")

@app.route("/add", methods=["POST"])
def post_add():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    # open the session collection
    session_collection = session_db.session_collection
    # get the data for this session
    session_data = list(session_collection.find({"session_id": session_id}))
    if len(session_data) == 0:
        response = redirect("/logout")
        return response
    assert len(session_data) == 1
    session_data = session_data[0]
    # get some information from the session
    user = session_data.get("user", "unknown user")
    text = request.form.get("text", "")
    author = request.form.get("author", "")
    access = request.form.get("access", "")
    allow_comments = request.form.get("allowComments", "false")
    if text != "" and author != "" and access != "":
        # open the quotes collection
        quotes_collection = quotes_db.quotes_collection
        # insert the quote
        quote_data = {"owner": user, "text": text, "author": author, "access": access, "allow_comments": allow_comments}
        print(quote_data)
        quotes_collection.insert_one(quote_data)
    # usually do a redirect('....')
    if access == "Private":
        return redirect("/myquotes")
    else:
        return redirect("/quotes")

@app.route("/edit", methods=["POST"])
def post_edit():
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    _id = request.form.get("_id", None)
    text = request.form.get("text", "")
    author = request.form.get("author", "")
    access = request.form.get("access", "")
    allow_comments = request.form.get("allowComments", "")
    if _id:
        session_collection = session_db.session_collection
        session_data = list(session_collection.find({"session_id": session_id}))
        session_data = session_data[0]
        user = session_data.get("user", "unknown user")
        # open the quotes collection
        quotes_collection = quotes_db.quotes_collection
        quote = quotes_db.quotes_collection.find_one({"_id": ObjectId(_id)})
        # update the values in this particular record
        if user == quote["owner"]:
            values = {"$set": {"text": text, "author": author, "access": access, "allow_comments": allow_comments}}
            print(values)
            data = quotes_collection.update_one({"_id": ObjectId(_id)}, values)
    # do a redirect('....')
    if access == "Private":
        return redirect("/myquotes")
    else:
        return redirect("/quotes")


@app.route("/delete", methods=["GET"])
@app.route("/delete/<id>", methods=["GET"])
def get_delete(id=None):
    session_id = request.cookies.get("session_id", None)
    print(request)
    if not session_id:
        response = redirect("/login")
        return response
    if id:
        session_collection = session_db.session_collection
        session_data = list(session_collection.find({"session_id": session_id}))
        session_data = session_data[0]
        user = session_data.get("user", "unknown user")
        # open the quotes collection
        quotes_collection = quotes_db.quotes_collection
        comment_collection = comments_db.comments_collection
        quote = quotes_db.quotes_collection.find_one({"_id": ObjectId(id)})
        print(quote)
        if user == quote["owner"]:
            comment_collection.delete_many({"quote_id": ObjectId(id)})
            quotes_collection.delete_one({"_id": ObjectId(id)})
        # delete the item
        # quotes_collection.delete_one({"_id": ObjectId(id)})
    # return to the quotes page
    return redirect("/myquotes")

@app.route("/delete/comment/<id>", methods=["GET"])
def get_delete_comment(id=None):
    session_id = request.cookies.get("session_id", None)
    if not session_id:
        response = redirect("/login")
        return response
    if id:
        # get some information from the session
        session_collection = session_db.session_collection
        session_data = list(session_collection.find({"session_id": session_id}))
        session_data = session_data[0]
        user = session_data.get("user", "unknown user")

        #if comment owner
        comment_collection = comments_db.comments_collection
        comment = comment_collection.find_one({"_id": ObjectId(id)})
        if user == comment["owner"]:
            comment_collection.delete_one({"_id": ObjectId(id)})
            print("Comment deleted by comment owner")

        #if quote owner
        quote_collection = quotes_db.quotes_collection
        quote = quote_collection.find_one({"_id": comment["quote_id"]})
        if user == quote["owner"]:
            comment_collection.delete_one({"_id": ObjectId(id)})
            print("Comment deleted by quote owner")
    # return to the quotes page
    return redirect("/quotes")