import os

from flask import Flask, render_template

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
        TEMPLATES_AUTO_RELOAD='TRUE',
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says home
    @app.route('/home')
    @app.route('/')
    def home():
        return render_template("home.html")

    # testovaci data
    films = [[1, 'Avatar', 5], [2, 'Gavatar', 4], [3, 'V for Vendeta', 5], [4, 'Thor: Dark Word', 3], [5, 'The Shining', 4]]

    @app.route('/profile')
    def profile():
        return render_template("profile.html", films=films)

    @app.route('/recommend')
    def recommend():
        return render_template("recommend.html", films=films)

    if __name__ == '__main__':
        app.run(debug=True)

    return app

