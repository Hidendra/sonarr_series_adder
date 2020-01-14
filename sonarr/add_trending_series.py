"""
Adds trending series from Trakt to Sonarr
"""

import argparse
import sys
from trakt import Trakt

from .sonarr_api import SonarrAPI


def main():
    parser = argparse.ArgumentParser(description='Adds trending series from Trakt to Sonarr if they are not already there')
    parser.add_argument('--host', required=True, help='Sonarr host')
    parser.add_argument('--api-key', required=True, help='Sonarr API key')
    parser.add_argument('--client-cert', help='TLS client cert to connect to Sonarr with')
    parser.add_argument('--client-key', help='TLS client cert key to connect to Sonarr with')
    parser.add_argument('--trakt-client-id', help='Trakt OAuth client ID')
    parser.add_argument('--trakt-client-secret', help='Trakt OAuth client secret')
    parser.add_argument('--trakt-fetch-num', type=int, default=100, help='number of top trending shows to load from Trakt (default: 100)')

    args = parser.parse_args()

    Trakt.configuration.defaults.client(
        id=args.trakt_client_id,
        secret=args.trakt_client_secret,
    )

    api_url = 'https://%s/api' % args.host
    client_cert = (args.client_cert, args.client_key,)
    trakt_fetch_num = args.trakt_fetch_num

    sonarr = SonarrAPI(api_url, args.api_key, client_cert)

    """
    The Sonarr quality profile to use for downloads
    """
    sonarr_selected_quality_profile = None

    sonarr_quality_profiles = sonarr.get_quality_profiles()

    for profile in sonarr_quality_profiles:
        if profile['name'] == 'HD-1080p':
            sonarr_selected_quality_profile = profile['id']
            sys.stderr.write('using Sonarr quality profile: %s\n' % profile['name'])
            break

    if not sonarr_selected_quality_profile:
        sys.stderr.write('could not find suitable quality profile in Sonarr\n')
        return 1

    # tvdbId
    sonarr_series = {show['tvdbId']: show for show in sonarr.get_series()}

    sys.stderr.write('Loaded %d series from Sonarr\n' % len(sonarr_series))

    trending = Trakt['shows'].trending(pagination=True)[:trakt_fetch_num]

    sys.stderr.write('Inspecting %d trending shows from Trakt\n' % len(trending))

    # Trending Trakt tv shows
    for show in trending:
        try:
            tvdbid = int(next((v[1] for i, v in enumerate(show.keys) if v[0] == 'tvdb'), None))
        except TypeError:
            # No tvdb id
            continue

        show_full_title = '%s (%s)' % (show.title, show.year)

        if tvdbid not in sonarr_series:
            sys.stderr.write('adding series to Sonarr: %s\n' % show_full_title)

            series_json = sonarr.constuct_series_json(tvdbid, sonarr_selected_quality_profile)
            series_json['addOptions']['ignoreEpisodesWithoutFiles'] = False
            series_json['addOptions']['searchForMissingEpisodes'] = True

            sonarr.add_series(series_json)

    return 0


if __name__ == '__main__':
    sys.exit(main())
