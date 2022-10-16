from users.models import User, DjangoUserModel
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin

class UserProxyMiddleware(MiddlewareMixin):
    """
    Middleware for changing request user class to Proxy Model, so custom methods
    could be used. Put the assignment in middleware after the authentication
    middleware and before any of my apps could reference it.

    Note: DRF perform token authetication after all middlewares described at settings.py
    To change User class at request to API, perform_autetication at view will be used.
    """

    def process_request(self, request):
        if hasattr(request, 'user'):
            if isinstance(request.user, DjangoUserModel):
                request.user.__class__ = User
            elif isinstance(request.user, AnonymousUser):
                pass
            else:
                raise RuntimeError('Invaluid request.user class. ')