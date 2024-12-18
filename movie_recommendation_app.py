import sys
import os
import json
import sqlite3
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QIcon, QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QDialogButtonBox
)
from urllib.parse import urlencode
import requests
import random

# Configuration
CONFIG_FILE = "config.json"
DATABASE_FILE = "favorites.db"
DEFAULT_THEME = "dark"

# Load or create configuration
def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"api_key": "your_api_key_here", "theme": DEFAULT_THEME}
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

def save_config(config):
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file)

config = load_config()

API_KEY = config["api_key"]
current_theme = config["theme"]

# TMDb API
BASE_URL = "https://api.themoviedb.org/3/"

def fetch_movies(page=1, genre_id=None):
    params = {
        "api_key": API_KEY,
        "page": page,
    }
    if genre_id:
        params["with_genres"] = genre_id

    url = f"{BASE_URL}discover/movie?{urlencode(params)}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []

def search_movies(query):
    url = f"{BASE_URL}search/movie?api_key={API_KEY}&query={query}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []

# Database setup
def setup_database():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS favorites (id INTEGER PRIMARY KEY, title TEXT)")
    conn.commit()
    conn.close()

def add_to_favorites(movie_title):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO favorites (title) VALUES (?)", (movie_title,))
    conn.commit()
    conn.close()

def get_favorites():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM favorites")
    favorites = [row[0] for row in cursor.fetchall()]
    conn.close()
    return favorites

# Settings Dialog
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setFixedSize(400, 200)

        layout = QFormLayout()

        self.api_key_input = QLineEdit(config["api_key"])
        layout.addRow("API Key:", self.api_key_input)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["dark", "light"])
        self.theme_combo.setCurrentText(config["theme"])
        layout.addRow("Theme:", self.theme_combo)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def save_settings(self):
        config["api_key"] = self.api_key_input.text()
        config["theme"] = self.theme_combo.currentText()
        save_config(config)
        self.accept()

# Main Application
class MovieApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Movie Recommendation System")
        self.setGeometry(100, 100, 900, 700)
        self.setWindowIcon(QIcon("icon.png"))
        self.current_page = 1
        self.current_genre = None
        self.setup_ui()

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Header
        self.header_label = QLabel("Movie Recommendation System")
        self.header_label.setFont(QFont("Arial", 20))
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.header_label)

        # Search Area
        search_layout = QVBoxLayout()
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search for a movie...")
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_movies)

        search_input_layout = QHBoxLayout()
        search_input_layout.addWidget(self.search_bar)
        search_input_layout.addWidget(self.search_button)

        search_layout.addLayout(search_input_layout)

        self.search_results_area = QScrollArea()
        self.search_results_area.setWidgetResizable(True)
        self.search_results_widget = QWidget()
        self.search_results_layout = QVBoxLayout()
        self.search_results_widget.setLayout(self.search_results_layout)
        self.search_results_area.setWidget(self.search_results_widget)

        search_layout.addWidget(self.search_results_area)
        self.layout.addLayout(search_layout)

        # Recommendations Area
        self.genre_combo = QComboBox()
        self.genre_combo.addItem("All", None)
        genres = [
            ("Action", 28),
            ("Comedy", 35),
            ("Drama", 18),
            ("Romance", 10749),
        ]
        for genre_name, genre_id in genres:
            self.genre_combo.addItem(genre_name, genre_id)

        self.genre_combo.currentIndexChanged.connect(self.change_genre)
        self.layout.addWidget(self.genre_combo)

        self.recommend_button = QPushButton("Get Recommendations")
        self.recommend_button.clicked.connect(self.show_recommendations)
        self.layout.addWidget(self.recommend_button)

        self.recommendations_area = QScrollArea()
        self.recommendations_area.setWidgetResizable(True)
        self.recommendations_widget = QWidget()
        self.recommendations_layout = QVBoxLayout()
        self.recommendations_widget.setLayout(self.recommendations_layout)
        self.recommendations_area.setWidget(self.recommendations_widget)

        self.layout.addWidget(self.recommendations_area)

        # Favorites Button
        self.favorites_button = QPushButton("View Favorites")
        self.favorites_button.clicked.connect(self.show_favorites)
        self.layout.addWidget(self.favorites_button)

        # Settings Button
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self.layout.addWidget(self.settings_button)

        self.update_theme()

    def search_movies(self):
        query = self.search_bar.text()
        if not query.strip():
            QMessageBox.warning(self, "Warning", "Please enter a search term.")
            return

        movies = search_movies(query)
        self.display_movies(movies, self.search_results_layout)

    def change_genre(self):
        self.current_genre = self.genre_combo.currentData()

    def show_recommendations(self):
        movies = fetch_movies(page=self.current_page, genre_id=self.current_genre)
        self.current_page += 1
        self.display_movies(movies, self.recommendations_layout)

    def show_favorites(self):
        favorites = get_favorites()
        self.clear_content(self.recommendations_layout)

        if not favorites:
            self.recommendations_layout.addWidget(QLabel("No favorites added yet."))
            return

        for movie in favorites:
            movie_frame = QFrame()
            movie_frame.setStyleSheet("QFrame { border: 1px solid gray; border-radius: 10px; margin: 5px; padding: 10px; background-color: #444; }")
            movie_layout = QHBoxLayout()
            movie_frame.setLayout(movie_layout)

            title_label = QLabel(movie)
            title_label.setFont(QFont("Arial", 12))
            title_label.setWordWrap(True)
            movie_layout.addWidget(title_label)

            add_button = QPushButton("Remove from Favorites")
            add_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            add_button.clicked.connect(lambda _, m=movie: self.remove_movie_from_favorites(m))
            movie_layout.addWidget(add_button)

            self.recommendations_layout.addWidget(movie_frame)

    def remove_movie_from_favorites(self, movie_title):
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE title = ?", (movie_title,))
        conn.commit()
        conn.close()
        QMessageBox.information(self, "Success", f"'{movie_title}' removed from favorites!")
        self.show_favorites()

    def add_movie_to_favorites(self, movie_title):
        add_to_favorites(movie_title)
        QMessageBox.information(self, "Success", f"'{movie_title}' added to favorites!")

    def open_settings(self):
        settings_dialog = SettingsDialog(self)
        if settings_dialog.exec():
            QMessageBox.information(self, "Settings Saved", "Settings have been updated.")
            self.update_theme()

    def update_theme(self):
        theme = {
            "dark": {"bg": "#2b2b2b", "fg": "#ffffff"},
            "light": {"bg": "#ffffff", "fg": "#000000"},
        }[current_theme]

        self.setStyleSheet(
            f"background-color: {theme['bg']}; color: {theme['fg']};"
        )

    def clear_content(self, layout):
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

    def display_movies(self, movies, layout):
        self.clear_content(layout)

        if not movies:
            layout.addWidget(QLabel("No movies found."))
            return

        # Shuffle the movie list to randomize the order
        random.shuffle(movies)

        for movie in movies:
            movie_frame = QFrame()
            movie_frame.setStyleSheet("QFrame { border: 1px solid gray; border-radius: 15px; margin: 5px; padding: 10px; background-color: #444; }")
            movie_layout = QHBoxLayout()
            movie_frame.setLayout(movie_layout)

            title_label = QLabel(movie["title"])
            title_label.setFont(QFont("Arial", 12))
            title_label.setWordWrap(True)
            movie_layout.addWidget(title_label)

            rating_label = QLabel(f"Rating: {movie.get('vote_average', 'Not Rated')}")
            movie_layout.addWidget(rating_label)

            add_button = QPushButton("Add to Favorites")
            add_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            add_button.clicked.connect(lambda _, m=movie["title"]: self.add_movie_to_favorites(m))
            movie_layout.addWidget(add_button)

            layout.addWidget(movie_frame)

if __name__ == "__main__":
    setup_database()

    app = QApplication(sys.argv)
    window = MovieApp()
    window.show()
    sys.exit(app.exec())
