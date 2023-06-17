#!/usr/bin/env -S python3 -u

# sudo apt install libcairo2-dev libgirepository1.0-dev
# pip install argparse spotipy pandas


from argparse import ArgumentParser
from os import environ, makedirs, chdir, system
from os.path import getmtime, exists
from pathlib import Path
from time import sleep, time

from pandas import DataFrame, DatetimeIndex, concat, to_datetime
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth


def send_notification(title, desc):
	system(f'notify-send "{title}" "{desc}"')


class Syncer:
	def __init__(self, playlist_orgn, playlist_dst, client_id=None, client_secret=None, save_path=None,
	             sync_every=None):
		"""
		Sync Spotify two playlists with each other (and keeping the order)
		
		:param playlist_orgn: origin playlist id (use `saved_tracks` to specify liked songs)
		:type playlist_orgn: str
		:param playlist_dst: destination playlist id (use `saved_tracks` to specify liked songs)
		:type playlist_dst: str
		:param client_id: spotify client id (can be specified with ENV:SPOTIFY_CLIENT_ID)
		:type client_id: str
		:param client_secret: spotify client secret (can be specified with ENV:SPOTIFY_CLIENT_SECRET)
		:type client_secret: str
		:param save_path: path to save the playlist spreadsheets
		:type save_path: str
		:param sync_every: seconds between each update (if is set sync() method will respect it)
		:type sync_every: int
		"""
		self.playlist_orgn = playlist_orgn
		self.playlist_dst = playlist_dst
		self.client_id = client_id or environ.get('SPOTIFY_CLIENT_ID')
		self.client_secret = client_secret or environ.get('SPOTIFY_CLIENT_SECRET')
		self.save_path = save_path or f'{Path(__file__).parent.absolute()}/log'
		self.sync_every = sync_every
		
		if not self.client_id:
			raise ValueError('client_id not specified')
		if not self.client_secret:
			raise ValueError('client_secret not specified')
		
		chdir(str(Path(__file__).parent.absolute()))
		self.sp = Spotify(
			auth_manager=SpotifyOAuth(
				client_id=self.client_id,
				client_secret=self.client_secret,
				redirect_uri="https://www.example.com",
				scope=','.join([
					'playlist-modify-public',
					'playlist-modify-private',
					'playlist-read-private',
					'user-library-read',
					'user-library-modify'
				])
			)
		)
	
	@classmethod
	def via_argparse(cls):
		parser = ArgumentParser('Spotify Playlist Syncer')
		parser.add_argument(
			'playlist_orgn',
			help='origin playlist id (use `saved_tracks` to specify liked songs)'
		)
		parser.add_argument(
			'playlist_dst',
			help='destination playlist id (use `saved_tracks` to specify liked songs)'
		)
		
		parser.add_argument(
			'-id', default=environ.get('SPOTIFY_CLIENT_ID'),
			help='spotify client id (can be specified with ENV:SPOTIFY_CLIENT_ID)')
		parser.add_argument(
			'-secret', default=environ.get('SPOTIFY_CLIENT_SECRET'),
			help='spotify client secret (can be specified with ENV:SPOTIFY_CLIENT_SECRET)')
		parser.add_argument(
			'-sp', dest='save_path', default=None,
			help='path to save the playlist spreadsheets')
		parser.add_argument(
			'-se', dest='sync_every', type=int, default=0,
			help='seconds between each sync')
		
		args = parser.parse_args()
		
		return cls(args.playlist_orgn, args.playlist_dst, args.id, args.secret, args.save_path, args.sync_every)
	
	@property
	def sync_available(self):
		if not self.sync_every:
			return True
		if not exists(self.save_path):
			return True
		orgn_path = f'{self.save_path}/tracks_orgn.xlsx'
		if not exists(orgn_path):
			return True
		return (time() - getmtime(orgn_path)) > self.sync_every
	
	def sync(self):
		if not self.sync_available:
			print('sync not available')
			return
		print(f'hello {self.sp.me()["display_name"]}')
		
		for i in range(3):
			try:
				send_notification('spotifySyncer', 'Syncing ...')
				tracks_orgn = self.read(self.playlist_orgn).assign(_from='orgn')
				tracks_dst = self.read(self.playlist_dst).assign(_from='dst')
				self.update(tracks_orgn, tracks_dst)
				self.save(tracks_orgn, tracks_dst)
				send_notification('spotifySyncer', 'Synced :)')
				break
			except Exception as e:
				print(f'{e.__class__.__name__}{e.args}')
				send_notification(f'spotifySyncer Error {i + 1}', f'{e.__class__.__name__}{e.args}')
				sleep(30)
	
	def save(self, tracks_orgn, tracks_dst):
		makedirs(self.save_path, exist_ok=True)
		tracks_orgn.to_excel(f'{self.save_path}/tracks_orgn.xlsx', index=False)
		tracks_dst.to_excel(f'{self.save_path}/tracks_dst.xlsx', index=False)
	
	def read(self, source):
		all_tracks = []
		
		print(f'downloading {source} .', end='')
		while True:
			for i in range(3):
				try:
					tracks = self.sp.current_user_saved_tracks(limit=50, offset=len(all_tracks)) \
						if source == 'saved_tracks' else \
						self.sp.playlist_items(source, limit=100, offset=len(all_tracks))
					break
				except Exception:
					sleep(1)
			else:
				raise RuntimeError()
			
			if not tracks['items']:
				break
			
			# print(tracks['items'][0])
			all_tracks.extend(tracks['items'])
			print('.', end='')
		print(f' got {len(all_tracks)} tracks')
		
		all_tracks = DataFrame(
			[
				[
					item['track']['id'],
					item['track']['name'],
					', '.join([artist['name'] for artist in item['track']['artists']]),
					item['track']['duration_ms'],
					item['added_at'],
				] for item in all_tracks
			],
			columns=['id', 'name', 'artists', 'duration_ms', 'added_at']
		)
		
		all_tracks['added_at'] = DatetimeIndex(to_datetime(all_tracks['added_at'], utc=True)).tz_convert(None)
		
		return all_tracks
	
	def update(self, tracks_orgn, tracks_dst):
		drop_duplicated = concat([tracks_orgn, tracks_dst]).drop_duplicates(['id'], keep=False)
		if drop_duplicated.empty:
			print('playlists are in perfect sync already !')
		
		new_saved_tracks = drop_duplicated.loc[drop_duplicated['_from'] == 'orgn']
		if not new_saved_tracks.empty:
			new_saved_tracks = new_saved_tracks.sort_values(['added_at'], ascending=True)
			print('new tracks: ', new_saved_tracks.name.tolist())
			for track in new_saved_tracks.to_dict('records'):
				print(f'adding {track["name"]}')
				for i in range(3):
					try:
						if self.playlist_dst == 'saved_tracks':
							self.sp.current_user_saved_tracks_add([track['id']])
						else:
							self.sp.playlist_add_items(self.playlist_dst, [track['id']])
						break
					except Exception:
						sleep(1)
				else:
					raise RuntimeError()
				sleep(1)
		
		deleted_saved_tracks = drop_duplicated.loc[drop_duplicated['_from'] == 'dst']
		if not deleted_saved_tracks.empty:
			print('deleted tracks: ', deleted_saved_tracks.name.tolist())
			for i in range(3):
				try:
					if self.playlist_dst == 'saved_tracks':
						self.sp.current_user_saved_tracks_delete(deleted_saved_tracks.id.tolist())
					else:
						self.sp.playlist_remove_all_occurrences_of_items(self.playlist_dst,
						                                                 deleted_saved_tracks.id.tolist())
					break
				except Exception:
					sleep(1)
			else:
				raise RuntimeError()


if __name__ == '__main__':
	Syncer.via_argparse().sync()
