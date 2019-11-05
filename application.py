import os
import requests
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# some configurations taken from lesson
app = Flask(__name__)
app.secret_key = "FfqGFceDWevssqdhxkow-Q"
engine = create_engine(
    "postgres://osljbpsqkhgovs:5400d8286a81b1a190405b20e1eb64cd3ecee71b64fd4eb34d5be63a2cedaf54@ec2-54-247-171-30.eu-west-1.compute.amazonaws.com:5432/d8ipu2ln9955st")
db = scoped_session(sessionmaker(bind=engine))

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# home site returns different html file for logged and unlogged users
@app.route("/")
def index():
    # when the user is logged in
    if not session.get("login") is None:
        return render_template("loggedindex.html", login=session.get("login")[1])

    # for unlogged users
    books = db.execute("SELECT * FROM booksreview LIMIT 5").fetchall()
    return render_template("index.html", books=books)

#####REGISTER############
@app.route("/register", methods=['Post', 'Get'])
def register():

    if request.method == 'POST':
        '''Register a new user'''
        # take the data from the website
        login = request.form.get("login")
        email = request.form.get("email")
        name = request.form.get("name")
        surname = request.form.get("surname")
        # Make sure the user does not exist yet.
        if db.execute("SELECT * FROM users WHERE login = :login", {"login": login}).rowcount > 0:
            return render_template("error.html", message="User already exist. Please change the login name")
        db.execute("INSERT INTO users (login, email, name, surname) VALUES (:login, :email, :name, :surname)",
                   {"login": login, "email": email,  "name": name, "surname": surname})
        db.commit()
        return render_template("success.html", message="You have successfully registered. Log in to your account")
    # if the user is logged in
    if not session.get("login") is None:
        return render_template("loggederror.html", message="you are already logged in", login=session.get("login")[1])
    return render_template("registration.html")

#########@@@@@  LOGIN  @@@@@######################
@app.route("/login", methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        login = request.form.get("login")
        email = request.form.get("email")

        if db.execute("SELECT * FROM users WHERE login=:login AND email=:email", {"login": login, "email": email}).rowcount == 0:
            return render_template(
                "error.html", message="there is no such a user or you have provided incorrect password")

        ####create SESSION object if login succeed#####
        else:
            user = db.execute(
                "SELECT * FROM users WHERE login=:login", {"login": login}).fetchone()
            session['login'] = user.login
            # return render_template("logsuccess.html", message=("you are now logged in as " + str(login)), login=user[5])
            return render_template("search.html")
    if not session.get("login") is None:
        return render_template("loggederror.html", message="you are already logged in")

    else:
        return render_template("login.html")

#########.......PROFILE........######################
@app.route("/profile")
def profile():

    if not session.get("login") is None:
        user = db.execute("SELECT * FROM users WHERE login=:login",
                          {"login": session.get("login")}).fetchone()
        books= db.execute("SELECT COUNT(*) FROM reviews WHERE user_id=:user_id", {"user_id": user[0]}).fetchall()[0][0]
        return render_template("profile.html", login=user.login, name=user.name, surname=user.surname, books=books)
    else:
        return redirect(url_for("login"))


@app.route("/logout")
def logout():
    return render_template("logout.html")


@app.route("/loggedout")
def loggedout():
    session.pop("login", None)
    return render_template("loggedout.html")

##########      o o o   DETAILS  o o o   ############################
@app.route("/details/<string:id>", methods=["POST", "GET"])
def details(id):
    if int(id) > 5000:
        return render_template("error.html", message="The id number you are loking for is too big. There is no book under that index.")
    if request.method == "POST":
        return id
  #  details = db.execute(
   #     "SELECT * FROM booksreview WHERE id=:id", {"id": id}).fetchone()

    alldetails = db.execute(
        "SELECT * FROM reviews FULL JOIN booksreview ON reviews.book_id=booksreview.id WHERE booksreview.id=:id",  {"id": id}).fetchall()
    details = alldetails[0]
    isreviewed= db.execute("SELECT * FROM reviews WHERE book_id=:book_id", {"book_id":id}).fetchone()
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "92iLADiOFkvu8LHRIn1hvQ", "isbns": details.isbn}).json()
    #if res.status_code != 200:
    #    return render_template("details.html", title=details.title, author=details.author, year=details.pub_year, isbn=details.isbn, reviews=alldetails, user=session.get("login"), res='Cannot access data from Goodreads')
    return render_template("details.html", title=details.title, author=details.author, year=details.pub_year, isbn=details.isbn, reviews=alldetails, isreviewed=isreviewed, user=session.get("login"), res=res['books'][0]['average_rating'], nores=res['books'][0]['ratings_count'])


####### ?????? SEARCH ???????? ##########################
@app.route("/search", methods=["POST", "GET"])
def search():
    if request.method == "GET":
        if not session.get("login") is None:
            return render_template("search.html")
        else:
            return render_template("error.html", message="Log in to search for a book")

    option = str(request.form.get("option"))
    search = '%' + request.form.get("search") + '%'

    if option == "title":
        booklist = db.execute(
            "SELECT * FROM booksreview WHERE title ILIKE :search", {"search": search}).fetchall()
    elif option == "author":
        booklist = db.execute(
            "SELECT * FROM booksreview WHERE author ILIKE :search", {"search": search}).fetchall()
    elif option == "isbn":
        booklist = db.execute(
            "SELECT * FROM booksreview WHERE isbn ILIKE :search", {"search": search}).fetchall()
    if len(booklist) == 0:
        return render_template("noresults.html")
    return render_template("searchlist.html", booklist=booklist)


@app.route("/review", methods=["GET", "POST"])
def review():
    if session.get("login") is None:
        return render_template("error.html", message="Log in to post a review.")
    if request.method == "GET":
        return render_template("review.html")
    score = int(request.form.get("score"))
    book_title = request.form.get("book")
    review = request.form.get("review")
    user_id = db.execute("SELECT id FROM users WHERE login = :login", {
                         "login": session.get("login")}).fetchone()[0]
    try:
        book_id = db.execute("SELECT id FROM booksreview WHERE title = :title", {
            "title": book_title}).fetchone()[0]
    except:
        return render_template("loggederror.html",
                               message="There is no such a title in our database.")
    isbn=db.execute("SELECT isbn FROM booksreview WHERE title=:book_title", {"book_title": book_title}).fetchone()[0]
    if db.execute("SELECT review FROM users JOIN reviews ON reviews.user_id=users.id JOIN booksreview ON booksreview.id=reviews.book_id WHERE login=:login AND isbn=:isbn",
        {"login": session.get("login"), "isbn": isbn}).fetchone()!= None:
        return render_template("error.html", message="You have already reviewed this book")
    db.execute(
        "INSERT INTO reviews (book_id, user_id, review, score) VALUES (:book_id,:user_id,:review,:score)", {"book_id": book_id, "user_id": user_id, "score": score, "review": review})
    db.commit()
    return render_template("loggedsuccess.html", message="your review has been added")


@app.route("/review/<string:isbn>")
def revisbn(isbn):
        if session.get("login") is None:
            return render_template("error.html", message="Log in to post a review.")
        if db.execute("SELECT review FROM users JOIN reviews ON reviews.user_id=users.id JOIN booksreview ON booksreview.id=reviews.book_id WHERE login=:login AND isbn=:isbn",{"login": session.get("login"), "isbn": isbn}).fetchone()!= None:
            return render_template("error.html", message="You have already reviewed this book")
        book=db.execute("SELECT title FROM booksreview WHERE isbn=:isbn", {"isbn":isbn}).fetchone()[0]
        return render_template("reviewtitle.html", book=book)

@app.route("/api/<string:isbn>")
def json(isbn):
    try:
        isthere=db.execute("SELECT isbn FROM booksreview WHERE isbn=:isbn", {"isbn":isbn}).fetchall()[0]
    except:
        return jsonify({"error": "Invalid isbn"}), 422
    details = db.execute(
        "SELECT * FROM reviews FULL JOIN booksreview ON reviews.book_id=booksreview.id WHERE booksreview.isbn=:isbn",  {"isbn": isbn}).fetchall()[0]
    review_count = db.execute(
        "SELECT COUNT(*) FROM reviews FULL JOIN booksreview ON booksreview.id=reviews.book_id WHERE booksreview.isbn=:isbn", {"isbn": isbn}).fetchall()[0][0]
    average_score=db.execute(
        "SELECT AVG(score) FROM reviews FULL JOIN booksreview ON booksreview.id=reviews.book_id WHERE booksreview.isbn=:isbn", {"isbn": isbn}).fetchall()[0][0]
    return render_template("api.html", title=details.title, author=details.author, year=details.pub_year, isbn=details.isbn, review_count=review_count, average_score=average_score)


@app.route("/whoami")
def whoami():
    user_id = db.execute("SELECT id FROM users WHERE login = :login", {
                         "login": session.get("login")}).fetchone()
    return str(user_id[0])




if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True, host='0.0.0.0', port=8000)
