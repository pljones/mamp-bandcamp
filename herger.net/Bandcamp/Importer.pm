package Plugins::Bandcamp::Importer;

use strict;
use Date::Parse qw(str2time);
use POSIX qw(strftime);

# can't "use base ()", as this would fail in LMS 7
BEGIN {
	eval {
		require Slim::Plugin::OnlineLibraryBase;
		our @ISA = qw(Slim::Plugin::OnlineLibraryBase);
	};
}

use Slim::Music::Import;
use Slim::Utils::Log;
use Slim::Utils::Prefs;
use Slim::Utils::Strings qw(string);

use constant CAN_IMPORTER => (Slim::Utils::Versions->compareVersions($::VERSION, '8.0.0') >= 0);

my $log = logger('plugin.bandcamp');
my $prefs = preferences('plugin.bandcamp');
my $cache;

sub initPlugin {
	my $class = shift;

	if (!CAN_IMPORTER) {
		$log->warn('The library importer feature requires at least Logitech Media Server 8.');
		return;
	}

	my $pluginData = Slim::Utils::PluginManager->dataForPlugin($class) || return;

	require Plugins::Bandcamp::API::Sync;
	$cache = Plugins::Bandcamp::API::Sync->init($pluginData);

	$class->SUPER::initPlugin(@_)
}

sub isImportEnabled { if (CAN_IMPORTER) {
	my ($class) = @_;

	if ($prefs->get('identity_token')) {
		$cache->set('library_fingerprint', -1, 30 * 86400);
		return $class->SUPER::isImportEnabled();
	}

	return;
} }

sub startScan { if (main::SCANNER) {
	my $class = shift;

	$class->initOnlineTracksTable();

	if (!Slim::Music::Import->scanPlaylistsOnly()) {
		$class->scanAlbums();
	}

	my $checksum = Plugins::Bandcamp::API::Sync->getLibraryChecksum();
	$cache->set('library_fingerprint', ($checksum || ''), 30 * 86400);

	$class->deleteRemovedTracks();

	Slim::Music::Import->endImporter($class);
} };

sub scanAlbums {
	my ($class) = @_;

	my $progress = Slim::Utils::Progress->new({
		'type'  => 'importer',
		'name'  => 'plugin_bandcamp_albums',
		'total' => 1,
		'every' => 1,
	});

	my @missingAlbums;

	main::INFOLOG && $log->is_info && $log->info("Reading albums...");
	$progress->update(string('PLUGIN_BANDCAMP_PROGRESS_READ_ALBUMS'));

	my $albums = Plugins::Bandcamp::API::Sync->myAlbums();
	$progress->total(scalar @$albums);

	my @albums;

	foreach my $album (@$albums) {
		my $albumDetails = $cache->get('album_with_tracks_' . $album->{id});

		if ($albumDetails && $albumDetails->{tracks} && ref $albumDetails->{tracks}) {
			$progress->update($album->{title});
			$class->storeTracks([
				grep { $_ } map { _prepareTrack($album, $_, $albumDetails) } @{ $albumDetails->{tracks} }
			]);

			main::SCANNER && Slim::Schema->forceCommit;
		}
		else {
			push @missingAlbums, $album;
		}
	}

	foreach my $album (@missingAlbums) {
		my $albumDetails = Plugins::Bandcamp::API::Sync->getAlbum($album->{id});
		$progress->update($album->{title});

		next unless $albumDetails && ref $albumDetails && $albumDetails->{tracks} && scalar @{$albumDetails->{tracks}};

		$albumDetails->{artist}    ||= $album->{band_name};
		$albumDetails->{band_name} ||= $album->{band_name};
		$albumDetails->{band_id}   ||= $album->{band_id};

		$cache->set('album_with_tracks_' . $album->{id}, $albumDetails, time() + 86400 * 90);

		$class->storeTracks([
			grep { $_ } map { _prepareTrack($album, $_, $albumDetails) } @{ $albumDetails->{tracks} }
		]);

		main::SCANNER && Slim::Schema->forceCommit;
	}

	$progress->final();
	main::SCANNER && Slim::Schema->forceCommit;
}

sub trackUriPrefix { 'bandcamp://' }

# This code is not run in the scanner, but in LMS
sub needsUpdate { if (!main::SCANNER) {
	my ($class, $cb) = @_;

	$cache ||= Plugins::Bandcamp::API::Common->init(Slim::Utils::PluginManager->dataForPlugin('Plugins::Bandcamp::Plugin'));

	my $oldFingerprint = $cache->get('library_fingerprint') || return $cb->(1);

	if ($oldFingerprint == -1) {
		return $cb->($oldFingerprint);
	}

	Plugins::Bandcamp::API::getLibraryChecksum(sub {
		my $newFingerPrint = shift || '';
		$cb->($newFingerPrint ne $oldFingerprint)
	});
} }

sub _prepareTrack {
	my ($album, $track, $albumDetails) = @_;

	return unless $track && $track->{streaming_url};

	my $url = sprintf('bandcamp://%s.mp3', $track->{track_id});

	Plugins::Bandcamp::API::Common::cache_track_info($track, $album);

	my $attributes = {
		url          => $url,
		TITLE        => $track->{title},
		ARTIST       => $album->{artist},
		ARTIST_EXTID => 'bandcamp:artist:' . $album->{band_id},
		# TRACKARTIST  => $track->{performer}->{name},
		ALBUM        => $album->{title},
		ALBUM_EXTID  => 'bandcamp:album:' . $album->{id},
		TRACKNUM     => $track->{number},
		GENRE        => 'Bandcamp',
		SECS         => $track->{duration},
		YEAR         => strftime('%Y', localtime($albumDetails->{release_date} || 0)),
		COVER        => $album->{cover},
		AUDIO        => 1,
		EXTID        => $url,
		TIMESTAMP    => str2time($album->{added} || 0),
		CONTENT_TYPE => 'mp3',
		SAMPLERATE   => 128_000,
		COMMENT      => $albumDetails->{about},
	};

	return $attributes;
}

1;

# add some helper methods to the main package
package Plugins::Bandcamp::Plugin;

sub onlineLibraryNeedsUpdate {
	my $class = shift;
	# require Plugins::Bandcamp::Importer;
	return Plugins::Bandcamp::Importer->needsUpdate(@_);
}

sub getLibraryStats {
	# require Plugins::Bandcamp::Importer;
	my $totals = Plugins::Bandcamp::Importer->getLibraryStats();
	return wantarray ? ('PLUGIN_BANDCAMP', $totals) : $totals;
}

# Collection summary
# curl --location --request GET 'https://bandcamp.com/api/fan/2/collection_summary' \
# --header 'Cookie: client_id=EC2FF8F471A0EB0915984425A5C0FA23879576ADFC9FF65111280186E58E08C7; fan_visits=10236; BACKENDID=bender24-4; session=1%09t%3A1606491461%09bp%3A1%09r%3A%5B%22322845039c10236a34939844x1606495375%22%2C%22364587321a34939844c0x1606494947%22%2C%22365547591x0a34939844x1606494866%22%5D; identity=7%0958IhReMTODjIDcbKQHKEZ415UpCJ7oFBne8qAupDu5g%3D%09%7B%22ex%22%3A0%2C%22id%22%3A1712700664%7D'

1;