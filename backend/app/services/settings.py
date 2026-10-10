from fastapi import HTTPException, status

from app.services.supabase import supabase


def get_profile(current_user: dict):
    """
    Return the currently authenticated user's profile.
    """

    user_id = current_user.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing.",
        )

    try:
        response = supabase.auth.admin.get_user_by_id(user_id)

        user = getattr(response, "user", None)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found.",
            )

        user_metadata = user.user_metadata or {}

        return {
            "id": str(user.id),
            "email": user.email,
            "full_name": (
                user_metadata.get("full_name")
                or user_metadata.get("name")
                or ""
            ),
            "role": user_metadata.get("role"),
            "email_confirmed": bool(user.email_confirmed_at),
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to load profile: {str(exc)}",
        )


def update_profile(
    current_user: dict,
    full_name: str,
):
    """
    Update the authenticated user's name.
    """

    user_id = current_user.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing.",
        )

    full_name = full_name.strip()

    if len(full_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must contain at least 2 characters.",
        )

    try:
        response = supabase.auth.admin.update_user_by_id(
            user_id,
            {
                "user_metadata": {
                    "full_name": full_name,
                }
            },
        )

        user = getattr(response, "user", None)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Profile update failed.",
            )

        user_metadata = user.user_metadata or {}

        return {
            "success": True,
            "message": "Name updated successfully.",
            "profile": {
                "id": str(user.id),
                "email": user.email,
                "full_name": (
                    user_metadata.get("full_name")
                    or user_metadata.get("name")
                    or full_name
                ),
                "role": user_metadata.get("role"),
                "email_confirmed": bool(user.email_confirmed_at),
            },
        }

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to update name: {str(exc)}",
        )


def change_password(
    current_user: dict,
    current_password: str,
    new_password: str,
    confirm_password: str,
):
    """
    Change the authenticated user's password.

    The current password is verified first.
    """

    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation password do not match.",
        )

    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    user_id = current_user.get("sub")
    email = current_user.get("email")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user information is incomplete.",
        )

    try:
        # First verify the existing password.
        verification = supabase.auth.sign_in_with_password(
            {
                "email": email,
                "password": current_password,
            }
        )

        if not getattr(verification, "user", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )

        # Update password using Supabase Admin API.
        supabase.auth.admin.update_user_by_id(
            user_id,
            {
                "password": new_password,
            },
        )

        return {
            "success": True,
            "message": "Password changed successfully.",
        }

    except HTTPException:
        raise

    except Exception as exc:
        error_message = str(exc).lower()

        if (
            "invalid login credentials" in error_message
            or "invalid_credentials" in error_message
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to change password: {str(exc)}",
        )