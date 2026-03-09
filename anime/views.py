import requests
import razorpay
import re
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from django.http import Http404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import WatchList
from .models import SubscriptionPlan, UserSubscription
from django.shortcuts import get_object_or_404



JIKAN_BASE_URL = "https://api.jikan.moe/v4"



def home(request):
    query = request.GET.get("q")
    selected_genres = request.GET.getlist("genre")

    # pagination
    page = int(request.GET.get("page", 1))
    limit = 12

    # ---------- MAIN ANIME LIST ----------
    if query:
        url = f"{JIKAN_BASE_URL}/anime"
        params = {
            "q": query,
            "page": page,
            "limit": limit,
        }
    else:
        url = f"{JIKAN_BASE_URL}/top/anime"
        params = {
            "page": page,
            "limit": limit,
        }

    resp = requests.get(url, params=params)
    data = resp.json()

    anime_list = data.get("data", [])
    pagination = data.get("pagination", {})

    # ---------- GENRE FILTER ----------
    all_genres = set()
    for anime in anime_list:
        for g in anime.get("genres", []):
            all_genres.add(g["name"])
    all_genres = sorted(all_genres)

    if selected_genres:
        anime_list = [
            anime for anime in anime_list
            if any(g["name"] in selected_genres for g in anime.get("genres", []))
        ]

    # ---------- 🔥 TRENDING ANIME ----------
    trending_anime = []

    if not query:
        trending_url = f"{JIKAN_BASE_URL}/anime"
        trending_params = {
            "order_by": "popularity",
            "sort": "asc",
            "limit": 10
        }

        trending_resp = requests.get(trending_url, params=trending_params)
        trending_data = trending_resp.json()

        for anime in trending_data.get("data", []):
            trending_anime.append({
                "mal_id": anime["mal_id"],
                "title": anime["title"],
                "image": anime["images"]["jpg"]["image_url"],
            })

    # ---------- 🎬 UPCOMING ANIME ----------
    upcoming_anime = []

    if not query:
        upcoming_url = f"{JIKAN_BASE_URL}/top/anime"
        upcoming_params = {
            "filter": "upcoming",
            "limit": 5
        }

        upcoming_resp = requests.get(upcoming_url, params=upcoming_params)
        upcoming_data = upcoming_resp.json()

        for anime in upcoming_data.get("data", []):
            upcoming_anime.append({
                "mal_id": anime["mal_id"],
                "title": anime["title"],
                "image": anime["images"]["jpg"]["large_image_url"],
                "synopsis": anime.get("synopsis", "No description available."),
                "type": anime.get("type"),
                "episodes": anime.get("episodes"),
                "year": anime.get("year"),
            })

    # ---------- CONTEXT ----------
    context = {
        "anime_list": anime_list,
        "query": query or "",
        "all_genres": all_genres,
        "selected_genres": selected_genres,
        "page": page,
        "has_next": pagination.get("has_next_page", False),
        "trending_anime": trending_anime,
        "upcoming_anime": upcoming_anime,
    }

    return render(request, "anime/home.html", context)





def anime_detail(request, mal_id):

    # ---------- FETCH ANIME DETAILS ----------
    url = f"{JIKAN_BASE_URL}/anime/{mal_id}"
    resp = requests.get(url)
    data = resp.json()

    anime = data.get("data")

    if not anime:
        return render(request, "404.html", status=404)

    # ---------- CHECK WATCHLIST ----------
    in_watchlist = False

    if request.user.is_authenticated:
        in_watchlist = WatchList.objects.filter(
            user=request.user,
            mal_id=mal_id
        ).exists()

    # ---------- CONTEXT ----------
    context = {
        "anime": anime,
        "in_watchlist": in_watchlist,
    }

    return render(request, "anime/anime_detail.html", context)


@login_required
def watch_episode(request, mal_id: int, episode_number: int):

    # ===============================
    # 0️⃣ SUBSCRIPTION CHECK
    # ===============================
    try:
        user_sub = UserSubscription.objects.get(user=request.user, active=True)
    except UserSubscription.DoesNotExist:
        messages.error(request, "You need an active subscription to watch episodes.")
        return redirect("anime:subscriptions")  # ✅ make sure this URL name exists

    if not user_sub.plan or not user_sub.plan.can_watch:
        messages.warning(request, "Upgrade to Premium to watch episodes 🔒")
        return redirect("anime:subscription_plans")

    # ===============================
    # 1️⃣ FETCH ANIME DETAILS
    # ===============================
    anime_resp = requests.get(f"{JIKAN_BASE_URL}/anime/{mal_id}")
    if anime_resp.status_code != 200:
        raise Http404("Anime not found")

    anime_data = anime_resp.json().get("data", {})

    # ===============================
    # 2️⃣ FETCH EPISODE LIST (PAGINATED)
    # ===============================
    episodes = []
    try:
        page = 1
        while True:
            eps_resp = requests.get(
                f"{JIKAN_BASE_URL}/anime/{mal_id}/episodes",
                params={"page": page},
                timeout=8
            )
            if eps_resp.status_code != 200:
                break

            page_data = eps_resp.json().get("data", [])
            if not page_data:
                break

            for e in page_data:
                number = e.get("number") or e.get("mal_id") or e.get("id")
                title = e.get("title") or e.get("title_japanese") or f"Episode {number}"
                episodes.append({"number": number, "title": title})

            page += 1
            if page > 20:  # safety
                break
    except Exception:
        episodes = []

    # fallback so UI never breaks
    if not episodes:
        episodes = [{"number": i, "title": f"Episode {i}"} for i in range(1, 13)]

    # ===============================
    # 3️⃣ FETCH CURRENT EPISODE INFO
    # ===============================
    ep_data = None
    try:
        ep_resp = requests.get(
            f"{JIKAN_BASE_URL}/anime/{mal_id}/episodes/{episode_number}",
            timeout=6
        )
        if ep_resp.status_code == 200:
            ep_json = ep_resp.json().get("data")
            if ep_json:
                ep_data = {
                    "number": ep_json.get("number"),
                    "title": ep_json.get("title"),
                    "synopsis": ep_json.get("synopsis") or ""
                }
    except Exception:
        ep_data = None

    # ===============================
    # 4️⃣ VIDEO SOURCE (DEV MODE)
    # ===============================
    video_path = (
        "https://test-videos.co.uk/vids/"
        "bigbuckbunny/mp4/h264/720/Big_Buck_Bunny_720_10s_1MB.mp4"
    )

    # ===============================
    # 5️⃣ RENDER PAGE
    # ===============================
    context = {
        "anime": anime_data,
        "episodes": episodes,
        "episode": ep_data,
        "episode_number": episode_number,
        "video_path": video_path,
    }

    return render(request, "anime/watch_episode.html", context)

# Login & Register start

def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(
                request,
                username=user_obj.username,
                password=password
            )
        except User.DoesNotExist:
            user = None

        if user:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect("anime:home")

        messages.error(request, "Invalid email or password")

    return render(request, "auth/login.html")


def is_strong_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."

    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."

    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "Password must contain at least one special character."

    return True, ""

def register_view(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect("anime:register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return redirect("anime:register")

        # ✅ Create user
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name
        )

        # ✅ ASSIGN FREE SUBSCRIPTION (HERE 👇)
        try:
            free_plan = SubscriptionPlan.objects.get(name="Free")
            UserSubscription.objects.create(
                user=user,
                plan=free_plan
            )
        except SubscriptionPlan.DoesNotExist:
            
            pass

        # ✅ Login user
        login(request, user)
        messages.success(request, "Registration successful! Welcome to AnimeGeek ❤️")

        return redirect("anime:home")

    return render(request, "auth/register.html")


def logout_view(request):
    logout(request)
    return redirect("anime:home")


@login_required
def add_to_watchlist(request, mal_id):
    anime_resp = requests.get(f"{JIKAN_BASE_URL}/anime/{mal_id}")
    anime = anime_resp.json().get("data")

    WatchList.objects.get_or_create(
        user=request.user,
        mal_id=mal_id,
        defaults={
            "title": anime.get("title"),
            "image_url": anime.get("images", {}).get("jpg", {}).get("image_url", ""),
        }
    )

    messages.success(request, "Added to your watchlist ❤️")
    return redirect(request.META.get("HTTP_REFERER", "anime:home"))

@login_required
def remove_from_watchlist(request, mal_id):
    WatchList.objects.filter(user=request.user, mal_id=mal_id).delete()
    messages.success(request, "Removed from watchlist")
    return redirect("anime:watchlist")


@login_required
def watchlist(request):
    items = WatchList.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "anime/watchlist.html", {"items": items})


def trending(request):
    trending_anime = [
        {
            "rank": 1,
            "title": "One Piece",
            "image": "https://cdn.myanimelist.net/images/anime/6/73245.jpg",
        },
        {
            "rank": 2,
            "title": "My Hero Academia",
            "image": "https://cdn.myanimelist.net/images/anime/10/78745.jpg",
        },
        {
            "rank": 3,
            "title": "One Punch Man",
            "image": "https://cdn.myanimelist.net/images/anime/12/76049.jpg",
        },
        {
            "rank": 4,
            "title": "A Gatherer's Adventure",
            "image": "https://cdn.myanimelist.net/images/anime/11/127978.jpg",
        },
        {
            "rank": 5,
            "title": "My Status as an Assassin",
            "image": "https://cdn.myanimelist.net/images/anime/1408/127443.jpg",
        },
        {
            "rank": 6,
            "title": "My Gift Lvl 9999",
            "image": "https://cdn.myanimelist.net/images/anime/1463/127201.jpg",
        },
    ]

    return render(request, "anime/home.html", {
        "trending_anime": trending_anime
    })



def subscription_plans(request):
    plans = SubscriptionPlan.objects.all()

    if request.GET.get("cancelled"):
        messages.warning(
            request,
            "❌ Payment cancelled. You can upgrade anytime."
        )

    return render(request, "anime/subscriptions.html", {"plans": plans})

    

    


# @login_required
# def upgrade_subscription(request, plan_id):
#     plan = get_object_or_404(SubscriptionPlan, id=plan_id)

#     user_sub, created = UserSubscription.objects.get_or_create(
#         user=request.user,
#         defaults={"plan": plan}
#     )

#     user_sub.plan = plan
#     user_sub.save()

#     messages.success(request, f"Upgraded to {plan.name} plan 🎉")
#     return redirect("anime:subscription_plans")

@login_required
def upgrade_subscription(request, plan_id):
    
    request.session["plan_id"] = plan_id

    
    return redirect("anime:upgrade")



# payment gateway

@login_required
def create_payment(request):
    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    premium_plan = SubscriptionPlan.objects.get(name="Premium")

    payment = client.order.create({
        "amount": premium_plan.price * 100,  # ₹ → paise
        "currency": "INR",
        "payment_capture": 1
    })

    context = {
        "order_id": payment["id"],
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "amount": premium_plan.price * 100,
    }
    return render(request, "payments/checkout.html", context)

@login_required
def payment_success(request):
    plan_id = request.session.get("plan_id")
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)

    UserSubscription.objects.update_or_create(
        user=request.user,
        defaults={
            "plan": plan,
            "active": True
        }
    )

    messages.success(request, "🎉 Premium activated successfully!")

    return redirect("anime:subscription_plans")