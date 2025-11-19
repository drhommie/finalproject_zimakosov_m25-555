from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Optional

from .logging_config import get_actions_logger

FuncType = Callable[..., Any]


def log_action(
    action: Optional[str] = None,
    *,
    verbose: bool = False,
) -> Callable[[FuncType], FuncType]:
    """Декоратор для логирования доменных операций.

    Логируем на уровне INFO структуру:
    - timestamp (через форматтер логгера)
    - action (BUY/SELL/REGISTER/LOGIN)
    - username или user_id
    - currency_code, amount
    - rate и base (если применимо)
    - result (OK/ERROR)
    - error_type и error_message при исключениях

    Декоратор не глотает исключения — только фиксирует их в логах.
    """

    def decorator(func: FuncType) -> FuncType:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_actions_logger()
            act = action or func.__name__.upper()

            user = kwargs.get("user")
            username: Optional[str] = None
            user_id: Optional[int] = None

            if user is not None:
                username = getattr(user, "username", None)
                user_id = getattr(user, "user_id", None)
            else:
                if "username" in kwargs:
                    username = str(kwargs["username"])

            user_repr = None
            if username is not None:
                user_repr = f"user='{username}'"
            elif user_id is not None:
                user_repr = f"user_id={user_id}"
            else:
                user_repr = "user=<anonymous>"

            currency = kwargs.get("currency_code") or kwargs.get("from_currency")
            base = kwargs.get("base_currency") or kwargs.get("to_currency")
            amount = kwargs.get("amount")

            try:
                result = func(*args, **kwargs)

                rate: Optional[float] = None
                estimated: Optional[float] = None
                wallet_context: str = ""

                if isinstance(result, dict):
                    raw_rate = result.get("rate")
                    if isinstance(raw_rate, (int, float)):
                        rate = float(raw_rate)
                    raw_est = result.get("estimated_value")
                    if isinstance(raw_est, (int, float)):
                        estimated = float(raw_est)

                    if verbose:
                        old_balance = result.get("old_balance")
                        new_balance = result.get("new_balance")
                        if isinstance(old_balance, (int, float)) and isinstance(
                            new_balance,
                            (int, float),
                        ):
                            wallet_context = (
                                f" wallet='{old_balance:.4f}→{new_balance:.4f}'"
                            )

                amount_repr = (
                    f"{float(amount):.4f}" if isinstance(amount, (int, float)) else "-"
                )
                rate_repr = f"{rate:,.2f}" if rate is not None else "-"
                est_repr = f"{estimated:,.2f}" if estimated is not None else "-"

                msg = (
                    f"{act} {user_repr} currency='{currency or '-'}' "
                    f"amount={amount_repr} rate={rate_repr} base='{base or '-'}' "
                    f"estimated={est_repr} result=OK{wallet_context}"
                )
                logger.info(msg)
                return result
            except Exception as exc:  # noqa: BLE001
                error_type = type(exc).__name__
                error_message = str(exc)

                amount_repr = (
                    f"{float(amount):.4f}" if isinstance(amount, (int, float)) else "-"
                )
                msg = (
                    f"{act} {user_repr} currency='{currency or '-'}' "
                    f"amount={amount_repr} base='{base or '-'}' "
                    f"result=ERROR error_type='{error_type}' "
                    f"error_message='{error_message}'"
                )
                logger.error(msg)
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
