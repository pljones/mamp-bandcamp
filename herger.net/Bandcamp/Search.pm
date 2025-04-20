package Plugins::Bandcamp::Search;

use strict;
use Tie::Cache::LRU;

use Slim::Utils::Log;
use Slim::Utils::Strings qw(string cstring);

use Plugins::Bandcamp::Plugin;
use Plugins::Bandcamp::API;
use Plugins::Bandcamp::Scraper;

use constant MAX_RECENT_ITEMS => 50;
use constant RECENT_CACHE_TTL => 'never';

my $log = logger('plugin.bandcamp');

my $search_results = {};

my %recent_searches;
tie %recent_searches, 'Tie::Cache::LRU', MAX_RECENT_ITEMS;

my $cache;

sub init {
	$cache = shift;

	# initialize recent searches: need to add them to the LRU cache ordered by timestamp
	my $cached = $cache->get('recent_searches');

	if ($cached && ref $cached && keys %$cached) {
		map {
			$recent_searches{$_} = $cached->{$_};
		} sort {
			$cached->{$a}->{ts} <=> $cached->{$a}->{ts}
		} keys %$cached;
	}
}

sub search {
	my ($client, $cb, $params, $args) = @_;

	$params->{search} ||= $args->{q};

	$search_results->{$client || ''} = {};

	_search($client, $cb, $params);
	_search_tags($client, $cb, $params);
	_search_fans($client, $cb, $params);
}

sub _search {
	my ($client, $cb, $params) = @_;

	Plugins::Bandcamp::Scraper::search($client,
		sub {
			my ($items) = @_;

			my $search = $params->{search};
			add_recent_search($search) if ($search && scalar @$items);

			my @results;

			foreach (@$items) {
				if ($_->{track_id}) {
					push @results, {
						name => $_->{name},
						line1 => $_->{artist} && $_->{name},
						line2 => $_->{artist} && $_->{artist},
						url  => \&Plugins::Bandcamp::Plugin::get_track,
						image=> $_->{art_lg_url},
						passthrough => [{
							track_id => $_->{track_id},
							art_lg_url => $_->{art_lg_url}
						}]
					};
					# push @results, @{ Plugins::Bandcamp::Plugin::track_list({ tracks => [$_] }) };
				}
				elsif ($_->{band_id}) {
					push @results, @{ Plugins::Bandcamp::Plugin::artist_list({ results => [$_] }) };
				}
				elsif ($_->{album_id}) {
					push @results, @{ Plugins::Bandcamp::Plugin::album_list($client, \&Plugins::Bandcamp::Plugin::get_album, { discography => [$_] }) };
				}
			}

			$search_results->{$client || ''}->{'search'} = \@results;
			_search_done($client, $cb);
		},
		$params,
	);
}

sub search_artists {
	my ($client, $cb, $params, $args) = @_;

	$params->{search} ||= $args->{q};

	$search_results->{$client || ''} = {
		tag_search => [],
	};

	_search_artists($client, $cb, $params);
}

sub search_tags {
	my ($client, $cb, $params, $args) = @_;

	$params->{search} ||= $args->{q};

	$search_results->{$client || ''} = {
		artist_search => [],
	};

	_search_tags($client, $cb, $params);
}

sub search_url {
	my ($client, $cb, $params, $args) = @_;

	$params->{search} ||= $args->{q};

	# Because search replaces '.' by ' ':
	$params->{search} =~ s/ /./g;

	$search_results->{$client || ''} = {};

	_search_url($client, $cb, $params);
}

sub _search_url {
	my ($client, $cb, $params) = @_;

	Plugins::Bandcamp::Plugin::get_item_info_by_url(
		$client, $cb, $params, { url => $params->{search} }
	);
}

sub _search_tags {
	my ($client, $cb, $params) = @_;

	Plugins::Bandcamp::Scraper::search_tags($client,
		sub {
			my ($items) = @_;

			my $search = $params->{search};
			add_recent_search($search) if $search && scalar @{ $items->{discography} };

			$search_results->{$client || ''}->{'tag_search'} = Plugins::Bandcamp::Plugin::album_list($client, \&Plugins::Bandcamp::Plugin::get_item_info_by_url, $items);
			_search_done($client, $cb);
		},
		$params,
	);
}

sub _search_artists {
	my ($client, $cb, $params) = @_;

	Plugins::Bandcamp::Scraper::search_artists($client,
		sub {
			my ($items) = @_;

			my $search = $params->{search};
			add_recent_search($search) if ($search && scalar @$items);

			$search_results->{$client || ''}->{'artist_search'} = Plugins::Bandcamp::Plugin::artist_list({ results => $items });
			_search_done($client, $cb);
		},
		$params,
	);
}

sub _search_fans {
	my ($client, $cb, $params) = @_;

	Plugins::Bandcamp::Scraper::search_fans($client,
		sub {
			my ($items) = @_;

			my $search = $params->{search};
			add_recent_search($search) if ($search && scalar @$items);

			$search_results->{$client || ''}->{'fan_search'} = Plugins::Bandcamp::Plugin::artist_list({ results => $items });
			_search_done($client, $cb);
		},
		$params,
	);
}

sub _search_done {
	my ($client, $cb) = @_;

	return unless $search_results->{$client || ''}->{'tag_search'}
		&& ($search_results->{$client || ''}->{'artist_search'} || $search_results->{$client || ''}->{'search'})
		&& $search_results->{$client || ''}->{'fan_search'};

	my $hasTags = scalar @{ $search_results->{$client || ''}->{'tag_search'} };

	my $items = [
		( map {
			if ($hasTags) {
				$_->{name}  .= ' (' . cstring($client, 'ARTIST') . ')';
				$_->{line1} .= ' (' . cstring($client, 'ARTIST') . ')' if $_->{line1};
				$_->{image} ||= 'html/images/artists.png';
			}
			$_;
		} @{ $search_results->{$client || ''}->{'artist_search'} || [] } ),

		( map {
			my $pt = $_->{passthrough};
			if ($pt->[0]->{album_id}) {
				$_->{name}  .= ' (' . cstring($client, 'ALBUM') . ')';
				$_->{line1} .= ' (' . cstring($client, 'ALBUM') . ')' if $_->{line1};
				$_->{image} ||= 'html/images/albums.png';
			}
			elsif ($pt->[0]->{band_id}) {
				$_->{name}  .= ' (' . cstring($client, 'ARTIST') . ')';
				$_->{line1} .= ' (' . cstring($client, 'ARTIST') . ')' if $_->{line1};
				$_->{image} ||= 'html/images/artists.png';
			}
			$_;
		} @{ $search_results->{$client || ''}->{'search'} || [] } )
	];

	push @$items, map {
		if ($hasTags) {
			$_->{image} ||= 'html/images/artists.png';
		}
		$_;
	} @{ $search_results->{$client || ''}->{'fan_search'} };

	push @$items, sort {
		uc($a->{name}) cmp uc($b->{name})
	} @{$search_results->{$client || ''}->{'tag_search'}};

	# artist_list would add the EMTPY entry...
	my $empty = cstring($client, 'EMPTY');
	$items = [ grep {
		$_->{name} ne $empty
	} @$items ];

	if (!scalar @$items) {
		$items = [{
			name => $empty,
			type => 'text',
		}];
	}

	$cb->( {
		items => $items
	} );
}

sub add_recent_search {
	my $search = shift;

	return unless $search;

	$recent_searches{$search} = {
		ts => time(),
	};

	# don't cache %recent_searches directly, as it's a Tie::Cache::LRU object
	$cache->set('recent_searches', { map {
		$_ => $recent_searches{$_}
	} keys %recent_searches }, RECENT_CACHE_TTL);
}

sub recent_searches {
	my ($client, $cb, $args) = @_;

	my $recent = [
		sort { lc($a) cmp lc($b) }
		grep { $recent_searches{$_} }
		keys %recent_searches
	];

	my $items = [];

	foreach (@$recent) {
		push @$items, {
			type => 'link',
			name => $_,
			url  => \&search,
			passthrough => [{
				q => $_
			}],
		}
	}

	$items = [ {
		name => string('EMPTY'),
		type => 'text',
	} ] if !scalar @$items;

	$cb->({
		items => $items
	});
}

1;