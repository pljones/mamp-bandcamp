package Plugins::Bandcamp::Settings;

use strict;
use base qw(Slim::Web::Settings);

use Slim::Utils::Prefs;

my $prefs = preferences('plugin.bandcamp');

sub name {
	return 'PLUGIN_BANDCAMP';
}

sub prefs {
	return ($prefs, 'username', 'identity_token');
}

sub page {
	return 'plugins/Bandcamp/settings.html';
}

1;