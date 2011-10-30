import urllib2, json

from gwibber.microblog import util

PROTOCOL_INFO = {
  "name": "Google+",
  "version": "0.1",

  "config": [
    "color",
    "username",
    "access_token",
  ],

  "authtype": "oauth2",
  "color": "#0773DD",

  "features": [
    "receive",
  ],

  "default_streams": [
    "receive",
  ],
}

URL_PREFIX = "https://www.googleapis.com/plus/v1"

class Client:
  def __init__(self, account):
    self.service = util.getbus("Service")
    if account.has_key("secret_token") and account.has_key("password"):
        account.pop("password")
    self.account = account

    if (not account.has_key("access_token") and
        not account.has_key("secret_token")):
        return [{"error": {
                    "type": "auth",
                    "account": self.account,
                    "message": _("Failed to find credentials")
                 }}]

    self.token = account["access_token"]

  def _actor(self, user):
    return {
        "name": user["name"],
        "nick": user["id"],
        "id": user["id"],
        "image": user.get("thumbnailUrl", "https://mail.google.com/mail/images/blue_ghost.jpg?sz=45"),
        "url": user.get("profileUrl", None),
        "is_me": user["id"] == self.account["user_id"],
    }

  def _message(self, data):
    m = {
        "mid": data["id"],
        "service": "google+",
        "account": self.account["id"],
        "time": util.parsetime(data["published"]),
        "url": data.get("links", {})["alternate"][0].get("href", ""),
        "source": data.get("source", {}).get("title", None),
        "sender": self._actor(data["actor"]),
    }

    m["text"] = data["object"]["content"]

    if data.get("source", {}).get("title", 0) == "Twitter":
      m["text"] = m["text"].split(">:", 1)[1].strip()
    
    m["html"] = m["text"]
    m["content"] = m["text"]

    if data.get("geocode", 0):
      m["location"] = {
          "lat": data["geocode"].split()[0],
          "lon": data["geocode"].split()[1],
      }

      if data.get("address", 0):
        m["location"]["address"] = data["address"]

    m["images"] = []
    for a in data["object"].get("attachments", []):
      if a["type"] == "photo":
        m["images"].append({
          "src": a["links"]["preview"][0]["href"],
          "url": a["links"]["enclosure"][0]["href"]
        })

      if a["type"] == "video":
        m["images"].append({
          "src": a["links"]["preview"][0]["href"],
          "url": a["links"]["alternate"][0]["href"],
        })

      if a["type"] == "article":
        m["content"] += "<p><b><a href=\"%s\">%s</a></b></p>" % (a["links"]["alternate"][0]["href"], a["title"])

    return m

  def _get(self, path, collection="items", parse="message", post=False,
           single=False, body=None, **args):

    url = "/".join((URL_PREFIX, path))
    
    url = url + "?oauth_token=" + self.token
    print url
    data = json.load(urllib2.urlopen(url))
    print data
    if single: return [getattr(self, "_%s" % parse)(data)]
    if parse: return [getattr(self, "_%s" % parse)(m) for m in data[collection]]
    else: return []

  def __call__(self, opname, **args):
    return getattr(self, opname)(**args)

  def receive(self, count=util.COUNT, since=None):
    return self._get("/people/me/activities/public", single=True)

  def user_messages(self, id, count=util.COUNT, since=None):
    return self._get("people/%s/activities/public" % id)

  # commented out buzz methods that can't be used in Google Plus readonly API
  #def send(self, message):
  #  text = json.dumps({"data": {"object": {"type": "note", "content": message}}})
  #  return self._get("activities/@me/@self", post=True, single=True, body=text)

  #def send_thread(self, message, target):
  #  text = json.dumps({"data": {"object": {"content": message}}})
  #  path = "activities/%s/@self/%s/@comments" % (target["sender"]["id"], target["mid"])
  #  self._get(path, post=True, single=True, body=text)
  #  return []


