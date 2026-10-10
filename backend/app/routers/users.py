from fastapi import APIRouter, Depends

from app.utils.auth import get_current_user


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user),
):
    """Return authenticated user's information."""

    return {
        "success": True,
        "user": {
            "id": current_user["sub"],
            "email": current_user.get("email"),
            "role": current_user.get("role"),
            "aal": current_user.get("aal"),
            "session_id": current_user.get("session_id"),
        },
    }