from django.urls import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from app.core.models import Notification, UserNotificationPreference

User = get_user_model()


@override_settings(
    NOTIFICATION_REDIS_TTL_SECONDS=3600,
    SYSTEM_NOTIFICATION_USER_COOLDOWN_SECONDS=3600,
)
class AuthAndViewsTests(TestCase):
    def setUp(self):
        self.password = "StrongPass123!"
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password=self.password,
        )

    def test_home_landing_allows_authenticated(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NotifyHub")

    def test_home_landing_shows_signup_for_anonymous(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Регистрация")
        self.assertContains(response, "Войти")

    def test_home_landing_shows_dashboard_link_when_authenticated(self):
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "В кабинет")

    def test_email_login_success(self):
        response = self.client.post(
            reverse("email-login"),
            {"email": "test@example.com", "password": self.password},
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("dashboard"))

    def test_dashboard_requires_auth(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.url)

    def test_toggle_preferences(self):
        self.client.login(username=self.user.username, password=self.password)
        response = self.client.post(
            reverse("toggle-preference"),
            {"key": "marketing_enabled", "value": "true"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            response.content,
            {
                "status": "success",
                "ok": True,
                "data": {"key": "marketing_enabled", "value": True},
            },
        )
        prefs = UserNotificationPreference.objects.get(user=self.user)
        self.assertTrue(prefs.marketing_enabled)

    def test_mark_notification_read(self):
        self.client.login(username=self.user.username, password=self.password)
        notification = Notification.objects.create(
            user=self.user,
            title="Test",
            message="Body",
            level="info",
        )
        response = self.client.post(
            reverse("read-notification", kwargs={"notification_id": notification.id})
        )
        self.assertEqual(response.status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
