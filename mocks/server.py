"""Mock server simulating all third-party platforms for zero-key contract and e2e testing."""

from fastapi import FastAPI, Header, HTTPException, Response, Request
from fastapi.responses import JSONResponse
import uuid
import time
import hmac
import hashlib

mock_app = FastAPI(title="IncuBrix Mock Platform Server")

# In-memory storage for mock server
MOCK_DISCOURSE_POSTS = {}
MOCK_LEMMY_POSTS = {}
MOCK_DEVTO_ARTICLES = {}
MOCK_GHOST_POSTS = {}
MOCK_WEBHOOK_DELIVERIES = {}
MOCK_HASHNODE_POSTS = {}
MOCK_SLACK_MESSAGES = {}

# Flags to trigger simulated failures
FLAGS = {
    "discourse_rate_limit": False,
    "discourse_timeout": False,
    "field_rename_drift": False,
    "webhook_revoked": False,
    "auth_expired": False,
}


@mock_app.post("/control/flags")
def set_flags(new_flags: dict):
    FLAGS.update(new_flags)
    return {"flags": FLAGS}


# -------------------------------------------------------------
# Discourse Mock
# -------------------------------------------------------------
@mock_app.post("/discourse/posts.json")
async def discourse_create_post(request: Request):
    if FLAGS.get("discourse_timeout"):
        time.sleep(3.0)  # simulate delay for timeout tests

    if FLAGS.get("discourse_rate_limit"):
        return JSONResponse(
            status_code=429,
            content={"errors": ["Rate limit exceeded"]},
            headers={"Retry-After": "15"},
        )

    auth = request.headers.get("Api-Key")
    if auth == "invalid-key" or FLAGS.get("auth_expired"):
        return JSONResponse(status_code=403, content={"errors": ["Invalid API key"]})

    body = await request.json()
    post_id = str(len(MOCK_DISCOURSE_POSTS) + 100)
    topic_id = str(int(post_id) + 500)
    topic_slug = body.get("title", "topic").lower().replace(" ", "-")[:20]

    record = {
        "id": int(post_id),
        "name": "mock_user",
        "username": request.headers.get("Api-Username", "system"),
        "raw": body.get("raw"),
        "topic_id": int(topic_id),
        "topic_slug": topic_slug,
        "reads": 42,
        "score": 10,
        "reply_count": 2,
        "actions_summary": [{"id": 2, "count": 5}],
    }

    if FLAGS.get("field_rename_drift"):
        # Drifts "id" to "identifier_token"
        drifted = {k: v for k, v in record.items() if k != "id"}
        drifted["identifier_token"] = int(post_id)
        return JSONResponse(content=drifted)

    MOCK_DISCOURSE_POSTS[post_id] = record
    return JSONResponse(content=record)


@mock_app.get("/discourse/posts/{post_id}.json")
def discourse_get_post(post_id: str):
    if post_id not in MOCK_DISCOURSE_POSTS:
        return JSONResponse(status_code=404, content={"errors": ["Not found"]})
    return JSONResponse(content=MOCK_DISCOURSE_POSTS[post_id])


@mock_app.delete("/discourse/posts/{post_id}.json")
def discourse_delete_post(post_id: str):
    if post_id in MOCK_DISCOURSE_POSTS:
        del MOCK_DISCOURSE_POSTS[post_id]
    return JSONResponse(content={"success": "OK"})


# -------------------------------------------------------------
# Lemmy Mock
# -------------------------------------------------------------
@mock_app.post("/lemmy/api/v3/user/login")
def lemmy_login(data: dict):
    if data.get("password") == "wrong":
        return JSONResponse(status_code=400, content={"error": "incorrect_login"})
    return {"jwt": "mock-lemmy-jwt-token-abcdef123"}


@mock_app.post("/lemmy/api/v3/post")
def lemmy_create_post(data: dict, authorization: str = Header(None)):
    if not authorization or "mock-lemmy" not in authorization:
        return JSONResponse(status_code=401, content={"error": "not_logged_in"})
    post_id = len(MOCK_LEMMY_POSTS) + 1
    post_view = {
        "post_view": {
            "post": {
                "id": post_id,
                "name": data.get("name"),
                "body": data.get("body"),
                "deleted": False,
            },
            "counts": {"comments": 4, "score": 12, "upvotes": 12, "downvotes": 0},
            "community": {"name": "technology"},
        }
    }
    MOCK_LEMMY_POSTS[str(post_id)] = post_view
    return post_view


@mock_app.get("/lemmy/api/v3/post")
def lemmy_get_post(id: int):
    post_id = str(id)
    if post_id not in MOCK_LEMMY_POSTS:
        return JSONResponse(status_code=404, content={"error": "post_not_found"})
    return MOCK_LEMMY_POSTS[post_id]


@mock_app.post("/lemmy/api/v3/post/delete")
def lemmy_delete_post(data: dict, authorization: str = Header(None)):
    post_id = str(data.get("post_id"))
    if post_id in MOCK_LEMMY_POSTS:
        MOCK_LEMMY_POSTS[post_id]["post_view"]["post"]["deleted"] = True
    return {"post_view": MOCK_LEMMY_POSTS.get(post_id, {})}


# -------------------------------------------------------------
# Dev.to Mock
# -------------------------------------------------------------
@mock_app.post("/devto/api/articles")
def devto_create_article(data: dict, api_key: str = Header(None, alias="api-key")):
    if api_key == "invalid-key":
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    article_id = len(MOCK_DEVTO_ARTICLES) + 1000
    art = data.get("article", {})
    record = {
        "id": article_id,
        "title": art.get("title"),
        "body_markdown": art.get("body_markdown"),
        "url": f"http://localhost:8080/devto/articles/{article_id}",
        "published": art.get("published", True),
        "page_views_count": 89,
        "positive_reactions_count": 18,
        "comments_count": 7,
    }
    MOCK_DEVTO_ARTICLES[str(article_id)] = record
    return record


@mock_app.get("/devto/api/articles/{article_id}")
def devto_get_article(article_id: str):
    if article_id not in MOCK_DEVTO_ARTICLES:
        return JSONResponse(status_code=404, content={"error": "not found"})
    return MOCK_DEVTO_ARTICLES[article_id]


@mock_app.delete("/devto/api/articles/{article_id}")
def devto_delete_article(article_id: str):
    if article_id in MOCK_DEVTO_ARTICLES:
        del MOCK_DEVTO_ARTICLES[article_id]
    return Response(status_code=204)


# -------------------------------------------------------------
# Ghost Mock
# -------------------------------------------------------------
@mock_app.post("/ghost/ghost/api/admin/posts/")
def ghost_create_post(data: dict, authorization: str = Header(None)):
    if not authorization or "Ghost" not in authorization:
        return JSONResponse(status_code=401, content={"errors": [{"message": "Invalid token"}]})
    post_data = data.get("posts", [{}])[0]
    post_id = f"ghost_{len(MOCK_GHOST_POSTS)+1}"
    record = {
        "id": post_id,
        "uuid": str(uuid.uuid4()),
        "title": post_data.get("title"),
        "slug": post_data.get("slug", "test-post"),
        "status": "published",
        "url": f"http://localhost:8080/ghost/{post_data.get('slug', 'test-post')}/",
    }
    MOCK_GHOST_POSTS[post_id] = record
    return {"posts": [record]}


@mock_app.get("/ghost/ghost/api/admin/posts/{post_id}/")
def ghost_get_post(post_id: str):
    if post_id not in MOCK_GHOST_POSTS:
        return JSONResponse(status_code=404, content={"errors": [{"message": "Post not found"}]})
    return {"posts": [MOCK_GHOST_POSTS[post_id]]}


@mock_app.delete("/ghost/ghost/api/admin/posts/{post_id}/")
def ghost_delete_post(post_id: str):
    if post_id in MOCK_GHOST_POSTS:
        del MOCK_GHOST_POSTS[post_id]
    return Response(status_code=204)


# -------------------------------------------------------------
# Generic Signed Webhook (HMAC) Partner Mock
# -------------------------------------------------------------
@mock_app.post("/webhook-partner/publish")
async def webhook_partner_publish(request: Request):
    if FLAGS.get("webhook_revoked"):
        return JSONResponse(
            status_code=410,
            content={"error": "Partner connection revoked or disabled"},
        )

    signature = request.headers.get("X-IncuBrix-Signature")
    timestamp = request.headers.get("X-IncuBrix-Timestamp")
    if not signature or not timestamp:
        return JSONResponse(status_code=401, content={"error": "Missing signature or timestamp"})

    raw_body = await request.body()
    secret = b"partner-secret-123456"
    expected = hmac.new(secret, f"{timestamp}.".encode() + raw_body, hashlib.sha256).hexdigest()

    # Replay protection check
    now = int(time.time())
    if abs(now - int(timestamp)) > 300:
        return JSONResponse(status_code=401, content={"error": "Timestamp outside acceptable window"})

    delivery_id = f"wh_{len(MOCK_WEBHOOK_DELIVERIES)+1}"
    MOCK_WEBHOOK_DELIVERIES[delivery_id] = {
        "status": "received",
        "timestamp": timestamp,
        "live_url": f"https://partner.com/posts/{delivery_id}",
    }
    return JSONResponse(
        content={
            "delivery_id": delivery_id,
            "live_url": f"https://partner.com/posts/{delivery_id}",
            "status": "published",
        }
    )


@mock_app.get("/webhook-partner/status/{delivery_id}")
def webhook_partner_status(delivery_id: str):
    if delivery_id not in MOCK_WEBHOOK_DELIVERIES:
        return JSONResponse(status_code=404, content={"error": "Delivery not found"})
    return MOCK_WEBHOOK_DELIVERIES[delivery_id]


@mock_app.delete("/webhook-partner/delete/{delivery_id}")
def webhook_partner_delete(delivery_id: str):
    if delivery_id in MOCK_WEBHOOK_DELIVERIES:
        del MOCK_WEBHOOK_DELIVERIES[delivery_id]
    return JSONResponse(content={"deleted": True})


# -------------------------------------------------------------
# Hashnode Mock (GraphQL)
# -------------------------------------------------------------
@mock_app.post("/hashnode/graphql")
async def hashnode_graphql(request: Request):
    body = await request.json()
    query = body.get("query", "")
    if "publishPost" in query:
        post_id = f"hn_{len(MOCK_HASHNODE_POSTS)+1}"
        record = {
            "id": post_id,
            "title": "Hashnode Post",
            "url": f"https://blog.hashnode.dev/{post_id}",
            "views": 250,
            "reactionCount": 35,
            "responseCount": 8,
        }
        MOCK_HASHNODE_POSTS[post_id] = record
        return {"data": {"publishPost": {"post": record}}}
    elif "removePost" in query:
        return {"data": {"removePost": {"post": {"id": "removed"}}}}
    elif "post(" in query:
        post_id = list(MOCK_HASHNODE_POSTS.keys())[0] if MOCK_HASHNODE_POSTS else "hn_1"
        return {"data": {"post": MOCK_HASHNODE_POSTS.get(post_id, {"views": 100})}}
    return {"data": {}}


# -------------------------------------------------------------
# Slack App Mock
# -------------------------------------------------------------
@mock_app.post("/slack/api/chat.postMessage")
async def slack_post_message(request: Request):
    body = await request.json()
    msg_id = f"msg_{int(time.time())}"
    MOCK_SLACK_MESSAGES[msg_id] = body
    return {
        "ok": True,
        "channel": body.get("channel", "C12345"),
        "ts": f"{time.time()}",
        "message": {"bot_id": "B123", "text": body.get("text")},
    }


@mock_app.post("/slack/api/chat.delete")
async def slack_delete_message(request: Request):
    return {"ok": True, "channel": "C12345", "ts": "123.456"}
