# django-distill

**WORK IN PROGRESS, DO NOT USE**

`django-distill` is a minimal configuration static site generator and publisher
for Django.

`django-distill` extends existing Django sites with the ability to export
fully functional static sites. It is suitable for sites such as blogs that have
a mostly static front end but you still want to use a CMS to manage the
content.

It plugs directly into the existing Django framework without the need to write
custom renderers or other more verbose code.

# Installation

Install from pip:

```bash
$ pip install --upgrade git+git://github.com/meeb/django-distill.git@master
```

Add `django_distill` to your `INSTALLED_APPS` in your `settings.py`:

```python
INSTALLED_APPS += ('django_distill',)
```

# Usage

Assuming you have an existing Django project, edit a `urls.py` to include the
`distill_url` function which replaces the existing `url` function and supports
a new keyword argument `distill`. The `distill` argument should be provided with
a function that returns an iterable. An example for a theoretical blogging app:

```python
# replaces the standard django.conf.urls.url, identical syntax
from django_distill import distill_url

from django.conf.urls import patterns
from blog.views import PostView, PostYear
from blog.models import Post

# /post/123-some-post-title
urlpatterns = patterns('blog',
    distill_url(r'^post/(?P<blog_id>[\d]+)-(?P<blog_title>[\w]+)$',
                PostView.as_view(),
                name='blog-post',
                distill=get_all_blogposts),
    distill_url(r'^posts-by-year/(?P<year>[\d]{4}))$',
                PostYear.as_view(),
                name='blog-year',
                distill=get_years),
)

def get_all_blogposts():
    # This function needs to return an iterable in the format of:
    # [(blog_id, blog_title), (blog_id, blog_title), ...]
    # to match the URL above that accepts two URL arguments.
    # You can just export a small subset of values here if you wish to
    # limit what pages will be generated.
    for post in Post.objects.all():
        yield (post.id, post.title)

def get_years():
    # You can also just return an iterable containing static strings. If the
    # URL only has one argument you can use a flat tuple or list:
    return ('2014', '2015')
```

Your site will still function identically with the above changes, however you
can now generate a complete functioning static site with:

```bash
$ ./manage.py distill-local [optional /path/to/export/directory]
```

Under the hood this simply iterates all URLs registered with `distill_url` and
generates the pages for them using `reverse` and then copies over the static
files. Existing files with the same name are replaced in the target directory.

# Configuration settings

You can set the following optional `settings.py` variables to speed up usage:

**DISTILL_DIR**: string, default directory to export to:

```python
DISTILL_DIR = '/path/to/export/directory'
```

**DISTILL_PUBLISH**: dictionary, like Django's `DATABASES`, supports `default`:

```python
DISTILL_PUBLISH = {
    'default': {
        ... options ...
    },
    'some-other-target': {
        ... options ...
    },
}
```

# Publishing sites

You can automatically publish sites to various supported remote targets through
back ends, very similar to how you can use MySQL, SQLite, PostgreSQL etc. with
Django by changing the back end engine. Currently the engines supported in
`django-distill` are:

**django_distill.backends.ftp**: Publish to an FTP server. Requires the Python
  library `ftplib`. Options:

```python
'ftp-publish-target': {
    'ENGINE': 'django_distill.backends.ftp',
    'PUBLIC_URL': 'http://.../',
    'PORT': 21,                 # optional, the default
    'TIMEOUT': 60,              # optional, the default, timeout in seconds
    'PASSIVE': False,           # optional, the default
    'HOSTNAME': '...',
    'USERNAME': '...',
    'PASSWORD': '...',
    'REMOTE_DIRECTORY': '...',  # path to remote web root, such as /docs/
},
```

**django_distill.backends.ftp_tls**: Publish to an FTP server with TLS
  support. Requires the Python library `ftplib`. Options:

```python
'ftp_tls-publish-target': {
    'ENGINE': 'django_distill.backends.ftp_tls',
    'PUBLIC_URL': 'http://.../',
    'PORT': 21,                 # optional, the default
    'TIMEOUT': 60,              # optional, the default, timeout in seconds
    'HOSTNAME': '...',
    'USERNAME': '...',
    'PASSWORD': '...',
    'REMOTE_DIRECTORY': '...',  # path to remote web root, such as /docs/
    'CONTEXT': ssl_context,     # optional, an ssl.SSLContext object to validate
                                # certificates with etc.
},
```

**django_distill.backends.amazon_s3**: Publish to an an Amazon S3 bucket.
  Requires the Python library `s3` (`$ pip install s3`). Options:

```python
's3-target': {
    'ENGINE': 'django_distill.backends.amazon_s3',
    'PUBLIC_URL': 'http://.../',
    'ACCESS_KEY_ID': '...',
    'SECRET_ACCESS_KEY': '...',
    'BUCKET': '...',
    'ENDPOINT': '...',
},
```

**django_distill.backends.rackspace_files**: Publish to an a Rackspace Cloud
  Files container.  Requires the Python library `pyrax` (`$ pip install pyrax`).
  Options:

```python
'some-rackspace-container':
    'ENGINE': 'django_distill.backends.rackspace_files',
    'PUBLIC_URL': 'http://.../',
    'USERNAME': '...',
    'API_KEY': '...',
    'REGION': '...',
    'CONTAINER': '...',
},
```

You can then publish the site with:

```bash
$ ./manage.py distill-publish [optional name here]
```

This will perform a full synchronisation, removing any remote files that are no
longer present in the generated static site and uploading any new or changed
files. The site will be built into a temporary directory locally first when
publishing. Each file will be checked that it has been published correctly by
requesting it via the `PUBLIC_URL`.

You can test your publishing target with:

```bash
$ ./manage.py distill-test-publish [optional name here]
```

This will connect to your publishing target, authenticate to it, upload a
randomly named file, verify it exists on the `PUBLIC_URL` and then delete it
again. Use this to check your publishing settings are correct.
