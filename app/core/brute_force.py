import time
import threading
from collections import deque
from fastapi import HTTPException, status

MAX_FAILED_PER_ACCOUNT = 5       # Lock account after 5 consecutive bad passwords
ACCOUNT_LOCKOUT_SECONDS = 900    # 15 minutes lockout
MAX_FAILED_PER_IP = 10           # Lock IP after 10 bad attempts across any accounts
IP_LOCKOUT_SECONDS = 900         # 15 minutes IP jail
FAILURE_WINDOW_SECONDS = 600     # 10 minutes sliding evaluation window


class BruteForceProtector:
    """Enterprise-grade brute force and credential stuffing defense.
    
    Protects both:
    1. Targeted user accounts against password guessing/dictionary attacks.
    2. IP addresses against distributed password-spraying attacks.
    """

    def __init__(self):
        self._account_failures: dict[str, deque[float]] = {}
        self._account_locks: dict[str, float] = {}
        self._ip_failures: dict[str, deque[float]] = {}
        self._ip_locks: dict[str, float] = {}
        self._lock = threading.Lock()
        self._last_prune = time.monotonic()

    def check_lockout(self, ip: str, email: str | None = None) -> None:
        """Raises HTTPException(429) if either the IP or the account is currently locked."""
        now = time.monotonic()
        with self._lock:
            self._prune_locked(now)

            # Check network IP lock
            ip_unlock = self._ip_locks.get(ip)
            if ip_unlock and now < ip_unlock:
                rem_seconds = int(ip_unlock - now) + 1
                rem_mins = max(1, (rem_seconds + 59) // 60)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed login attempts from this network. Temporarily blocked for security. Please try again in {rem_mins} minute(s)."
                )

            # Check specific user account lock
            if email:
                clean_email = email.strip().lower()
                acct_unlock = self._account_locks.get(clean_email)
                if acct_unlock and now < acct_unlock:
                    rem_seconds = int(acct_unlock - now) + 1
                    rem_mins = max(1, (rem_seconds + 59) // 60)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many consecutive failed login attempts for this account. Account is temporarily locked for security. Please try again in {rem_mins} minute(s)."
                    )

    def record_failure(self, ip: str, email: str | None = None) -> None:
        """Records a failed authentication attempt for both IP and target account."""
        now = time.monotonic()
        with self._lock:
            # 1. Track IP failures
            ip_dq = self._ip_failures.setdefault(ip, deque())
            ip_dq.append(now)
            cutoff = now - FAILURE_WINDOW_SECONDS
            while ip_dq and ip_dq[0] <= cutoff:
                ip_dq.popleft()
            if len(ip_dq) >= MAX_FAILED_PER_IP:
                self._ip_locks[ip] = now + IP_LOCKOUT_SECONDS
                ip_dq.clear()

            # 2. Track targeted account failures
            if email:
                clean_email = email.strip().lower()
                acct_dq = self._account_failures.setdefault(clean_email, deque())
                acct_dq.append(now)
                while acct_dq and acct_dq[0] <= cutoff:
                    acct_dq.popleft()
                if len(acct_dq) >= MAX_FAILED_PER_ACCOUNT:
                    self._account_locks[clean_email] = now + ACCOUNT_LOCKOUT_SECONDS
                    acct_dq.clear()

    def record_success(self, ip: str, email: str | None = None) -> None:
        """Clears failure counters upon successful authentication."""
        with self._lock:
            if email:
                clean_email = email.strip().lower()
                self._account_failures.pop(clean_email, None)
                self._account_locks.pop(clean_email, None)
            ip_dq = self._ip_failures.get(ip)
            if ip_dq:
                ip_dq.popleft()
                if not ip_dq:
                    self._ip_failures.pop(ip, None)

    def _prune_locked(self, now: float) -> None:
        if now - self._last_prune < 60.0:
            return
        self._last_prune = now
        cutoff = now - FAILURE_WINDOW_SECONDS
        for storage in (self._account_failures, self._ip_failures):
            stale_keys = []
            for k, dq in storage.items():
                while dq and dq[0] <= cutoff:
                    dq.popleft()
                if not dq:
                    stale_keys.append(k)
            for k in stale_keys:
                storage.pop(k, None)


protector = BruteForceProtector()
