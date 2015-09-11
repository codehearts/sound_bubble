## Sound Bubble
A simple Flask app that provides a web interface to MPD. I'm personally using it to control the background music in my dorm room from my phone and laptop.

#### Installation
Because of limitations with `Flask-SocketIO`, this script only runs under Python 2. You'll need to install the prerequisets with `pip install -r requirements.txt`  (or `pip2` on distributions like Arch Linux).

#### Usage
Simply run `python sound_bubble.py`(or `python2` on distributions like Arch Linux), and press `ctrl+c` to stop it.

#### Features
- [x] A single user account for managing the MPD server
  - [x] Play/pause/skip buttons
  - [x] Add music to playlist
  - [ ] Manage current playlist
  - [ ] Set shuffle/repeat/single mode/consume
  - [ ] Set priority of songs
- [x] Extract album artwork from audio files
  - [ ] Resize cover art for reduced bandwidth
  - [ ] Download missing artwork from online APIs
- [ ] Mobile-friendly layout
