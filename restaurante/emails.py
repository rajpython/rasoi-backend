

# from django.conf import settings
# from djoser.email import PasswordResetEmail

# class CustomPasswordResetEmail(PasswordResetEmail):
#     def get_context_data(self):
#         context = super().get_context_data()
#         # Safely pull from DJOSER dict or fallback
#         djoser_config = getattr(settings, "DJOSER", {})
#         context["domain"] = djoser_config.get("DOMAIN") or "localhost:3000"
#         context["protocol"] = djoser_config.get("PROTOCOL") or "http"
#         context["site_name"] = djoser_config.get("SITE_NAME") or context["domain"]

#         return context

        # print("=== PASSWORD RESET EMAIL CONTEXT ===")
        # print("domain:", context["domain"])
        # print("protocol:", context["protocol"])
        # print("site_name:", context["site_name"])
        # print("===================================")

# from django.conf import settings
# from django.core.mail import EmailMultiAlternatives
# from django.template.loader import get_template
# from djoser.email import PasswordResetEmail
# import datetime

# class CustomPasswordResetEmail(PasswordResetEmail):
#     template_name = "email/password_reset.html"  # Explicitly set template

#     def get_context_data(self):
#         context = super().get_context_data()
#         djoser_config = getattr(settings, "DJOSER", {})
#         context["domain"] = djoser_config.get("DOMAIN") or "localhost:3000"
#         context["protocol"] = djoser_config.get("PROTOCOL") or "http"
#         context["site_name"] = djoser_config.get("SITE_NAME") or context["domain"]
#         context["frontend_url"] = f"{context['protocol']}://{context['domain']}"
#         context["now"] = datetime.datetime.now()
#         # Use 'user' or 'username' as appropriate for your template
#         context["user"] = context.get("user") or context.get("username") or "मेहमान"
#         return context

#     def send(self, to):
#         context = self.get_context_data()
#         subject = self.get_subject()
#         # from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER
#         from_email = settings.EMAIL_HOST_USER
#         html_content = get_template(self.template_name).render(context)
#         print("=== FINAL EMAIL RENDER ===")
#         print(html_content)
#         print("=== END RENDER ===")
#         email_message = EmailMultiAlternatives(
#             subject=subject,
#             body=html_content,  # fallback body
#             from_email=from_email,
#             to=to
#         )
#         email_message.attach_alternative(html_content, "text/html")
#         email_message.send()


# from django.conf import settings
# from django.core.mail import EmailMultiAlternatives
# from django.template.loader import get_template
# from djoser.email import PasswordResetEmail
# import datetime

# class CustomPasswordResetEmail(PasswordResetEmail):
#     template_name = "email/password_reset.html"

#     def get_context_data(self):
#         context = super().get_context_data()
#         djoser_config = getattr(settings, "DJOSER", {})
#         context["domain"] = djoser_config.get("DOMAIN") or "localhost:3000"
#         context["protocol"] = djoser_config.get("PROTOCOL") or "http"
#         context["site_name"] = djoser_config.get("SITE_NAME") or context["domain"]
#         context["frontend_url"] = f"{context['protocol']}://{context['domain']}"
#         context["now"] = datetime.datetime.now()

#         # Robust user stringification
#         user_val = context.get("user")
#         if hasattr(user_val, "get_username"):
#             user_str = user_val.get_username()
#         elif user_val:
#             user_str = str(user_val)
#         else:
#             user_str = context.get("username") or "मेहमान"
#         context["user"] = user_str

#         print("=== PASSWORD RESET CONTEXT ===")
#         for k, v in context.items():
#             print(f"{k}: {v} ({type(v)})")
#         return context

#     def send(self, to):
#         context = self.get_context_data()
#         subject = self.get_subject()
#         from_email = settings.EMAIL_HOST_USER
#         html_content = get_template(self.template_name).render(context)
#         print("=== FINAL EMAIL RENDER ===")
#         print(html_content)
#         print("=== END RENDER ===")
#         email_message = EmailMultiAlternatives(
#             subject=subject,
#             body=html_content,
#             from_email=from_email,
#             to=to
#         )
#         email_message.attach_alternative(html_content, "text/html")
#         email_message.send()


from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template, render_to_string
from djoser.email import PasswordResetEmail
import datetime

class CustomPasswordResetEmail(PasswordResetEmail):
    template_name = "email/password_reset_chat.html"
    subject_template_name = "email/password_reset_subject.txt"  # Optional, recommended

    def get_context_data(self):
        context = super().get_context_data()
        djoser_config = getattr(settings, "DJOSER", {})
        context["domain"] = djoser_config.get("DOMAIN") or "localhost:3000"
        context["protocol"] = djoser_config.get("PROTOCOL") or "http"
        context["site_name"] = djoser_config.get("SITE_NAME") or context["domain"]
        context["frontend_url"] = f"{context['protocol']}://{context['domain']}"
        context["now"] = datetime.datetime.now()
        context["photo_link"] = f"{settings.BACKEND_URL}/static/img/bannocopy.jpg"
        context["photo_chat"] = f"{settings.BACKEND_URL}/static/img/chaatGPT-logo.png"

        # Make sure 'user' is a string, not a User object
        user_val = context.get("user")
        if hasattr(user_val, "get_username"):
            user_str = user_val.get_username()
        elif user_val:
            user_str = str(user_val)
        else:
            user_str = context.get("username") or "मेहमान"
        context["user"] = user_str

        return context

    def get_subject(self, context):
        # Use template if available, else fallback
        try:
            subject = render_to_string(self.subject_template_name, context).strip()
        except Exception:
            subject = "धन्नो बन्नो की रसोई: पासवर्ड रिसेट लिंक"
        return subject

    def send(self, to):
        context = self.get_context_data()
        subject = self.get_subject(context)
        # from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.EMAIL_HOST_USER
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
        html_content = get_template(self.template_name).render(context)
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=html_content,  # fallback body for old clients
            from_email=from_email,
            to=to
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send()



#IF IN CASE ONE WANTS TO REVISIT THE TEMPLATES



# from django.conf import settings
# from djoser.email import PasswordResetEmail
# from django.utils import timezone

# class CustomPasswordResetEmail(PasswordResetEmail):
#     def get_context_data(self):
#         context = super().get_context_data()
#         context["frontend_url"] = settings.FRONTEND_URL
#         context["username"] = self.context.get("user").get_username()
#         context["now"] = timezone.now()
#         print("=== LIVE CONTEXT ===")
#         for key, value in context.items():
#             print(f"{key}: {value}")
#         print("=== END CONTEXT ===")
#         return context

# restaurante/emails.py



# from django.conf import settings
# from django.utils import timezone
# from djoser.email import PasswordResetEmail
# from django.core.mail import EmailMultiAlternatives

# class CustomPasswordResetEmail(PasswordResetEmail):
#     def get_context_data(self):
#         context = super().get_context_data()
#         context["frontend_url"] = settings.FRONTEND_URL
#         context["username"] = self.context.get("user")
#         context["now"] = timezone.now()
#         return context

#     def get_email_message(self, to):
#         context = self.get_context_data()
#         html_content = self.template.render(context)
#         subject = self.get_subject()
#         print("=== ACTUAL EMAIL BEING SENT ===")
#         print(html_content)
#         print("=== END ===")
#         message = EmailMultiAlternatives(subject=subject, body=html_content, to=to)
#         message.attach_alternative(html_content, "text/html")
#         return message

#     # def send(self, to):
#     #     context = self.get_context_data()
#     #     html_content = self.template.render(context)
#     #     subject = self.get_subject()
#     #     from_email = settings.DEFAULT_FROM_EMAIL

#     #     print("=== FINAL EMAIL RENDER ===")
#     #     print(html_content)
#     #     print("=== END RENDER ===")

#     #     # Create email with BOTH plain + HTML (fallback)
#     #     email_message = EmailMultiAlternatives(
#     #         subject=subject,
#     #         body=html_content,  # fallback body
#     #         from_email=from_email,
#     #         to=to
#     #     )
#     #     email_message.attach_alternative(html_content, "text/html")
#     #     email_message.send()
