from __future__ import absolute_import, unicode_literals

import octoprint.plugin
import vimeo
from slack import WebClient


class SlackNotifyPlugin(octoprint.plugin.EventHandlerPlugin,
                        octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.TemplatePlugin):
    def get_settings_defaults(self):
        return dict(vimeo_token=None, vimeo_key=None, vimeo_secret=None,
                    bot_token=None, channel_id=None)

    def get_settings_restricted_paths(self):
        return dict(admin=["bot_token", "vimeo_token",
                           "vimeo_key", "vimeo_secret"])

    def _send_to_slack(self, message, media=None, filename=None):
        slack_token = self._settings.get(['bot_token'])
        recipient = self._settings.get(['channel_id'])
        if not slack_token or not recipient:
            self._logger.warning('Slack settings misconfigured')
            return

        slack_client = WebClient(slack_token)

        if media:
            vimeo_token = self._settings.get(['vimeo_token'])
            vimeo_key = self._settings.get(['vimeo_key'])
            vimeo_secret = self._settings.get(['vimeo_secret'])
            vimeo_client = vimeo.VimeoClient(
                token=vimeo_token,
                key=vimeo_key,
                secret=vimeo_secret,
            )
            vimeo_uri = vimeo_client.upload(media, data={
                'name': filename,
                'description': 'Automated upload from printer'
            })
            vimeo_id = vimeo_uri.split('/').pop()
            vimeo_url = 'https://vimeo.com/' + vimeo_id
            message = message + '. Upladed to vimeo ' + vimeo_url
            self._logger.info(message)

        slack_client.chat_postMessage(
            channel=recipient,
            text=message)

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
            self._send_to_slack(
                message,
                media=payload['movie'],
                filename=payload['movie_basename'])
        else:
            return

    def get_template_configs(self):
        return [
            dict(type="settings", name="Slack Notify", custom_bindings=False)
        ]


__plugin_implementation__ = SlackNotifyPlugin()

__plugin_pythoncompat__ = ">=3,<4"
