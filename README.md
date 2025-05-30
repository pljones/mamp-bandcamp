# MusicAssistant Music Provider for Bandcamp

This is a response to a [Music Assisant discussion](https://github.com/orgs/music-assistant/discussions/2315) where
the idea of having Bandcamp as a music provider in Music Assistant was raised.

Other existing software, such as [Lyrion](https://github.com/LMS-Community/slimserver), already have Bandcamp integration and
the work needed to port from the LMS plugin to MA seemed fairly straight forwards.

As an exercise in getting CoPilot to do its job - now that it is free to use on GitHub - I decided to ask it to supply a complete
implementation for Music Assistant, based on the work done for Lyrion.  This repository is based on the results.

Here is what I asked CoPilot to do:
<blockquote>
Can you provide something like the MusicAssistant YouTube plugin
<br/>https://github.com/music-assistant/server/blob/dev/music_assistant/providers/ytmusic/__init__.py
<br/>but for Bandcamp, based on the LMS Bandcamp plugin from
<br/>https://github.com/LMS-Community/slimserver/blob/public/9.1/Slim/Plugin/OnlineLibrary/Plugin.pm
<br/>This should be a full implementation, with all necessary files.
All rights of the original creators of the source should be annotated with the necessary licence notices included.
</blockquote>

....

...a dream is just a dream...

Time went by, certainly.  It became clearer that AI was not going to be able to parse the LMS data structures, form a model
of what the Bandcamp LMS plugin was doing in concrete terms, abstract that model, parse the MA data structures, form an
abstract model of what an MA music provider should do, map the LMS Bandcamp plugin abstract model to the MA music provider
abstract model and then generate a concrete implementation of that model.

Yes, it sounds like a lot of hard work.  That, of course, is why I wanted to off-load it.

None of the AI models could self-monitor progress, identify failures, identify loops, recover from errors, nor even simply
keep track of the goal.

So this branch is archived at this point.  The next commit will revert "main" back to the beginning and start over - by hand.

....

During the development cycle with CoPilot, I had to provide it with the unpacked ZIP of the LMS BandsCampout
perl source.  That is also available in this repository.  CoPilot used this to develop the Bandcamp-specific features.

The MusicAssistant YouTube Music provider was used to guide the structure for the resultant MA provider, including
the cookie-based authentication.

This repository includes [the full CoPilot Session transcript](CoPilot-Session-transcript.log).

# License Information

## LMS Bandcamp Plugin
The LMS Bandcamp plugin is licensed under the GNU General Public License, version 2. All modifications and derivations include proper attribution.

## MusicAssistant YouTube Plugin
The MusicAssistant YouTube plugin is used as a reference under its respective license.  (Apache License Version 2.0)

## Bandcamp Plugin Implementation
This implementation is a derivative work based on the above-mentioned plugins and adheres to their licensing terms.
It can be redistribute under the GNU Affero General Public License Version 3.
