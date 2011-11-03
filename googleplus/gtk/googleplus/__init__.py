import gettext
from gettext import gettext as _
import gtk
import json
from oauth import oauth
import pango
import urllib2
import urlparse
import webkit

from gwibber.microblog.util import resources

if hasattr(gettext, 'bind_textdomain_codeset'):
  gettext.bind_textdomain_codeset('gwibber','UTF-8')
gettext.textdomain('gwibber')

gtk.gdk.threads_init()

sigmeth = oauth.OAuthSignatureMethod_HMAC_SHA1()

OAUTH_URL = "https://accounts.google.com/o/oauth2/auth"
CLIENT_ID = "939657648296-rple60h3f0qa1lp78d8g95mdj4nddosf.apps.googleusercontent.com"
CLIENT_SECRET = "gNxO6p7Vp_XWjqbyGkbBAOaW"
REDIRECT_URI = "http://gwibber.com/0/auth.html"
SCOPE = "https://www.googleapis.com/auth/plus.me"


class AccountWidget(gtk.VBox):
  """
  AccountWidget: A widget that provides a user interface for configuring
  Google+ accounts in Gwibber
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
      self.ui.get_object("googleplus_auth_done_label"). \
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

    url = '%s?client_id=%s&redirect_uri=%s&scope=%s&response_type=token' % \
          (OAUTH_URL, CLIENT_ID, REDIRECT_URI, SCOPE)

    web.load_uri(url)
    web.set_size_request(500, 400)
    web.connect("title-changed", self.on_googleplus_auth_title_change)

    self.scroll = gtk.ScrolledWindow()
    self.scroll.add(web)

    self.pack_start(self.scroll, True, True, 0)
    self.show_all()

    self.ui.get_object("vbox1").hide()
    self.ui.get_object("vbox_advanced").hide()
    self.dialog.infobar.set_message_type(gtk.MESSAGE_INFO)

  def on_googleplus_auth_title_change(self, web=None, title=None, data=None):
    if title.get_title() == "Success":
      if hasattr(self.dialog, "infobar_content_area"):
        for child in self.dialog.infobar_content_area.get_children():
          child.destroy()
      self.dialog.infobar_content_area = self.dialog.infobar.get_content_area()
      self.dialog.infobar_content_area.show()
      self.dialog.infobar.show()

      message_label = gtk.Label(_("Verifying"))
      message_label.set_use_markup(True)
      message_label.set_ellipsize(pango.ELLIPSIZE_END)
      self.dialog.infobar_content_area.add(message_label)
      self.dialog.infobar.show_all()
      self.scroll.hide()

      # Get the access_token from the callback uri
      # it's formatted as http://gwibber.com/0/auth.html#access_token=1/QbIbRMWW
      url = web.get_main_frame().get_uri()
      data = urlparse.parse_qs(url.split("#", 1)[1])
      self.access_token = data["access_token"][0]
      self.account["access_token"] = self.access_token

      self.ui.get_object("vbox1").show()
      self.ui.get_object("vbox_advanced").show()

      # Make a request with our new token for the user's own data
      url = "https://www.googleapis.com/plus/v1/people/me?oauth_token=" + \
            self.access_token
      data = json.load(urllib2.urlopen(url))
      self.account["username"] = str(data["displayName"])
      self.account["user_id"] = data["id"]

      if isinstance(data, dict):
        if data.has_key("id"):
          saved = self.dialog.on_edit_account_save()
        else:
          print "Failed"
          self.dialog.infobar.set_message_type(gtk.MESSAGE_ERROR)
          message_label.set_text(_("Authorization failed. Please try again."))
      else:
        print "Failed"
        self.dialog.infobar.set_message_type(gtk.MESSAGE_ERROR)
        message_label.set_text(_("Authorization failed. Please try again."))

      if saved:
        message_label.set_text(_("Successful"))
        self.dialog.infobar.set_message_type(gtk.MESSAGE_INFO)
        #self.dialog.infobar.hide()

      self.ui.get_object("hbox_googleplus_auth").hide()
      label = _("%s has been authorized by Google+") % self.account["username"]
      self.ui.get_object("googleplus_auth_done_label").set_label(label)
      self.ui.get_object("hbox_googleplus_auth_done").show()
      if self.dialog.ui and self.account.has_key("id") and not saved:
        self.dialog.ui.get_object("vbox_save").show()
      elif self.dialog.ui and not saved:
        self.dialog.ui.get_object("vbox_create").show()

    self.window.resize(*self.winsize)

    if title.get_title() == "Failure":
      web.hide()
      self.dialog.infobar.set_message_type(gtk.MESSAGE_ERROR)
      message_label.set_text(_("Authorization failed. Please try again."))
      self.dialog.infobar.show_all()

      self.ui.get_object("vbox1").show()
      self.ui.get_object("vbox_advanced").show()
      self.window.resize(*self.winsize)
