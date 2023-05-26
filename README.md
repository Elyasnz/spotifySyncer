# spotifySyncer
Sync Spotify Playlists with each other <br>
this library is a wrapper for [spotipy](https://github.com/spotipy-dev/spotipy)

## Requirements
```
sudo apt install libcairo2-dev libgirepository1.0-dev
pip install argparse spotipy pandas
```

## Create Spotify Developer App
To start using this code you must first create an app in [spotify developer](https://developer.spotify.com/dashboard/create) <br>
set App name and description as you want and set Redirect URI to https://www.example.com <br>
after creating your app head on to your app settings and copy the Client ID and Client Secret and your done with this dashboard

## Copy Playlists Id
then go to your Spotify account and copy the share link for the playlists you want to sync (for liked-songs playlist just put `saved_tracks`) <br>
Note: share links will look something like https://open.spotify.com/playlist/{id}?si={something} and we only want the `id` part

## Authentication
this script uses spotipy Oauth so the first time you run the code it will open a browser and ask for verification <br>
after accepting the agreement you will be redirected to another page (https://www.example.com) <br>
then you must copy the full link (with parameters) of that page and paste it into the terminal to complete the verification

## CronJob
you can add this script as a CronJob to be updated at a desired timespan <br>
you can also use `--sync_every` option to make sure if the script ran multiple times, the additional sync requests will be filtered out <br>
example cronjob to run every hour but sync every day: <br>
`0 * * * * XDG_RUNTIME_DIR=/run/user/$(id -u) /path/to/spotifySyncer.py saved_tracks PLAYLIST_ID -id CLIENT_ID -secret CLIENT_SECRET -se 86400` <br>
### Why do it like this?
this is done to make sure the playlist will be updated if the system is up for an hour but also avoids additional bandwidth and system usage <br>
for example, if the first try fails due to the systems internet connection it will be synced at the second try the next hour but it will not be synced until 24 hours after the successful sync <br>
the `XDG_RUNTIME_DIR` variable is used to keep the notifications working

## Usage
```
usage: Spotify Playlist Syncer [-h] [-id ID] [-secret SECRET] [-sp SAVE_PATH] [-se SYNC_EVERY] playlist_orgn playlist_dst

positional arguments:
  playlist_orgn   origin playlist id (use `saved_tracks` to specify liked songs)
  playlist_dst    destination playlist id (use `saved_tracks` to specify liked songs)

options:
  -h, --help      show this help message and exit
  -id ID          spotify client id (can be specified with ENV:SPOTIFY_CLIENT_ID)
  -secret SECRET  spotify client secret (can be specified with ENV:SPOTIFY_CLIENT_SECRET)
  -sp SAVE_PATH   path to save the playlist spreadsheets
  -se SYNC_EVERY  seconds between each sync

```
## Example:
sync Spotify liked songs with a public playlist <br>
`spotifySyncer.py saved_tracks PLAYLIST_ID -id CLIENT_ID -secret CLIENT_SECRET`
