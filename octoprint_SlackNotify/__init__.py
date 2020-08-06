from __future__ import absolute_import, unicode_literals

import os

import octoprint.plugin
from slackclient import SlackClient

from moviepy.editor import *


class SlackNotifyPlugin(octoprint.plugin.EventHandlerPlugin,
                        octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.TemplatePlugin):
    def get_settings_defaults(self):
        return dict(bot_token=None, channel_id=None)

    def get_settings_restricted_paths(self):
        return dict(admin=["bot_token"])

    def _time_symetrize(self, clip):
        """ Returns the clip played forwards then backwards. In case
        you are wondering, vfx (short for Video FX) is loaded by
        >>> from moviepy.editor import * """
        return concatenate([clip, clip.fx(vfx.time_mirror)])

    def _send_to_slack(self, message, media=None):
        token = self._settings.get(['bot_token'])
        recipient = self._settings.get(['channel_id'])
        if not token or not recipient:
            self._logger.warning('Slack settings misconfigured')
            return

        client = SlackClient(token)

        if media:
            # Videos don't automatically unfurl, so convert to a gif

            # NOTE: Broken, requies `export FFMPEG_BINARY=/usr/bin/ffmpeg` and still throws an error

            gif_file = media + ".gif"
            clip = (VideoFileClip(media, audio=False)
                    .fx(self._time_symetrize))
            clip.write_gif(gif_file)
            # Send gif
            result = client.api_call(
                "files.upload",
                channels=[recipient],
                file=open(gif_file, 'rb'),
                title=message,
            )
            os.remove(gif_file) # Clean up
        else:
            result = client.api_call(
                "chat.postMessage",
                channel=recipient,
                text=message,
            )

    def on_event(self, event, payload):
        if event == 'PrintStarted':
            message = 'Started printing %s' % payload['name']
            self._send_to_slack(message)
        elif event == 'PrintFailed':
            message = 'Failed to print %s after %s with reason: %s' % (
                payload['name'], payload['time'], payload['reason'])
            self._send_to_slack(message)
        elif event == 'PrintCancelling':
            message = 'Cancelled print %s with message: %s' % (
                payload['name'], payload['firmwareError'])
            self._send_to_slack(message)
        elif event == 'PrintDone':
            message = 'Finished printing %s total print time %s' % (
                payload['name'], payload['time'])
            self._send_to_slack(message)
        elif event == 'MovieDone':
            message = 'Finished rendering timelapse for %s' % payload['gcode']
            self._send_to_slack(message, payload['movie'])
        else:
            return

    def get_template_configs(self):
        return [
            dict(type="settings", name="Slack Notify", custom_bindings=False)
        ]


__plugin_implementation__ = SlackNotifyPlugin()
