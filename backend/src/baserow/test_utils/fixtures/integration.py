from baserow.contrib.integrations.local_baserow.models import LocalBaserowIntegration


class IntegrationFixtures:
    def create_local_baserow_integration(self, **kwargs):
        if not kwargs.get("authorized_user", None):
            if not kwargs.get("user", None):
                kwargs["user"] = self.create_user()

            kwargs["authorized_user"] = kwargs["user"]

        integration = self.create_integration(LocalBaserowIntegration, **kwargs)
        return integration

    def create_integration(self, model_class, user=None, application=None, **kwargs):
        if not application:
            if user is None:
                user = self.create_user()

            application_args = kwargs.pop("application_args", {})
            application = self.create_builder_application(user=user, **application_args)

        if "order" not in kwargs:
            kwargs["order"] = model_class.get_last_order(application)

        integration = model_class.objects.create(application=application, **kwargs)

        return integration
