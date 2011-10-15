import gettext
from gettext import gettext as _
import gtk, webkit
import json
from oauth import oauth
import urllib2
import urlparse

from gwibber.microblog.util import resources

if hasattr(gettext, 'bind_textdomain_codeset'):
  gettext.bind_textdomain_codeset('gwibber','UTF-8')
gettext.textdomain('gwibber')

gtk.gdk.threads_init()

sigmeth = oauth.OAuthSignatureMethod_HMAC_SHA1()


class AccountWidget(gtk.VBox):
  """
  AccountWidget: A widget that provides a user interface for configuring
  facebook accounts in Gwibber
  """

  def __init__(self, account=None, dialog=None):
    """Creates the account pane for configuring Google+ accounts"""
    gtk.VBox.__init__(self, False, 20)
    self.ui = gtk.Builder()
    self.ui.set_translation_domain("gwibber")
    self.ui.add_from_file(resources.get_ui_asset("gwibber-accounts-googleplus.ui"))
    self.ui.connect_signals(self)
    self.vbox_settings = self.ui.get_object("vbox_settings")
    self.pack_start(self.vbox_settings, False, False)
    self.show_all()

    self.account = account or {}
    self.dialog = dialog

    if self.account.get("access_token", 0) and self.account.get("username", 0):
      self.ui.get_object("hbox_googleplus_auth").hide()
      self.ui.get_object("fb_auth_done_label"). \
              set_label(_("%s has been authorized by Google+") %
                        self.account["username"])
      self.ui.get_object("hbox_googleplus_auth_done").show()
    else:
      self.ui.get_object("hbox_googleplus_auth_done").hide()
      if self.dialog.ui:
        self.dialog.ui.get_object('vbox_create').hide()

  def on_googleplus_auth_clicked(self, widget, data=None):
    self.winsize = self.window.get_size()

    web = webkit.WebView()
    web.get_settings().set_property("enable-plugins", False)
    web.load_html_string(_("<p>Please wait...</p>"), "file:///")

    self.consumer = oauth.OAuthConsumer("anonymous", "anonymous")

    params = {
      "oauth_consumer_key": self.consumer.key,
      "oauth_timestamp": oauth.generate_timestamp(),
      "oauth_nonce": oauth.generate_nonce(),
      "oauth_version": oauth.OAuthRequest.version,
      "oauth_callback": "http://www.gwibber.com/0/auth.html",
      "scope": "https://www.googleapis.com/auth/plus.me",
    }

    request = oauth.OAuthRequest("POST","https://www.google.com/accounts/OAuthGetRequestToken", params)
    request.sign_request(sigmeth, self.consumer, token=None)

    tokendata = urllib2.urlopen(request.http_url, request.to_postdata()).read()
    print tokendata
    self.token = oauth.OAuthToken.from_string(tokendata)

    url = "https://www.google.com/accounts/OAuthAuthorizeToken?oauth_token=" + self.token.key

    web.load_uri(url)
    web.set_size_request(450, 340)
    web.connect("title-changed", self.on_googleplus_auth_title_change)

    scroll = gtk.ScrolledWindow()
    scroll.add(web)

    self.pack_start(scroll, True, True, 0)
    self.show_all()

    self.ui.get_object("vbox1").hide()
    self.ui.get_object("vbox_advanced").hide()

  def on_googleplus_auth_title_change(self, web=None, title=None, data=None):
    if title.get_title() == "Success":
      url = web.get_main_frame().get_uri()
      data = urlparse.parse_qs(url.split("?", 1)[1])
      verifier = data["oauth_verifier"][0]
      self.token.set_verifier(verifier)

      http_url = "https://www.google.com/accounts/OAuthGetAccessToken"
      request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                                                           self.token, 
                                                           verifier=verifier,
                                                           http_url=http_url)
      request.sign_request(sigmeth, self.consumer, self.token)

      tokendata = urllib2.urlopen(request.to_url()).read()
      data = urlparse.parse_qs(tokendata)

      self.account["access_token"] = data["oauth_token"][0]
      self.account["secret_token"] = data["oauth_token_secret"][0]

      token = oauth.OAuthToken(self.account["access_token"],
                               self.account["secret_token"])

      http_url = "https://www.googleapis.com/plus/v1/people/me/activities/public"
      params = {"alt": "json"}
      request = oauth.OAuthRequest.from_consumer_and_token(self.consumer,
                                                           token,
                                                           http_url=http_url,
                                                           parameters=params)
      request.sign_request(sigmeth, self.consumer, token)

      print request.to_url()
      data = json.loads(urllib2.urlopen(request.to_url()).read())["data"]
      self.account["username"] = data["displayName"]
      self.account["user_id"] = data["id"]

      self.ui.get_object("hbox_googleplus_auth").hide()
      label = _("%s has been authorized by Google+") % str(self.account["username"])
      self.ui.get_object("fb_auth_done_label").set_label(label)
      self.ui.get_object("hbox_googleplus_auth_done").show()
      if self.dialog.ui:
        self.dialog.ui.get_object("vbox_create").show()

      web.hide()
      self.window.resize(*self.winsize)
      self.ui.get_object("vbox1").show()
      self.ui.get_object("vbox_advanced").show()

    if title.get_title() == "Failure":
      d = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
        gtk.BUTTONS_OK, _("Authorization failed. Please try again."))
      if d.run(): d.destroy()

      web.hide()
      self.window.resize(*self.winsize)
