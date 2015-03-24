# If Config is None all calls to ConfigProxy will fail with AttributeError
# but there is no way to inspect for it
Config = None

class ConfigProxy:

    def __getattr__(self, attrname):
        return getattr(Config, attrname)

