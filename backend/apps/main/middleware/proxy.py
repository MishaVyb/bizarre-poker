from users.models import User, UserModel
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin

class UserProxyMiddleware(MiddlewareMixin):
    """Middleware for changing request user class to Proxy Model, so custom methods
    could be applied. Put the assignment in middleware after the authentication
    middleware and before any of my apps could reference it.
    """

    def process_request(self, request):
        if hasattr(request, 'user'):
            if isinstance(request.user, UserModel):
                request.user.__class__ = User
            elif isinstance(request.user, AnonymousUser):
                pass
            else:
                raise RuntimeError('request.user class is not UserModel')