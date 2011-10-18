============
 gwibber-plugins-googleplus
============

The plugin provides Google+ functionality limited to the API's current state. It is based on Buzz plugin.

For now it's just read-only and not fully working - you can only get authorized with your Google Account.

ToDo:
* rewrite the plugin to use OAuth 2.0
* authorize with Google+ through an API key, not a website call
* work out a way to load friends' content

Usage
-----------

Copy the googleplus directory to /usr/share/gwibber/plugins
and restart gwibber-service.
