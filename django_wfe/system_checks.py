import os
import tempfile

from django.conf import settings
from django.core import checks

from .tasks import test_dramatiq
from .settings import WFE_LOG_DIR


REQUIRED_SETTINGS = [
    "WFE_WORKFLOWS",
]

IMPORTANT_OPTIONAL_SETTINGS = []


# DJANGO-WFE CHECK MESSAGES:

# django_wfe.config:
class MissingSettingsError(checks.Error):
    def __init__(self, setting_name, *args, **kwargs):
        super().__init__(
            f'django-wfe settings error: "{setting_name}" not found in django.conf.settings',
            hint=f'Please add "{setting_name}" to your settings.py file',
            obj=settings,
            id="django_wfe.config.E001",
            *args,
            **kwargs,
        )


class MissingSettingsInfo(checks.Info):
    def __init__(self, setting_name, *args, **kwargs):
        super().__init__(
            f'django-wfe settings info: "{setting_name}" was not defined, a default value will be used.',
            obj=settings,
            id="django_wfe.config.I001",
            *args,
            **kwargs,
        )


# django_wfe.dramatiq:
class DramatiqProblemWarning(checks.Warning):
    def __init__(self, dramatiq_exception, *args, **kwargs):
        super().__init__(
            f"Sending a task to dramatiq finished with {type(dramatiq_exception).__name__}: {dramatiq_exception}",
            hint="Please check dramatiq and the broker are set up and are working correctly",
            obj=settings,
            id="django_wfe.dramatiq.W001",
            *args,
            **kwargs,
        )


# django_wfe.logs
class LogDirNoneError(checks.Error):
    def __init__(self, *args, **kwargs):
        super().__init__(
            f"Django WFE log directory is not defined (WFE_LOG_DIR is None).",
            # hint="Remember you can define logs directory explicitly with WFE_LOGS_PATH setting.",
            hint="Please specify BASE_DIR or WFE_LOG_DIR Django setting.",
            obj=settings,
            id="django_wfe.logs.E001",
            *args,
            **kwargs,
        )


class LogDirNotDirError(checks.Error):
    def __init__(self, *args, **kwargs):
        super().__init__(
            f"Django WFE log directory ({WFE_LOG_DIR}) exists in the file system, but is not a directory.",
            hint=f"Please check WFE_LOG_DIR setting, explicitly define or change it to point at a directory.",
            obj=settings,
            id="django_wfe.logs.E002",
            *args,
            **kwargs,
        )


class LogDirParentDoesNotExistError(checks.Error):
    def __init__(self, *args, **kwargs):
        super().__init__(
            f"Django WFE parent of the log directory ({WFE_LOG_DIR}) does not exist.",
            hint=f"Make sure all parents exist for the {WFE_LOG_DIR}.",
            obj=settings,
            id="django_wfe.logs.E003",
            *args,
            **kwargs,
        )


class LogDirPermissionError(checks.Error):
    def __init__(self, path, *args, **kwargs):
        super().__init__(
            f"Permission denied for creating {path} in the file system.",
            hint=f"Please grant proper privileges on the {path}.",
            obj=settings,
            id="django_wfe.logs.E004",
            *args,
            **kwargs,
        )


class LogDirOtherError(checks.Error):
    def __init__(self, action, error, *args, **kwargs):
        super().__init__(
            f"Django WFE log failed on: {action}, with an error: {error}",
            obj=settings,
            id="django_wfe.logs.E005",
            *args,
            **kwargs,
        )


# DJANGO-WFE SYSTEM CHECKS:


@checks.register()
def settings_check(app_configs, **kwargs):
    errors = []

    for setting_name in REQUIRED_SETTINGS:
        try:
            getattr(settings, setting_name)
        except AttributeError:
            errors.append(MissingSettingsError(setting_name))

    for setting_name in IMPORTANT_OPTIONAL_SETTINGS:
        try:
            getattr(settings, setting_name)
        except AttributeError:
            errors.append(MissingSettingsInfo(setting_name))

    return errors


@checks.register()
def dramatiq_check(app_configs, **kwargs):
    errors = []

    try:
        test_dramatiq.send()
    except Exception as e:
        errors.append(DramatiqProblemWarning(e))

    return errors


@checks.register()
def log_dir_check(app_configs, **kwargs):
    errors = []

    # check if WFE_LOG_DIR is defined
    if WFE_LOG_DIR is None:
        errors.append(LogDirNoneError())

    else:

        check_dir_writability = True

        if os.path.exists(WFE_LOG_DIR):
            # if WFE_LOG_DIR exists in the file system, make sure it's a directory
            if not os.path.isdir(WFE_LOG_DIR):
                errors.append(LogDirNotDirError)
                check_dir_writability = False
        else:
            # try to create a log directory, if it does not exist
            try:
                os.mkdir(WFE_LOG_DIR)
            except FileNotFoundError:
                errors.append(LogDirParentDoesNotExistError())
                check_dir_writability = False
            except PermissionError:
                errors.append(LogDirPermissionError(WFE_LOG_DIR))
                check_dir_writability = False
            except Exception as e:
                errors.append(
                    LogDirOtherError(
                        action="Log directory creation failed with an exception",
                        error=f"{type(e).__name__}: {e}",
                    )
                )
                check_dir_writability = False

        if check_dir_writability:
            # check writability of the WFE_LOG_DIR
            try:
                with tempfile.NamedTemporaryFile(dir=WFE_LOG_DIR) as tmp_file:
                    with open(tmp_file.name, "w") as file:
                        file.write("Some random string.")

            except PermissionError:
                errors.append(
                    LogDirPermissionError(os.path.join(WFE_LOG_DIR, "tempfile"))
                )
            except Exception as e:
                errors.append(
                    LogDirOtherError(
                        action="Creation of the logfile failed",
                        error=f"{type(e).__name__}: {e}",
                    )
                )

    return errors
