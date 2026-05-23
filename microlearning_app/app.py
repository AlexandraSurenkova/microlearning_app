# ============================================================
#                    MICROLEARNING APP
# ============================================================
#
# Назначение:
# Веб-приложение для микрообучения на Flask.
#
# Основная идея:
# Пользователь получает одну случайную статью
# из Википедии в день и может отметить её
# как изученную.
#
# Основной функционал:
# 1. Получение статьи дня
# 2. Сохранение статьи в базе данных
# 3. Ведение прогресса обучения
# 4. Просмотр истории изученных материалов
#
# Технологии:
# - Python
# - Flask
# - SQLite
# - SQLAlchemy
# - Wikipedia REST API
#
# ============================================================


# ============================================================
#                    ИМПОРТ БИБЛИОТЕК
# ============================================================

import os
import sys
import requests

from datetime import (
    datetime,
    timezone,
    timedelta,
    date
)

from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    flash
)

from flask_sqlalchemy import SQLAlchemy


# ============================================================
#               НАСТРОЙКА ПУТЕЙ ПРИЛОЖЕНИЯ
# ============================================================
#
# При сборке в .exe через PyInstaller
# пути к templates и static меняются.
#
# Данный блок обеспечивает корректную
# работу приложения как в .py, так и в .exe.
#
# ============================================================

if getattr(sys, 'frozen', False):

    # Путь внутри собранного .exe
    base_path = sys._MEIPASS

else:

    # Путь при обычном запуске Python-файла
    base_path = os.path.abspath(".")


# ============================================================
#                 СОЗДАНИЕ FLASK-ПРИЛОЖЕНИЯ
# ============================================================

app = Flask(

    __name__,

    template_folder=os.path.join(
        base_path,
        'templates'
    ),

    static_folder=os.path.join(
        base_path,
        'static'
    )
)


# ============================================================
#                НАСТРОЙКА БАЗЫ ДАННЫХ
# ============================================================

# Подключение SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = (
    'sqlite:///microlearning.db'
)

# Отключение лишних уведомлений SQLAlchemy
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Секретный ключ Flask
app.secret_key = 'super_secret_key_for_coursework'

# Инициализация SQLAlchemy
db = SQLAlchemy(app)


# ============================================================
#                МОДЕЛЬ ПРОГРЕССА ОБУЧЕНИЯ
# ============================================================
#
# Таблица хранит:
# - название изученной статьи;
# - дату просмотра;
# - статус завершения.
#
# ============================================================

class UserProgress(db.Model):

    # Уникальный идентификатор записи
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Название статьи
    lesson_title = db.Column(
        db.String(300),
        nullable=False
    )

    # Флаг завершения
    completed = db.Column(
        db.Boolean,
        default=False
    )

    # Дата и время изучения
    viewed_at = db.Column(

        db.DateTime,

        default=lambda: datetime.now(
            timezone(
                timedelta(hours=3)
            )
        )
    )


# ============================================================
#                    МОДЕЛЬ СТАТЬИ ДНЯ
# ============================================================
#
# Таблица хранит:
# - текущую статью дня;
# - дату статьи;
# - текст статьи;
# - ссылку на источник.
#
# Это позволяет показывать одну и ту же
# статью в течение суток.
#
# ============================================================

class DailyArticle(db.Model):

    # Уникальный идентификатор
    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Дата статьи
    article_date = db.Column(
        db.Date,
        unique=True,
        nullable=False
    )

    # Заголовок статьи
    title = db.Column(
        db.String(300),
        nullable=False
    )

    # Содержание статьи
    content = db.Column(
        db.Text,
        nullable=False
    )

    # Ссылка на Википедию
    source_url = db.Column(
        db.String(500),
        nullable=False
    )


# ============================================================
#                 СОЗДАНИЕ ТАБЛИЦ БД
# ============================================================

with app.app_context():

    # Автоматическое создание таблиц
    db.create_all()


# ============================================================
#          ФУНКЦИЯ ПОЛУЧЕНИЯ СЛУЧАЙНОЙ СТАТЬИ
# ============================================================
#
# Функция отправляет запрос к API Википедии
# и получает:
# - заголовок статьи;
# - краткое описание;
# - ссылку на полную статью.
#
# ============================================================

def get_random_wiki_article():

    try:

        # URL API Википедии
        url = (
            "https://ru.wikipedia.org/"
            "api/rest_v1/page/random/summary"
        )

        # Заголовок User-Agent обязателен
        headers = {

            "User-Agent": "MicroLearningApp/1.0"
        }

        # Отправка GET-запроса
        response = requests.get(

            url,

            headers=headers,

            timeout=10
        )

        # Проверка успешности запроса
        if response.status_code != 200:

            print(
                "Ошибка API:",
                response.status_code
            )

            return None

        # Преобразование ответа в JSON
        data = response.json()

        # Формирование словаря статьи
        lesson = {

            "title": data.get(
                "title",
                "Без названия"
            ),

            "content": data.get(
                "extract",
                "Описание отсутствует."
            ),

            "source_url": data.get(
                "content_urls",
                {}
            ).get(
                "desktop",
                {}
            ).get(
                "page",
                "https://ru.wikipedia.org"
            )
        }

        return lesson

    except Exception as e:

        print(
            "Ошибка загрузки статьи:",
            e
        )

        return None


# ============================================================
#                    ГЛАВНАЯ СТРАНИЦА
# ============================================================

@app.route('/')
def home():

    return render_template(
        "index.html"
    )


# ============================================================
#                  СТРАНИЦА "СТАТЬЯ ДНЯ"
# ============================================================
#
# Алгоритм работы:
#
# 1. Проверяется наличие статьи
#    для текущей даты.
#
# 2. Если статья уже существует —
#    она отображается пользователю.
#
# 3. Если статьи нет —
#    приложение получает новую статью
#    из Википедии и сохраняет её в БД.
#
# ============================================================

@app.route('/daily')
def daily():

    # Получение текущей даты
    today = date.today()

    # Поиск статьи дня в базе данных
    existing_article = db.session.query(
        DailyArticle
    ).filter_by(
        article_date=today
    ).first()

    # Если статья уже существует
    if existing_article:

        lesson = {

            "title": existing_article.title,

            "content": existing_article.content,

            "source_url": existing_article.source_url
        }

    else:

        # Получение новой статьи
        article = get_random_wiki_article()

        # Проверка успешности загрузки
        if not article:

            return (
                "Не удалось загрузить статью.",
                500
            )

        # Создание объекта статьи
        new_article = DailyArticle(

            article_date=today,

            title=article["title"],

            content=article["content"],

            source_url=article["source_url"]
        )

        # Сохранение статьи в БД
        db.session.add(new_article)

        db.session.commit()

        lesson = article

    # Отображение страницы статьи
    return render_template(

        "lesson.html",

        lesson=lesson
    )


# ============================================================
#             МАРШРУТ ОТМЕТКИ О ПРОХОЖДЕНИИ
# ============================================================
#
# Пользователь может отметить статью
# как изученную.
#
# Повторное добавление одной и той же
# статьи за один день запрещено.
#
# ============================================================

@app.route('/complete/<lesson_title>')
def complete_lesson(lesson_title):

    # Получение текущей даты
    today = date.today()

    # Проверка существования записи
    existing_progress = db.session.query(
        UserProgress
    ).filter_by(
        lesson_title=lesson_title
    ).filter(
        db.func.date(
            UserProgress.viewed_at
        ) == today
    ).first()

    # Если статья уже была изучена
    if existing_progress:

        flash(

            "Вы уже изучили статью сегодня!",

            "warning"
        )

    else:

        # Создание записи прогресса
        progress = UserProgress(

            lesson_title=lesson_title,

            completed=True,

            viewed_at=datetime.now()
        )

        # Сохранение записи
        db.session.add(progress)

        db.session.commit()

        flash(

            "Статья успешно добавлена в прогресс!",

            "success"
        )

    # Возврат к статье дня
    return redirect(
        url_for('daily')
    )


# ============================================================
#                 СТРАНИЦА ПРОГРЕССА
# ============================================================
#
# Отображает список всех изученных статей.
#
# ============================================================

@app.route('/progress')
def progress():

    # Получение данных прогресса
    progress_data = db.session.query(

        UserProgress.lesson_title,

        UserProgress.completed,

        UserProgress.viewed_at

    ).all()

    # Отображение страницы прогресса
    return render_template(

        'progress.html',

        progress_data=progress_data
    )


# ============================================================
#                    СТРАНИЦА ПОМОЩИ
# ============================================================

@app.route('/help')
def app_help():

    return render_template(
        'help.html'
    )

# ============================================================
#                ЗАВЕРШЕНИЕ ПРИЛОЖЕНИЯ
# ============================================================

@app.route('/shutdown')
def shutdown():

    os._exit(0)


# ============================================================
#                  ЗАПУСК ПРИЛОЖЕНИЯ
# ============================================================

if __name__ == '__main__':

    # Запуск Flask-сервера
    app.run(debug=True)
