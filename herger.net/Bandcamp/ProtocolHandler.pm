package Plugins::Bandcamp::ProtocolHandler;

use strict;
use base qw(Slim::Player::Protocols::HTTPS);

# use Scalar::Util qw(blessed);

use Slim::Utils::Log;

use Plugins::Bandcamp::Plugin;

use constant PAGE_URL_REGEX   => qr{^https?://(?:[a-z0-9-]+\.)?bandcamp\.com/}i;

Slim::Player::ProtocolHandlers->registerURLHandler(PAGE_URL_REGEX, __PACKAGE__) if Slim::Player::ProtocolHandlers->can('registerURLHandler');

my $log = logger('plugin.bandcamp');

sub new {
	my $class  = shift;
	my $args   = shift;

	my $client = $args->{client};
	my $song   = $args->{song};

	# use streaming url but avoid redirection loop
	my $streamUrl = ($args->{redir} ? $args->{url} : $song->streamUrl()) || return;

	main::INFOLOG && $log->info( 'Remote streaming Bandcamp track: ' . $streamUrl );

	my $sock = $class->SUPER::new( {
		url     => $streamUrl,
		song    => $args->{song},
		client  => $client,
		bitrate => 128_000,
	} ) || return;

	${*$sock}{contentType} = 'audio/mpeg';

	return $sock;
}

sub explodePlaylist {
	my ($class, $client, $url, $cb) = @_;

	if ($url =~ m{https?://bandcamp\.com/stream_redirect}) {
		return $cb->([$url]);
	}

	Plugins::Bandcamp::Plugin::get_item_info_by_url( $client, sub {
		$cb->([ map { $_->{'play'} // () } @{$_[0]} ]);
	}, {}, { 'url' => $url } );
}

sub getMetadataFor {
	my ( $class, $client, $url ) = @_;
	return Plugins::Bandcamp::Plugin::metadata_provider($client, $url);
}

sub scanUrl {
	my ($class, $url, $args) = @_;
	$args->{'cb'}->($args->{'song'}->currentTrack());
}

sub formatOverride { 'mp3' }

sub getNextTrack {
	my ($class, $song, $successCb, $errorCb) = @_;

	my $url = $song->currentTrack()->url;

	if ($url =~ /^http/) {
		$song->streamUrl($url);
		$successCb->();
		return;
	}

	# Get next track
	my $id = Plugins::Bandcamp::API::Common::track_key($url);

	Plugins::Bandcamp::API::get_track_info({
		track_id => $id
	}, sub {
		my $trackInfo = shift;
		my $redirect;

		if ($trackInfo && $trackInfo->{streaming_url}) {
			my $http = Slim::Networking::Async::HTTP->new;
			$http->send_request( {
				request     => HTTP::Request->new( HEAD => $trackInfo->{streaming_url} ),
				onRedirect  => sub {
					my $newRedirect = $http->response->headers->header('Location');

					$redirect = $newRedirect if $newRedirect;
				},
				onBody => sub {
					$song->streamUrl($redirect || $trackInfo->{streaming_url});
					$successCb->();
				},
				onError     => sub {
					my ($self, $error) = @_;
					$log->warn( "could not find Bandcamp header $error" );
					$errorCb->('PROBLEM_CONVERT_STREAM');
				},
			} );
		}
		else {
			$errorCb->('PROBLEM_CONVERT_STREAM');
		}
	});
}


1;