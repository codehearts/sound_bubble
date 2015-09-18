## Sound Bubble
A simple Flask app that provides a web interface to MPD. I'm personally using it to control the background music in my dorm room from my phone and laptop.

#### Installation
Because of limitations with `Flask-SocketIO`, this script only runs under Python 2. You'll need to install the prerequisets with `pip install -r requirements.txt`  (or `pip2` on distributions like Arch Linux).

If you intend to modify the stylesheet, you'll need to install Ruby and the `bundler` gem as well. Then simply run `bundle install` to install necessary gems. Once that's done, you can freely modify the Sass styles in `sass/` and run `sass sass/style.scss:static/style.css` to compile your changes. You can also watch for changes with `sass --watch sass:static`.

#### Usage
Simply run `python sound_bubble.py`(or `python2` on distributions like Arch Linux), and press `ctrl+c` to stop it.

#### Features
- [x] A single user account for managing the MPD server
  - [x] Play/pause/skip buttons
  - [x] Add music to playlist
  - [ ] Manage current playlist
  - [ ] Set shuffle/repeat/single mode/consume
  - [ ] Set priority of songs
  - [x] Persistent login between sessions
- [x] Extract album artwork from audio files
  - [x] Resize cover art for reduced bandwidth
  - [ ] Download missing artwork from online APIs
  - [ ] Change/upload artwork for songs
- [x] Mobile-friendly layout
