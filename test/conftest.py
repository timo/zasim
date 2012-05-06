# make py.test use coredumps.

def pytest_sessionstart(*args, **kwargs):
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (-1, -1))
