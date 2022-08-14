import wrapt

@wrapt.when_imported('jinja2')
def patch(jinja2):
    import markupsafe
    try:
        getattr(jinja2, 'Markup')
    except:
        setattr(jinja2, 'Markup', markupsafe.Markup)
