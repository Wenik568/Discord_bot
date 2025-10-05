# 🎵 Discord Музичний Бот

Повнофункціональний музичний бот для Discord з підтримкою YouTube та Spotify.

## ✨ Функції

- 🎵 Відтворення музики з YouTube (пошук та посилання)
- 🎧 Підтримка Spotify посилань
- 📝 Черга пісень
- 🔁 Повтор треків
- ⏯️ Пауза/продовження
- ⏭️ Пропуск пісень
- 📋 Підтримка плейлистів

## 📦 Встановлення

### 1. Встановіть Python 3.8+

### 2. Встановіть FFmpeg

**Windows:**
- Завантажте з [ffmpeg.org](https://ffmpeg.org/download.html)
- Додайте FFmpeg до PATH

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### 3. Встановіть залежності

```bash
pip install -r requirements.txt
```

### 4. Налаштуйте бота

1. Створіть додаток на [Discord Developer Portal](https://discord.com/developers/applications)
2. Створіть бота та скопіюйте токен
3. Увімкніть `Message Content Intent` та `Server Members Intent`
4. Створіть файл `.env` на основі `.env.example`:

```bash
cp .env.example .env
```

5. Додайте ваш токен в `.env`:
```
DISCORD_TOKEN=ваш_токен_тут
```

6. **(Опціонально)** Для точного пошуку Spotify треків з артистом:
   - Створіть додаток на [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Скопіюйте Client ID та Client Secret
   - Додайте в `.env`:
   ```
   SPOTIFY_CLIENT_ID=ваш_client_id
   SPOTIFY_CLIENT_SECRET=ваш_client_secret
   ```

### 5. Запустіть бота

```bash
python music_bot.py
```

## 🎮 Команди

### Основні команди
- `!play <пісня/URL>` або `!p <пісня/URL>` - Грати музику
- `!pause` - Призупинити відтворення
- `!resume` - Продовжити відтворення
- `!skip` або `!s` - Пропустити поточну пісню
- `!stop` - Зупинити музику та очистити чергу
- `!leave` або `!dc` - Відключити бота

### Черга
- `!queue` або `!q` - Показати чергу пісень
- `!np` або `!nowplaying` - Що зараз грає
- `!loop` - Увімкнути/вимкнути повтор

### Допомога
- `!help_music` - Показати всі команди

## 📖 Приклади використання

```
!play Never Gonna Give You Up
!play https://www.youtube.com/watch?v=dQw4w9WgXcQ
!play https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT
!play https://www.youtube.com/playlist?list=PLxxxxxxx
!queue
!skip
!loop
```

## 🔧 Вимоги

- Python 3.8 або новіше
- FFmpeg
- Discord Bot Token
- Стабільне інтернет-з'єднання

## ⚠️ Важливо

- Переконайтеся, що FFmpeg встановлено та доданий до PATH
- Увімкніть всі необхідні Intents в Discord Developer Portal
- Бот потребує дозволів: підключення до голосових каналів, говорити, читати повідомлення

## 🐛 Можливі проблеми

**Бот не відповідає:**
- Перевірте, чи увімкнений `Message Content Intent`

**Помилки при відтворенні:**
- Переконайтеся, що FFmpeg встановлено правильно
- Перевірте інтернет-з'єднання

**Spotify не працює:**
- Spotify посилання конвертуються через YouTube, тому результати можуть відрізнятися

## 📝 Ліцензія

MIT License
