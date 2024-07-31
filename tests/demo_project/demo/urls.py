from django.urls import path
from ninja import NinjaAPI
from someapp.api import router

api_v1 = NinjaAPI()
api_v1.add_router("/", router)

urlpatterns = [
    path("api/", api_v1.urls),
]
