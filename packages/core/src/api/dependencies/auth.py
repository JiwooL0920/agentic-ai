"""Authentication dependencies."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status


class User:
    def __init__(self, user_id: str, email: str | None = None):
        self.user_id = user_id
        self.email = email


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        if token == "invalid":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return User(user_id=f"user_{token[:8]}", email=None)

    return User(user_id="anonymous", email=None)


CurrentUser = Annotated[User, Depends(get_current_user)]
